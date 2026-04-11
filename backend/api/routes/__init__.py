from .auth import router as auth_router
from .transactions import router as transactions_router
from .learning import router as learning_router
from .stocks import router as stocks_router
from .gamification import router as gamification_router

__all__ = [
    "auth_router",
    "transactions_router",
    "learning_router",
    "stocks_router",
    "gamification_router",
]
