# GPT Model Interaction UI (Bedrock-like Playground) — Design Answer

## 0. How to frame this in the interview

This is a **full-stack product design** question, not a pure backend-scale question. The interviewer
wants to see:

1. A clean **frontend architecture** (components, state, streaming render).
2. A correct **real-time streaming** path from the browser → backend → model and back.
3. A sensible **data model** for snapshots (immutable, versioned, parameter-complete).
4. **Search** and **sharing** with proper access control.
5. Trade-offs: SSE vs WebSocket, Postgres vs Elasticsearch, link sharing vs ACLs, cancellation, cost.

Suggested time budget (45 min): requirements 5 → API + data model 10 → high-level diagram 5 →
deep dives (streaming, snapshots, search, sharing) 20 → scaling/wrap-up 5.

---

## 1. Requirements

### Functional
| # | Feature | Notes |
|---|---------|-------|
| F1 | Enter prompt, submit, stream response in real time | Token-by-token rendering, stop button, choose model + params (temperature, top_p, max_tokens, system prompt, stop sequences) |
| F2 | Save snapshot of current interaction | Messages + model + all params + metadata (token usage, latency, timestamps), optional title/tags |
| F3 | Search saved snapshots | By title, tags, prompt/response text, model, date range |
| F4 | Share snapshots | Public/unlisted link, share with specific users/org, view-only; recipient can "fork" into their own playground |

### Non-functional
- **Low time-to-first-token (TTFT)**: our overhead < ~100 ms on top of model latency.
- **Smooth rendering**: no jank at 50–100 tokens/s; markdown + code blocks render incrementally.
- **Reliability**: dropped connections should not lose the response; can resume or at least recover.
- **Security**: API keys never in the browser; shared snapshots respect permissions; abuse/rate limits.
- **Scale (assume)**: 1M DAU, ~10 prompts/user/day → ~10M generations/day ≈ ~120 QPS avg, ~1k QPS peak;
  each stream lasts 5–60 s → **~10–60k concurrent open streams at peak**. Snapshots: ~1M/day, avg ~20 KB
  → ~20 GB/day, ~7 TB/yr. Reads (search/view) >> writes.

### Out of scope (say so explicitly)
Model training/serving internals, billing, fine-tuning, RAG/knowledge bases, agents.

---

## 2. UI / UX layout

```
+----------------------------------------------------------------------------------+
|  [Logo]  Playground   Snapshots   Shared with me                 [search 🔍] [👤] |
+----------------------+-----------------------------------------+-----------------+
|  SNAPSHOT SIDEBAR    |  CONVERSATION                           |  PARAMETERS     |
|                      |                                         |                 |
|  [+ New]             |  System: "You are a helpful..."  [edit] |  Model          |
|  ------------------  |                                         |  [gpt-x     v]  |
|  🔍 filter...        |  👤 User                                 |                 |
|  ★ Pricing prompt v3 |    Explain CRDTs in 3 bullets.          |  Temperature    |
|    SQL helper        |                                         |  0 ---o----- 2  |
|    Summarizer test   |  🤖 Assistant              ⏱ 1.2s 312tok |  (0.7)          |
|    ...               |    • CRDTs are data structures that...  |  Top P   [1.0]  |
|                      |    • They merge without coordinat▌      |  Max tok [1024] |
|                      |                                         |  Stop seq [   ] |
|                      |                                         |                 |
|                      +-----------------------------------------+  [Reset]        |
|                      | Type a message...                       |                 |
|                      |                       [■ Stop] [Send ⏎] |                 |
|                      +-----------------------------------------+                 |
|                      |  [💾 Save snapshot] [🔗 Share] [⑂ Fork]  |                 |
+----------------------+-----------------------------------------+-----------------+
```

Key UX details:
- **Send** disabled while streaming; it becomes **Stop** (aborts the stream server-side too).
- Streaming cursor `▌`, auto-scroll that **pauses if the user scrolls up** ("↓ Jump to latest" pill).
- Per-message actions: copy, regenerate, edit-and-resubmit (creates a branch).
- "Unsaved changes" indicator; `Cmd+S` saves snapshot.
- Shared snapshot view = same layout but read-only, with a **"Open in Playground"** (fork) button.

---

## 3. High-level architecture

