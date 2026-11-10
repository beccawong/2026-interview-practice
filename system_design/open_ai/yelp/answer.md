# POI System (Yelp-like): Design Answer

## 0. How to frame this in the interview

This is a **read-heavy geo-search** problem. The interviewer mainly wants to see:

1. A **data model** that handles spatial queries well (geohash / quadtree / S2 / spatial index).
2. A **search path** that serves text + category + location under 200 ms.
3. **Different consistency levels** in one system: POI core data is strongly consistent, while
   reviews and ratings are eventually consistent.
4. **Photos** stored in object storage and served through a CDN.
5. **Rating aggregation** and **review pagination** that hold up when one POI has 50k reviews.
6. **Read scaling**: caches, replicas, sharding.

Suggested time budget (45 min): requirements + estimates 5 → API + data model 10 → high-level
diagram 5 → deep dives (geo index, search, ratings, photos, consistency) 20 → scaling/wrap-up 5.

---

## Geo primer (read this first if geo indexing is new to you)

### P1. Why is "near me" hard?

A location is just two numbers: **latitude** (north/south, −90 to 90) and **longitude**
(east/west, −180 to 180).

```
pois table
id | name          | lat     | lng
1  | Joe's Ramen   | 37.7749 | -122.4194
2  | Central Park  | 40.7829 |  -73.9654
...200 million rows
```

The obvious query for "within 2 km of me" is:

```sql
SELECT * FROM pois
WHERE lat BETWEEN 37.76 AND 37.79
  AND lng BETWEEN -122.43 AND -122.40;
```

A normal database index is a sorted list, so it can only sort by **one thing at a time**.

```
Index on lat alone matches a thin strip that wraps the whole planet:

   ─────────────────────────────────────────── lat 37.79
   ███████████████████████████████████████████  ← SF, but also Spain, Japan, Korea...
   ─────────────────────────────────────────── lat 37.76

Index on lng alone matches a strip running pole to pole:
             │█│
             │█│   ← SF, but also Alaska, Mexico, Antarctica...
             │█│

What you actually want is the small square where they cross:
             │█│
   ──────────┼█┼──────────
   ██████████│▓│██████████   ▓ = the answer
   ──────────┼█┼──────────
             │█│
```

The database grabs millions of rows from one strip and then filters them, which is slow.
**Every geo indexing technique solves the same problem: turning two dimensions into something
one sorted index can handle.**

### P2. The core trick: chop the map into grid cells

Draw a grid over the world and give each cell a name. Store the cell name on each POI.

```
 ┌─────┬─────┬─────┬─────┐
 │ A1  │ A2  │ A3  │ A4  │
 ├─────┼─────┼─────┼─────┤
 │ B1  │ B2 ●│ B3  │ B4  │   ● = Joe's Ramen → cell "B2"
 ├─────┼─────┼─────┼─────┤
 │ C1  │ C2  │ C3  │ C4  │
 └─────┴─────┴─────┴─────┘
```

"Near me" now becomes: **look up which cell I'm in, then fetch the POIs in that cell.** That's a
plain lookup on one column, which is fast.

```sql
SELECT * FROM pois WHERE cell = 'B2';
```

### P3. Geohash: the same grid, nested

Geohash cuts the world in half, then in half again, and keeps going. Each cut adds a character
to the name, so **a longer name means a smaller cell**.

```
"9"        → huge area (part of a continent)
"9q"       → a large region
"9q8"      → roughly the Bay Area
"9q8y"     → roughly a city
"9q8yy"    → ~5 km square
"9q8yyd"   → ~1 km square   ← good size for "near me"
```

The useful property is that **places that share a prefix are near each other.** Everything in
"9q8yy…" is in the same ~5 km area. That means a normal sorted index works:

```sql
SELECT * FROM pois WHERE geohash LIKE '9q8yyd%';
```

### P4. The edge problem (interviewers often ask about this)

Suppose you stand at the edge of your cell. A coffee shop 20 m away can be in the
**neighbouring** cell, so searching only your own cell misses it.

```
 ┌─────────┬─────────┐
 │         │         │
 │      me●│☕       │   ☕ is 20 m away but in a different cell
 │         │         │
 └─────────┴─────────┘
```

**Fix:** search your cell **plus the 8 cells around it**, then compute the exact distance to
each result and drop anything farther than the radius.

```
 ┌───┬───┬───┐
 │ ✓ │ ✓ │ ✓ │
 ├───┼───┼───┤
 │ ✓ │ ● │ ✓ │   9 cells → candidates → exact distance check → sort → top 20
 ├───┼───┼───┤
 │ ✓ │ ✓ │ ✓ │
 └───┴───┴───┘
```

### P5. Quadtree: a grid that adapts to density

A fixed grid has a weakness. A Manhattan cell might hold 50,000 POIs while a desert cell holds
0. A quadtree **only splits a cell when it gets crowded**:

