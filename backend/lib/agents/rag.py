from typing import Literal, Optional, List
from pydantic import Field, BaseModel
from ..node import Node

class RAGNode(Node):
    """
    A node that ingests a Pathway table of documents and creates a fully
    processed and indexed DocumentStore. This node acts as a sink,
    encapsulating the parsing, splitting, embedding, and indexing pipeline.
    """
    category: Literal["rag"] = "rag"
    node_id: Literal["rag_node"] = "rag_node"
    description: str
    n_inputs: Literal[1] = 1 

    # --- Parser Configuration ---
    parser_type: Literal["Unstructured"] = Field(
        default="Unstructured",
        description="The type of parser to use for processing raw documents."
    )
    # Add specific UnstructuredParser settings if needed, e.g.:
    # parser_chunking_mode: Optional[str] = Field(default="elements", description="Chunking mode for the parser.")

    # --- Splitter Configuration ---
    splitter_type: Literal["TokenCount"] = Field(
        default="TokenCount",
        description="The type of splitter to use for chunking documents."
    )
    splitter_max_tokens: int = Field(
        default=512,
        description="The maximum number of tokens per chunk."
    )
    splitter_min_tokens: int = Field(
        default=50,
        description="The minimum number of tokens per chunk."
    )

    # --- Embedder Configuration ---
    embedder_type: Literal["Gemini", "OpenAI", "SentenceTransformer"] = Field(
        default="Gemini",
        description="The embedding model provider to use."
    )
    embedder_model: str = Field(
        default="models/text-embedding-004",
        description="The specific model name for the selected embedder."
    )
    google_api_key: Optional[str] = Field(
        default=None,
        description="API key for Google Gemini embedder."
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="API key for OpenAI embedder."
    )

    # --- Retriever/Index Configuration ---
    retriever_type: Literal["Vector", "Hybrid"] = Field(
        default="Hybrid",
        description="The retrieval strategy. 'Vector' for vector-only search, 'Hybrid' for vector + keyword (BM25) search."
    )
    
    # Vector Index (BruteForceKnn) Settings
    vector_dimensions: int = Field(
        default=768,
        description="The number of dimensions for the vector embeddings."
    )
    
    # Keyword Index (TantivyBM25) Settings (used in Hybrid mode)
    bm25_ram_budget: int = Field(
        default=52428800, # 50MB
        description="RAM budget in bytes for the BM25 keyword index."
    )




