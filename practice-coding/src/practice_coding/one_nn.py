"""
Nearest Neighbor Classifier (1-NN -> KNN)

More likely in ML-adjacent roles. No numpy or sklearn for Parts 1-3 unless
the interviewer allows it.

Part 1 - 1-NN
    fit(points: list[list[float]], labels: list[str])
    predict(point) -> label of the closest training point (Euclidean).

Part 2 - KNN
    predict(point, k) -> majority label among the k nearest neighbors.
    Decide and document how ties are broken. Use a heap to find the k
    nearest instead of sorting everything.

Part 3 - Evaluation
    Split data into train/test sets and report accuracy. Pick k by
    trying several values.

Part 4 - Follow-ups to be ready to discuss
    - Vectorize with numpy; complexity of predict for n points in d dims.
    - Other distance metrics (Manhattan, cosine) and feature scaling.
    - Faster nearest-neighbor search: KD-trees, approximate NN (embeddings).

Sources:
    https://www.interviewquery.com/interview-guides/openai-software-engineer
    https://www.tryexponent.com/guides/openai-research-engineer-interview-guide
"""
