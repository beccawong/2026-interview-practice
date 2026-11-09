# Crossword Solver: scaling past one machine

## 1. Frame the problem
- A crossword is a **constraint-satisfaction problem**. Slots are the variables, words of the right length are the domains, and crossing cells are binary constraints. Words are also globally unique (an all-different constraint).
- It is NP-hard in general, so we can't promise speed for every puzzle. The thing that matters is the structure of the **constraint graph** (nodes = slots, edges = crossings). Real grids are planar and locally connected: a slot only crosses its neighbours.
- "Too big for one machine" can mean one of two things. Ask which:
  1. **Memory**: the grid or dictionary doesn't fit. Example: a 100k × 100k grid is 10^10 cells, and the slots/crossings index alone is tens of GB.
  2. **Compute**: it fits, but the search tree is huge.
  The answers differ. (1) needs partitioning. (2) needs parallel search.

## 2. Single-node baseline (what `cross_word.py` does)
- MRV + forward checking + a `(length, pos, letter) → words` index. In production, store it as bitsets/roaring bitmaps so candidate lookup is a bitwise AND.
- Every distributed design below reuses this solver as the **worker kernel**.

## 3. Architecture
```
Client ─► API Gateway ─► Job Service ──► Job DB (status, metadata)
                              │
                              ▼
                        Partitioner ──► Object store (board tiles, slot graph)
                              │
                              ▼
                   Task queue (Kafka / SQS)
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Solver worker    Solver worker    Solver worker   (stateless, autoscaled)
             │  ▲             │  ▲             │  ▲
             ▼  │             ▼  │             ▼  │
     Boundary/coordination store (etcd / Redis / FoundationDB)
             │
             ▼
        Coordinator / Merger ──► Result store ──► Client (poll or webhook)
```
- **Dictionary service**: shard by word length (a partition only needs the lengths it contains). Every worker keeps a read-only copy of the bitset index for its lengths; it's built once and cached.
- Jobs are async: submit → `job_id` → poll or webhook. Large puzzles can take minutes to hours.

## 4. Partitioning strategy
Partition the **constraint graph**, not raw pixels:
- **Spatial tiling** (simple): cut the grid into K×K tiles. A slot that crosses a tile boundary becomes a **boundary slot**. It's easy to reason about, but some slots get cut.
- **Graph partitioning** (better): run METIS-style min-edge-cut on the slot graph. The goal is to minimise **crossings between partitions** (the separator) while keeping partitions balanced. Fewer cut edges means less coordination.
- Prefer cutting along **black-square-heavy** regions. Long blocked runs are natural separators.
- Each partition gets: its interior slots, a read-only copy of the boundary slots it touches (halo), and the pre-filled letters.

### Clarification: what gets "cut"
- In **graph partitioning**, a slot is never split. Each whole slot belongs to exactly one partition. What gets cut is a **crossing (edge)**: an Across slot in P1 and a Down slot in P2 that share a cell.
- **Black-square runs need no special representation.** They show up as *missing edges*. A full row of `#` means no Down slot spans it, so nothing above that row crosses anything below it. The graph is naturally disconnected or sparse there, and a min-cut partitioner finds the gap by itself.
- Edge weights can bias the cut, e.g. weight crossings in long slots higher because they're harder to fix. Node weights (≈ slot length × domain size) keep partitions balanced by work, not by slot count.
- METIS (multilevel): **coarsen** (repeatedly merge tightly connected slots) → partition the small graph → **uncoarsen + refine** (Kernighan–Lin / Fiduccia–Mattheyses: move boundary nodes if that reduces the cut without unbalancing).
- **Cut crossing ownership**: the shared cell belongs to the partition that owns one side (rule: lower partition id). The owner assigns the letter. The other partition holds a **read-only halo copy** of the owner's slot (really just the shared cells) and treats those letters like pre-filled cells. If it can't fill its slots under them, it sends a nogood back to the owner instead of overwriting. (Ownership only matters for option B. In option A, both sides enumerate letters for the shared cells and the join picks a consistent pair.)
### Worked example (ASCII)