```
 Rule: if a box holds more than 100 POIs, split it into 4.

 ┌───────────────┬───────────────┐
 │               │ ┌──┬──┐       │
 │   (empty      │ ├──┼──┤ city! │  ← keeps splitting where it's dense
 │    desert)    │ └──┴──┘       │
 ├───────────────┼───────────────┤
 │               │               │
 │  (farmland)   │  (small town) │  ← stays big where it's sparse
 └───────────────┴───────────────┘
```

It's a tree you keep in memory. To answer a query, you walk down to the box containing the user
and its neighbouring boxes.

### P6. What you'd actually use: off-the-shelf tools

In practice you don't build any of this yourself. These tools already do it:

- **PostGIS** (a Postgres extension): `WHERE ST_DWithin(location, my_point, 2000)`
- **Elasticsearch**: a `geo_point` field plus a `geo_distance` filter
- **Redis**: `GEOADD` / `GEOSEARCH` (internally it uses geohash)

### P7. What to say in the interview if you don't know this

Geo indexing is one section of a 45-minute interview. If you reason from first principles, the
interviewer gets the signal they're looking for. You could say something like:

> "A normal index can't search two dimensions efficiently, because lat and lng each match a huge
> strip. So I'd split the map into grid cells and store each POI's cell ID. Then 'near me' is a
> lookup on my cell plus the neighbouring cells, followed by an exact distance filter. Geohash is
> a standard way to name those cells. In production I'd use something built in, like
> Elasticsearch's geo_point or PostGIS, rather than building it myself."

That one paragraph covers the problem, the solution, the edge case and the practical choice. If
they push further, mention that a quadtree handles dense cities better than a fixed grid.

A common mistake is to say "I'll use PostGIS" and stop there. Explaining **why** a regular index
fails (P1) is what shows you understand it.

Section 6 below goes deeper on the same ideas.

---

## 1. Requirements

### Functional
| # | Feature | Notes |
|---|---------|-------|
| F1 | Search POIs by name, category, location | Free text ("ramen"), category filter, "near me" / within radius / map viewport |
| F2 | View POI details | Description, address, hours, photos, avg rating, paginated reviews |
| F3 | Add POIs | Goes through dedup + (light) moderation |
| F4 | Submit reviews + ratings | 1–5 stars + text, one review per user per POI (editable) |
| F5 | Upload photos | Several per POI, shown as thumbnails and full size |
| F6 | Radius search | "within 2 km of (lat, lng)", sorted by distance / relevance / rating |

### Non-functional
- **Latency**: search p99 < 200 ms, POI detail p99 < 100 ms.
- **Availability**: 99.99% for reads. Writes can degrade gracefully (queue them).
- **Scale**: millions of POIs, tens of millions of users.
- **Read : write** ≈ 100:1 or higher.
- **Consistency**:
  - POI core data (name, address, location, hours, status): **strong**. When an owner
    updates the hours or marks the place "permanently closed", every later read sees the change.
  - Reviews, ratings, photo counts: **eventual**, with seconds of lag allowed.

### Out of scope (say so explicitly)
Ads and sponsored ranking, reservations/ordering, messaging, a full recommendation/personalization
system, fraud ML (mentioned briefly only).

---

## 2. Back-of-the-envelope estimates

```
POIs                 : 200M                (worldwide, incl. long tail)
POI row size         : ~2 KB               -> 200M * 2KB      = ~400 GB   (fits in a sharded RDBMS)
Reviews              : 2B total, ~1 KB     -> ~2 TB
Photos               : 1B total, ~2 MB orig + thumbnails -> ~2-3 PB in object storage

DAU                  : 50M
Searches/user/day    : 5   -> 250M/day  ≈ 3K QPS avg,  ~10K QPS peak
Detail views/day     : 10  -> 500M/day  ≈ 6K QPS avg,  ~20K QPS peak
Photo fetches        : 20 per detail    -> ~400K req/s peak  (=> must be on a CDN)

Writes
  new reviews/day    : 2M   ≈ 25 QPS
  new photos/day     : 3M   ≈ 35 QPS  (~6 TB/day ingest)
  new/edited POIs    : 200K ≈ 2-3 QPS
```

Takeaways:
- POI metadata is **small**. The hot working set fits in memory (Redis), and a geo index over
  200M points fits in RAM across a modest cluster.
- Photo bandwidth dwarfs everything else, so it **has to** go through a CDN.
- Write QPS is tiny. Writes are not hard to scale. The hard parts are consistency and fan-out
  of derived data (search index, aggregates, caches).

---

## 3. API

