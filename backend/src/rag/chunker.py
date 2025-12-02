from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


@dataclass
class DocumentChunk:
    """Document chunk data class"""
    content: str
    token_count: int
    metadata: Dict[str, Any]


class DocumentChunker:
    """Document chunker"""
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding_name = encoding_name
        # Prepare encoder in advance to avoid repeated creation
        self._encoding = tiktoken.get_encoding(encoding_name)

    def chunk_document(
        self,
        content: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """Chunk document"""
        if not content:
            return []

        base_metadata = metadata.copy() if metadata else {}

        Hsplitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "H1"),
                ("##", "H2"),
                ("###", "H3"),
                ("####", "H4"),
                ("#####", "H5"),
                ("######", "H6"),
            ]
        )
        markdown_documents = Hsplitter.split_text(content)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        split_documents = text_splitter.split_documents(markdown_documents)

        chunks: List[DocumentChunk] = []

        for doc in split_documents:
            chunk_content = doc.page_content.strip()
            if not chunk_content:
                continue

            chunk_metadata = {**doc.metadata, **base_metadata}

            chunks.append(DocumentChunk(
                content=chunk_content,
                token_count=self._count_tokens(chunk_content),
                metadata=chunk_metadata,
            ))

        if not chunks:
            return [DocumentChunk(
                content=content,
                token_count=self._count_tokens(content),
                metadata=base_metadata,
            )]

        return chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        return len(self._encoding.encode(text))
    