**Board** (`#` = black, `_` = empty; small numbers mark slot starts):
```
      c0  c1  c2  c3  c4  c5  c6  c7  c8
r0   1_   _  2_   #   #   #  3_   _  4_
r1    _   #   _   #   #   #   _   #   _
r2   5_   _   _   _   _   _   _   _   _      <- 5 Across: one 9-letter slot
r3    _   #   _   #   #   #   _   #   _
r4   6_   _   _   #   #   #  7_   _   _
```
**Slots** (9 nodes):
```
1A (r0,c0..2)  len 3      1D (c0, r0..4) len 5
3A (r0,c6..8)  len 3      2D (c2, r0..4) len 5
5A (r2,c0..8)  len 9      3D (c6, r0..4) len 5
6A (r4,c0..2)  len 3      4D (c8, r0..4) len 5
7A (r4,c6..8)  len 3
```
**Crossings** (12 edges, labelled by the shared cell):
```
1A-1D (0,0)   1A-2D (0,2)   1D-5A (2,0)   2D-5A (2,2)   1D-6A (4,0)   2D-6A (4,2)
3A-3D (0,6)   3A-4D (0,8)   3D-5A (2,6)   4D-5A (2,8)   3D-7A (4,6)   4D-7A (4,8)
```
**Constraint graph** (node = slot, edge = shared cell):
```
        LEFT CLUSTER                         RIGHT CLUSTER
     1A            6A                     3A            7A
     │  ╲        ╱  │                     │  ╲        ╱  │
     │    ╲    ╱    │                     │    ╲    ╱    │
     │      ╳       │                     │      ╳       │
     │    ╱    ╲    │                     │    ╱    ╲    │
     │  ╱        ╲  │                     │  ╱        ╲  │
     1D            2D                     3D            4D
     │              │                     │              │
     └──────────────┴──────── 5A ─────────┴──────────────┘
                     (2,0) (2,2)    (2,6) (2,8)
```
Same thing as an adjacency list:
```
1A: 1D, 2D            3A: 3D, 4D
6A: 1D, 2D            7A: 3D, 4D
5A: 1D, 2D, 3D, 4D    <- the only slot touching both sides
```
The black block at c3..c5 (rows 0,1,3,4) adds **no edges**. No Down slot exists in c3..c5, and no Across slot in rows 0/1/3/4 spans it. That missing connectivity is the "black-square run". The only thing crossing the gap is 5A.

**Good cut (2 cut edges)**: put 5A with the left side.
```
               P1                          ┆               P2
     1A            6A                      ┆   3A            7A
     │  ╲        ╱  │                      ┆   │  ╲        ╱  │
     │      ╳       │                      ┆   │      ╳       │
     │  ╱        ╲  │                      ┆   │  ╱        ╲  │
     1D            2D                      ┆   3D            4D
     │              │                      ┆   │              │
     └──────────────┴──────── 5A ──────────✂───┴──────────────┘
                                           ┆
   cut edges (2):  5A-3D @ (2,6),   5A-4D @ (2,8)
   P1 = {1A, 1D, 2D, 6A, 5A}  (weight ≈ 3+5+5+3+9 = 25)
   P2 = {3A, 3D, 4D, 7A}      (weight ≈ 3+5+5+3   = 16)
```
On the board, the partition boundary runs *between slots*, not through 5A:
```
      c0  c1  c2  c3  c4  c5 │c6  c7  c8
r0   P1  P1  P1   #   #   #  │P2  P2  P2
r1   P1   #  P1   #   #   #  │P2   #  P2
r2   P1  P1  P1  P1  P1  P1  P1* P1  P1*     <- 5A is whole, owned by P1
r3   P1   #  P1   #   #   #  │P2   #  P2
r4   P1  P1  P1   #   #   #  │P2  P2  P2

 *  (2,6) and (2,8): owned by P1 (5A decides the letters).
    P2 keeps a read-only halo copy of 5A: in practice just those 2 cells.
    To P2's solver, 3D and 4D look like they have pre-filled letters at row 2.
```

**Bad cut for contrast**: split by direction (all Across in P1, all Down in P2). Every crossing is Across×Down, so **all 12 edges are cut**. Every single letter would need cross-machine agreement. A min-cut partitioner would never choose this.

**Negotiation on the good cut (option B)**:
```
P1 solves 5A = "ABCDEFGHI"  ──publish v1: (2,6)=G, (2,8)=I──►  P2
P2: no 5-letter word with G at pos 2 for 3D  ──nogood{(2,6)=G}──► P1
P1 picks another 5A avoiding G at c6       ──publish v2────────► P2
P2 solves 3D, 4D, 3A, 7A under v2  ✓
```

- With **spatial tiling**, a slot *can* physically span two tiles. Assign the whole slot to one tile (e.g. the one containing its start cell), and the other tile sees those cells as halo. That's the same owner/reader model.

## 5. Solving across partitions: three options