```
# Search
GET  /v1/search?q=ramen&category=restaurant&lat=37.77&lng=-122.41&radius_m=2000
                &sort=relevance|distance|rating&open_now=true&cursor=<opaque>&limit=20
  -> { results: [{poi_id, name, category, lat, lng, distance_m,
                  avg_rating, review_count, thumb_url}], next_cursor }

GET  /v1/search/viewport?min_lat=..&min_lng=..&max_lat=..&max_lng=..&category=..  (map pan/zoom)

# POI
GET  /v1/pois/{poi_id}                      -> core data + rating summary + top photos
POST /v1/pois                               -> {name, category, address, lat, lng, hours, ...}
PATCH/v1/pois/{poi_id}   (If-Match: <version>)   optimistic concurrency on core data

# Reviews
GET  /v1/pois/{poi_id}/reviews?sort=newest|top|rating_desc&cursor=<opaque>&limit=20
POST /v1/pois/{poi_id}/reviews              -> {rating: 1..5, text}  (Idempotency-Key header)
PUT  /v1/reviews/{review_id}
DELETE /v1/reviews/{review_id}

# Photos (two-step: get presigned URL, upload directly to object storage)
POST /v1/pois/{poi_id}/photos:initUpload    -> {photo_id, upload_url (presigned PUT), expires_at}
POST /v1/pois/{poi_id}/photos/{photo_id}:complete  -> {status: "processing"}
GET  /v1/pois/{poi_id}/photos?cursor=..     -> [{photo_id, thumb_url, medium_url, full_url}]
```

Notes:
- **Cursor pagination** everywhere. Offset pagination falls over on deep pages and on
  lists that change while you page through them.
- **Idempotency keys** on POST so mobile retries don't create duplicate reviews.
- **`If-Match` / version** on POI updates so two concurrent editors can't silently overwrite each other.

---

## 4. High-level architecture

```
                                  ┌──────────────────────┐
     Mobile / Web clients ───────▶│   CDN (photos, static,│◀──── photo bytes (99% of bandwidth)
            │                     │   some search caching)│
            │                     └──────────┬───────────┘
            ▼                                │ origin miss
   ┌──────────────────┐                      ▼
   │ API Gateway / LB │              ┌───────────────┐
   │ auth, rate limit │              │ Object Storage│  (S3/GCS: originals + resized variants)
   └───┬────┬────┬────┘              └───────▲───────┘
       │    │    │                           │ presigned PUT (client uploads directly)
       │    │    └──────────────────┐        │
       ▼    ▼                       ▼        │
┌──────────┐ ┌───────────────┐ ┌─────────────┴──┐
│ Search   │ │  POI Service  │ │ Review/Photo   │
│ Service  │ │ (core data,   │ │ Service        │
│          │ │  strong cons.)│ │ (eventual)     │
└────┬─────┘ └──┬─────────┬──┘ └──┬──────────┬──┘
     │          │         │       │          │
     │     ┌────▼───┐ ┌───▼────┐ ┌▼────────┐ │ publish events
     │     │ Redis  │ │POI DB  │ │Review DB│ │ (review.created, photo.uploaded,
     │     │ cache  │ │Postgres│ │Cassandra│ │  poi.updated via CDC)
     │     │(detail,│ │+PostGIS│ │/Dynamo  │ │
     │     │ stats) │ │sharded │ │by poi_id│ │
     │     └────▲───┘ └───┬────┘ └─────────┘ │
     │          │         │ CDC (Debezium)   │
     │          │         ▼                  ▼
     │          │   ┌───────────────────────────────┐
     │          │   │        Kafka (event bus)      │
     │          │   └──┬──────────┬──────────┬──────┘
     │          │      │          │          │
     │          │      ▼          ▼          ▼
     │          │ ┌─────────┐ ┌─────────┐ ┌──────────────┐
     │          └─┤ Rating  │ │ Indexer │ │ Photo        │
     │            │Aggregator│ │         │ │ Processor    │
     │            └────┬────┘ └────┬────┘ │(resize, NSFW,│
     │                 │           │      │ EXIF strip)  │
     │                 ▼           ▼      └──────────────┘
     │          poi_stats table  ┌─────────────────────────┐
     │          (rating_sum,     │ Search Index            │
     └─────────────────────────▶│ Elasticsearch/OpenSearch │
                 queries          │ (text + geo_point +     │
                                  │  category + rating)     │
                                  └─────────────────────────┘
```

How data moves:
- **Source of truth for POIs** is the relational DB. The search index, caches and aggregates
  are all **derived** from it and can be rebuilt.
- **Writes** go to the owning service's DB. **Derived views** are updated asynchronously off Kafka.
- **Reads** go to cache → DB (POI detail) or to the search index (search).

---

## 5. Data model

### 5.1 POI DB (PostgreSQL + PostGIS), strongly consistent

