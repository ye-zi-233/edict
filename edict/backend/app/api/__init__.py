from .tasks import router as tasks_router
from .agents import router as agents_router
from .events import router as events_router
from .admin import router as admin_router
from .websocket import router as websocket_router
from .compat import router as compat_router
from .models import router as models_router
from .task_ops import router as task_ops_router
from .scheduler import router as scheduler_router
from .skills import router as skills_router
from .morning import router as morning_router
from .officials import router as officials_router

__all__ = [
    "tasks_router",
    "agents_router",
    "events_router",
    "admin_router",
    "websocket_router",
    "compat_router",
    "models_router",
    "task_ops_router",
    "scheduler_router",
    "skills_router",
    "morning_router",
    "officials_router",
]
