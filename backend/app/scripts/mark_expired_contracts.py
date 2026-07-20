from app.config.database import SessionLocal
from app.services import contract_service


def run() -> None:
    db = SessionLocal()
    try:
        contratos = contract_service.mark_expired_contracts(db)
        if not contratos:
            print("Nenhum contrato vencido encontrado.")
            return
        for contract in contratos:
            print(f"Contrato {contract.id} marcado como vencido (data_fim={contract.data_fim}).")
    finally:
        db.close()


if __name__ == "__main__":
    run()
