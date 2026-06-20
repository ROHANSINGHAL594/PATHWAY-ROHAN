from typing import Optional
import docker
import os
import logging
from dotenv import load_dotenv
from utils.logging import get_logger, configure_root
import string, secrets
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Load environment from known locations so containers inherit required keys
load_dotenv(os.path.join(BASE_DIR, ".env"))
load_dotenv(os.path.join(PROJECT_ROOT, ".compose.env"))
load_dotenv(os.path.join(PROJECT_ROOT, "agentic", ".env"))

configure_root()
logger = get_logger(__name__)


PIPELINE_IMAGE = os.getenv("PIPELINE_IMAGE", "backend-pipeline:latest")
POSTGRES_IMAGE = os.getenv("POSTGRES_IMAGE", "backend-postgres:latest")
AGENTIC_IMAGE = os.getenv("AGENTIC_IMAGE", "backend-agentic:latest")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
PIPELINE_CONTAINER_PORT = os.getenv("PIPELINE_CONTAINER_PORT", "8000/tcp")
PIPELINE_ERROR_INDEXING_PORT = os.getenv("PIPELINE_ERROR_INDEXING_PORT", "11111/tcp")
AGENTIC_CONTAINER_PORT = os.getenv("AGENTIC_CONTAINER_PORT", "5333/tcp")

dev = os.getenv("ENVIRONMENT", "prod") == "dev"
dynamic_ports = os.getenv("DYNAMIC_PORTS", "true") == "true"

project_root = os.path.join(os.getcwd(),"backend")


def rand_str(n=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))


