import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import ORIGIN, START_DAYS_AHEAD
from db import get_all, init_db


NAMES = {
    "AKL": "Auckland",
    "CSX": "Changsha",
    "WLG": "Wellington",
    "MEL": "Melbourne",
    "SYD": "Sydney",
    "NYC": "New York",
}


def city(code):
    return f"{NAMES.get(code, code)} ({code})"


def ts(value):
    return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M")


def itinerary(row):
    arrival = row.get("arrival_time") or "?"
    flight = row.get("flight_number") or "Flight"
    duration = row.get("duration") or ""
    stops = row.get("stops")
    stop_text = "" if pd.isna(stops) else f" · {int(stops)} stop" + ("" if int(stops) == 1 else "s")
    return " · ".join([f"{row['time']} -> {arrival}", str(flight), str(duration)]).strip(" ·") + stop_text


def load_data():
    init_db()
    rows = get_all()
    df = pd.DataFrame([dict(row) for row in rows])
    if df.empty:
        return df
    df["date_dt"] = pd.to_datetime(df["date"])
    df["scrape_dt"] = pd.to_datetime(df["scrape_ts"])
    df["itinerary"] = df.apply(itinerary, axis=1)
    return df


FLIGHT_COLUMNS = ["time", "arrival_time", "flight_number", "duration"]


def default_date(dates):
    target = (
        pd.Timestamp.now(tz="Pacific/Auckland").date()
        + pd.Timedelta(days=START_DAYS_AHEAD)
    ).strftime("%Y-%m-%d")
    for value in dates:
        if value >= target:
            return pd.to_datetime(value).date()
    return pd.to_datetime(dates[-1]).date()


def date_input(dates, value=None, key="departure_date"):
    values = [pd.to_datetime(value).date() for value in dates]
    selected = st.sidebar.date_input(
        "Departure date",
        value=value or default_date(dates),
        min_value=min(values),
        max_value=max(values),
        key=key,
    )
    value = selected.strftime("%Y-%m-%d")
    if value not in dates:
        st.warning("No saved prices are available for this date.")
        st.stop()
    return value


def latest_rows(df):
    return df[df["scrape_ts"] == df.groupby("date")["scrape_ts"].transform("max")].copy()


def flight_history_counts(df):
    return (
        df.assign(**{col: df[col].fillna("") for col in FLIGHT_COLUMNS})
        .groupby(["date"] + FLIGHT_COLUMNS)
        .size()
        .reset_index(name="captures")
    )


def line_chart(df, x, y, title, x_title, y_title, hover=None):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            customdata=df[hover] if hover else None,
            hovertemplate="%{x}<br>Price %{y:.0f}<extra></extra>",
        )
    )
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), xaxis_title=x_title, yaxis_title=y_title)
    fig.update_xaxes(automargin=True)
    st.subheader(title)
    st.plotly_chart(fig, width="stretch")


st.set_page_config(page_title="Air NZ Flight Price Tracker", layout="wide")
st.title("Air NZ Flight Price Tracker")

data = load_data()
if data.empty:
    st.info("No flight prices have been saved yet.")
    st.stop()

st.sidebar.header("Chart")
chart = st.sidebar.radio(
    "Choose chart",
    ["Buy timing", "Departure timing"],
    format_func=lambda value: {
        "Buy timing": "Price history by booking lead time",
        "Departure timing": "Lowest price by departure date",
    }[value],
)

destinations = sorted(data.loc[data["dept"] == ORIGIN, "arrv"].unique())
arrv = st.sidebar.selectbox("Destination", destinations, format_func=city)
route = data[(data["dept"] == ORIGIN) & (data["arrv"] == arrv)].copy()
currency = route["currency"].dropna().iloc[0] if route["currency"].notna().any() else "NZD"
st.caption(f"{city(ORIGIN)} to {city(arrv)} · latest capture {ts(route['scrape_ts'].max())}")

if chart == "Buy timing":
    dates = sorted(route["date"].unique())
    counts = flight_history_counts(route)
    best_count = counts.sort_values(["captures", "date"], ascending=[False, True]).iloc[0]
    selected_date = date_input(
        dates,
        value=pd.to_datetime(best_count["date"]).date(),
        key=f"buy_date_{arrv}",
    )
    date_rows = route[route["date"] == selected_date].copy()
    current = latest_rows(date_rows).sort_values(["time", "price"]).reset_index(drop=True)
    current_counts = flight_history_counts(date_rows).drop(columns=["date"])
    current = current.assign(**{col: current[col].fillna("") for col in FLIGHT_COLUMNS})
    current = current.merge(current_counts, on=FLIGHT_COLUMNS, how="left")
    current["captures"] = current["captures"].fillna(1).astype(int)
    current["flight_option"] = current["itinerary"] + " · " + current["captures"].astype(str) + " captures"
    default_flight_index = int(current["captures"].idxmax())
    selected_flight = st.sidebar.selectbox(
        "Flight",
        current["flight_option"].tolist(),
        index=default_flight_index,
        key=f"buy_flight_{arrv}_{selected_date}",
    )
    flight = current[current["flight_option"] == selected_flight].iloc[0]

    history = date_rows[
        (date_rows["time"] == flight["time"])
        & (date_rows["arrival_time"].fillna("") == str(flight.get("arrival_time") or ""))
        & (date_rows["flight_number"].fillna("") == str(flight.get("flight_number") or ""))
        & (date_rows["duration"].fillna("") == str(flight.get("duration") or ""))
    ].sort_values("scrape_dt")
    history["days_before_departure"] = (
        pd.to_datetime(selected_date) - history["scrape_dt"]
    ).dt.total_seconds().div(86400).round(1)

    if len(history) < 2:
        st.info("This flight has only one saved capture so far. The line will appear after at least two daily captures.")
    line_chart(
        history,
        "days_before_departure",
        "price",
        "Price by booking lead time",
        "Days before departure",
        f"Price ({currency})",
    )
    st.dataframe(
        history[["scrape_ts", "days_before_departure", "price", "currency"]].rename(
            columns={
                "scrape_ts": "Captured at",
                "days_before_departure": "Days before departure",
                "price": "Price",
                "currency": "Currency",
            }
        ),
        width="stretch",
        hide_index=True,
    )

else:
    start = (
        pd.Timestamp.now(tz="Pacific/Auckland").date()
        + pd.Timedelta(days=START_DAYS_AHEAD)
    ).strftime("%Y-%m-%d")
    current = latest_rows(route[route["date"] >= start])
    if current.empty:
        current = latest_rows(route)
    best = current.loc[current.groupby("date")["price"].idxmin()].sort_values("date")

    line_chart(
        best,
        "date",
        "price",
        "Lowest price by departure date",
        "Departure date",
        f"Lowest price ({currency})",
    )
    st.dataframe(
        best[["date", "time", "arrival_time", "flight_number", "duration", "stops", "price", "currency"]].rename(
            columns={
                "date": "Departure date",
                "time": "Departure",
                "arrival_time": "Arrival",
                "flight_number": "Flight",
                "duration": "Duration",
                "stops": "Stops",
                "price": "Price",
                "currency": "Currency",
            }
        ),
        width="stretch",
        hide_index=True,
    )
