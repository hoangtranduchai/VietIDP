# -*- coding: utf-8 -*-
"""
RAG Engine — Retrieval-Augmented Generation
=============================================
Tích hợp ChromaDB + Ollama Embeddings cho tìm kiếm ngữ nghĩa
trên văn bản hành chính cực dài (>50 trang).

Workflow:
  1. Chia văn bản thành chunks
  2. Embed bằng nomic-embed-text (qua Ollama)
  3. Lưu vào ChromaDB (persistent local)
  4. Query: embed câu hỏi → tìm top-K chunks → đưa vào LLM
"""

import os
import json
import hashlib
import requests
from pathlib import Path

from src.config import Config


class RAGEngine:
    """
    RAG Engine sử dụng ChromaDB local + Ollama embeddings.
    Hoàn toàn offline, không gửi dữ liệu ra internet.
    """

    def __init__(self, collection_name="vietidp_docs",
                 persist_dir=None, embedding_model="nomic-embed-text"):
        self.embedding_model = embedding_model
        self.ollama_embed_url = Config.OLLAMA_URL.replace("/api/generate", "/api/embeddings")
        self.collection = None
        self.client = None

        persist_dir = persist_dir or str(Config.DATA_DIR / "chromadb")
        os.makedirs(persist_dir, exist_ok=True)

        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"✅ RAG Engine initialized (ChromaDB: {persist_dir})")
            print(f"   Collection '{collection_name}': {self.collection.count()} documents")
        except ImportError:
            print("⚠️ ChromaDB chưa cài. Chạy: pip install chromadb")
        except Exception as e:
            print(f"⚠️ RAG init error: {e}")

    def _get_embedding(self, text: str) -> list:
        """Lấy embedding vector từ Ollama (nomic-embed-text)."""
        try:
            response = requests.post(
                self.ollama_embed_url,
                json={"model": self.embedding_model, "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("embedding", [])
        except Exception as e:
            print(f"⚠️ Embedding error: {e}")
        return []

    def _chunk_text(self, text: str, chunk_size: int = 1000,
                    overlap: int = 200) -> list:
        """Chia text thành chunks theo paragraph boundary."""
        if len(text) <= chunk_size:
            return [text]

        paragraphs = text.split('\n')
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 1 > chunk_size and current:
                chunks.append(current.strip())
                overlap_text = current[-overlap:] if len(current) > overlap else ""
                current = overlap_text + '\n' + para
            else:
                current += '\n' + para if current else para

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def add_document(self, doc_id: str, text: str, metadata: dict = None):
        """
        Index 1 văn bản vào ChromaDB.

        Args:
            doc_id: ID duy nhất của văn bản
            text: Nội dung văn bản
            metadata: Metadata bổ sung (tên file, ngày, v.v.)
        """
        if self.collection is None:
            print("⚠️ ChromaDB chưa sẵn sàng")
            return

        chunks = self._chunk_text(text)
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            embedding = self._get_embedding(chunk)
            if not embedding:
                continue

            ids.append(chunk_id)
            documents.append(chunk)
            embeddings.append(embedding)
            meta = {"doc_id": doc_id, "chunk_index": i, "total_chunks": len(chunks)}
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)

        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            print(f"  ✅ Indexed {len(ids)} chunks for '{doc_id}'")

    def query(self, question: str, n_results: int = 5,
              doc_id_filter: str = None) -> list:
        """
        Tìm kiếm ngữ nghĩa trong ChromaDB.

        Args:
            question: Câu hỏi
            n_results: Số kết quả trả về
            doc_id_filter: Lọc theo doc_id cụ thể

        Returns:
            list[dict]: Danh sách chunks phù hợp nhất
        """
        if self.collection is None:
            return []

        query_embedding = self._get_embedding(question)
        if not query_embedding:
            return []

        where_filter = {"doc_id": doc_id_filter} if doc_id_filter else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        chunks = []
        if results and results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                chunks.append({
                    'text': doc,
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0,
                })

        return chunks

    def query_and_answer(self, question: str, doc_id: str = None,
                         n_results: int = 5) -> tuple:
        """
        RAG pipeline: query ChromaDB → build context → gọi LLM.

        Returns:
            tuple: (answer_str, source_chunks)
        """
        from src.llm.ollama_client import OllamaClient
        from src.llm.prompts import PROMPTS

        chunks = self.query(question, n_results=n_results, doc_id_filter=doc_id)

        if not chunks:
            return "Không tìm thấy thông tin liên quan trong cơ sở dữ liệu.", []

        context = "\n---\n".join([c['text'] for c in chunks])

        prompt = PROMPTS['chat'].format(context=context, question=question)

        client = OllamaClient()
        result, error = client.generate(prompt, format_json=False)

        if error:
            return f"Lỗi LLM: {error}", chunks

        return result, chunks

    def delete_document(self, doc_id: str):
        """Xóa tất cả chunks của 1 văn bản."""
        if self.collection is None:
            return
        existing = self.collection.get(where={"doc_id": doc_id})
        if existing and existing['ids']:
            self.collection.delete(ids=existing['ids'])
            print(f"  🗑️ Deleted {len(existing['ids'])} chunks for '{doc_id}'")

    @property
    def total_documents(self) -> int:
        """Tổng số chunks trong collection."""
        return self.collection.count() if self.collection else 0