```
pois
──────────────────────────────────────────────────────────
poi_id         BIGINT  PK        (Snowflake-style id)
name           TEXT
category_ids   INT[]             (restaurant, cafe, park ...)
description    TEXT
address        JSONB             (street, city, region, postal, country)
location       GEOGRAPHY(Point)  -- lat/lng, GiST index
geohash        CHAR(12)          -- precomputed, B-tree index (prefix scans)
phone, website TEXT
hours          JSONB             -- {mon:[["09:00","17:00"]], ..., tz:"America/LA"}
status         ENUM(active, closed_temp, closed_perm, pending_review, merged)
owner_user_id  BIGINT NULL
version        INT               -- optimistic locking for edits
created_at, updated_at

poi_stats            (separate table: high-churn, eventually consistent)
──────────────────────────────────────────────────────────
poi_id         BIGINT PK
rating_sum     BIGINT
rating_count   INT
rating_hist    INT[5]            -- count of 1★..5★ (for histogram UI)
photo_count    INT
bayes_score    REAL              -- precomputed ranking score
updated_at
```

**Why split `poi_stats` from `pois`?** Ratings change all the time and are eventually consistent.
Core data rarely changes and has to be strongly consistent. Keeping them in separate tables means
a rating update never contends with core data rows or invalidates them. Each one can also be cached
on its own TTL.

### 5.2 Reviews (Cassandra / DynamoDB, wide-column, partitioned by POI)

```
reviews_by_poi                     -- main access pattern: "reviews for this POI"
──────────────────────────────────────────────────────────
PARTITION KEY  poi_id
CLUSTERING     created_at DESC, review_id DESC
columns        user_id, rating, text, helpful_count, status, photo_ids

reviews_by_user                    -- "my reviews" + enforces 1 review/user/POI
──────────────────────────────────────────────────────────
PARTITION KEY  user_id
CLUSTERING     poi_id
columns        review_id, rating, created_at
```

Why a wide-column store: reviews are append-heavy and always read "by POI, newest first".
Once there are billions of rows, this partition and clustering layout serves that read
efficiently. Postgres partitioned by `poi_id` would also work at this write rate (25 QPS).
Either answer is defensible as long as you explain it.

Other sort orders ("top", "lowest rating") come from **extra denormalized tables**
(`reviews_by_poi_top`, clustered by `helpful_count`) or from the search index.

### 5.3 Photos

```
photos (metadata in DB; bytes in object storage)
──────────────────────────────────────────────────────────
photo_id, poi_id, user_id, review_id NULL,
storage_key   "photos/{poi_id}/{photo_id}/"   -> orig.jpg, 1080.webp, 320.webp, 64.webp
status        ENUM(uploading, processing, active, rejected)
width, height, created_at
```

---

## 6. Deep dive: geospatial indexing

Core query: **"Find POIs within R meters of (lat, lng), optionally matching text/category, ranked."**

A naive `WHERE lat BETWEEN .. AND lng BETWEEN ..` with two separate B-tree indexes is too slow.
Each index alone matches a huge band of the globe, and the DB has to intersect them.

### 6.1 Options

```
┌───────────────┬───────────────────────────────┬──────────────────────────────────────┐
│ Approach      │ How                           │ Trade-offs                           │
├───────────────┼───────────────────────────────┼──────────────────────────────────────┤
│ Geohash       │ Interleave lat/lng bits →     │ + simple, works in any KV/B-tree     │
│               │ base32 string. Shared prefix  │ + easy to shard & cache by cell      │
│               │ = nearby (mostly).            │ - edge effects → query 9 cells       │
│               │                               │ - fixed grid; dense cities skewed    │
├───────────────┼───────────────────────────────┼──────────────────────────────────────┤
│ Quadtree      │ Recursively split a cell into │ + adapts to density (Manhattan vs    │
│               │ 4 until ≤ K POIs per leaf.    │   Sahara)                            │
│               │ Usually in-memory.            │ - in-memory structure to build,      │
│               │                               │   replicate and rebuild              │
├───────────────┼───────────────────────────────┼──────────────────────────────────────┤
│ Google S2 /   │ Project the sphere onto cube  │ + better cell shapes, no pole issues │
│ Uber H3       │ faces / hexagons, Hilbert     │ + region covering for any shape      │
│               │ curve cell IDs (64-bit ints). │ - more complex library               │
├───────────────┼───────────────────────────────┼──────────────────────────────────────┤
│ R-tree / GiST │ PostGIS, ES/Lucene BKD trees  │ + exact radius/polygon queries, off  │
│ / BKD         │ index bounding boxes.         │   the shelf                          │
│               │                               │ + combine with text in one engine    │
│               │                               │ - harder to shard by hand            │
└───────────────┴───────────────────────────────┴──────────────────────────────────────┘
```

### 6.2 Geohash intuition (the part to draw on the whiteboard)

