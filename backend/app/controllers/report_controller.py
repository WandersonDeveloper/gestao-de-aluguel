from datetime import date

from sqlalchemy.orm import Session

from app.schemas.report import DashboardReport, MostRentedEquipmentEntry, OverdueByClientEntry, RentalReport
from app.services import report_service


def rental_report(db: Session, data_inicio: date | None, data_fim: date | None) -> RentalReport:
    return report_service.rental_report(db, data_inicio, data_fim)


def most_rented_equipment(db: Session, limit: int) -> list[MostRentedEquipmentEntry]:
    return report_service.most_rented_equipment(db, limit)


def overdue_report(db: Session) -> list[OverdueByClientEntry]:
    return report_service.overdue_report(db)


def dashboard_report(db: Session) -> DashboardReport:
    return report_service.dashboard_report(db)
