from rank_bm25 import BM25Okapi
from nltk.tokenize import word_tokenize


class BM25Reranker:
    def __init__(self, tokenizer=word_tokenize):
        self.tokenizer = tokenizer
        self.bm25 = None

    def preprocess(self, text):
        return self.tokenizer(text.lower())

    def fit(self, documents):
        tokenized_docs = [self.preprocess(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def rerank(self, query, top_k=3):
        tokenized_query = self.preprocess(query)
        scores = self.bm25.get_scores(tokenized_query)
        return sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