### A. Decompose-and-join (best when separators are small)
1. Each worker solves its partition. Instead of returning one solution, it returns **the set of feasible boundary assignments** ("signatures": letters on the cut cells plus the words it used).
2. The coordinator **joins** neighbouring partitions' signature sets on the shared cells, like a database join or tree-decomposition DP. Done hierarchically (merge pairs, then pairs of pairs), it's a reduce tree.
3. Once a globally consistent combination is chosen, push it back down so each worker materialises its interior.
#### Option A walkthrough: 4 partitions, pairs, then pair of pairs

**Layout.** Four partitions. The cut crossings (shared cells) are named by the boundary they sit on:
```
 ┌─────────────┬─────────────┐
 │             x1            │      x1, x2 : cells shared by P1 | P2
 │     P1      x2     P2     │      y1, y2 : cells shared by P3 | P4
 │             │             │      u      : cell shared by P1 | P3
 ├──────u──────┼──────v──────┤      v      : cell shared by P2 | P4
 │             y1            │
 │     P3      y2     P4     │
 │             │             │
 └─────────────┴─────────────┘
```
**Reduce tree.** Pair partitions that share the **most** cut cells first, so most shared cells are eliminated early:
```
                     ROOT   join on {u, v}
                   ╱                ╲
     P12  join on {x1,x2}       P34  join on {y1,y2}
          ╱        ╲                 ╱        ╲
        P1          P2             P3          P4
     bnd{x1,x2,u} bnd{x1,x2,v}  bnd{u,y1,y2} bnd{v,y1,y2}
```

**Level 0: each worker enumerates signatures** (feasible letters on *its* boundary cells, plus a pointer to the interior solution):
```
 P1 (x1 x2 u)     P2 (x1 x2 v)     P3 (u y1 y2)     P4 (v y1 y2)
 s1: G  E  T      t1: G  E  N      r1: T  A  R      q1: N  A  R
 s2: R  S  A      t2: R  S  E      r2: A  O  K      q2: N  O  K
 s3: G  S  O      t3: M  S  N      r3: O  A  R      q3: E  O  K
```
All four run in parallel. None of them talks to the others.

> **What is s1 / t1 / r1 / q1?** IDs for one *complete, valid fill of that partition's interior*. The letter prefix just says which partition it came from (s=P1, t=P2, r=P3, q=P4). Each row is that fill **summarised by only the letters it puts on the shared cells**. The full fill stays cached on the worker. Only `(id, boundary letters, words used)` travels up the tree.
>
> Concrete, using the 9-column board above with P1 = {1A, 1D, 2D, 6A, 5A} (boundary cells (2,6), (2,8)):
> ```
>  fill s1                      fill s2
>  P E A # . . .                P E A # . . .
>  A # D # . . .                A # D # . . .
>  C R O S S W[O]R[D]           C R O S S W[A]L[K]
>  E # B # . . .                E # B # . . .
>  D Y E # . . .                D Y E # . . .
>  1A PEA 1D PACED 2D ADOBE     same, but 5A CROSSWALK
>  6A DYE 5A CROSSWORD
>  signature s1 = (O, D)        signature s2 = (A, K)
> ```
> Two fills with the same boundary letters are interchangeable to every other partition, so the worker keeps one per key (that dedupe is what keeps the lists small). The G/E/T letters in the 4-partition tables are placeholders.

**Level 1: join pairs on their shared cells, then project the shared cells away.**
```
 P1 ⋈ P2  on (x1,x2)                     P3 ⋈ P4  on (y1,y2)
 ───────────────────────────────          ───────────────────────────────
 s1 (G,E) + t1 (G,E)  ✓ → u=T v=N         r1 (A,R) + q1 (A,R)  ✓ → u=T v=N
 s2 (R,S) + t2 (R,S)  ✓ → u=A v=E         r3 (A,R) + q1 (A,R)  ✓ → u=O v=N
 s3 (G,S)   no match  ✗ dropped           r2 (O,K) + q2 (O,K)  ✓ → u=A v=N
 t3 (M,S)   no match  ✗ dropped           r2 (O,K) + q3 (O,K)  ✓ → u=A v=E

 P12 signatures over (u v):               P34 signatures over (u v):
   T N  ← [s1,t1]                           T N  ← [r1,q1]
   A E  ← [s2,t2]                           O N  ← [r3,q1]
                                            A N  ← [r2,q2]
                                            A E  ← [r2,q3]
```
After the join, x1/x2 and y1/y2 are **internal** to the merged block, so they're dropped from the key. Only the cells P12 shares with P34 (u, v) remain, plus back-pointers. The signature shrinks as you go up the tree. That's the whole trick (same idea as variable elimination / tree-decomposition DP).

