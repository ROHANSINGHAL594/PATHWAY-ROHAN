import logging
import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# Add parent directory to path to import postgres_util
sys.path.insert(0, str(Path(__file__).parent.parent))
from postgres_util import postgre_url
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

def get_ist_now():
    """Get current time in IST as a naive datetime (timezone-stripped)."""
    return datetime.now(IST).replace(tzinfo=None)

Base = declarative_base()

class LogEntry(Base):
    """SQLAlchemy model for log entries."""
    __tablename__ = "logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=get_ist_now)
    level = Column(String(20))
    level_no = Column(Integer)
    logger = Column(String(255))
    message = Column(Text)
    module = Column(String(255))
    function = Column(String(255))
    line = Column(BigInteger)
    pathname = Column(Text)
    process_id = Column(BigInteger)
    thread_id = Column(BigInteger)
    exception = Column(Text, nullable=True)

class MultiEndpointLogHandler(logging.Handler):
    """
    A handler that writes log records to PostgreSQL.
    Falls back to a file if PostgreSQL is unavailable.

    Sends important logs (WARNING and above) to both MongoDB and PostgreSQL.
    """
    def __init__(
        self,
        postgres_uri: str = None,
        mongo_uri: str = None,
        mongo_database: str = "easyworkflow",
        mongo_collection: str = "logs",
        fallback_file: str = "fallback.log",
        level: int = logging.NOTSET,
        mongo_level: int = logging.WARNING,
    ):

        super().__init__(level)

        self.postgres_uri = postgres_uri or os.getenv("POSTGRES_URI")
        self.workflow_id = os.getenv("PIPELINE_ID", "GLOBAL")
        self.mongo_uri = mongo_uri or os.getenv("MONGO_URI")
        self.mongo_database_name = mongo_database
        self.mongo_collection_name = mongo_collection
        self.fallback_file = fallback_file
        self.mongo_level = mongo_level  # Level at which to send to MongoDB

        self.engine = None
        self.Session = None
        self.mongo_client: Optional[MongoClient] = None
        self.mongo_collection = None
        self.fallback_handler: Optional[logging.FileHandler] = None

        self._connect_postgres()
        self._connect_mongo()


    def _connect_postgres(self):
        """Attempt to connect to PostgreSQL using SQLAlchemy."""
        try:
            self.engine = create_engine(self.postgres_uri, pool_pre_ping=True)
            # Create tables if they don't exist
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError as e:
            print(f"PostgreSQL connection failed: {e}. Using fallback file logging.")
            self.engine = None
            self.Session = None
            self._setup_fallback()

    def _connect_mongo(self):
        """Attempt to connect to MongoDB for important logs."""
        try:
            self.mongo_client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.mongo_client.admin.command("ping")
            db = self.mongo_client[self.mongo_database_name]
            self.mongo_collection = db[self.mongo_collection_name]
        except PyMongoError as e:
            print(f"MongoDB connection failed: {e}. Important logs will only go to PostgreSQL/file.")
            self.mongo_client = None
            self.mongo_collection = None


    def _setup_fallback(self):
        """Set up file handler as fallback."""
        if self.fallback_handler is None:
            self.fallback_handler = logging.FileHandler(self.fallback_file)
            self.fallback_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )

    def _get_short_message(self, record: logging.LogRecord) -> str:
        """
        Get a short message for system-generated logs.
        Extracts just the core message without extra formatting.
        """
        # Get the raw message (without any formatting applied)
        msg = record.getMessage()
        
        # If it's a system-generated message (from internal modules), keep it short
        system_modules = ['uvicorn', 'fastapi', 'sqlalchemy', 'pymongo', 'motor', 'httpx', 'httpcore']
        if any(mod in record.name.lower() for mod in system_modules):
            # Keep only the first line and limit length
            first_line = msg.split('\n')[0]
            if len(first_line) > 100:
                return first_line[:97] + "..."
            return first_line
        
        return msg

    def _build_log_dict(self, record: logging.LogRecord) -> dict:
        """Build a dictionary from a log record."""
        # Use short message for system-generated logs
        message = self._get_short_message(record)
        
        log_entry = {
            "pipeline_id": self.workflow_id,  # Use pipeline_id for consistency with API
            "timestamp": get_ist_now(),
            "level": record.levelname.lower(),  # Lowercase for frontend consistency
            "level_no": record.levelno,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
            "process_id": record.process,
            "thread_id": record.thread,
            "source": record.module,  # Use module as source for frontend display
            "exception": None,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = (
                self.formatter.formatException(record.exc_info)
                if self.formatter
                else str(record.exc_info)
            )
        return log_entry

    def _send_to_mongo(self, log_entry: dict):
        """Send important logs to MongoDB."""
        if self.mongo_collection is not None:
            try:
                self.mongo_collection.insert_one(log_entry.copy())
            except PyMongoError as e:
                print(f"MongoDB insert failed: {e}")

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to PostgreSQL (all logs), fallback file,
        and MongoDB for important logs (WARNING, CRITICAL and above).
        """
        log_entry = self._build_log_dict(record)

        # Send important logs
        if record.levelno >= self.mongo_level:
            self._send_to_mongo(log_entry)

        # Try PostgreSQL
        if self.Session is not None:
            try:
                session = self.Session()
                db_entry = LogEntry(
                    timestamp=log_entry["timestamp"],
                    level=log_entry["level"],
                    level_no=log_entry["level_no"],
                    logger=log_entry["logger"],
                    message=log_entry["message"],
                    module=log_entry["module"],
                    function=log_entry["function"],
                    line=log_entry["line"],
                    pathname=log_entry["pathname"],
                    process_id=log_entry["process_id"],
                    thread_id=log_entry["thread_id"],
                    exception=log_entry["exception"],
                )
                session.add(db_entry)
                session.commit()
                session.close()
                return
            except SQLAlchemyError as e:
                print(f"PostgreSQL insert failed: {e}. Falling back to file.")
                self._setup_fallback()
                self.Session = None

        # Use fallback file handler
        if self.fallback_handler:
            self.fallback_handler.emit(record)

    def close(self):
        """Clean up resources."""
        if self.engine:
            self.engine.dispose()
        if self.mongo_client:
            self.mongo_client.close()
        if self.fallback_handler:
            self.fallback_handler.close()
        super().close()


def setup_logging(
    postgres_uri: str = postgre_url,
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://host.docker.internal:27017"),
    mongo_database: str = os.getenv("MONGO_DB", "easyworkflow"),
    mongo_collection: str = os.getenv("LOGS_COLLECTION", "logs"),
    fallback_file: str = "fallback_logs.log",
    level: int = logging.INFO,
    mongo_level: int = logging.WARNING,
) -> logging.Logger:
    """
    Set up logging with PostgreSQL handler, file fallback, and MongoDB for important logs.

    Args:
        postgres_uri: PostgreSQL connection URI (SQLAlchemy format)
        mongo_uri: MongoDB connection URI for important logs
        mongo_database: MongoDB database name for important logs
        mongo_collection: MongoDB collection name for important logs
        fallback_file: Path to fallback log file
        level: Logging level for all logs
        mongo_level: Minimum level to send to MongoDB (default: WARNING)

    Returns:
        Configured logger
    """
    logger = logging.getLogger()
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add PostgreSQL handler with fallback and MongoDB for important logs
    handler = MultiEndpointLogHandler(
        postgres_uri=postgres_uri,
        mongo_uri=mongo_uri,
        mongo_database=mongo_database,
        mongo_collection=mongo_collection,
        fallback_file=fallback_file,
        level=level,
        mongo_level=mongo_level,
    )
    logger.addHandler(handler)

    # Console handler for visibility
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(console_handler)
    return logger

custom_logger = setup_logging()