```
                                    +-------------------+
                                    |   CDN (static JS, |
                                    |   public snapshot |
                                    |   pages cached)   |
                                    +---------+---------+
                                              |
  +-----------+   HTTPS / SSE        +--------v---------+
  |  Browser  | <------------------> |  API Gateway /   |  authN (session/JWT), rate limit,
  |  (SPA)    |                      |  Load Balancer   |  request size limits, WAF
  +-----------+                      +---+----------+---+
                                         |          |
                     streaming requests  |          |  CRUD / search / share
                                         v          v
                         +---------------+--+   +---+-----------------+
                         | Inference Proxy  |   |  Snapshot Service   |
                         | (stream service) |   |  (REST, stateless)  |
                         +---+---------+----+   +--+------+------+----+
                             |         |           |      |      |
            model API (SSE / |         | usage     |      |      | change events (CDC / outbox)
            gRPC stream)     |         | events    |      |      v
                             v         v           |      |   +--+-----------+
                  +----------+--+  +---+------+    |      |   | Queue/Kafka  |
                  | Model       |  | Usage /  |    |      |   +--+-----------+
                  | Provider(s) |  | Metering |    |      |      |
                  | (GPT, ...)  |  | (Kafka)  |    |      |      v
                  +-------------+  +----------+    |      |   +--+-----------+
                                                   |      |   | Indexer      |
                       +---------------------------+      |   +--+-----------+
                       v                                  v      v
               +-------+--------+              +----------+---+--------+
               |  PostgreSQL    |              |  Search index         |
               |  (metadata,    |              |  (OpenSearch/ES)      |
               |   ACLs, shares)|              +-----------------------+
               +-------+--------+
                       |  large blobs (full transcript JSON)
                       v
               +-------+--------+       +-------------------+
               |  Object Store  |       | Redis             |
               |  (S3)          |       | (rate limits,     |
               +----------------+       |  stream buffers,  |
                                        |  share-link cache)|
                                        +-------------------+
```

Why split **Inference Proxy** from **Snapshot Service**?
- Very different workload profiles: proxy = long-lived connections, I/O bound, scaled by
  concurrent streams; snapshot service = short request/response CRUD, scaled by QPS.
- Proxy holds the provider API keys; keeps the blast radius small.

---

## 4. API design

### 4.1 Generation (streaming)

```
POST /v1/generations            (Accept: text/event-stream)
{
  "model": "gpt-x",
  "messages": [
    {"role": "system", "content": "You are..."},
    {"role": "user",   "content": "Explain CRDTs in 3 bullets."}
  ],
  "params": {"temperature": 0.7, "top_p": 1.0, "max_tokens": 1024, "stop": []},
  "client_request_id": "uuid-from-browser"     // idempotency key: makes POST retries safe
}

Response: SSE stream (every `id:` = sequence number in the server-side log, see §5.5)
  id: 0  event: meta     data: {"generation_id":"gen_123","model":"gpt-x@2026-08-01"}
         event: status   data: {"state":"retrying","attempt":2}          // optional, pre-first-token
  id: 1  event: delta    data: {"text":"• CRDTs"}
  id: 2  event: delta    data: {"text":" are data"}
  ...
  id: N  event: end      data: {"finish_reason":"stop","usage":{"prompt":40,"completion":312}}
  (or)   event: error    data: {"code":"upstream_reset","recoverable":true}
  (or)   event: error    data: {"code":"rate_limited","retry_after":5,"recoverable":false}
  (or)   event: cancelled

POST /v1/generations/{id}/cancel                              // Stop button
GET  /v1/generations/{id}/stream   (Last-Event-ID: 57)         // resume after disconnect / refresh
POST /v1/generations/{id}/continue                            // resume after interrupted/length stop
                                                              // (Regenerate = a fresh POST /generations)
```

Two IDs, two jobs:

| ID | Minted by | Purpose |
|---|---|---|
| `client_request_id` | Browser, before sending | **Idempotent POST.** A re-sent POST (timeout before `meta`, double click) maps via `SETNX req:{client_request_id} → generation_id` to the existing generation and re-attaches instead of paying for a second one. |
| `generation_id` | Server, at upstream start | **Names the generation itself.** Key for the Redis log, resume, cancel, continue, metering, traces, and the assistant message in snapshots. |

### 4.2 Snapshots

```
POST   /v1/snapshots                    create (body: full snapshot, see §6)
GET    /v1/snapshots/{id}               read (ACL checked)
GET    /v1/snapshots/{id}/versions      list versions
POST   /v1/snapshots/{id}/versions      save new version (optimistic concurrency: If-Match: <version>)
PATCH  /v1/snapshots/{id}               title/tags/description
DELETE /v1/snapshots/{id}               soft delete
POST   /v1/snapshots/{id}/fork          copy into caller's workspace

GET    /v1/snapshots/search?q=crdt&model=gpt-x&tag=prod&owner=me|shared|all
                       &from=2026-01-01&cursor=...&limit=20
```

### 4.3 Sharing

```
POST   /v1/snapshots/{id}/shares
       {"principal_type":"user",  "principal_id":"user_42",  "access":"view|edit", "version":3}
       {"principal_type":"group", "principal_id":"group_7",  "access":"view"}
       {"principal_type":"org",   "principal_id":"org_3",    "access":"view"}
       {"principal_type":"link",  "link_audience":"anyone|org", "access":"view", "expires_at":"..."}
       -> {"share_id":"shr_9", "url":"https://app/s/9fK2xQ..."}   (link only: unguessable 128-bit token)
GET    /v1/snapshots/{id}/shares                list grants (owner/editors only)
GET    /v1/shared-with-me?cursor=...            snapshots shared to any of my principals
DELETE /v1/snapshots/{id}/shares/{share_id}     revoke
GET    /s/{token}                               resolve link -> read-only snapshot
```

---

## 5. Deep dive: real-time streaming (F1)

### 5.1 Transport choice

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Polling | Simple | Laggy, wasteful | ✗ |
| **SSE** (`text/event-stream` over HTTP POST via `fetch` + ReadableStream) | Server→client is exactly our pattern; works through proxies/HTTP2; built-in `id`/resume semantics; trivial to implement; same as OpenAI's own API | One direction only (cancel is a separate POST) | ✓ **Choose this** |
| WebSocket | Bi-directional, good for collaborative/multi-stream | Stateful, harder LB/auth, overkill for request→stream | Consider later for live co-editing |

