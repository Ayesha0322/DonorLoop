import sqlite3
import config

conn = sqlite3.connect(config.DB_PATH)

for table in ["donors", "requests", "outreach_log", "escalation_log"]:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {count}")

conn.close()
