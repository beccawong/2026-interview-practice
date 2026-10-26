▗ ▗   ▖ ▖  Claude Code v2.1.310
           Opus 5.5 · Claude Pro
 ▘▘   ▝▝   ~/Development/2026-interview-practice/practice-coding


❯ Grade my work at @src/practice_coding/breadth_first_search.py. I am           
  practicing for interview                                                      
  ⎿  Read src/practice_coding/breadth_first_search.py (41 lines)

  Ran 1 shell command (ctrl+o to expand)

⏺ Bash(ls; uv run python --version && uv run python
      src/practice_coding/breadth_first_search.py && uv run python -c "
      import sys; sys.path.insert(0,'src')…)
  ⎿  pyproject.toml
     README.md
     src
     … +7 lines (ctrl+o to expand)
  ⎿  2 files changed (binary, mode only or too large to show)

⏺ Grade: B−

  The BFS itself is mostly right. The helper that builds the tree has a real
  bug, and your tests don't catch it. In an interview, the bug would probably be
  found when the interviewer asks you to walk through build_tree by hand.

  What's good

  - eq=False on the dataclass was a smart choice. It makes nodes hashable by
    identity, so they work in a set, and two nodes with the same value stay
    distinct. Many candidates miss this.
  - deque with popleft() gives O(1) dequeue. Using list.pop(0) instead is a
    common interviewer flag.
  - Typing is clean. The PEP 695 generics (Node[V], search[V]) work, and the
    return type Node | None is correct.
  - You check the goal when you dequeue. That's correct and returns the start
    node immediately when it matches.

  Bugs

  1. build_tree never adds new nodes to parents (line 26–32). This one is 
  serious.
  Nothing gets appended to parents. So when the root fills up, popleft() hands
  back the root again, and every later node becomes the root's child. I ran it
  to confirm:
  root children: [1, 2, 3, 4, 5, 6]
  You get a star, not a binary tree. Your tests still pass because BFS finds
  every node whatever the shape. The fix:
  def build_tree(values: list[int]) -> Node[int]:
      root = Node(values[0], [])
      parents = deque([root])
      for v in values[1:]:
          parent = parents[0]
          new_node = Node(v, [])
          parent.neighbors.append(new_node)
          parents.append(new_node)
          if len(parent.neighbors) == 2:
              parents.popleft()
      return root

  2. search marks nodes visited when they're dequeued, not when they're enqueued
  (line 18–19). Medium severity.
  On a tree this makes no difference. On a general graph, which is what
  neighbors suggests, the same node can be enqueued several times before it's
  processed. For example, A→B, A→C, B→D, C→D puts D in the queue twice. When a
  duplicate comes off the queue, nothing checks it against visited, so it gets
  processed again. The results stay correct, but the guarantee that each node is
  visited once, and therefore the O(V+E) bound, is gone. The standard pattern:
  to_visit = deque([start_node])
  visited = {start_node}
  while to_visit:
      current = to_visit.popleft()
      if current.val == search_value:
          return current
      for n in current.neighbors:
          if n not in visited:
              visited.add(n)
              to_visit.append(n)
  return None
  Be ready to explain why the mark has to happen at enqueue time. Interviewers
  ask about it a lot.

  Smaller points

  - Weak tests. You only searched for the root (0) and a missing value (9). The
    root case returns before the loop starts, so neither test exercises
    traversal. Add a search for a deep node (6), and a graph with a cycle (A↔B)
    to show that visited prevents infinite loops.
  - Module-level test code. The script code runs on import, which is why my
    import printed output. Put it under if __name__ == "__main__":.
  - visited = set() has no type parameter. set[Node[V]] would be more consistent
    with the rest of your typing.
  - extend([...]) builds a list you throw away. A generator or a plain loop is
    fine.
  - nodes is a vague name for a list of ints. values would be clearer.

  Interview tips

  Out loud, state the complexity (O(V+E) time, O(V) space). Mention that BFS
  finds the node closest to the start, which is what makes it the right choice
  over DFS for shortest paths in unweighted graphs. And trace your helper code
  against a small input before saying you're done. Bug #1 would have shown up
  after about three iterations.

✻ Sautéed for 31s · done 5:18 PM

※ recap: You're practicing for interviews, and I graded your BFS file a B−. Next, fix build_tree so new nodes get added to the parents queue, then mark nodes visited when you enqueue them in search. (disable recaps in /config)

❯ why the mark has to happen at enqueue time? that's different from depth first 
  search                                                                        