```
 Precision → cell size (approx)
   4 chars : 39 km × 19.5 km
   5 chars : 4.9 km × 4.9 km
   6 chars : 1.2 km × 0.61 km      ← good for "near me" (≈1-2 km radius)
   7 chars : 153 m × 153 m

 Query: 1 km around user U, who sits near the edge of cell "9q8yyd".
 A POI 50 m away might sit in the neighbouring cell with a different prefix,
 so we always search the cell plus its 8 neighbours:

        ┌─────────┬─────────┬─────────┐
        │ 9q8yyc  │ 9q8yyf  │ 9q8yyg  │
        ├─────────┼─────────┼─────────┤
        │ 9q8yy9  │ 9q8yyd ●U│ 9q8yye │   ● U = user
        ├─────────┼─────────┼─────────┤
        │ 9q8yy3  │ 9q8yy6  │ 9q8yy7  │
        └─────────┴─────────┴─────────┘
             ▲ circle of radius R spans several cells

 Steps:
   1. Pick precision p so that cell size ≳ R.
   2. cells = geohash(U, p) + 8 neighbours
   3. candidates = POIs WHERE geohash LIKE cell% for each cell  (9 prefix range scans)
   4. Filter exactly: haversine(U, poi) ≤ R
   5. Rank, top-K.
   If there are too few results, drop to p-1 (bigger cells) and repeat.
```

### 6.3 Quadtree (worth mentioning for density adaptivity)

```
                    ┌───────────────────────────────┐
                    │            World              │
                    └───┬──────────┬────────┬───────┘
                 NW ────┘     NE   │   SW   └──── SE
          ┌──────────────┐   (leaf: 40 POIs)  ...
          │  NW (dense)  │
          └─┬───┬───┬───┬┘
            │   │   │   └ leaf (87 POIs)
            │   │   └ leaf (12)
            │   └ split again (SF downtown: 10k POIs → keep splitting until ≤100/leaf)
            └ leaf (3)

  Memory: 200M POIs / 100 per leaf ≈ 2M leaves; each POI stores (id, lat, lng) ≈ 24B
          → ~5 GB + nodes: fits on one beefy box, so replicate it many times for read QPS.
  Updates: new POIs append to a leaf; rebuild/split offline or incrementally.
```

### 6.4 Recommendation

Use **Elasticsearch / OpenSearch** as the search engine. Store each POI as a document with a
`geo_point` field (backed by Lucene BKD trees) plus the text fields, categories, and rating
fields. A single query then handles **text + category filter + geo radius + ranking** together.
That combination is exactly what this product needs, and building it by hand from geohash
tables + an inverted index is a lot of work.

- Shard the index **by geography** (e.g. by S2 level-4/geohash-3 region → shard), so a
  "near me" query only touches 1–2 shards instead of fanning out to every shard.
  Hot regions (NYC, Tokyo) get more replicas.
