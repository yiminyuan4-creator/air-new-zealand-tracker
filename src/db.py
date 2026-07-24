import sqlite3
from datetime import datetime
from typing import Iterable

from config import DB_PATH

DB = DB_PATH

INSERT_SQL = '''
    INSERT INTO flights (
        dept, arrv, date, time, arrival_time, flight_number,
        price, currency, duration, stops, airline, source_url, scrape_ts
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
'''

INSERT_COLUMNS = (
    'dept',
    'arrv',
    'date',
    'time',
    'arrival_time',
    'flight_number',
    'price',
    'currency',
    'duration',
    'stops',
    'airline',
    'source_url',
    'scrape_ts',
)


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
    return save_many([{
        'dept': dept,
        'arrv': arrv,
        'date': date,
        'time': time,
        'arrival_time': arrival_time,
        'flight_number': flight_number,
        'price': price,
        'currency': currency,
        'duration': duration,
        'stops': stops,
        'airline': airline,
        'source_url': source_url,
        'scrape_ts': scrape_ts,
    }])


def save_many(flights: Iterable[dict]):
    rows = []
    for flight in flights:
        values = dict(flight)
        values.setdefault('currency', 'NZD')
        values.setdefault('airline', 'Air NZ')
        values['scrape_ts'] = values.get('scrape_ts') or datetime.now().isoformat(timespec='seconds')
        rows.append(tuple(values.get(column) for column in INSERT_COLUMNS))
    if not rows:
        return 0

    conn = _connect()
    try:
        conn.executemany(INSERT_SQL, rows)
        conn.commit()
    finally:
        conn.close()
    return len(rows)


def get_all():
    conn = _connect()
    rows = conn.execute('SELECT * FROM flights ORDER BY scrape_ts DESC, date, time').fetchall()
    conn.close()
    return rows
