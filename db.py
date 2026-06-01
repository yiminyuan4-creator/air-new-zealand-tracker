import sqlite3
from datetime import datetime

DB = "flights.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS flights (
            id INTEGER PRIMARY KEY,
            dept TEXT, arrv TEXT, date TEXT, time TEXT,
            price REAL, duration TEXT, stops INT,
            airline TEXT DEFAULT 'Air NZ',
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dept, arrv, date, time, ts)
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_route ON flights(dept, arrv)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_date ON flights(date)')
    conn.commit()
    conn.close()

def save(dept, arrv, date, time, price, duration=None, stops=None):
    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            'INSERT INTO flights (dept, arrv, date, time, price, duration, stops, ts) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (dept, arrv, date, time, price, duration, stops, datetime.now())
        )
        conn.commit()
    except:
        pass
    finally:
        conn.close()

def get_flight_history(dept, arrv, date, time):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT price, ts FROM flights WHERE dept=? AND arrv=? AND date=? AND time=? ORDER BY ts',
        (dept, arrv, date, time)
    ).fetchall()
    conn.close()
    return rows

def get_route_data(dept, arrv, date):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        'SELECT time, price, ts FROM flights WHERE dept=? AND arrv=? AND date=? ORDER BY ts, time',
        (dept, arrv, date)
    ).fetchall()
    conn.close()
    return rows

def get_all():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM flights ORDER BY ts DESC').fetchall()
    conn.close()
    return rows