- Keep PostGIS on the source-of-truth DB for admin tools, dedup checks ("is there already a
  POI within 30 m with a similar name?"), and as a fallback.
- Mention geohash/quadtree as **what the engine does internally** and as the answer if the
  interviewer says "no Elasticsearch, build it yourself". Section 6.2 is that build-it-yourself plan.

---

## 7. Deep dive: search path (< 200 ms)

```
Client ──▶ Gateway ──▶ Search Service
                          │
                          │ 1. normalize: q="ramen", category, (lat,lng), radius,
                          │    open_now, sort. Build cache key from
                          │    (geohash6(lat,lng), q, category, sort, page)
                          ▼
                     ┌──────────┐ hit (~30-50% for popular cells/queries)
                     │ Redis    │────────────────────────────────────▶ return (≈5 ms)
                     │ search   │
                     │ cache    │ miss
                     └────┬─────┘
                          ▼
             2. ES query on 1-2 geo shards:
                bool:
                  must:   multi_match(q → name^3, categories^2, review_keywords)
                  filter: geo_distance(R, U), term(category), term(status=active)
                function_score:
                  relevance * w1  +  bayes_score * w2  +  gauss(distance, scale=R/2) * w3
                size: 20, search_after: <cursor>
                          │   (≈ 20-60 ms)
                          ▼
             3. Hydrate (optional): batch MGET poi:{id} summaries from Redis
                (thumb_url, open_now computed from hours + tz)
                          │
                          ▼
             4. Return results + next_cursor; write to search cache (TTL 60-300 s)
```

Latency budget:

```
 Gateway + auth            5 ms
 Cache lookup              2 ms
 ES query (1-2 shards)    20-60 ms
 Hydration (Redis MGET)    5 ms
 Serialization + network  20-40 ms
 ──────────────────────────────────
 p50 ≈ 60-80 ms, p99 < 200 ms ✔
```

Details worth mentioning:
- **Autocomplete / typeahead**: a separate ES `completion` suggester or edge-ngram field, biased
  by the user's location.
- **Search cache key** uses a *coarsened* location (geohash-6) so nearby users share entries.
  Don't use exact lat/lng, or nothing would ever hit the cache.
- **Ranking** uses a Bayesian average, not the raw mean, so a POI with a single 5★ review doesn't
  outrank one with 4.6★ over 3,000 reviews (see §9).
- **Freshness**: the ES index lags the DB by ~1–5 s through CDC. Search is allowed to be
  slightly stale. The **detail page** is what must be strongly consistent (§10).

---

## 8. Deep dive: POI detail view

```
GET /v1/pois/123
        │
        ▼
 ┌─────────────┐   parallel fan-out (scatter-gather), each with a timeout
 │ POI Service │──┬──────────────────────┬────────────────────────┬────────────────┐
 └─────────────┘  ▼                      ▼                        ▼                ▼
          core data                rating summary            top photos       first page reviews
     Redis poi:123:v{ver}      Redis stats:123 (TTL 60s)   Redis photos:123   Review svc (cursor)
     └miss→ POI DB primary     └miss→ poi_stats            └miss→ photos tbl   └ Cassandra
        (see §10)
                  │                      │                        │                │
                  └──────────────┬───────┴────────────────────────┴────────────────┘
                                 ▼
                       merge → response (~30-60 ms)
                       photo URLs point at CDN, e.g. https://cdn.x.com/p/123/987/320.webp
```

If a non-critical piece (photos, reviews) times out, return the page without it
(**graceful degradation**). The core data piece is the only one that must succeed.

---

## 9. Deep dive: reviews, rating aggregation, pagination

### 9.1 Write path for a review (eventual consistency)

```
POST /reviews ──▶ Review Service
                     │ 1. auth, rate-limit, idempotency-key check
                     │ 2. conditional insert in reviews_by_user (poi_id, user_id)
                     │    → rejects a 2nd review by the same user (LWT / conditional put)
                     │ 3. insert reviews_by_poi
                     │ 4. emit event to Kafka (outbox pattern, so DB write + event are atomic)
                     ▼
               201 Created (user immediately sees their own review: client-side
                            optimistic insert + read-your-writes from the review partition)

Kafka topic "review-events" (partitioned by poi_id → per-POI ordering)
   │
   ├──▶ Rating Aggregator ──▶ UPDATE poi_stats SET rating_sum += Δ, rating_count += δ,
   │                              rating_hist[r] += 1 ... (idempotent by event_id)
   │                         ──▶ invalidate Redis stats:{poi_id}
   │                         ──▶ (batched) push new bayes_score to ES doc
   │
   ├──▶ Moderation / spam (async ML; can hide review later → emits review.hidden)
   │
   └──▶ Notification to POI owner, analytics, etc.
```

### 9.2 Aggregation math

Store a running **sum and count**, never recompute an average by scanning reviews:

```
 event               Δsum   Δcount
 create(rating=r)    +r     +1
 update(old→new)     new-old 0
 delete(rating=r)    -r     -1
 hidden by mod       -r     -1

 avg = rating_sum / rating_count

 Ranking score (Bayesian average, prior m reviews at global mean C):
   bayes = (C*m + rating_sum) / (m + rating_count)       e.g. C=3.7, m=20
```

- **Idempotency**: the aggregator records processed `event_id`s (or applies the update in the same
  transaction as an `(poi_id, last_offset)` row). Kafka redelivery then never double-counts.
- **Hot POIs** (a viral place getting 1000 reviews/min): partition by `poi_id` so updates are
  serialized, and **micro-batch** them (sum all deltas over 1 s, then do one UPDATE).
- **Drift repair**: a nightly batch job recomputes sum/count from the reviews table and fixes
  any drift.

### 9.3 Review pagination

```
Offset pagination (BAD at depth):       Keyset / cursor pagination (GOOD):
  SELECT ... ORDER BY created_at DESC     SELECT ... WHERE poi_id = ?
  LIMIT 20 OFFSET 40000                     AND (created_at, review_id) < (:c_ts, :c_id)
  → scans & discards 40k rows             ORDER BY created_at DESC, review_id DESC
  → duplicates/skips when new             LIMIT 20
    reviews arrive while paging           → O(page) using clustering order

cursor = base64({"ts": 1730000000, "id": 98765, "sort": "newest"})   (opaque to client)
```

- The first page of reviews for popular POIs is cached in Redis (TTL ~60 s, also invalidated on a
  new review). Deep pages go straight to Cassandra, which is cheap given the clustering order.
- "Top reviews" sort: a separate clustered table (or ES) ordered by `helpful_count`, recomputed
  periodically. It doesn't need to be live.

---

## 10. Deep dive: strong consistency for POI core data

The requirement: after a POI edit commits, **every** subsequent detail read returns the new data.
Read replicas and caches are the usual ways this breaks, so here is how each is handled:

```
                   PATCH /pois/123  (If-Match: v7)
                            │
                            ▼
                    ┌───────────────┐
                    │ POI Service   │
                    └───────┬───────┘
                            │ UPDATE pois SET ..., version = 8
                            │ WHERE poi_id=123 AND version=7    ← optimistic concurrency
                            ▼                                     (0 rows → 409 Conflict)
                 ┌─────────────────────┐
                 │ Shard primary (sync │  sync replica in another AZ
                 │ replication → 1 AZ) │──────────────▶ (no data loss on failover)
                 └──────────┬──────────┘
                            │ commit OK
                            ▼
                 Redis: SET poi:123:meta {version: 8}     (tiny pointer key)
                        DEL  poi:123:v7                   (best effort)
                            │
                            ▼
                      200 OK {version: 8}
                            │
                 CDC → Kafka → Indexer updates ES (async, search may lag a few s)

  Read path:
      ver = GET poi:123:meta             (Redis, strongly ordered per key)
      body = GET poi:123:v{ver}          hit → return
                                         miss → read from PRIMARY, populate v{ver}
```

Points to make:
- **Versioned cache keys**: a reader can never get a stale body from Redis, because it looks up the
  current version first. A stale `v7` entry can sit in the cache without harm. Nobody asks for it.
- **Reads that miss the cache go to the primary**, not to async replicas. That's affordable
  because the cache absorbs ~95%+ of reads and the data is tiny. Async replicas serve search
  indexing, analytics, and admin scans. If you really need replicas for detail reads, route them
  with **LSN tracking**: only use a replica whose replay position ≥ the commit LSN of the latest
  version.
- If Redis is unavailable → fall back to the primary (protected by a circuit breaker and a
  request-coalescing layer).
- **Failover**: synchronous replication to one standby (or a consensus-based store such as
  Spanner / CockroachDB / Aurora) means a primary loss doesn't lose committed edits.
- **Search results** are explicitly allowed to be a few seconds stale. Clicking through to detail
  always shows the truth. A closed POI briefly appearing in search is acceptable. A closed POI on
  the detail page is not.

**Adding a new POI**:
```
 POST /pois ─▶ normalize address ─▶ geocode (lat/lng) ─▶ dedup check:
     PostGIS: ST_DWithin(location, :pt, 50m) AND similarity(name, :name) > 0.7
        ├─ likely duplicate → return existing / ask user "Is it this one?"
        └─ new → INSERT status='pending_review' (or 'active' for trusted users)
                 → moderation queue → active → CDC → indexed
```

---

## 11. Deep dive: photos

```
 ① initUpload                                  ③ PUT bytes directly (bypasses our servers)
 Client ──────────▶ Photo Service              Client ───────────────────────▶ Object Storage
        ◀────────── {photo_id, presigned_url}                                   (bucket: raw/)
                    (row: status=uploading)                                         │
                                                                                    │ ④ ObjectCreated
 ② ...                                                                              ▼    event
                                                                          ┌───────────────────┐
                                                                          │ Queue (SQS/Kafka) │
                                                                          └─────────┬─────────┘
                                                                                    ▼
                                                                          ┌───────────────────┐
                                                                          │ Photo Workers     │
                                                                          │ - validate type   │
                                                                          │ - strip EXIF/GPS  │
                                                                          │ - NSFW / spam ML  │
                                                                          │ - resize: 64/320/ │
                                                                          │   1080 + WebP/AVIF│
                                                                          └─────────┬─────────┘
                                                                                    │ write variants
                                                                                    ▼
                                                                         Object Storage (public/)
                                                                                    │
                                    status=active, photo_count += 1  ◀──────────────┘
                                                                                    
 Serving:
   Client ──▶ CDN edge ──(miss)──▶ Origin shield ──(miss)──▶ Object Storage
     URLs are immutable & content-addressed:  /p/{poi_id}/{photo_id}/{size}.webp
     → Cache-Control: public, max-age=31536000, immutable   (cache hit ratio > 98%)
```

- **Presigned URLs**: upload bytes never pass through app servers, which saves bandwidth and
  keeps the app tier stateless and cheap. The URL is short-lived and capped by size/type.
- **Immutable URLs**: there's no CDN invalidation problem. A changed photo gets a new photo_id.
- **Storage tiering**: originals move to infrequent-access/cold storage after 30 days. Only the
  resized variants stay hot.
- Deleting or moderating a photo: mark it `rejected` in the DB so the API stops returning the
  URL, and issue a CDN purge for that path (rare).

---

## 12. Scaling for high read traffic

```
          request
             │
   ┌─────────▼──────────┐   L0: client cache (ETag / If-None-Match on POI detail)
   │   CDN edge         │   L1: photos, static assets, (optionally) anonymous search
   └─────────┬──────────┘       responses for coarse geo cells, short TTL
             │
   ┌─────────▼──────────┐   L2: in-process LRU in services (hot POI summaries, ~1-5 s TTL
   │ Service local LRU  │       for eventual data only; NOT for core data)
   └─────────┬──────────┘
             │
   ┌─────────▼──────────┐   L3: Redis cluster (POI detail, stats, review page 1,
   │ Redis cluster      │       search results). Consistent hashing, replicas per shard.
   └─────────┬──────────┘
             │
   ┌─────────▼──────────┐   L4: datastores
   │ ES  │ PG  │ Cass.  │       ES: geo-sharded, replicas scale reads
   └────────────────────┘       PG: sharded by poi_id, primary + sync standby + async replicas
                                Cassandra: partitioned by poi_id, RF=3
```

**Sharding**
- **POI DB**: shard by `hash(poi_id)` for even load. Geo queries don't hit the DB (ES serves
  them), so geo locality in the DB doesn't matter. ~400 GB means only a handful of shards are needed.
