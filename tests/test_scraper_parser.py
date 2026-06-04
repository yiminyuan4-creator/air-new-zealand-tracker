import sys
from pathlib import Path
import unittest
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".deps"))
sys.path.insert(0, str(ROOT / "src"))

from scraper import BlockedError, ResultsNotReadyError, Scraper, selected_dates, selected_routes


class ParserTest(unittest.TestCase):
    def test_parse_card_extracts_flight_price_and_times(self):
        text = "Air New Zealand NZ401 departs 9:00AM arrives 10:05AM non-stop 1h 5m from NZD $99"

        row = Scraper.__new__(Scraper)._parse_card(
            text,
            "AKL",
            "WLG",
            "2026-07-01",
            "https://example.test",
            "2026-06-02T18:00:00",
        )

        self.assertEqual(row["time"], "09:00")
        self.assertEqual(row["arrival_time"], "10:05")
        self.assertEqual(row["flight_number"], "NZ0401")
        self.assertEqual(row["price"], 99.0)
        self.assertEqual(row["stops"], 0)

    def test_parse_airnz_leg_option_dom(self):
        from bs4 import BeautifulSoup

        html = """
        <div data-automation="leg-option" data-automation-flight-numbers="NZ0481">
          <div data-automation="leg-option-departure-time">Departs 3:10PM</div>
          <div data-automation="leg-option-arrival-time">Arrives 4:20PM</div>
          <div data-automation="leg-option-flight-count" title="NZ0481">2 flights</div>
          <div data-automation="leg-option-duration">1h 10m</div>
          <div data-automation="leg-option-cost-ds"><span>$157</span></div>
          <div data-automation="leg-option-cost-db"><span>$187</span></div>
        </div>
        """

        rows = Scraper.__new__(Scraper)._parse_airnz_leg_options(
            BeautifulSoup(html, "html.parser"),
            "AKL",
            "WLG",
            "2026-06-03",
            "https://example.test",
            "2026-06-02T18:00:00",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["time"], "15:10")
        self.assertEqual(rows[0]["arrival_time"], "16:20")
        self.assertEqual(rows[0]["flight_number"], "NZ0481")
        self.assertEqual(rows[0]["price"], 157.0)
        self.assertEqual(rows[0]["stops"], 1)

    def test_parse_airnz_flight_row_dom(self):
        from bs4 import BeautifulSoup

        html = """
        <div class="testid__FlightRow">
          <div class="testid__DepartureTime">Departs 7:20pm AKL</div>
          <div class="testid__ArrivalTime">Arrives 9:30pm MEL</div>
          <div>A321neo 1 Flight 4h 10m</div>
          <div class="testid__PriceCardRadioDesktop-1-5-js">seat $325</div>
          <div class="testid__PriceCardRadioDesktop-1-5-wk">the works $365</div>
          <div class="testid__PriceCardRadioDesktop-1-5-wf">works flexi $425</div>
        </div>
        """

        rows = Scraper.__new__(Scraper)._parse_airnz_flight_rows(
            BeautifulSoup(html, "html.parser"),
            "AKL",
            "MEL",
            "2026-12-13",
            "https://example.test",
            "2026-06-02T18:00:00",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["time"], "19:20")
        self.assertEqual(rows[0]["arrival_time"], "21:30")
        self.assertEqual(rows[0]["flight_number"], "A321NEO")
        self.assertEqual(rows[0]["price"], 325.0)
        self.assertEqual(rows[0]["currency"], "NZD")
        self.assertEqual(rows[0]["duration"], "4h 10m")
        self.assertEqual(rows[0]["stops"], 0)

    def test_parse_card_does_not_treat_flight_number_as_price(self):
        text = "Air New Zealand NZ401 departs 09:00 arrives 10:05"

        row = Scraper.__new__(Scraper)._parse_card(
            text,
            "AKL",
            "WLG",
            "2026-07-01",
            "https://example.test",
            "2026-06-02T18:00:00",
        )

        self.assertIsNone(row)

    def test_wait_for_results_stops_on_block_page(self):
        class Body:
            text = "Access denied. Too many requests."

        class Driver:
            def find_element(self, *_args):
                return Body()

        scraper = Scraper.__new__(Scraper)
        scraper.driver = Driver()

        with self.assertRaises(BlockedError):
            scraper._wait_for_results()

    def test_wait_for_results_rejects_empty_airnz_shell(self):
        class Body:
            text = "Search for Flights Sign in Need help? Live chat with our team 24/7 Copyright 2026"

        class Driver:
            page_source = "<html><body>Search for Flights</body></html>"

            def find_element(self, *_args):
                return Body()

        scraper = Scraper.__new__(Scraper)
        scraper.driver = Driver()

        import scraper as scraper_module

        old_timeout = scraper_module.TIMEOUT
        scraper_module.TIMEOUT = 0.01
        try:
            with self.assertRaises(ResultsNotReadyError):
                scraper._wait_for_results()
        finally:
            scraper_module.TIMEOUT = old_timeout

    def test_has_loaded_flight_results_requires_flight_dom(self):
        class Driver:
            page_source = '<div class="testid__FlightRow">Departs 7:00am Arrives 8:45am seat $312</div>'

        scraper = Scraper.__new__(Scraper)
        scraper.driver = Driver()

        self.assertTrue(scraper._has_loaded_flight_results("Departs 7:00am Arrives 8:45am seat $312"))

    def test_selected_routes_parses_cli_routes(self):
        self.assertEqual(
            selected_routes(["akl:wlg", "AKL:SYD"]),
            [{"dept": "AKL", "arrv": "WLG"}, {"dept": "AKL", "arrv": "SYD"}],
        )

    def test_selected_dates_validates_iso_dates(self):
        self.assertEqual(selected_dates(["2026-12-13"]), ["2026-12-13"])
        with self.assertRaises(SystemExit):
            selected_dates(["13/12/2026"])

    def test_run_uses_exact_dates(self):
        scraper = Scraper.__new__(Scraper)
        calls = []

        def fake_search(dept, arrv, departure_date):
            calls.append((dept, arrv, departure_date))
            return [{"price": 1}]

        scraper.search = fake_search
        scraper._sleep = lambda: None

        total = scraper.run(
            routes=[{"dept": "AKL", "arrv": "CSX"}],
            dates=["2026-12-13"],
        )

        self.assertEqual(total, 1)
        self.assertEqual(calls, [("AKL", "CSX", "2026-12-13")])

    def test_run_stops_cleanly_after_block_with_partial_data(self):
        scraper = Scraper.__new__(Scraper)
        calls = []

        def fake_search(dept, arrv, departure_date):
            calls.append((dept, arrv, departure_date))
            if len(calls) == 1:
                return [{"price": 1}]
            raise BlockedError("blocked")

        scraper.search = fake_search
        scraper._sleep = lambda: None

        total = scraper.run(
            routes=[{"dept": "AKL", "arrv": "WLG"}],
            dates=["2026-06-07", "2026-06-08"],
        )

        self.assertEqual(total, 1)
        self.assertEqual(
            calls,
            [("AKL", "WLG", "2026-06-07"), ("AKL", "WLG", "2026-06-08")],
        )

    def test_date_window_starts_on_third_future_day(self):
        dates = Scraper.__new__(Scraper)._date_window(
            days=30,
            start_days_ahead=3,
            today=date(2026, 6, 3),
        )

        self.assertEqual(len(dates), 30)
        self.assertEqual(dates[0], "2026-06-06")
        self.assertEqual(dates[-1], "2026-07-05")

    def test_jobs_limits_and_rotates_search_window(self):
        routes = [{"dept": "AKL", "arrv": code} for code in ["CSX", "WLG", "MEL", "SYD", "NYC"]]
        dates = Scraper.__new__(Scraper)._date_window(
            days=30,
            start_days_ahead=3,
            today=date(2026, 6, 5),
        )
        scraper = Scraper.__new__(Scraper)

        first = scraper._jobs(routes, dates, max_searches=50, today=date(2026, 6, 5))
        second = scraper._jobs(routes, dates, max_searches=50, today=date(2026, 6, 6))

        self.assertEqual(len(first), 50)
        self.assertEqual(len(second), 50)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
