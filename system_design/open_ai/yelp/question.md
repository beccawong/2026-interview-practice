QUESTION: POI System (Yelp-like)

Design a Point of Interest (POI) system similar to Yelp.

Functional Requirements:
- Users can search for POIs (restaurants, shops, parks, etc.) by name, category, or location.
- Users can view details of a POI, including description, address, photos, ratings, and reviews.
- Users can add new POIs and submit reviews and ratings for existing POIs.
- Users can upload photos for a POI.
- The system should support searching for POIs ⁤⁣‌⁣⁡‌⁢‌⁡‍⁣⁡‌⁢‍⁣‌‌⁢‌⁢‌⁡⁢‌⁢⁣⁢‌⁡‌⁢‌⁢‌⁤⁡‍⁢⁣‌⁢‌⁡⁢‍‍⁢‌⁣⁢‌⁣⁡‌‍‍⁡‌⁤⁡‌‍⁤‌‍⁤‌⁢‌⁣⁡⁢⁡⁤‌⁡‍⁡‍⁡‍⁣⁡‌⁡‌⁡‌⁤⁡‌⁢‍⁡⁤⁣⁡‍⁢⁡‍‍⁣⁡⁢‌⁡‍⁡‌near a given geographic location (e.g., within a radius).

Non-Functional Requirements:
- Low latency for search and POI detail views (e.g., < 200ms for search).
- High availability and scalability to support millions of POIs and users.
- The system should handle a high read-to-write ratio (reads are much more frequent than writes).
- Data consistency for reviews and ratings should be eventual, but POI core data should be strongly consistent.

Design Considerations:
- How to model POI data and geographic location for efficient spatial queries.
- How to index and search POIs by text and location (e.g., geohashing, quadtree, or spatial databases).
- How to store and serve photos (e.g., object storage with CDN).
- How to handle rating aggregation and review pagination.
- How to scale the system for high read traffic (e.g., caching, read replicas).
