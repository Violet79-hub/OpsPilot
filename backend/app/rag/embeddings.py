"""Offline sparse lexical embeddings. No claim of pretrained semantic embeddings."""

from sklearn.feature_extraction.text import HashingVectorizer
from app.config import EMBEDDING_DIM

vectorizer = HashingVectorizer(
    n_features=EMBEDDING_DIM,
    alternate_sign=False,
    norm="l2",
    ngram_range=(1, 2),
    stop_words="english",
)


def embed(texts: list[str]) -> list[list[float]]:
    return vectorizer.transform(texts).toarray().tolist()
