
from src.database.connection import get_connection


def verify_database():
    with get_connection() as connection:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
        """).fetchall()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_issues = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("\nDATABASE VERIFICATION")
        print("---------------------")
        print(f"Tables found: {len(tables)}")
        for table in tables:
            print(f"- {table[0]}")

        print(f"\nIntegrity check: {integrity}")
        print(f"Foreign key issues: {len(foreign_key_issues)}")

        if foreign_key_issues:
            for issue in foreign_key_issues:
                print(issue)

        if integrity != "ok" or foreign_key_issues:
            raise SystemExit("Database verification failed.")

        print("\nDatabase verification successful!")


if __name__ == "__main__":
    verify_database()
