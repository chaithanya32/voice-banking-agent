from app.models import PaymentRecord
from app.services import payment_confirmation
from app.services.payment_confirmation import create_payment


def test_payment_persists_across_database_sessions():
    payment = create_payment("Ravi Kumar", "500 rupees")

    # Open a new session against the same test database.
    with payment_confirmation.SessionLocal() as session:
        saved_payment = session.get(PaymentRecord, payment.payment_id)

        assert saved_payment is not None
        assert saved_payment.payee_name == "Ravi Kumar"
        assert saved_payment.status == "pending"
