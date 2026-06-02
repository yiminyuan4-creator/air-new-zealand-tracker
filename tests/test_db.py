import os
import sqlite3
import tempfile
import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.tmp.name, "flights.db")

        import db

        self.db = db
        self.db.DB = os.environ["DB_PATH"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_query_route_and_flight_history(self):
        self.db.init_db()
        rows = [
            {
                "dept": "AKL",
                "arrv": "WLG",
                "date": "2026-07-01",
                "time": "09:00",
                "arrival_time": "10:05",
                "flight_number": "NZ401",
                "price": 99.0,
                "scrape_ts": "2026-06-02T18:00:00",
            },
            {
                "dept": "AKL",
                "arrv": "WLG",
                "date": "2026-07-01",
                "time": "09:00",
                "arrival_time": "10:05",
                "flight_number": "NZ401",
                "price": 119.0,
                "scrape_ts": "2026-06-03T18:00:00",
            },
        ]

        self.assertEqual(self.db.save_many(rows), 2)
        self.assertEqual(len(self.db.get_route_data("AKL", "WLG", "2026-07-01")), 2)
        history = self.db.get_flight_history("AKL", "WLG", "2026-07-01", "09:00")
        self.assertEqual([r["price"] for r in history], [99.0, 119.0])

    def test_flight_history_can_filter_same_departure_time_itineraries(self):
        self.db.init_db()
        rows = [
            {
                "dept": "AKL",
                "arrv": "CSX",
                "date": "2026-12-13",
                "time": "23:55",
                "arrival_time": "13:00",
                "flight_number": "NZ0289",
                "duration": "18h 5m",
                "price": 1696.0,
                "scrape_ts": "2026-06-02T09:27:09",
            },
            {
                "dept": "AKL",
                "arrv": "CSX",
                "date": "2026-12-13",
                "time": "23:55",
                "arrival_time": "16:00",
                "flight_number": "NZ0289",
                "duration": "21h 5m",
                "price": 1796.0,
                "scrape_ts": "2026-06-02T09:27:09",
            },
        ]

        self.db.save_many(rows)

        history = self.db.get_flight_history(
            "AKL",
            "CSX",
            "2026-12-13",
            "23:55",
            "13:00",
            "NZ0289",
            "18h 5m",
        )
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["arrival_time"], "13:00")

    def test_init_db_migrates_old_schema_with_ts(self):
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute(
            """
            CREATE TABLE flights (
                id INTEGER PRIMARY KEY,
                dept TEXT, arrv TEXT, date TEXT, time TEXT,
                price REAL, duration TEXT, stops INT,
                airline TEXT DEFAULT 'Air NZ',
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            INSERT INTO flights (dept, arrv, date, time, price, duration, stops, ts)
            VALUES ('AKL', 'SYD', '2026-07-01', '08:00', 199.0, '3h 30m', 0, '2026-06-02T18:00:00')
            """
        )
        conn.commit()
        conn.close()

        self.db.init_db()

        rows = self.db.get_route_data("AKL", "SYD", "2026-07-01")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["scrape_ts"], "2026-06-02T18:00:00")


if __name__ == "__main__":
    unittest.main()
