import pandas as pd
from db import get_flight_history, get_route_data, get_all

class Analyzer:
    @staticmethod
    def flight_history(dept, arrv, date, time):
        """Get price history for a flight"""
        rows = get_flight_history(dept, arrv, date, time)
        return [{'ts': r['ts'], 'price': r['price']} for r in rows]
    
    @staticmethod
    def route_prices(dept, arrv, date):
        """Get prices for all flights on route"""
        rows = get_route_data(dept, arrv, date)
        data = {}
        for r in rows:
            t = r['time']
            if t not in data:
                data[t] = []
            data[t].append({'ts': r['ts'], 'price': r['price']})
        return data
    
    @staticmethod
    def summary():
        """Database summary"""
        flights = get_all()
        routes = {}
        for f in flights:
            k = f"{f['dept']}->{f['arrv']}"
            routes[k] = routes.get(k, 0) + 1
        return {
            'total': len(flights),
            'routes': len(routes),
            'by_route': routes
        }
