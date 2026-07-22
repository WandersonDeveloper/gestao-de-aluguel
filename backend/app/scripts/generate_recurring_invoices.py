from app.config.database import SessionLocal
from app.services import invoice_service


def run() -> None:
    db = SessionLocal()
    try:
        faturas = invoice_service.generate_next_recurring_invoices(db)
        if not faturas:
            print("Nenhuma fatura recorrente pendente de geração.")
            return
        for invoice in faturas:
            print(
                f"Fatura {invoice.id} gerada para o contrato {invoice.contrato_id} "
                f"(vencimento={invoice.data_vencimento}, valor={invoice.valor})."
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
