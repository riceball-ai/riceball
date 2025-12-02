import logging
from typing import Dict, Any, List, Optional

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document as VectorDocument
from langchain_core.vectorstores import VectorStoreRetriever

from src.config import settings


logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """Encapsulate Chroma vector store operations"""

    def __init__(self) -> None:
        self.host = settings.CHROMA_SERVER_HOST
        self.port = settings.CHROMA_SERVER_PORT


    def _get_collection(
        self,
        collection_name: str,
        embedding_function: Optional[Embeddings] = None,
    ) -> Chroma:
        kwargs: Dict[str, Any] = {
            "collection_name": collection_name,
            "host": self.host,
            "port": self.port
        }
        if embedding_function is not None:
            kwargs["embedding_function"] = embedding_function

        return Chroma(**kwargs)
    

    async def get_retriever(
        self,
        collection_name: str,
        embedding_function: Embeddings,
        **kwargs: Any
    ) -> VectorStoreRetriever:
        collection = self._get_collection(
            collection_name,
            embedding_function=embedding_function,
        )
        retriever = collection.as_retriever(**kwargs)
        return retriever
    

    async def add_documents(
        self,
        collection_name: str,
        documents: List[VectorDocument],
        embedding_function: Optional[Embeddings] = None,
    ) -> None:
        if not documents:
            return

        collection = self._get_collection(
            collection_name,
            embedding_function=embedding_function,
        )

        # Ensure each document has valid string content
        for doc in documents:
            if not isinstance(doc.page_content, str):
                raise ValueError(f"Document content must be a string, got {type(doc.page_content)}")
            if not doc.page_content.strip():
                raise ValueError("Document content cannot be empty")

        # Extract document IDs
        ids = [doc.id for doc in documents]

        try:
            await collection.aadd_documents(
                documents=documents,
                ids=ids
            )
        except Exception as exc:
            logger.error(
                "Failed to add documents to Chroma collection %s: %s",
                collection_name,
                exc,
            )
            raise


    async def delete_documents(
        self,
        collection_name: str,
        ids: List[str],
    ) -> None:
        if not ids:
            return

        collection = self._get_collection(collection_name)

        try:
            await collection.adelete(ids=ids)
        except Exception as exc:
            logger.error(
                "Failed to delete documents %s from Chroma collection %s: %s",
                ids,
                collection_name,
                exc,
            )
            raise