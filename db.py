import sqlite3
from datetime import datetime
from typing import Iterable

from config import DB_PATH

DB = DB_PATH


def _connect():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS flights (
                id INTEGER PRIMARY KEY,
                dept TEXT, arrv TEXT, date TEXT, time TEXT,
                arrival_time TEXT, flight_number TEXT,
                price REAL, currency TEXT DEFAULT 'NZD',
                duration TEXT, stops INT,
                airline TEXT DEFAULT 'Air NZ',
                source_url TEXT,
                scrape_ts TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        existing = {row['name'] for row in c.execute('PRAGMA table_info(flights)').fetchall()}
        for column, definition in {
            'arrival_time': 'TEXT',
            'flight_number': 'TEXT',
            'currency': "TEXT DEFAULT 'NZD'",
            'source_url': 'TEXT',
            'scrape_ts': 'TEXT',
            'created_at': 'TEXT',
        }.items():
            if column not in existing:
                c.execute(f'ALTER TABLE flights ADD COLUMN {column} {definition}')
                existing.add(column)

        fallback_columns = [col for col in ('scrape_ts', 'ts', 'created_at') if col in existing]
        fallback = ', '.join(fallback_columns + ['CURRENT_TIMESTAMP'])
        c.execute(f"UPDATE flights SET scrape_ts = COALESCE({fallback}) WHERE scrape_ts IS NULL")
        c.execute("UPDATE flights SET currency = COALESCE(currency, 'NZD') WHERE currency IS NULL")
        c.execute('CREATE INDEX IF NOT EXISTS idx_route_date ON flights(dept, arrv, date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_flight ON flights(dept, arrv, date, time, flight_number)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_scrape_ts ON flights(scrape_ts)')
        conn.commit()
    finally:
        conn.close()


def save(
    dept,
    arrv,
    date,
    time,
    price,
    arrival_time=None,
    flight_number=None,
    currency='NZD',
    duration=None,
    stops=None,
    airline='Air NZ',
    source_url=None,
    scrape_ts=None,
):
    scrape_ts = scrape_ts or datetime.now().isoformat(timespec='seconds')
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO flights (
                dept, arrv, date, time, arrival_time, flight_number,
                price, currency, duration, stops, airline, source_url, scrape_ts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                dept, arrv, date, time, arrival_time, flight_number,
                price, currency, duration, stops, airline, source_url, scrape_ts
            )
        )
        conn.commit()
    finally:
        conn.close()


def save_many(flights: Iterable[dict]):
    count = 0
    for flight in flights:
        save(**flight)
        count += 1
    return count


def get_flight_history(dept, arrv, date, time, arrival_time=None, flight_number=None, duration=None):
    conn = _connect()
    params = [dept, arrv, date, time]
    filters = ['dept=?', 'arrv=?', 'date=?', 'time=?']
    for column, value in (
        ('arrival_time', arrival_time),
        ('flight_number', flight_number),
        ('duration', duration),
    ):
        if value:
            filters.append(f'{column}=?')
            params.append(value)
    rows = conn.execute(
        f'''
        SELECT price, currency, scrape_ts, flight_number, arrival_time, duration, stops
        FROM flights
        WHERE {' AND '.join(filters)}
        ORDER BY scrape_ts
        ''',
        params
    ).fetchall()
    conn.close()
    return rows


def get_route_data(dept, arrv, date, scrape_ts=None):
    conn = _connect()
    params = [dept, arrv, date]
    where = 'dept=? AND arrv=? AND date=?'
    if scrape_ts:
        where += ' AND scrape_ts=?'
        params.append(scrape_ts)
    rows = conn.execute(
        f'''
        SELECT time, arrival_time, flight_number, price, currency, scrape_ts, duration, stops
        FROM flights
        WHERE {where}
        ORDER BY scrape_ts, time, price
        ''',
        params
    ).fetchall()
    conn.close()
    return rows


def get_routes():
    conn = _connect()
    rows = conn.execute('SELECT DISTINCT dept, arrv FROM flights ORDER BY dept, arrv').fetchall()
    conn.close()
    return rows


def get_dates(dept=None, arrv=None):
    conn = _connect()
    if dept and arrv:
        rows = conn.execute(
            'SELECT DISTINCT date FROM flights WHERE dept=? AND arrv=? ORDER BY date',
            (dept, arrv)
        ).fetchall()
    else:
        rows = conn.execute('SELECT DISTINCT date FROM flights ORDER BY date').fetchall()
    conn.close()
    return [r['date'] for r in rows]


def get_scrape_times(dept=None, arrv=None, date=None):
    conn = _connect()
    params = []
    where = []
    if dept and arrv:
        where.extend(['dept=?', 'arrv=?'])
        params.extend([dept, arrv])
    if date:
        where.append('date=?')
        params.append(date)
    clause = f"WHERE {' AND '.join(where)}" if where else ''
    rows = conn.execute(
        f'SELECT DISTINCT scrape_ts FROM flights {clause} ORDER BY scrape_ts DESC',
        params
    ).fetchall()
    conn.close()
    return [r['scrape_ts'] for r in rows]


def get_all():
    conn = _connect()
    rows = conn.execute('SELECT * FROM flights ORDER BY scrape_ts DESC, date, time').fetchall()
    conn.close()
    return rows