Note: native `EventSource` only supports GET, so use `fetch()` with a streaming body reader
(or `@microsoft/fetch-event-source`) to POST the prompt and read SSE.

### 5.2 End-to-end sequence

```
Browser                 Gateway          Inference Proxy            Model Provider       Redis
  |  POST /generations    |                    |                          |                 |
  |---------------------->| auth, rate-limit   |                          |                 |
  |                       |------------------->| validate params,         |                 |
  |                       |                    | moderation (input),      |                 |
  |                       |                    | quota check, SETNX req:{client_request_id} |
  |                       |                    | mint gen_123, acquire lease (epoch 1) ---> |
  |                       |                    | XADD gen:gen_123 {start} ----------------> |
  |  id:0 event: meta     |<-------------------|                          |                 |
  |<----------------------|                    | POST stream=true ------->|                 |
  |                       |                    |<--- chunk "• CRDTs" -----|                 |
  |                       |                    |(1) XADD {delta seq=1} ------------------>  | ack
  |  id:1 event: delta    |<-------------------|(2) only after ack, send  |                 |
  |<----------------------|                    |<--- chunk " are data" ---|                 |
  |                       |                    |(1) XADD {delta seq=2} ------------------>  | ack
  |  id:2 event: delta    |<-------------------|(2) send                  |                 |
  |   ... render ...      |                    |          ...             |                 |
  |                       |                    |<--- [DONE] -------------|                 |
  |                       |                    | XADD {end, usage} (terminal) ------------> |
  |  id:N event: end      |<-------------------| emit usage -> Kafka; persist message -> PG/S3
  |<----------------------|                    |                          |                 |
```

**Invariant: log first, then send.** The client only ever receives what is already in the Redis log,
so the client can be *behind* the log (fixed by replay) but never *ahead* of it (unfixable). See §5.6.

### 5.3 Proxy responsibilities
- **Never expose provider keys** to the client; proxy injects them.
- **Backpressure**: proxy is async (Node/Go/Python asyncio); flush each chunk immediately,
  disable response buffering (`X-Accel-Buffering: no`, gzip off for SSE), heartbeats (`: ping`
  every 15 s) to keep idle LBs from killing the connection.
- **Cancellation**: `/cancel` (may land on any pod) publishes `cancel:{generation_id}` on Redis
  pub/sub; the owning pod aborts upstream. On client disconnect, keep generating for a ~30–60 s
  grace period (so a reconnect resumes seamlessly), then abort if nobody re-attached → saves cost.
- **Resumability**: the upstream connection is decoupled from the client connection via a
  per-generation log in Redis (§5.5). A flaky network costs a reconnect, not a regeneration.
- **Timeouts & retries**: silent retry only when the log has *no deltas yet* (§5.7).
  Circuit breaker per provider/model.
- **Rate limiting**: token bucket per user/org in Redis on both requests/min and tokens/min.
- **Safety**: input moderation before calling the model; output moderation can run on the
  accumulating buffer asynchronously and cut the stream if it trips.

### 5.5 The generation log in Redis (source of truth while streaming)

Status is **not stored as a mutable field**. Status transitions are entries in the same append-only
log as the tokens, so a token and a status change can never disagree.

```
gen:{id}          Redis Stream  — the log (append-only, TTL ~10 min after terminal entry)
   0    {type: start,  attempt: 1, model: "gpt-x@2026-08-01", provider: "openai-us-east"}
   1..N {type: delta,  attempt: 1, text: "..."}           # batched every ~20–50 ms
   N+1  {type: end,    attempt: 1, finish_reason: stop|length|content_filter,
                       usage: {prompt: 40, completion: 312}}
     or {type: error,  attempt: 1, code: upstream_5xx|timeout|stalled|owner_lost,
                       recoverable: true|false}
     or {type: cancelled, by: user|abandoned}

gen:{id}:owner    Redis Hash    — write authority (the only mutable state)
   pod          = "proxy-7"
   epoch        = 5             # fencing token; +1 on every takeover
   lease_until  = now + 10s     # heartbeated every ~3 s by the owner

req:{client_request_id} → gen_id   # idempotency mapping for POST retries
```

Status is **derived**:

```
status(id):
    last = XREVRANGE gen:{id} + - COUNT 1
    if last.type in {end, error, cancelled}:  return last.type        # terminal, immutable
    o = HGETALL gen:{id}:owner
    if now > o.lease_until:                   return "orphaned"        # owner is dead
    return "streaming" if any delta else "pending"
```

The two reads aren't atomic, but that's safe: a terminal entry never changes, and acting on an
expired lease only happens through the atomic `takeover()` below, which re-checks both.

If a stored `status` is wanted for dashboards / "list active generations", write it **inside the same
Lua script** as the append that changes it and treat it as a display-only cache — never as the input
to takeover / retry / continue decisions.

### 5.6 Consistency: Redis log vs. client stream

The tempting design — "update status in Redis, and also send to client" — is two writes with a race
window in either order. The design avoids it with three rules:

