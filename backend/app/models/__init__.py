# Modelos SQLAlchemy (tabelas do PostgreSQL).
# Importados aqui para que Base.metadata os enxergue no autogenerate do Alembic.
from app.models.client import Client
from app.models.contract import Contract
from app.models.contract_amendment import ContractAmendment
from app.models.contract_item import ContractItem
from app.models.equipment import Equipment
from app.models.equipment_category import EquipmentCategory
from app.models.equipment_stock import EquipmentStock
from app.models.filial import Filial
from app.models.inventory_movement import InventoryMovement
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.message_template import MessageTemplate
from app.models.payment import Payment
from app.models.service_order import ServiceOrder
from app.models.supplier import Supplier
from app.models.user import User

__all__ = [
    "Client",
    "Contract",
    "ContractAmendment",
    "ContractItem",
    "Equipment",
    "EquipmentCategory",
    "EquipmentStock",
    "Filial",
    "InventoryMovement",
    "Invoice",
    "InvoiceItem",
    "MessageTemplate",
    "Payment",
    "ServiceOrder",
    "Supplier",
    "User",
]
