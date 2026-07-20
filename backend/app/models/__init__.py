# Modelos SQLAlchemy (tabelas do PostgreSQL).
# Importados aqui para que Base.metadata os enxergue no autogenerate do Alembic.
from app.models.client import Client
from app.models.contract import Contract
from app.models.contract_amendment import ContractAmendment
from app.models.contract_item import ContractItem
from app.models.equipment import Equipment
from app.models.equipment_category import EquipmentCategory
from app.models.inventory_movement import InventoryMovement
from app.models.service_order import ServiceOrder
from app.models.user import User

__all__ = [
    "Client",
    "Contract",
    "ContractAmendment",
    "ContractItem",
    "Equipment",
    "EquipmentCategory",
    "InventoryMovement",
    "ServiceOrder",
    "User",
]