def run_pipeline_container(client: docker.DockerClient, pipeline_id: str):
    # Ensure images exist
    try:
        client.images.get(PIPELINE_IMAGE)
        logger.info(f"Found image: {PIPELINE_IMAGE}")
    except docker.errors.ImageNotFound:
        logger.error(f"Image not found: {PIPELINE_IMAGE}")
        raise docker.errors.ImageNotFound(f"Image '{PIPELINE_IMAGE}' not found. Run `docker compose build` first.")
    
    try:
        client.images.get(POSTGRES_IMAGE)
        logger.info(f"Found image: {POSTGRES_IMAGE}")
    except docker.errors.ImageNotFound:
        logger.error(f"Image not found: {POSTGRES_IMAGE}")
        raise docker.errors.ImageNotFound(f"Image '{POSTGRES_IMAGE}' not found. Run `docker compose build` first.")
    
    try:
        client.images.get(AGENTIC_IMAGE)
        logger.info(f"Found image: {AGENTIC_IMAGE}")
    except docker.errors.ImageNotFound:
        logger.error(f"Image not found: {AGENTIC_IMAGE}")
        raise docker.errors.ImageNotFound(f"Image '{AGENTIC_IMAGE}' not found. Run `docker compose build` first.")
    
    logger.info("All required images found.")

    # Ensure container does not already exist
    try:
        client.containers.get(pipeline_id)
        raise ValueError(f"Container '{pipeline_id}' already exists")
    except docker.errors.NotFound:
        pass

    # Create a dedicated network for this pipeline instance
    network_name = f"net_{pipeline_id}"
    network = client.networks.create(network_name, driver="bridge")
    logger.info(f"Created network: {network_name}")

    # Generate RW dynamic credentials
    read_user = f"read_{rand_str(6)}".lower()
    read_pass = rand_str(24).lower()
    write_user = f"write_{rand_str(6)}".lower()
    write_pass = rand_str(24).lower()

    # Start Postgres container first
    db_container_name = f"db_{pipeline_id}"
    db_container = client.containers.run(
        image=POSTGRES_IMAGE,
        name=db_container_name,
        detach=True,
        environment={
            "POSTGRES_DB": "db",
            "POSTGRES_USER": "admin",
            "POSTGRES_PASSWORD": POSTGRES_PASSWORD,
            "POSTGRES_READ_USER": read_user,
            "POSTGRES_READ_PASSWORD": read_pass,
            "POSTGRES_WRITE_USER": write_user,
            "POSTGRES_WRITE_PASSWORD": write_pass,

        },
        network=network_name,
        ports={"5432/tcp": 5432 if not dynamic_ports else None},   # dynamic host port
    )

    logger.info(f"Started DB container: {db_container_name}")

    # Wait for PostgreSQL to be ready and initialization to complete
    logger.info("Waiting for PostgreSQL to be ready...")
    max_retries = 3
    retry_interval = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Check if container is still running
            db_container.reload()
            if db_container.status != "running":
                raise Exception(f"DB container stopped unexpectedly: {db_container.status}")
            
            # Execute health check inside the container
            # Check both pg_isready and that the write user exists (init script completed)
            exit_code, output = db_container.exec_run(
                f"pg_isready -U admin -d db && psql -U admin -d db -tAc \"SELECT 1 FROM pg_roles WHERE rolname = '{write_user}'\" | grep -q 1",
                demux=True
            )
            
            if exit_code == 0:
                logger.info(f"PostgreSQL is ready after {attempt + 1} attempts")
                break
            else:
                if attempt < max_retries - 1:
                    logger.debug(f"PostgreSQL not ready yet (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_interval)
                else:
                    logger.warning(f"PostgreSQL may not be fully initialized after {max_retries} attempts, continuing anyway...")
        except Exception as e:
            if attempt < max_retries - 1:
                logger.debug(f"Health check failed (attempt {attempt + 1}): {e}")
                time.sleep(retry_interval)
            else:
                logger.warning(f"Could not verify PostgreSQL health after {max_retries} attempts: {e}")


    agentic_container_name = f"agentic_{pipeline_id}"
    # Start agentic container (needs write access for runbook registry tables)
    agentic_container = client.containers.run(
        image=AGENTIC_IMAGE,
        name=agentic_container_name,
        detach=True,
        environment={
            "PIPELINE_ID": pipeline_id,
            "POSTGRES_HOST": db_container_name,
            "POSTGRES_DB": "db",
            "POSTGRES_USER": write_user,
            "POSTGRES_PASSWORD": write_pass,
            "DATABASE_URL": f"postgresql+asyncpg://{write_user}:{write_pass}@{db_container_name}:5432/db",
            "PATHWAY_API_URL": f"http://{pipeline_id}:{PIPELINE_ERROR_INDEXING_PORT.split('/')[0]}",
            "MONGO_URI": os.getenv("MONGO_URI", ""),
            "MONGO_DB": os.getenv("MONGO_DB", "easyworkflow"),
            "LOGS_COLLECTION": os.getenv("LOGS_COLLECTION", "logs"),
            # LLM API keys - ensure both GOOGLE_API_KEY and GEMINI_API_KEY are set
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")),
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
            "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY", ""),
            "LANGSMITH_TRACING": os.getenv("LANGSMITH_TRACING", "true"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
            "CONTEXT7_API_KEY": os.getenv("CONTEXT7_API_KEY", ""),
        },
        network=network_name,
        ports={AGENTIC_CONTAINER_PORT: AGENTIC_CONTAINER_PORT if not dynamic_ports else None},   # dynamic host port
        volumes=({
            os.path.join(project_root, "agentic"): {
                "bind": "/app/agentic", 
                "mode": "ro"
            },
            os.path.join(project_root, "lib"): {
                "bind": "/app/lib",
                "mode": "ro"
            },
            os.path.join(project_root, "postgres_util.py"): {
                "bind": "/app/postgres_util.py",
                "mode": "ro"
            },
            os.path.join(project_root, "agentic/.env"): {
                "bind": "/app/.env",
                "mode": "ro"
            }
        } if dev else {})
    )

    logger.info(f"Started Agentic container: {agentic_container_name}")


    pipeline_container = client.containers.run(
        image=PIPELINE_IMAGE,
        name=pipeline_id,
        detach=True,
        environment={
            "PIPELINE_ID": pipeline_id,
            "AGENTIC_URL": f"http://{agentic_container_name}:{AGENTIC_CONTAINER_PORT.split('/')[0]}",
            "POSTGRES_HOST": db_container_name,
            "POSTGRES_DB": "db",
            "POSTGRES_USER": write_user,
            "POSTGRES_PASSWORD": write_pass,
            "ERROR_INDEXING_HOST": "0.0.0.0",
            "ERROR_INDEXING_PORT": PIPELINE_ERROR_INDEXING_PORT.split('/')[0],
            "ERRORS_JSON_PATH": "/errors.json",
            "EMBEDDING_MODEL": "models/text-embedding-004",
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
            "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", os.getenv("GEMINI_API_KEY", "")),
            "PATHWAY_LICENSE_KEY": os.getenv("PATHWAY_LICENSE_KEY", ""),
            "MONGO_URI": os.getenv("MONGO_URI", ""),
            "MONGO_DB": os.getenv("MONGO_DB", "easyworkflow"),
            "WORKFLOW_COLLECTION": os.getenv("WORKFLOW_COLLECTION", "workflows"),
            "VERSION_COLLECTION": os.getenv("VERSION_COLLECTION", "versions"),
            "LOGS_COLLECTION": os.getenv("LOGS_COLLECTION", "logs"),
            "FLOWCHART_FILE": "flowchart.json",
        },
        network=network_name,
        ports={
            PIPELINE_CONTAINER_PORT: PIPELINE_CONTAINER_PORT if not dynamic_ports else None,
            PIPELINE_ERROR_INDEXING_PORT: PIPELINE_ERROR_INDEXING_PORT if not dynamic_ports else None,
        },
        volumes=({  
            os.path.join(project_root, "pipeline"): {
                "bind": "/app/pipeline",
                "mode": "ro"
            },
            os.path.join(project_root, "lib"): {
                "bind": "/app/lib",
                "mode": "ro"
            },
            os.path.join(project_root, "postgres_util.py"): {
                "bind": "/app/postgres_util.py",
                "mode": "ro"
            },
            os.path.join(project_root, "pipeline/.env"): {
                "bind": "/app/.env",
                "mode": "ro"
            }
        } if dev else {})
    )

    # Wait for port assignments with retry logic
    max_retries = 5
    retry_delay = 0.5  # seconds
    
    assigned_pipeline_port = None
    assigned_pipeline_error_port = None
    assigned_agentic_port = None
    assigned_database_port = None
    
    for attempt in range(max_retries):
        try:
            pipeline_container.reload()
            agentic_container.reload()
            db_container.reload()
            
            # Check if ports are assigned
            if (pipeline_container.ports and 
                PIPELINE_CONTAINER_PORT in pipeline_container.ports and
                pipeline_container.ports[PIPELINE_CONTAINER_PORT] and
                PIPELINE_ERROR_INDEXING_PORT in pipeline_container.ports and
                pipeline_container.ports[PIPELINE_ERROR_INDEXING_PORT] and
                agentic_container.ports and
                AGENTIC_CONTAINER_PORT in agentic_container.ports and
                agentic_container.ports[AGENTIC_CONTAINER_PORT] and
                db_container.ports and
                "5432/tcp" in db_container.ports and
                db_container.ports["5432/tcp"]):
                
                assigned_pipeline_port = pipeline_container.ports[PIPELINE_CONTAINER_PORT][0]['HostPort']
                assigned_pipeline_error_port = pipeline_container.ports[PIPELINE_ERROR_INDEXING_PORT][0]['HostPort']
                assigned_agentic_port = agentic_container.ports[AGENTIC_CONTAINER_PORT][0]['HostPort']
                assigned_database_port = db_container.ports["5432/tcp"][0]['HostPort']
                break
            else:
                logger.warning(f"Port assignments not ready, attempt {attempt + 1}/{max_retries}")
                time.sleep(retry_delay)
        except Exception as e:
            logger.warning(f"Error checking port assignments (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
    
    if not all([assigned_pipeline_port, assigned_pipeline_error_port, assigned_agentic_port, assigned_database_port]):
        logger.error(f"Failed to determine assigned host ports after {max_retries} attempts")
        logger.error(f"Pipeline ports: {pipeline_container.ports}")
        logger.error(f"Agentic ports: {agentic_container.ports}")
        logger.error(f"DB ports: {db_container.ports}")
        try:
            pipeline_container.stop()
            pipeline_container.remove()
            db_container.stop()
            db_container.remove()
            agentic_container.stop()
            agentic_container.remove()
            network.remove()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
        raise RuntimeError("Failed to determine assigned host port.")

    logger.info(f"Pipeline container running on host port {assigned_pipeline_port}")
    logger.info(f"Pipeline error indexing on host port {assigned_pipeline_error_port}")
    logger.info(f"Agentic container running on host port {assigned_agentic_port}")

    return {
        "pipeline_container_id": pipeline_container.id,
        "db_container_id": db_container.id,
        "agentic_container_id": agentic_container.id,
        "network": network_name,
        "pipeline_host_port": assigned_pipeline_port,
        "pipeline_error_indexing_port": assigned_pipeline_error_port,
        "agentic_host_port": assigned_agentic_port,
        "db_host_port": assigned_database_port,
    }


def stop_docker_container(client: docker.DockerClient, pipeline_id: str):
    db_container_name = f"db_{pipeline_id}"
    agentic_container_name = f"agentic_{pipeline_id}"
    network_name = f"net_{pipeline_id}"

    # Stop pipeline container
    try:
        pipeline_container = client.containers.get(pipeline_id)
        pipeline_container.stop()
        pipeline_container.remove()
        logger.info(f"Removed pipeline container {pipeline_id}")
    except docker.errors.NotFound:
        pass

    # Stop DB container
    try:
        db_container = client.containers.get(db_container_name)
        db_container.stop()
        db_container.remove()
        logger.info(f"Removed DB container {db_container_name}")
    except docker.errors.NotFound:
        pass

    try:
        agentic_container = client.containers.get(agentic_container_name)
        agentic_container.stop()
        agentic_container.remove()
        logger.info(f"Removed Agentic container {agentic_container_name}")
    except docker.errors.NotFound:
        pass

    # Remove network
    try:
        network = client.networks.get(network_name)
        network.remove()
        logger.info(f"Removed network {network_name}")
    except docker.errors.NotFound:
        pass

    return {"pipeline_id": pipeline_id, "cleaned": True}
