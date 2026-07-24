import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import CITY_NAMES, ORIGIN, START_DAYS_AHEAD
from db import get_all, init_db


def city(code):
    return f"{CITY_NAMES.get(code, code)} ({code})"


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


def date_capture_counts(df):
    return (
        df.groupby("date")["scrape_ts"]
        .nunique()
        .reset_index(name="captures")
    )


def line_chart(df, x, y, title, x_title, y_title, hover=None):
    fig = go.Figure()
    hovertemplate = "%{x}<br>Price %{y:.0f}<extra></extra>"
    if hover:
        details = "".join(f"<br>{label}: %{{customdata[{i}]}}" for i, label in enumerate(hover))
        hovertemplate = f"{x_title}: %{{x}}<br>Price: %{{y:.0f}}{details}<extra></extra>"
    fig.add_trace(
        go.Scatter(
            x=df[x],
            y=df[y],
            mode="lines+markers",
            customdata=df[hover] if hover else None,
            hovertemplate=hovertemplate,
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
    counts = date_capture_counts(route)
    best_count = counts.sort_values(["captures", "date"], ascending=[False, True]).iloc[0]
    selected_date = date_input(
        dates,
        value=pd.to_datetime(best_count["date"]).date(),
        key=f"buy_date_{arrv}",
    )
    date_rows = route[route["date"] == selected_date].copy()
    idx = date_rows.groupby("scrape_ts")["price"].idxmin()
    history = date_rows.loc[idx].sort_values("scrape_dt")
    history["days_before_departure"] = (
        pd.to_datetime(selected_date) - history["scrape_dt"]
    ).dt.total_seconds().div(86400).round(1)
    history["Captured"] = history["scrape_dt"].dt.strftime("%Y-%m-%d %H:%M")
    history = history.sort_values("days_before_departure")
    table = history.sort_values("scrape_dt", ascending=False)
    latest = table.iloc[0]
    st.caption(
        f"Latest saved price for {selected_date}: {currency} {latest['price']:.0f} "
        f"captured {ts(latest['scrape_ts'])}"
    )

    if len(history) < 2:
        st.info("This route/date has only one saved capture so far. The line will appear after at least two captures.")
    line_chart(
        history,
        "days_before_departure",
        "price",
        "Price by booking lead time",
        "Days before departure",
        f"Price ({currency})",
        ["Captured", "itinerary"],
    )
    st.dataframe(
        table[[
            "scrape_ts",
            "days_before_departure",
            "time",
            "arrival_time",
            "flight_number",
            "duration",
            "price",
            "currency",
        ]].rename(
            columns={
                "scrape_ts": "Captured at",
                "days_before_departure": "Days before departure",
                "time": "Departure",
                "arrival_time": "Arrival",
                "flight_number": "Flight",
                "duration": "Duration",
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
