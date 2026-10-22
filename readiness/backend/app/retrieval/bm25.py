import math
import re
from typing import List, Dict, Tuple, Any
from app.retrieval.aliases import normalize_text


class BM25Retriever:
    """
    Lightweight, fast in-memory BM25 ranker for symptoms, manual passages, and causes.
    Guaranteed sub-10ms response time without external services.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus: List[Dict[str, Any]] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}

    def index(self, documents: List[Dict[str, Any]]) -> None:
        """
        documents: List of dicts, each must have 'id' and 'text', plus arbitrary metadata.
        """
        self.corpus = documents
        self.doc_lengths = []
        self.doc_freqs = {}

        total_length = 0
        for doc in documents:
            tokens = self._tokenize(doc.get("text", ""))
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        n_docs = len(documents)
        self.avg_doc_len = (total_length / n_docs) if n_docs > 0 else 0.0

        # Calculate IDF
        self.idf = {}
        for token, freq in self.doc_freqs.items():
            self.idf[token] = math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)

    def _tokenize(self, text: str) -> List[str]:
        norm = normalize_text(text)
        return [t for t in norm.split() if len(t) > 1]

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        tokens = self._tokenize(query)
        if not tokens or not self.corpus:
            return []

        scores: List[float] = [0.0] * len(self.corpus)

        for i, doc in enumerate(self.corpus):
            doc_tokens = self._tokenize(doc.get("text", ""))
            doc_len = self.doc_lengths[i]
            tf: Dict[str, int] = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            doc_score = 0.0
            for token in tokens:
                if token not in tf:
                    continue
                token_tf = tf[token]
                token_idf = self.idf.get(token, 0.0)
                numerator = token_tf * (self.k1 + 1.0)
                denominator = token_tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0))
                doc_score += token_idf * (numerator / denominator)

            scores[i] = doc_score

        indexed_scores = [(self.corpus[i], scores[i]) for i in range(len(self.corpus)) if scores[i] > 0.0]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores[:top_k]
