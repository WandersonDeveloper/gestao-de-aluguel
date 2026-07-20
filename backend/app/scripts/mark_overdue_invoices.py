from app.config.database import SessionLocal
from app.services import invoice_service


def run() -> None:
    db = SessionLocal()
    try:
        faturas = invoice_service.mark_overdue_invoices(db)
        if not faturas:
            print("Nenhuma fatura vencida encontrada.")
            return
        for invoice in faturas:
            print(
                f"Fatura {invoice.id} marcada como atrasada "
                f"(vencimento={invoice.data_vencimento}, multa={invoice.multa_juros_aplicado})."
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
