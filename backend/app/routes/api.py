from fastapi import APIRouter

from app.routes.auth_routes import router as auth_router
from app.routes.client_routes import router as client_router
from app.routes.contract_routes import router as contract_router
from app.routes.equipment_category_routes import router as equipment_category_router
from app.routes.equipment_routes import router as equipment_router
from app.routes.health_routes import router as health_router
from app.routes.service_order_routes import router as service_order_router
from app.routes.user_routes import router as user_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(client_router)
api_router.include_router(equipment_category_router)
api_router.include_router(equipment_router)
api_router.include_router(contract_router)
api_router.include_router(service_order_router)