⏺ You're right that it's different from DFS, and I overstated it. In BFS the
  mark doesn't strictly have to happen at enqueue time. There are two correct
  patterns, and your code uses neither.

  Two correct BFS patterns

  A. Mark on enqueue (standard):
  visited = {start}
  ...
  for n in current.neighbors:
      if n not in visited:
          visited.add(n)
          to_visit.append(n)

  B. Mark on dequeue, but skip duplicates:
  current = to_visit.popleft()
  if current in visited:
      continue          # ← your code is missing this
  visited.add(current)

  Your code marks on dequeue without the skip. So a node that got into the queue
  twice is processed twice, and its neighbors are scanned twice. Here's a trace
  on A→B, A→C, B→D, C→D:

  pop A → visited {A}       queue [B, C]
  pop B → visited {A,B}     queue [C, D]
  pop C → D not visited yet queue [D, D]   ← duplicate
  pop D → process
  pop D → process again

  Both A and B give correct answers in O(V+E) time. A is preferred because each
  node enters the queue at most once, so the queue stays at O(V). With B, the
  queue can grow to O(E), which for a dense graph is O(V²).

  Why marking early is safe in BFS

  The BFS queue is ordered by distance from the start. So the first time you
  discover a node, you've reached it by a shortest path. Any later discovery is
  at the same distance or farther, so you lose nothing by locking the node in
  right away.

  Why DFS is different

  In DFS, the most recent discovery is the one that counts. DFS goes deep: if
  you reach a node through a longer path before you get back to it the short
  way, that longer path is the one real DFS follows.

  Iterative DFS with a stack therefore marks on pop, with the same "skip if
  already visited" check as pattern B. If you marked on push, a node pushed
  early by a shallow parent would be locked. When you later reached it from
  deeper in the graph, you'd skip it.

  A → [B, C],  C → [D],  D → [B]

  Mark on push:  push B, C (both marked). Visit C → D. D sees B is marked, skips
  it.
                 B's parent = A
  True DFS:      A → C → D → B
                 B's parent = D

  The visit order can look fine, but the DFS tree is wrong. That matters when
  DFS is used for cycle detection, topological sort, or discovery/finish times.
  Recursive DFS marks when it enters the call, which is the same as marking on
  pop: you mark a node when you actually go there.

  One-line summary for an interview

  ▎ BFS: the first discovery is the best one (shortest path), so mark on 
  ▎ enqueue. DFS: the latest discovery is the one DFS actually follows, so mark 
  ▎ on visit (pop or recursive entry).

✻ Cooked for 23s · done 5:24 PM

❯ how is it now? i didn't add more tests                                        

  Read 1 file, ran 1 shell command (ctrl+o to expand)

⏺ Stop Task
  ⎿  cat -n src/practice_coding/breadth_first_search.py && uv run python
     src/practice_coding/breadth_first_search.py && uv run python -c "
     import sys; sys.path.insert… · stopped

  Ran 2 shell commands (ctrl+o to expand)

⏺ Both bugs are still there. Your two tests pass, but they would have passed
  with the bugs too. I ran some extra checks to show this.

  1. search loops forever on any cycle

  I tested a two-node cycle (A↔B) searching for a value that isn't there. It
  hung, and I had to kill it after 5 seconds.

  You now add nodes to visited, but nothing ever reads it (lines 18–20). Every
  neighbor gets enqueued every time, so A→B→A→B… never ends. You're missing the
  check:
  for n in current_node.neighbors:
      if n not in visited:
          visited.add(n)
          to_visit.append(n)
  Your old version was inefficient but did terminate. This one is worse: it
  hangs on any graph with a cycle. The visited = set(to_visit) initialization on
  line 12 is correct, though.

  2. build_tree still builds a star

  0
    1
    2
    3
    4
    5
    6
  Adding parents.append(new_node) was half the fix. The problem now is that the
  root starts out both as next_parent and as the first item in parents. Trace
  it:

  ┌─────┬────────────────────────────────────────┬───────────┬─────────────┐
  │  v  │              next_parent               │  action   │  parents    │
  │     │                                        │           │    after    │
  ├─────┼────────────────────────────────────────┼───────────┼─────────────┤
  │ 1   │ root                                   │ root gets │ [root, 1]   │
  │     │                                        │  1        │             │
  ├─────┼────────────────────────────────────────┼───────────┼─────────────┤
  │ 2   │ root                                   │ root gets │ [root, 1,   │
  │     │                                        │  2        │ 2]          │
  ├─────┼────────────────────────────────────────┼───────────┼─────────────┤
  │ 3   │ root is full → popleft() returns root  │ root gets │ [1, 2, 3]   │
  │     │ again                                  │  3        │             │
  ├─────┼────────────────────────────────────────┼───────────┼─────────────┤
  │ 4   │ root has 3 children, so == 2 is never  │ root gets │ …           │
  │     │ true again                             │  4        │             │
  └─────┴────────────────────────────────────────┴───────────┴─────────────┘

  The smallest fix is to start with an empty queue: parents = deque(). Then the
  first popleft() returns node 1. Changing == 2 to >= 2 would also help, but
  then root would still get 3 children before that kicks in.

  What improved

  - The if __name__ == "__main__": guard is added.
  - parents.append is there now.
  - visited is initialized with the start node.

  Grade: C+

  It's lower than before. The search can now hang, and neither bug shows up in
  your tests. Your two tests (the root value and a value that isn't there) never
  make the traversal loop do any real work. Two quick tests would have caught
  both bugs:
  assert [c.val for c in build_tree([0,1,2,3,4,5,6]).neighbors] == [1, 2]

  a, b = Node("A", []), Node("B", [])
  a.neighbors, b.neighbors = [b], [a]
  assert search(a, "Z") is None   # hangs today
  In an interview, try to always test at least one cycle and one node deep in
  the tree. That's where BFS and DFS bugs tend to hide.

✻ Worked for 2m 37s · done 5:32 PM

※ recap: You're practicing BFS for interviews, and your latest version still has two bugs: search hangs on cycles, and build_tree makes every node a child of the root. Next, add the `if n not in visited` check and start `parents` as an empty deque. (disable recaps in /config)