1. **The log is the source of truth; the client is a reader of the log.**
2. **The server never tracks what the client received.** The client owns its cursor (`Last-Event-ID`).
3. **Status is derived** from terminal entry + lease (§5.5), not a separately updated field.

Write order:

```
model token ──> proxy ──(1) XADD gen:{id} seq=141 ──> Redis   (acked)
                     └─(2) after ack: SSE id=141 ──> browser
```

| Order | Proxy dies between (1) and (2) | Outcome |
|---|---|---|
| **Log first, then send** ✅ | Token 141 in log, client never got it | Client reconnects with `Last-Event-ID: 140` → replay delivers 141. **Nothing lost.** |
| Send first, then log ❌ | Client has 141, log doesn't | Client is *ahead* of the truth: Continue resumes from 140 → duplicated/forked text; snapshot ≠ what user saw. **Corrupt.** |

A failed send to the client changes no server state — the client simply reconnects and reports its
cursor.

**Fencing against zombie writers.** If proxy-7 GC-pauses past its lease, proxy-3 may take over
(mark failed, or start a Continue attempt). When proxy-7 wakes up it must not append. Every append
carries the writer's epoch and is checked atomically in Lua:

```
append(gen_id, epoch, entry):              -- Lua, atomic
    o = HGETALL gen:{id}:owner
    if o.epoch != epoch or now > o.lease_until:  return REJECTED   -- zombie: abort upstream
    if log has terminal entry:                   return REJECTED
    XADD gen:{id} * entry
    return OK

takeover(gen_id):                          -- Lua, atomic
    if lease alive or terminal entry present:    return NO
    HSET gen:{id}:owner pod=me epoch=epoch+1 lease_until=now+10s
    return new epoch
```

Redis serializes appends and takeovers, so the log can never contain interleaved writes from two owners.

**Walkthrough — "first token logged, proxy dies, client received nothing":**

```
proxy-7: XADD start, XADD delta seq=1 ✔        (client has nothing yet)
proxy-7: X dies before sending seq=1
browser: connection drops → GET /generations/gen_123/stream, Last-Event-ID: 0
proxy-3: replays seq 0..1 from log → browser now shows "• CRDTs"
proxy-3: no terminal entry + lease expired → "orphaned" → takeover() → epoch 6
         log has deltas?  no  → silently restart upstream (user saw nothing; safe)
                          yes → append {type:error, code:owner_lost, recoverable:true}
                                → browser shows partial + [Continue] [Regenerate]
```

**Residual edges & costs:**
- *Latency*: one Redis write per batch (~0.5–1 ms); batch deltas per 20–50 ms, invisible next to
  the client's rAF batching.
- *Redis failover* (async replication) can lose the last few entries, so the client may report
  `Last-Event-ID` 145 while the log ends at 140. Treat as **interrupted** (offer Continue/Regenerate),
  never pretend to resume. `WAIT 1 <ms>` closes the window at a latency cost — usually not worth it.
- *Redis fully down*: degrade to direct streaming without resumability; alert on it.
- *Durability*: the Redis log is a short-lived buffer. On the terminal entry, the proxy persists the
  final assistant message to Postgres/S3 keyed by `generation_id` — that's what snapshots reference.

### 5.7 Server → model failure handling

The pivot is the **first delta in the log**. Before it, nothing has been shown to the user, so a retry
is invisible and safe. After it, a silent retry would splice a *different* continuation onto text the
user has already read.

```
                  start entry
   +---------+   (upstream opened)                first delta
   | pending |--------------------------------------------------> streaming
   +----+----+   <-- retry w/ backoff, fallback (same gen_id) -->     |
        |                                                             |-- [DONE]/stop ---> end(stop)
        | retries exhausted / 4xx                                     |-- max_tokens ----> end(length)
        v                                                             |-- moderation ----> end(content_filter)
   error(recoverable=false)          error(recoverable=true) <--------|-- upstream reset / stall
                                     error(owner_lost)  <-------------|-- lease expired (pod died)
                                     cancelled  <---------------------|-- user Stop / abandoned
```

**A. Before first token** — connection refused, 5xx, 429, no first token within ~10–20 s.
- Retry upstream 2–3× with exponential backoff + jitter under the **same `generation_id`**
  (new `start` entry with `attempt: 2`). Client may get `event: status {"state":"retrying"}`.
- 429 with short `Retry-After` → wait and retry; long → `error{rate_limited, retry_after}`.
- Per provider/model **circuit breaker**; fall back to another region/deployment of the
  **same pinned model version** — never silently swap models (it breaks snapshot reproducibility).
- Non-retryable 4xx (bad params, context too long, input moderation) → fail immediately.

**B. Mid-stream** — upstream connection reset, provider error event, or **stall** (watchdog: no
delta for ~30 s).
- **No auto-retry.** Append `error{recoverable:true}`, keep the partial text, bill only tokens received.
- **Continue** → `POST /generations/{id}/continue`: new upstream call with the original messages +
  the partial assistant text as a prefill/prefix. **Same `generation_id`**, `attempt: 2`, sequence
  numbers keep counting (141, 142, …) in the same log — still one message to the user.
