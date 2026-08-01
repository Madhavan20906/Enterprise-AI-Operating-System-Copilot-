from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from app.config import settings
import logging
import numpy as np

logger = logging.getLogger(__name__)

class QdrantRAG:
    def __init__(self):
        self.client = None
        self.embeddings = None
        self.reranker = None
        
        if settings.QDRANT_HOST:
            try:
                self.client = QdrantClient(
                    host=settings.QDRANT_HOST,
                    port=settings.QDRANT_PORT,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    https=False,
                    check_compatibility=False
                )
                logger.info("Connected to Qdrant.")
                # Ensure the collection exists
                self._ensure_collection_exists()
            except Exception as e:
                logger.error(f"Qdrant connection failed: {e}")
        
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")

        try:
            # Load cross-encoder for re-ranking if model name is configured
            self.reranker = CrossEncoder(settings.RERANKER_MODEL)
            logger.info("Loaded CrossEncoder reranker.")
        except Exception as e:
            logger.warning(f"Could not load CrossEncoder reranker, fallback to score-based: {e}")

    def _ensure_collection_exists(self):
        if not self.client:
            return
        
        collections = self.client.get_collections().collections
        exists = any(c.name == settings.QDRANT_COLLECTION for c in collections)
        
        if not exists:
            # Default vector size for all-MiniLM-L6-v2 is 384
            vector_size = 384
            self.client.create_collection(
                collection_name=settings.QDRANT_COLLECTION,
                vectors_config=qmodels.VectorParams(
                    size=vector_size,
                    distance=qmodels.Distance.COSINE
                )
            )
            # Create text index for keyword search
            self.client.create_payload_index(
                collection_name=settings.QDRANT_COLLECTION,
                field_name="content",
                field_schema=qmodels.TextIndexParams(
                    type="text",
                    tokenizer=qmodels.TokenizerType.WORD,
                    min_token_len=2,
                    max_token_len=20,
                    lowercase=True
                )
            )
            logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION}")

    def search_dense(self, query: str, limit: int = 10, filter_dict: dict = None) -> list[dict]:
        """
        Dense Vector Retrieval
        """
        if not self.client or not self.embeddings:
            return []
        
        query_vector = self.embeddings.embed_query(query)
        
        q_filter = self._build_qdrant_filter(filter_dict)
        
        results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=limit,
            query_filter=q_filter
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content", ""),
                "metadata": hit.payload
            }
            for hit in results
        ]

    def search_keyword(self, query: str, limit: int = 10, filter_dict: dict = None) -> list[dict]:
        """
        Keyword Retrieval using Qdrant full-text index
        """
        if not self.client:
            return []
        
        q_filter = self._build_qdrant_filter(filter_dict)
        
        # Combine keyword query filter with metadata filter
        text_match_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="content",
                    match=qmodels.MatchText(text=query)
                )
            ]
        )
        if q_filter:
            text_match_filter.must.extend(q_filter.must or [])
            text_match_filter.should.extend(q_filter.should or [])
            text_match_filter.must_not.extend(q_filter.must_not or [])
            
        results = self.client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=text_match_filter,
            limit=limit,
            with_payload=True
        )[0]
        
        return [
            {
                "id": hit.id,
                "score": 1.0,  # scroll doesn't have vector scores
                "content": hit.payload.get("content", ""),
                "metadata": hit.payload
            }
            for hit in results
        ]

    def search_hybrid(self, query: str, limit: int = 10, filter_dict: dict = None) -> list[dict]:
        """
        Hybrid Search (Dense + Keyword combined using Reciprocal Rank Fusion)
        """
        dense_results = self.search_dense(query, limit=limit * 2, filter_dict=filter_dict)
        keyword_results = self.search_keyword(query, limit=limit * 2, filter_dict=filter_dict)
        
        # Apply Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        k = 60  # RRF constant
        
        def add_scores(results):
            for rank, hit in enumerate(results):
                doc_id = hit["id"]
                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = {"hit": hit, "score": 0.0}
                rrf_scores[doc_id]["score"] += 1.0 / (k + rank + 1)
        
        add_scores(dense_results)
        add_scores(keyword_results)
        
        sorted_docs = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
        
        results = []
        for item in sorted_docs[:limit]:
            hit = item["hit"]
            hit["rrf_score"] = item["score"]
            results.append(hit)
            
        return results

    def rerank_results(self, query: str, hits: list[dict], limit: int = 5) -> list[dict]:
        """
        Re-ranks retrieved documents using a Cross-Encoder
        """
        if not hits:
            return []
        
        if not self.reranker:
            # Fallback to simple top limit based on existing score
            return hits[:limit]
            
        pairs = [[query, hit["content"]] for hit in hits]
        scores = self.reranker.predict(pairs)
        
        for idx, score in enumerate(scores):
            hits[idx]["rerank_score"] = float(score)
            
        sorted_hits = sorted(hits, key=lambda x: x["rerank_score"], reverse=True)
        return sorted_hits[:limit]

    def _build_qdrant_filter(self, filter_dict: dict) -> qmodels.Filter | None:
        if not filter_dict:
            return None
            
        conditions = []
        for key, val in filter_dict.items():
            if val is not None:
                if isinstance(val, list):
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchAny(any=val)
                        )
                    )
                else:
                    conditions.append(
                        qmodels.FieldCondition(
                            key=key,
                            match=qmodels.MatchValue(value=val)
                        )
                    )
                    
        return qmodels.Filter(must=conditions) if conditions else None

    def index_splits(self, splits: list, document_id: int, filename: str, extra_meta: dict = None) -> int:
        """
        Helper method to index document chunks into Qdrant.
        """
        if not self.client or not self.embeddings:
            return 0
            
        texts = [split.page_content for split in splits]
        vectors = self.embeddings.embed_documents(texts)
        
        points = []
        for idx, (text, vector) in enumerate(zip(texts, vectors)):
            payload = {
                "document_id": document_id,
                "filename": filename,
                "content": text,
                "chunk_index": idx,
                **(extra_meta or {})
            }
            # Copy other metadata fields from splits if present
            if hasattr(splits[idx], "metadata") and splits[idx].metadata:
                payload.update(splits[idx].metadata)
                
            points.append(
                qmodels.PointStruct(
                    id=f"{document_id}_{idx}",
                    vector=vector,
                    payload=payload
                )
            )
            
        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points
        )
        return len(points)

    def delete_document_points(self, document_id: int):
        if not self.client:
            return
        self.client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id)
                        )
                    ]
                )
            )
        )

qdrant_rag = QdrantRAG()