- **ES**: shard by **geographic region**, so a local query only touches nearby shards. Split
  hot regions into more shards and replicas.
- **Reviews**: partition by `poi_id`. For mega-popular POIs, bucket the partition
  (`poi_id#bucket_month`) so it doesn't grow without bound.

**Hot keys** (a famous restaurant goes viral):
- Replicate hot keys across Redis replicas, or use a local LRU with short TTL.
- **Request coalescing / single-flight**: on a cache miss, only one request rebuilds the entry.
  The others wait for it, which prevents a thundering herd.
- Add TTL jitter to avoid synchronized expiries.

**Multi-region**
```
   ┌───────── US region ─────────┐         ┌──────── EU region ─────────┐
   │ API, ES (full replica),     │◀──────▶│ API, ES (full replica),     │
   │ Redis, Cassandra (local DC) │ async   │ Redis, Cassandra (local DC) │
   │ POI DB: primary for US POIs │ repl.   │ POI DB: primary for EU POIs │
   └─────────────────────────────┘         └─────────────────────────────┘
```
- Home each POI's core data in the region where the POI physically is (a "geo-homed primary").
  Edits are routed to that region, which keeps strong consistency per POI. Most traffic for a
  POI is local anyway.
- Reviews and photo metadata use multi-DC Cassandra (LOCAL_QUORUM), which is eventually
  consistent across regions. That matches the requirement.

