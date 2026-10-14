from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # Registers all models with Base.metadata


def initialize_database():
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    payment_columns = {
        column["name"]
        for column in inspector.get_columns("payments")
    }

    if "customer_id" not in payment_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE payments "
                    "ADD COLUMN customer_id VARCHAR(36) "
                    "REFERENCES customers(id)"
                )
            )

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_payments_customer_id "
                "ON payments (customer_id)"
            )
        )

    print("VoxBank database initialized successfully.")
    print("Tables:", ", ".join(inspect(engine).get_table_names()))


if __name__ == "__main__":
    initialize_database()
