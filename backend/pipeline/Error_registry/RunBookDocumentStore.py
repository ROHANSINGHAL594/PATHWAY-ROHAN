import logging
import json
import os
import time
from typing import Any

import pathway as pw
from dotenv import load_dotenv
from pathway.xpacks.llm.document_store import DocumentStore
from pathway.xpacks.llm.servers import DocumentStoreServer
from pathway.xpacks.llm import embedders, parsers, splitters
from pathway.stdlib.indexing import BruteForceKnnFactory, BruteForceKnnMetricKind

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

pw.set_license_key(os.getenv("Pathway_api_KEY"))


# ===== CUSTOM JSON PARSER =====
def parse_json_entry(contents: bytes, **kwargs) -> list[tuple[str, dict[str, Any]]]:
    """
    Custom parser that treats each JSON entry as a separate chunk. 
    Perfect for MongoDB exports where each entry is a row.
    
    Parse JSON file and return list of (text_for_embedding, metadata) tuples
    """
    try:
        data = json.loads(contents.decode('utf-8'))
        
        # Handle array of objects (typical MongoDB export)
        if isinstance(data, list):
            return _parse_array(data)
        # Handle single object
        elif isinstance(data, dict):
            return [_parse_single_entry(data, 0)]
        else:
            logging.warning("JSON data is neither list nor dict")
            return []
            
    except Exception as e:
        logging.error(f"Error parsing JSON: {e}")
        return []


def _parse_array(data: list) -> list[tuple[str, dict]]:
    """Parse array of JSON objects"""
    results = []
    for idx, entry in enumerate(data):
        if isinstance(entry, dict):
            results.append(_parse_single_entry(entry, idx))
    return results


def _parse_single_entry(entry: dict, idx: int, source_name: str = "default") -> tuple[str, dict]:
    """
    Parse a single JSON entry. 
    Extracts first column for semantic matching.
    Returns: (text_for_embedding, metadata)
    """
    # Get the first column/field for semantic matching
    # Option 1: Use the first key
    if entry:
        first_column_name = list(entry.keys())[0]
        text_for_embedding = str(entry.get(first_column_name, ""))
    else:
        text_for_embedding = ""
    
    # Option 2: If you know the column name, use it directly:
    # text_for_embedding = str(entry.get("your_column_name", ""))
    
    # Store full entry as metadata for retrieval
    metadata = {
        "entry_index": idx,
        "full_data": entry,
        "first_column": text_for_embedding,
        "source": source_name  # Use provided source name
    }
    
    return (text_for_embedding, metadata)


# ===== MAIN APPLICATION =====
class JsonIndexingApp:
    def __init__(
        self,
        json_sources: dict[str, str] = None,  # {"source_name": "path/to/file.json"}
        host: str = "0.0.0.0",
        port: int = 8000,
        embedding_model: str = "models/text-embedding-004",
        with_cache: bool = True,
    ):
        # Support multiple sources or single file
        if json_sources:
            self.json_sources = json_sources
        else:
            self.json_sources = {"default": "/errors.json"}
        
        self.host = host
        self.port = port
        self.embedding_model = embedding_model
        self.with_cache = with_cache
        
    def create_document_store(self) -> DocumentStore:
        """Create and configure the document store with all components"""
        
        # 1. DATA SOURCE - Monitor multiple JSON files
        sources = []
        for source_name, file_path in self.json_sources.items():
            logging.info(f"Setting up file watcher for source '{source_name}': {file_path}")
            
            # Create parser that includes source name in metadata
            def make_source_parser(src_name):
                def source_parser(contents: bytes, **kwargs) -> list[tuple[str, dict[str, Any]]]:
                    """Parser with source name embedded"""
                    try:
                        data = json.loads(contents.decode('utf-8'))
                        results = []
                        if not data:
                            return []
                        if isinstance(data, list):
                            for idx, entry in enumerate(data):
                                if isinstance(entry, dict):
                                    results.append(_parse_single_entry(entry, idx, src_name))
                        elif isinstance(data, dict):
                            results.append(_parse_single_entry(data, 0, src_name))
                        
                        return results
                    except Exception as e:
                        logging.error(f"Error parsing JSON from {src_name}: {e}")
                        return []
                return source_parser
            
            source_table = pw.io.fs.read(
                path=file_path,
                format="binary",
                with_metadata=True,
            )
            
            sources.append(source_table)
        
        # 2. PARSER - Custom JSON parser (will be called per source)
        def parse_json_entry_multi(contents: bytes, **kwargs) -> list[tuple[str, dict[str, Any]]]:
            """Generic parser - source name added via metadata"""
            try:
                data = json.loads(contents.decode('utf-8'))
                if not data:
                    return []
                if isinstance(data, list):
                    return _parse_array(data)
                elif isinstance(data, dict):
                    return [_parse_single_entry(data, 0)]
                else:
                    logging.warning("JSON data is neither list nor dict")
                    return []
            except Exception as e:
                logging.error(f"Error parsing JSON: {e}")
                return []
        
        parser = parse_json_entry_multi
        
        # 3. SPLITTER - Not needed since each JSON entry is already a chunk
        # But if you want to split further, you can use:
        # splitter = splitters.TokenCountSplitter(max_tokens=400)
        splitter = None
        
        # 4. EMBEDDER - For semantic search on first column (Google Gemini)
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable. "
                "Please set one of these to use the embedder."
            )
        embedder = embedders.GeminiEmbedder(
            model=self.embedding_model,
            api_key=api_key
        )
        
        # 5. RETRIEVER - Vector index for similarity search
        retriever_factory = BruteForceKnnFactory(
            reserved_space=1000,
            embedder=embedder,
            metric=BruteForceKnnMetricKind.COS,
        )
        
        # 6. CREATE DOCUMENT STORE
        document_store = DocumentStore(
            docs=sources,
            parser=parser,
            splitter=splitter,
            retriever_factory=retriever_factory,
        )
        
        return document_store
    
    def run(self):
        """Run the indexing server"""
        logging.info("Creating document store...")
        document_store = self.create_document_store()
        
        logging.info(f"Starting server on {self.host}:{self.port}")
        server = DocumentStoreServer(self.host, self.port, document_store)
        
        # Run the server (this blocks and runs continuously)
        server.run(
            with_cache=self.with_cache,
            terminate_on_error=False,
        )



# ===== RUN THE APPLICATION =====
if __name__ == "__main__":
    # Check if data file exists
    if not os.path.exists("/errors.json"):
        logging.warning("/errors.json not found! Creating empty file.")
        with open("/errors.json", "w") as f:
            f.write("[]")
    # Get configuration from environment variables
    host = os.getenv("ERROR_INDEXING_HOST", "0.0.0.0")
    port = int(os.getenv("ERROR_INDEXING_PORT", "11111"))
    errors_json = os.getenv("ERRORS_JSON_PATH", "/errors.json")
    embedding_model = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
    try:
        app = JsonIndexingApp(
            json_sources={"default": errors_json},
            host=host,
            port=port,
            embedding_model=embedding_model,
            with_cache=True,
        )  
        logging.info("Starting Pathway document indexing server...")
        app.run()
    except Exception as e:
        logging.error(f"Error running indexing server: {e}")