- **Regenerate** → a brand-new `POST /generations` → **new `generation_id`**; replaces the message
  (optionally kept as a sibling "version 1/2").

**C. Proxy pod dies** — lease expires; the next reader (usually the reconnecting client's new pod)
runs `takeover()` and appends `error{owner_lost}` (or silently restarts if no deltas). Same UX as B.
Planned deploys drain gracefully (stop accepting new streams, let current ones finish, cap ~2 min),
so this is rare.

**D. Client disconnects** — not a model failure. Upstream keeps writing to the log during the grace
period; reconnect with `generation_id` + `Last-Event-ID` → replay + live tail. No reconnect →
abort upstream, append `cancelled{by: abandoned}`.

**E. User Stop** — `/cancel` → pub/sub → owner aborts upstream, appends `cancelled{by: user}`,
meters usage so far.

**F. Normal-but-not-success endings** — `length` → "Stopped at max tokens" + Continue;
`content_filter` → policy notice, no retry offered.

### 5.8 What the end user experiences

| # | Situation | User sees | Partial kept? | Actions | `generation_id` |
|---|---|---|---|---|---|
| 1 | Happy path | Streaming text → done | yes | copy, regenerate, save | one ID |
| 2 | Transient upstream failure, pre-first-token | Slightly longer "Thinking…", maybe "Retrying…" | n/a | none | same ID, attempt 2 |
| 3 | Provider overloaded / rate limited | "Model busy, retrying in 8s" or error | n/a | Retry | same ID / new on manual retry |
| 4 | Bad request (context too long, bad params) | Inline error on composer/param | n/a | edit & resend | ID → error |
| 5 | Mid-stream failure / stall | Partial + "Response interrupted" | **yes** | **Continue** / **Regenerate** | Continue = same; Regenerate = new |
| 6 | User's network blip / page refresh | "Reconnecting…" pill, then catches up | yes | none | same ID (resume) |
| 7 | Proxy pod crash | Brief reconnect → same as #5 (or invisible if no deltas yet) | yes | Continue / Regenerate | same ID, takeover |
| 8 | User presses Stop | Text freezes, "Stopped" | yes | Continue / Regenerate | same ID → cancelled |
| 9 | Hit max_tokens | "Stopped at max tokens" | yes | Continue | same ID |
| 10 | Content filter | Policy notice | per policy | edit prompt | same ID → end(content_filter) |

Guarantees to the user:
1. **Never lose text you've seen** — it's in the log before it reached your screen.
2. **Hide what can be hidden** (#2, #6, #7-before-first-token) — at most a slower spinner.
3. **Never show silently corrupted output** — no spliced retries, no model swaps.
4. **When it can't be hidden, one-click recovery** — Continue keeps context, Regenerate starts fresh.
5. **Don't pay for failures** — meter only received tokens; abort abandoned streams.

Client state machine:

```
          send                 meta(gen_id)            delta
 idle ---------> connecting ----------------> waiting ---------> streaming
                    |  ^                        |  status:retrying    |
                    |  | reconnect w/           v                     |-- end ------------> done
                    |  | gen_id+Last-Event-ID  retrying (spinner)     |-- error(rec) -----> interrupted
                    |  +--------- reconnecting <----- network drop ---|        [Continue][Regenerate]
                    |                (backoff, up to ~60s)            |-- cancelled ------> stopped
                    +-- HTTP 4xx / 429 / error(non-rec) --> error (show cause)
```

The client persists `generation_id` + last sequence number in its local draft, so even a full page
refresh mid-stream resumes: on load, if the last message is still `streaming`, it re-attaches.

### 5.9 Frontend streaming render

```
 fetch() ReadableStream
        |
        v
 +----------------+    parse "event:/data:" lines (handle chunks split mid-line!)
 |  SSE parser    |
 +-------+--------+
         | deltas
         v
 +----------------+    append to a mutable buffer (ref), NOT setState per token
 | token buffer   |
 +-------+--------+
         | requestAnimationFrame (~60 fps) flush
         v
 +----------------+    store: messages[], status: idle|streaming|done|error
 | state store    |    (Zustand/Redux)
 +-------+--------+
         v
 +----------------+    incremental markdown render; only last message re-renders
 | <MessageList>  |    (memoized older messages, virtualized list for long chats);
 +----------------+    syntax highlighting deferred until code block closes
```

- **Batching via rAF** is the key perf trick: 100 tokens/s × setState = jank; batch to frames.
- `AbortController` wired to the Stop button (also calls `/cancel`).
- Sanitize rendered markdown (DOMPurify) — model output is untrusted (XSS via shared snapshots!).
- Accessibility: `aria-live="polite"` region, but announce in sentence-sized chunks, not per token.

### 5.10 Frontend component tree

```
<App>
 ├─ <TopNav> (global search box)
 ├─ <SnapshotSidebar>           -> useSnapshotsQuery (React Query, cached, paginated)
 ├─ <PlaygroundPage>
 │    ├─ <SystemPromptEditor>
 │    ├─ <MessageList>          -> virtualized; <Message> memoized
 │    │     └─ <StreamingMessage> (reads token buffer)
 │    ├─ <Composer>             -> Send / Stop, Cmd+Enter
 │    └─ <SnapshotActions>      -> Save / Share / Fork
 ├─ <ParameterPanel>            -> model select, sliders; persisted to URL + local draft
 ├─ <SearchPage>                -> filters, results with highlighted snippets
 └─ <SharedSnapshotView>        -> read-only route /s/:token
```

State split:
- **Server state** (snapshots, search results, shares) → React Query (caching, invalidation).
- **Client/session state** (current messages, params, streaming status) → Zustand store,
  autosaved to `localStorage`/IndexedDB as a **draft** so a refresh doesn't lose work.

---

## 6. Deep dive: snapshots (F2)

### 6.1 What is a snapshot?
An **immutable, self-contained record** that lets anyone reproduce the interaction:

```json
{
  "snapshot_id": "snp_abc",
  "version": 3,
  "title": "CRDT explainer",
  "tags": ["docs", "eval"],
  "model": {"id": "gpt-x", "version": "2026-08-01"},     // pin exact model version!
  "params": {"temperature": 0.7, "top_p": 1, "max_tokens": 1024, "stop": [], "seed": 42},
  "system_prompt": "You are...",
  "messages": [
    {"role":"user","content":"Explain CRDTs..."},
    {"role":"assistant","content":"• CRDTs are...","generation_id":"gen_123",
     "usage":{"prompt_tokens":40,"completion_tokens":312},"latency_ms":1200,"finish_reason":"stop"}
  ],
  "created_by": "user_1", "created_at": "2026-11-09T10:00:00Z"
}
```

Model version pinning + seed matters because "reproduce what I saw" is the core value of a
playground snapshot; output is still non-deterministic, so we store the actual output, not just inputs.

### 6.2 Storage model

```
PostgreSQL (source of truth for metadata + ACL)

 orgs(id PK, name)
 users(id PK, org_id FK -> orgs, email, ...)
 groups(id PK, org_id FK -> orgs, name)                  -- e.g. "ml-eval-team"
 group_members(group_id FK, user_id FK, PK(group_id, user_id))
   INDEX (user_id)                                        -- "which groups am I in?"

 snapshots(
   id PK, owner_id, org_id, title, tags[], current_version,
   model_id,
   visibility,        -- DISPLAY CACHE ONLY (badge: private|org|link|public), recomputed
                      -- from shares on change; never used for access checks (§8.3)
   created_at, updated_at, deleted_at
 )

 snapshot_versions(
   snapshot_id, version, PK(snapshot_id, version),
   blob_key,                               -- s3://snapshots/{id}/{version}.json(.gz)
   content_hash, size_bytes,
   preview_text,                           -- first ~500 chars, for list views
   params_json, created_by, created_at
 )

 shares(                                 -- one row per grant; full semantics in §8.2
   id PK, snapshot_id FK,
   version NULL,                          -- NULL = always latest; else pinned version
   principal_type,                        -- user | group | org | link
   principal_id NULL,                     -- user/group/org id (polymorphic); NULL for link
   token_hash NULL,                       -- link only: hash of token, never the token
   link_audience NULL,                    -- link only: anyone | org
   access,                                -- view | edit
   expires_at, revoked_at, created_by, created_at,
   CHECK ( (principal_type =  'link' AND token_hash IS NOT NULL AND principal_id IS NULL)
        OR (principal_type <> 'link' AND principal_id IS NOT NULL AND token_hash IS NULL) ),
   UNIQUE (snapshot_id, principal_type, principal_id)
 )
   INDEX (principal_type, principal_id)   -- "Shared with me"
   INDEX (token_hash)                     -- link resolution

S3: full transcript JSON (can be 100s of KB with long contexts / attachments)
```

Why split metadata/blob: list and search views never need the whole transcript; Postgres rows stay
small; S3 is cheap and immutable versions are naturally content-addressable. Small snapshots (< ~64 KB)
could be inlined in a JSONB column to save a round trip — a fine optimization to mention.

### 6.3 Save flow

```
Browser                Snapshot Svc               S3            Postgres            Outbox/Kafka
  | POST /snapshots      |                         |                |                    |
  | (Idempotency-Key)    |                         |                |                    |
  |--------------------->| validate, size limit,   |                |                    |
  |                      | redact secrets (opt.)   |                |                    |
  |                      |--- PUT blob ----------->|                |                    |
  |                      |--- BEGIN; insert snapshot + version + outbox row; COMMIT ->  |
  |  201 {id, version}   |                         |                |---- CDC/poll ----->|
  |<---------------------|                         |                |                    |--> Indexer
```

- Blob first, then DB commit → no dangling DB rows pointing at missing blobs (orphan blobs get GC'd).
- **Transactional outbox** guarantees search index eventually reflects every commit.
- Saving again creates a **new version** (`If-Match: version` → 409 on conflict if two tabs edit).
- Option: server can save the assistant message itself from the proxy (it saw the full output),
  so the client only sends `generation_id`s — prevents users "forging" model output in snapshots
  that are later shared. Good trust point to raise.

---

## 7. Deep dive: search (F3)

### 7.1 Index document

```
{
  snapshot_id, version, owner_id, org_id,
  title, tags, model_id,
  content: "system + user + assistant text (truncated to N KB)",
  acl_principals: ["user:1", "org:7", "group:12", "public"],   // denormalized for filtering
  created_at, updated_at
}
```

### 7.2 Query path

```
 Browser --(debounced 250ms)--> GET /snapshots/search?q=...
                                     |
                                     v
                              Snapshot Service
                    resolve caller principals: [user:1, org:7, group:12]
                                     |
                                     v
             OpenSearch: bool{ must: multi_match(q, [title^3, tags^2, content]),
                               filter: terms(acl_principals, caller_principals),
                                       term(model_id), range(created_at) }
                         + highlight(content) + search_after cursor
                                     |
                                     v
                     results -> (optional) re-check ACL in Postgres for top-K
                                     |
                                     v
                    [{id, title, snippet with <em>crdt</em>, model, updated_at}]
```

- **Start simple**: Postgres `tsvector` + GIN index (+ `pg_trgm` for fuzzy titles) is enough for
  millions of rows per tenant. Move to OpenSearch when you need relevance tuning, highlights,
  facets at scale, or the corpus hits billions of docs. Say this explicitly — interviewers like it.
- **ACL in the index** (filter by principals) keeps search fast. `acl_principals` stores the
  **unexpanded** grants (`group:12`, not every member of group 12), and the query filters on the
  caller's **expanded** principal list — so group membership changes never require re-indexing; only
  adding/revoking a share does (emit an event to re-index that doc's `acl_principals`). Link shares
  have no principal, so link-only snapshots don't show up in the recipient's search (optionally
  record a "recently viewed" row when they open the link). Because indexing is eventually consistent, do a final
  **authoritative ACL check** in Postgres on the returned page to avoid leaking a just-revoked doc.
- Optional: **semantic search** — embed prompts/responses, store vectors (pgvector/OpenSearch k-NN),
  hybrid BM25 + vector scoring ("find prompts like this one").
- Sidebar "recent snapshots" doesn't use search — plain indexed Postgres query
  `WHERE owner_id=? ORDER BY updated_at DESC` with keyset pagination.

---

## 8. Deep dive: sharing (F4)

### 8.1 Share modes

```
                 +------------------- Share dialog --------------------+
                 |  People / groups:  [ alice@co ] [view v]  [Add]     |
                 |  General access:   ( ) Restricted                   |
                 |                    (•) Anyone in my org with link   |
                 |                    ( ) Anyone with link (public)    |
                 |  Version:  (•) This version (v3)  ( ) Always latest |
                 |  Expires:  [ 30 days v ]                            |
                 |  [Copy link]                         [Done]         |
                 +-----------------------------------------------------+
```

- **Default to sharing a pinned, immutable version** — the recipient sees exactly what you saw,
  and later edits don't silently change what was shared.
- Link token: 128-bit random, base62 in the URL; **store only its hash** in `shares`.
- Recipients get **view** by default; they **fork** to experiment (fork copies the blob reference
  — copy-on-write, no data duplication until they change it).

### 8.2 Principals and the shares model

A **principal** is anything that can be granted access: a user, a group, an org (or later a service
account). `shares.principal_id` is the grantee's id and `principal_type` says which table it refers to:

```
principal_type=user   principal_id=user_42    -> Alice
principal_type=group  principal_id=group_7    -> "ml-eval-team"
principal_type=org    principal_id=org_3      -> everyone in Acme Corp
principal_type=link   principal_id=NULL       -> whoever holds the token (token_hash instead)
```

This is a **polymorphic reference**: one table and one query for every kind of grant, at the cost
that Postgres can't enforce the FK — the CHECK constraint plus app-level validation keep it sane.

The share dialog's "General access" maps onto share rows (no separate visibility source of truth):

| Dialog setting | Share rows |
|---|---|
| Restricted | only `user` / `group` rows |
| Anyone in my org | `principal_type=org, principal_id=org_3` |
| Anyone in my org with the link | `link`, `link_audience=org` |
| Anyone with the link (public) | `link`, `link_audience=anyone` |

### 8.3 Access check

Step 1 — expand the caller into principals once per request (cached in Redis, short TTL, busted on
membership change):

```
principals(user_1) = [user:1, org:3, group:7, group:12]
   -- users.org_id  +  SELECT group_id FROM group_members WHERE user_id = 1
```

Step 2 — match against the snapshot's grants:

```sql
SELECT max(access) FROM shares
WHERE snapshot_id = :snap
  AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
  AND (version IS NULL OR version = :requested_version)
  AND (principal_type, principal_id) IN (('user',1), ('org',3), ('group',7), ('group',12));
```

```
           +--------+           +-----------+            +---------------+
 request ->| caller |-- expand ->| principals|-- match --> | shares rows   |--> view / edit / 404
           | user_1 |  (org,    | user:1    |             | for snapshot  |
           +--------+   groups) | org:3     |             +---------------+
                                | group:7   |
                                | group:12  |
                                +-----------+
```

Full rule:

```
can_access(caller, snapshot, version, link_token?):
    if snapshot.deleted:                                   deny
    if caller == snapshot.owner:                           allow (edit)
    if link_token:
        s = shares WHERE token_hash = hash(link_token) AND snapshot matches, not revoked/expired
        if s and (s.link_audience == anyone
                  or (s.link_audience == org and caller.org == snapshot.org)):  allow (s.access)
    if principal-match query above returns a row:          allow (that access)
    deny  -> return 404 (not 403) to avoid confirming existence
```

Cache resolved `token_hash → (snapshot_id, version, access, audience)` in Redis (short TTL,
invalidated on revoke).

**Why grant to the group, not to each member:** membership is resolved at *check time*, not
share time. Bob joins `ml-eval-team` → instantly sees everything shared with the group; no share
rows change and no re-indexing (§7.2). Someone leaves the group/org → access is gone as soon as
their cached principal list expires or is busted.

**"Shared with me":**

```sql
SELECT DISTINCT snapshot_id FROM shares
WHERE (principal_type, principal_id) IN (:caller_principals)
  AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
ORDER BY created_at DESC LIMIT 20;      -- uses INDEX (principal_type, principal_id)
```

Org-wide grants can be split into a separate "Org" tab so they don't flood the list.

### 8.4 Public shared page
- `/s/{token}` rendered server-side (SSR) for fast first paint + link-preview (OpenGraph) cards.
- Immutable pinned versions → cache aggressively at the CDN (`Cache-Control: public, max-age`)
  for public links; on revoke, purge the CDN key. Org/private shares are `private, no-store`.
- Strip sensitive fields (owner email, internal usage/cost) from public views.
- Abuse: report button, moderation scan on publish-to-public, rate-limit link creation.

---

## 9. Scaling & reliability

| Concern | Approach |
|---|---|
| 10–60k concurrent streams | Async proxy, ~5–10k conns/instance → handful of pods per region; autoscale on open-connection count, not CPU. Graceful drain on deploy (stop accepting, let streams finish). |
| LB idle timeouts | SSE heartbeats; LB idle timeout ≥ 5 min. |
| Proxy pod crash / deploy | Generation log + lease in Redis; any pod can replay and take over (fenced by epoch); graceful drain on deploy (§5.6–5.7). |
| Redis (generation logs) | Sharded by `generation_id` (Redis Cluster); short TTL keeps memory small (~10–60k active logs × tens of KB). Failover loss → treated as interrupted. |
| Provider outages / limits | Per-model circuit breaker, queue/429 with `retry_after`, fallback region/provider. |
| Cost control | Abort upstream on disconnect; per-org token quotas; metering via Kafka → billing. |
| Snapshot read hot spots (viral public link) | CDN + Redis cache of immutable versions. |
| DB growth (~7 TB/yr blobs) | Blobs in S3 with lifecycle tiering; Postgres holds only metadata; partition/shard by `org_id` if needed. |
| Search index lag | Outbox + indexer with retries/DLQ; UI shows newly saved snapshot from local cache immediately (read-your-writes). |
| Multi-region | Stateless services per region; Postgres primary + read replicas; route streams to nearest region with model capacity. |

## 10. Observability
- Metrics: TTFT, tokens/s, stream completion vs abort vs error rate, proxy overhead latency,
  snapshot save latency, search p95, indexer lag.
- Tracing: `generation_id` / `client_request_id` propagated browser → proxy → provider.
- Client RUM: render FPS during streaming, long tasks.

## 11. Security & privacy checklist
- Provider keys only server-side; per-user auth on every request.
- Sanitize markdown/HTML from model output (XSS especially on shared pages); CSP headers.
- Snapshot ownership & ACLs enforced server-side; 404 on unauthorized.
- Optional secret/PII scanner on save and before making public.
- Data retention + hard delete (GDPR): delete blobs, index docs, CDN purge.
- Audit log for share creation/revocation.

---

## 12. Trade-offs to call out (summary)

```
 SSE                 vs WebSocket      -> SSE: one-way stream fits; simpler infra. WS only for collab.
 Client-sent output  vs Server-recorded -> Server-recorded output = trustworthy shared snapshots.
 Mutable snapshot    vs Versioned       -> Versioned/immutable: reproducible, cacheable, safe sharing.
 Postgres FTS        vs OpenSearch      -> Start with PG FTS; graduate when scale/relevance demands.
 ACL in index        vs ACL post-filter -> Index filter for speed + authoritative recheck on page.
 Share "latest"      vs pinned version  -> Pinned by default; "latest" as an opt-in.
 Retry mid-stream    vs fail            -> Only retry before first token; afterwards surface error +
                                           offer "continue"/regenerate.
 Send-then-log       vs log-then-send   -> Log first: client can lag the log (replay fixes) but never
                                           lead it (unfixable).
 Stored status       vs derived status  -> Derived from terminal entry + lease; no second write to race.
 Trust the lease     vs fencing epoch   -> Leases alone allow zombie writers after GC pauses; epoch-checked
                                           appends in Lua make takeover safe.
```

## 13. Possible extensions (if time remains)
- **Compare mode**: same prompt across 2–3 models/param sets side-by-side (fan-out N streams).
- Prompt templates with `{{variables}}` and batch runs over a dataset (evals).
- Live collaborative editing of a snapshot (CRDT/OT over WebSocket).
- Export snapshot as code (curl / Python / JS SDK snippet with the same params) — Bedrock/OpenAI
  playgrounds both do this and it's a nice touch to mention.