**Level 2: root joins the pair of pairs on (u,v).**
```
 P12 ⋈ P34  on (u,v)
 ─────────────────────────────────────────────────────────────
 (T,N) [s1,t1] + (T,N) [r1,q1]  key ✓   word check ✗  (s1 and q1 both use "TIRE")
 (A,E) [s2,t2] + (A,E) [r2,q3]  key ✓   word check ✓  → SOLUTION
 (O,N), (A,N) from P34           no partner in P12 → dropped
```
Global word uniqueness is checked at each join by intersecting the word sets the signatures carry. Empty intersection = OK.

**Top-down: materialise.**
```
                ROOT picks (u=A, v=E)
               ╱                    ╲
     P12 → [s2, t2]              P34 → [r2, q3]
        ╱        ╲                  ╱        ╲
   P1: use s2   P2: use t2    P3: use r2   P4: use q3
   (x1=R,x2=S,u=A) ...        each worker writes out its cached interior fill
```
If the root finds **no** match, the leaves enumerate more signatures (they were capped at N) and the failing levels re-join. Only when every leaf is exhausted is the puzzle UNSAT.

**Where it can blow up**
```
 signatures at a node ≈ (alphabet)^(# shared cells) in the worst case
   2 shared cells → ≤ 26² = 676        fine
  10 shared cells → ≤ 26¹⁰ ≈ 1.4e14    infeasible → need narrow cuts (min-cut!)
```
That's why the partitioner minimises cut crossings: it directly bounds the size of everything that flows up this tree. Carrying full word sets also inflates signatures. In practice carry only the words of length ≥ k (short words rarely collide in big dictionaries, or are allowed to repeat), or fall back to optimistic dedupe + re-solve.

- Pros: embarrassingly parallel and deterministic. Cons: signature sets can blow up if the separator is wide. Mitigate by capping at N signatures per partition and re-requesting more on failure.

### B. Asynchronous negotiation (scales to huge boards)
- Every **boundary cell has exactly one owner** (e.g. the lower partition id). That is the rule for consistency at intersections.
- Owners propose letters/words for their boundary slots and publish them to the coordination store with a **version number**.
- Neighbours solve their interior under those proposals. If they can't, they send back a **nogood** ("letters X at cells Y are impossible for me"). The owner adds it as a constraint and re-proposes. This is Asynchronous Backtracking (ABT) from the distributed-CSP literature.
- Alternative: **min-conflicts local search**. Start from a full assignment, then let partitions repair boundary conflicts iteratively. It's fast in practice but not complete (it may not prove "no solution").

### C. Parallel search (when the problem fits in memory but the search is huge)
- Split the **search tree** instead of the board. The coordinator expands the top few MRV decisions into many subproblems ("slot 17 = TIRE, slot 4 = BATH, …"). Workers take them from a queue, with **work stealing** for balance.
- The first worker to find a solution wins and the others are cancelled. Workers share learned nogoods through a pub/sub channel.

In an interview I'd lead with **A for moderate boards and B for truly massive ones**, and mention C as orthogonal: you can run C inside each partition.

## 6. Consistency details
- **Intersection letters**: single owner per boundary cell, plus versioned writes (CAS on `cell → (letter, version)`). A worker's interior solution is valid only for the boundary version it was computed against. Stale results are discarded.
- **Global word uniqueness**: a sharded `word → partition_id` reservation table with compare-and-set. If a reservation fails, that word is excluded locally and the partition re-solves. Cheaper option: let partitions use words optimistically and dedupe at merge time, re-solving the losing partition.
- **Termination / "no solution"**: needed for completeness. The coordinator tracks outstanding work. If the root subproblem's nogood is derived (option B) or every subtree is exhausted (option C), the answer is UNSAT.

## 7. Fault tolerance and operations
- Workers are stateless. Each task is `(job_id, partition_id, boundary_version)`, so it's idempotent and safe to retry.
- Checkpoint partial assignments and learned nogoods to the object store so a crashed worker's replacement doesn't restart from zero.
- Timeouts plus speculative re-execution for stragglers (one hard partition shouldn't stall the job).
- Metrics: backtracks/sec per partition, boundary conflict rate, signature-set size, job latency. If a partition keeps conflicting, re-partition by merging it with its neighbour.

## 8. Trade-offs to call out
| Choice | Win | Cost |
|---|---|---|
| Graph partitioning vs tiling | fewer cut crossings | partitioning step is itself expensive |
| Decompose-and-join | simple, parallel, complete | signature blow-up on wide separators |
| Async negotiation | scales, low memory per node | chatty, harder to debug, needs termination detection |
| Optimistic word uniqueness | fewer round trips | wasted work on collisions |
| Local search | fast on easy/large grids | can't prove unsatisfiable |