---

## 13. Reliability, abuse, and operations

- **Rate limits** on writes per user/IP: reviews, POI creation, photo uploads.
- **Fake reviews**: async ML scoring. Suspicious reviews are hidden (and the aggregator subtracts
  them). New accounts' reviews carry less weight in `bayes_score`.
- **Index rebuild**: because ES is derived, we can rebuild it from a DB snapshot plus a Kafka
  replay into a new index, then switch an alias. No downtime.
- **Backpressure**: if Kafka consumers lag, writes still succeed. Only the derived views
  (search/ratings) get staler. Alert when consumer lag exceeds N seconds.
- **Monitoring**: search p50/p99, cache hit ratio per layer, CDC lag, aggregator lag, ES shard
  hotness, CDN hit ratio.

---

## 14. Summary: key decisions and trade-offs

```
┌─────────────────────────────┬──────────────────────────────┬───────────────────────────────┐
│ Decision                    │ Choice                       │ Why / trade-off               │
├─────────────────────────────┼──────────────────────────────┼───────────────────────────────┤
│ Source of truth for POIs    │ Sharded Postgres (+PostGIS)  │ Strong consistency, txns,     │
│                             │ sync standby                 │ optimistic locking            │
│ Text + geo search           │ Elasticsearch, geo-sharded   │ One query for text+geo+rank;  │
│                             │ fed by CDC                   │ seconds of staleness OK       │
│ Geo index concept           │ Geohash/S2 cells (BKD in ES) │ 9-cell lookup; quadtree if    │
│                             │                              │ density adaptivity needed     │
│ Reviews                     │ Cassandra by poi_id,         │ Append-heavy, cursor paging,  │
│                             │ clustered by time            │ eventual consistency OK       │
│ Ratings                     │ Running sum/count via Kafka  │ O(1) reads; idempotent; batch │
│                             │ aggregator + Bayesian score  │ for hot POIs; nightly repair  │
│ Photos                      │ Presigned upload → S3 →      │ Bytes never touch app tier;   │
│                             │ workers → CDN (immutable)    │ ~98% CDN hit ratio            │
│ Read scaling                │ CDN + Redis + replicas +     │ Versioned cache keys keep core│
│                             │ versioned keys               │ data strongly consistent      │
│ Pagination                  │ Keyset cursors               │ O(page), stable under inserts │
└─────────────────────────────┴──────────────────────────────┴───────────────────────────────┘
```

**One-sentence pitch:** Postgres is the strongly consistent source of truth for POIs. A
CDC-fed, geo-sharded Elasticsearch index serves text + radius search in under 200 ms. Reviews
live in a POI-partitioned wide-column store and update aggregates asynchronously through Kafka.
Photos are uploaded directly to object storage and served from a CDN. Layered caches with
versioned keys absorb the read load without breaking consistency for core POI data.
