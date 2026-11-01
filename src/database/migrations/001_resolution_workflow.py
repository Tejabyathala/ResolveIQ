import sqlite3
from pathlib import Path

DATABASE_PATH = (
    Path(__file__).resolve().parents[3]
    / "output"
    / "resolveiq.db"
)


def migrate():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = OFF")

        connection.execute("BEGIN")

        connection.execute("""
            ALTER TABLE resolution
            ADD COLUMN refund_amount_paise INTEGER
            CHECK (
                refund_amount_paise IS NULL
                OR refund_amount_paise > 0
            )
        """)

        connection.execute("""
            ALTER TABLE resolution
            ADD COLUMN created_at TEXT
        """)

        connection.execute("""
            CREATE TABLE resolution_new (
                resolution_id TEXT PRIMARY KEY,
                complaint_id TEXT NOT NULL,

                resolution_type TEXT NOT NULL
                    CHECK (resolution_type IN (
                        'REFUND', 'REPLACEMENT', 'REPAIR',
                        'INFORMATION', 'REJECTED'
                    )),

                resolution_notes TEXT NOT NULL,
                resolved_at TEXT,

                approved_by_agent_id TEXT,

                resolution_status TEXT NOT NULL
                    CHECK (resolution_status IN (
                        'PROPOSED', 'APPROVED',
                        'COMPLETED', 'REJECTED'
                    )),

                refund_amount_paise INTEGER
                    CHECK (
                        refund_amount_paise IS NULL
                        OR refund_amount_paise > 0
                    ),

                created_at TEXT NOT NULL,

                FOREIGN KEY (complaint_id)
                    REFERENCES complaint(complaint_id)
                    ON DELETE RESTRICT,

                FOREIGN KEY (approved_by_agent_id)
                    REFERENCES agent(agent_id)
                    ON DELETE RESTRICT,

                CHECK (
                    (resolution_type = 'REFUND'
                        AND refund_amount_paise IS NOT NULL)
                    OR
                    (resolution_type != 'REFUND'
                        AND refund_amount_paise IS NULL)
                )
            )
        """)

        connection.execute("DROP TABLE resolution")

        connection.execute("""
            ALTER TABLE resolution_new
            RENAME TO resolution
        """)

        connection.commit()

        print("Resolution workflow migration completed.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()