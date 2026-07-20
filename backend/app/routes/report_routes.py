from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import report_controller
from app.schemas.report import DashboardReport, MostRentedEquipmentEntry, OverdueByClientEntry, RentalReport
from app.utils.deps import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])


@router.get("/rentals", response_model=RentalReport)
def rental_report(
    data_inicio: date | None = None, data_fim: date | None = None, db: Session = Depends(get_db)
) -> RentalReport:
    return report_controller.rental_report(db, data_inicio, data_fim)


@router.get("/most-rented-equipment", response_model=list[MostRentedEquipmentEntry])
def most_rented_equipment(limit: int = 10, db: Session = Depends(get_db)) -> list[MostRentedEquipmentEntry]:
    return report_controller.most_rented_equipment(db, limit)


@router.get("/overdue-invoices", response_model=list[OverdueByClientEntry])
def overdue_report(db: Session = Depends(get_db)) -> list[OverdueByClientEntry]:
    return report_controller.overdue_report(db)


@router.get("/dashboard", response_model=DashboardReport)
def dashboard_report(db: Session = Depends(get_db)) -> DashboardReport:
    return report_controller.dashboard_report(db)
