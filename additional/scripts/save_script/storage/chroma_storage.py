import os

import chromadb
from UnionChatBot.utils.EmbeddingAPI import MyEmbeddingFunction
from UnionChatBot.utils.save_script.models.document import Document
from typing import List


class ChromaStorage:
    def __init__(self, host="localhost", port=8000):
        self.client = chromadb.HttpClient(host=host, port=port)
        self.embedding_func = MyEmbeddingFunction(
            api_url=os.getenv("EMBEDDING_API"),
            folder_id=os.getenv("FOLDER_ID"),
            iam_token=os.getenv("API_KEY"),
        )

    def get_collection(self, name: str):
        return self.client.get_or_create_collection(
            name=name,
            embedding_function=self.embedding_func,
            metadata={"hnsw:space": "cosine"},
        )

    def store_documents(self, coll_name: str, documents: List[Document]) -> None:
        collection = self.get_collection(coll_name)
        existing_ids = set(
            collection.get(ids=[doc.doc_id for doc in documents]).get("ids", [])
        )
        new_docs = [doc for doc in documents if doc.doc_id not in existing_ids]
        if not new_docs:
            print("Нет новых документов")
            return
        contents = [doc.content for doc in new_docs]
        metas = [doc.metadata for doc in new_docs]
        ids = [doc.doc_id for doc in new_docs]
        collection.add(documents=contents, metadatas=metas, ids=ids)
        print(f"Добавлено {len(ids)} документов")
