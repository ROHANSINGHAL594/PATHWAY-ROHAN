from typing import List
import pathway as pw
from lib.agents.rag import RAGNode
from .helpers import MappingValues


def rag_node(inputs: List[pw.Table], node: RAGNode):
    """
    Create a RAG node with MCP server exposure for document store.
    
    This function:
    1. Takes the input table of documents
    2. Creates a parser, splitter, embedder, and retriever/index
    3. Builds a DocumentStore
    4. Exposes the DocumentStore via an MCP server on a unique port
    
    Args:
        inputs: List containing a single table of documents with content and metadata
        node: RAGNode configuration containing parser, splitter, embedder, and retriever settings
    
    Returns:
        The DocumentStore which acts as a sink and can be queried via MCP
    """
    # Check if xpacks is available
    if not hasattr(pw, 'xpacks'):
        raise ImportError(
            "Pathway xpacks.llm module is not available.\n"
            "This feature requires a Pathway license key.\n\n"
            "To use RAG MCP features:\n"
            "1. Get a free license key at: https://pathway.com/get-license\n"
            "2. Set the environment variable: export PATHWAY_LICENSE_KEY=your-key\n"
            "3. Restart your application\n\n"
            "Alternatively, the xpacks module might not be properly installed.\n"
            "Try: pip install 'pathway[xpack-llm]' --upgrade"
        )
    
    if len(inputs) != 1:
        raise ValueError(f"RAGNode expects exactly 1 input, got {len(inputs)}")
    
    docs_table = inputs[0]
    
    # --- Parser Configuration ---
    if node.parser_type == "Unstructured":
        parser = pw.xpacks.llm.parsers.UnstructuredParser()
    else:
        raise ValueError(f"Unsupported parser type: {node.parser_type}")
    
    # --- Splitter Configuration ---
    if node.splitter_type == "TokenCount":
        splitter = pw.xpacks.llm.splitters.TokenCountSplitter(
            max_tokens=node.splitter_max_tokens,
            min_tokens=node.splitter_min_tokens
        )
    else:
        raise ValueError(f"Unsupported splitter type: {node.splitter_type}")
    
    # --- Embedder Configuration ---
    if node.embedder_type == "Gemini":
        if not node.google_api_key:
            raise ValueError("google_api_key is required for Gemini embedder")
        embedder = pw.xpacks.llm.embedders.GeminiEmbedder(
            api_key=node.google_api_key,
            model=node.embedder_model,
            cache_strategy=pw.udfs.DefaultCache()
        )
    elif node.embedder_type == "OpenAI":
        if not node.openai_api_key:
            raise ValueError("openai_api_key is required for OpenAI embedder")
        embedder = pw.xpacks.llm.embedders.OpenAIEmbedder(
            api_key=node.openai_api_key,
            model=node.embedder_model,
            cache_strategy=pw.udfs.DefaultCache()
        )
    elif node.embedder_type == "SentenceTransformer":
        embedder = pw.xpacks.llm.embedders.SentenceTransformerEmbedder(
            model=node.embedder_model,
            cache_strategy=pw.udfs.DefaultCache()
        )
    else:
        raise ValueError(f"Unsupported embedder type: {node.embedder_type}")
    
    # --- Retriever/Index Configuration ---
    if node.retriever_type == "Vector":
        # Vector-only search using BruteForceKnn
        knn_index = pw.stdlib.indexing.BruteForceKnnFactory(
            reserved_space=1000,
            embedder=embedder,
            metric=pw.engine.BruteForceKnnMetricKind.COS,
            dimensions=node.vector_dimensions
        )
        retriever_factory = knn_index
        
    elif node.retriever_type == "Hybrid":
        # Hybrid search: Vector (BruteForceKnn) + Keyword (BM25)
        knn_index = pw.stdlib.indexing.BruteForceKnnFactory(
            reserved_space=1000,
            embedder=embedder,
            metric=pw.engine.BruteForceKnnMetricKind.COS,
            dimensions=node.vector_dimensions
        )
        bm25_index = pw.stdlib.indexing.TantivyBM25Factory(
            ram_budget=node.bm25_ram_budget
        )
        retriever_factory = pw.stdlib.indexing.HybridIndexFactory(
            retriever_factories=[knn_index, bm25_index]
        )
    else:
        raise ValueError(f"Unsupported retriever type: {node.retriever_type}")
    
    # --- Create DocumentStore ---
    document_store = pw.xpacks.llm.document_store.DocumentStore(
        docs=docs_table,
        parser=parser,
        splitter=splitter,
        retriever_factory=retriever_factory
    )
    
    # --- Expose via MCP Server ---
    # Each RAG node gets its own unique MCP server
    # Port is dynamically assigned based on a base port + node hash or ID
    # Using description hash to make port somewhat predictable but unique
    import hashlib
    port_offset = int(hashlib.md5(node.description.encode()).hexdigest()[:4], 16) % 10000
    mcp_port = 8100 + port_offset
    
    mcp_server = pw.xpacks.llm.mcp_server.PathwayMcp(
        name=f"RAG MCP Server - {node.description[:50]}",
        transport="streamable-http",
        host="localhost",
        port=mcp_port,
        serve=[document_store]
    )
    
    # Log the MCP server configuration
    print(f"[RAG Node] Created MCP server for '{node.description}'")
    print(f"[RAG Node] MCP Server URL: http://localhost:{mcp_port}/mcp/")
    print(f"[RAG Node] Embedder: {node.embedder_type} ({node.embedder_model})")
    print(f"[RAG Node] Retriever: {node.retriever_type}")
    
    return mcp_port


rag_mappings: dict[str, MappingValues] = {
    "rag_node": {
        "node_fn": rag_node
    }
}
