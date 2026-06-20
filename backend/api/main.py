import os
import docker
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from .routers.auth.database import Base
from .routers.main_router import router
from .routers.websocket import watch_changes
from utils.logging import get_logger, configure_root
from .routers.websocket import close_inactive_connections
import certifi

configure_root()
logger = get_logger(__name__)
load_dotenv()


MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "db")
WORKFLOW_COLLECTION = os.getenv("WORKFLOW_COLLECTION", "workflows")
# Actions are actions from rule book, in our notation there are alerts which are a specific type of notifications

NOTIFICATION_COLLECTION = os.getenv("NOTIFICATION_COLLECTION", "notifications")
# Support both LOG_COLLECTION and LOGS_COLLECTION for backwards compatibility
LOG_COLLECTION = os.getenv("LOG_COLLECTION", os.getenv("LOGS_COLLECTION", "logs"))
VERSION_COLLECTION = os.getenv("VERSION_COLLECTION", "versions")
RCA_COLLECTION = os.getenv("RCA_COLLECTION", "rca_events")  # RCA events collection
# Global variables
mongo_client = None
db = None
workflow_collection = None
notification_collection = None
version_collection = None
user_collection = None
docker_client = None
rca_collection = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mongo_client, db, workflow_collection, notification_collection, user_collection, docker_client, version_collection, rca_collection
    # global log_collection  # Commented out - logs not implemented yet

    # ---- STARTUP ----
    if not MONGO_URI:
        raise RuntimeError("MONGO_URI not set in environment")

    mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
    db = mongo_client[MONGO_DB]
    workflow_collection = db[WORKFLOW_COLLECTION]
    version_collection = db[VERSION_COLLECTION]
    notification_collection = db[NOTIFICATION_COLLECTION]
    log_collection = db[LOG_COLLECTION]  # Commented out - logs not implemented yet
    rca_collection = db[RCA_COLLECTION]  # RCA events collection
    print(f"Connected to MongoDB, DB: {MONGO_DB}", flush=True)

    # Create SQL database tables for users
    try:
        from .routers.auth.database import get_engine
        db_engine = get_engine()
        # Use begin() for transaction, but check=True to ensure it works
        async with db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        print("SQL database tables created/verified", flush=True)
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database: {e}")
        logger.error("User authentication features will not work until PostgreSQL is available.")
        print(f"ERROR: PostgreSQL connection failed: {e}", flush=True)
        print("ERROR: User authentication features will not work until PostgreSQL is available.", flush=True)
        print("Run 'python3 backend/auth/init_db.py' to create the tables manually.", flush=True)

    app.state.workflow_collection = workflow_collection
    app.state.version_collection = version_collection
    app.state.notification_collection = notification_collection
    app.state.log_collection = log_collection  # Commented out - logs not implemented yet
    app.state.rca_collection = rca_collection  # RCA events collection
    app.state.mongo_client=mongo_client
    app.state.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
    app.state.algorithm = os.getenv("ALGORITHM", "HS256")
    app.state.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    app.state.refresh_token_expire_minutes = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 43200))
    app.state.revoked_tokens = set()  # default 30 days
    app.state.docker_client = docker.from_env()

    print(f"Connected to docker daemon")
    # All changes (notifications, workflows, logs, RCA) go through single global WebSocket connection
    # Includes Slack notifications for critical logs and RCA updates
    asyncio.create_task(watch_changes(notification_collection, log_collection, workflow_collection, rca_collection))
    print("Started MongoDB change stream listener (notifications, logs, workflows, RCA)")
    ws_cleanup_task = asyncio.create_task(close_inactive_connections())
    print("Started WebSocket inactivity cleanup task")


    yield

     # ---- SHUTDOWN ----
    if docker_client:
        docker_client.close()
        print("Docker connection closed")
    if mongo_client:
        mongo_client.close()
        print("MongoDB connection closed.")
    try:
        from .routers.auth.database import get_engine
        db_engine = get_engine()
        await db_engine.dispose()
        print("SQL database connection closed.")
    except Exception as e:
        logger.warning(f"Error closing PostgreSQL connection: {e}")


app = FastAPI(title="Pipeline API", lifespan=lifespan)

origins = [
    # TODO: Add final domain
    "http://localhost:5173",
    "http://localhost:8083",
    "http://localhost:4173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # if i set it to ["*"] it causes the issue of first login request fail https://stackoverflow.com/a/19744754/23078987
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)