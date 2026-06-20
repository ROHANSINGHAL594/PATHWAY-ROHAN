from fastapi import APIRouter
from .auth.routes import router as auth_router
from .version_manager.routes import router as version_control_router
from .connectors.whatsapp import router as whatsapp_router
from .pipelines import router as pipelines_router
from .schemas import router as schemas_router
from .websocket import router as websocket_router
from .overview import router as overview_router
from .rca import router as rca_router
from .test_routes import router as test_router
from .action import router as action_router, agentic_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(version_control_router, prefix="/version", tags=["version"])
router.include_router(whatsapp_router, prefix="/connectors/whatsapp", tags=["whatsapp"])
router.include_router(pipelines_router, prefix="/pipelines", tags=["pipelines"])
router.include_router(schemas_router, prefix="/schema", tags=["schemas"])
router.include_router(websocket_router, prefix="/ws", tags=["websocket"])  # Prefix for /ws/ws and /ws/alerts/{id}
router.include_router(overview_router, prefix="/overview", tags=["overview"])
router.include_router(rca_router, prefix="/rca", tags=["rca"])
router.include_router(test_router, prefix="/test", tags=["test"])
router.include_router(action_router, prefix="/action", tags=["action"])
router.include_router(agentic_router, prefix="/agentic", tags=["agentic"])
