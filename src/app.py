import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import ROUTES, START_DAYS_AHEAD
from db import (
    get_all,
    get_dates,
    get_flight_history,
    get_route_data,
    get_routes,
    get_scrape_times,
    init_db,
)


AIRPORT_NAMES = {
    "AKL": "Auckland",
    "CSX": "Changsha",
    "WLG": "Wellington",
    "MEL": "Melbourne",
    "SYD": "Sydney",
    "NYC": "New York",
}


def city_name(code):
    return AIRPORT_NAMES.get(code, code)


def city_label(code):
    name = city_name(code)
    return f"{name} ({code})" if name != code else code


def short_ts(value):
    if not value:
        return ""
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return str(value)


def itinerary_label(row):
    arrival = row.get("arrival_time") or "?"
    flight = row.get("flight_number") or "Flight"
    duration = row.get("duration") or ""
    stops = row.get("stops")
    stop_text = "" if stops in (None, "") else f" · {stops} stop"
    if stops not in (None, "", 1, "1"):
        stop_text += "s"
    pieces = [f"{row['time']} -> {arrival}", str(flight)]
    if duration:
        pieces.append(str(duration))
    return " · ".join(pieces) + stop_text


def money(value, currency):
    if pd.isna(value):
        return "-"
    return f"{currency} {float(value):,.0f}"


def default_departure_index(dates):
    today = pd.Timestamp.now(tz="Pacific/Auckland").date()
    target = (today + pd.Timedelta(days=START_DAYS_AHEAD)).strftime("%Y-%m-%d")
    for index, value in enumerate(dates):
        if value >= target:
            return index
    return max(len(dates) - 1, 0)


st.set_page_config(page_title="Air NZ Flight Price Tracker", layout="wide")

st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            padding: 0.8rem 0.9rem;
            background: rgba(250, 250, 250, 0.72);
        }
        [data-testid="stSidebar"] h2 { padding-top: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

init_db()
flights = get_all()

st.title("Air NZ Flight Price Tracker")

if not flights:
    st.info("No flight prices have been saved yet. Run the scraper to populate SQLite.")
    st.stop()

all_df = pd.DataFrame([dict(f) for f in flights])
route_rows = get_routes()
route_options = [(r["dept"], r["arrv"]) for r in route_rows] or [
    (r["dept"], r["arrv"]) for r in ROUTES
]

st.sidebar.header("Filters")

origin_options = sorted({dept for dept, _ in route_options})
default_origin = origin_options.index("AKL") if "AKL" in origin_options else 0
dept = st.sidebar.selectbox("From", origin_options, index=default_origin, format_func=city_label)

destination_options = sorted({arrv for d, arrv in route_options if d == dept})
if not destination_options:
    st.warning("No destinations are available for this origin.")
    st.stop()
arrv = st.sidebar.selectbox("To", destination_options, format_func=city_label)

dates = get_dates(dept, arrv)
if not dates:
    st.warning("No departure dates are available for this route.")
    st.stop()
date_values = [pd.to_datetime(value).date() for value in dates]
departure_value = st.sidebar.date_input(
    "Departure date",
    value=date_values[default_departure_index(dates)],
    min_value=min(date_values),
    max_value=max(date_values),
)
departure_date = departure_value.strftime("%Y-%m-%d")
if departure_date not in dates:
    st.warning("No saved prices are available for this departure date.")
    st.stop()

scrape_times = get_scrape_times(dept, arrv, departure_date)
if not scrape_times:
    st.warning("No captured prices are available for this route and date.")
    st.stop()
selected_scrape = st.sidebar.selectbox(
    "Captured at",
    scrape_times,
    format_func=short_ts,
)

route_rows = get_route_data(dept, arrv, departure_date, selected_scrape)
route_df = pd.DataFrame([dict(r) for r in route_rows])

if route_df.empty:
    st.warning("No rows match this selection.")
    st.stop()

route_df["dept"] = dept
route_df["arrv"] = arrv
route_df["date"] = departure_date
route_df = route_df.sort_values(["time", "price"], na_position="last").reset_index(drop=True)
route_df["itinerary"] = route_df.apply(itinerary_label, axis=1)
selected_itinerary = st.sidebar.selectbox("Flight", route_df["itinerary"].tolist())
flight_row = route_df.loc[route_df["itinerary"] == selected_itinerary].iloc[0]

history_rows = get_flight_history(
    dept,
    arrv,
    departure_date,
    flight_row["time"],
    flight_row.get("arrival_time"),
    flight_row.get("flight_number"),
    flight_row.get("duration"),
)
history_df = pd.DataFrame([dict(r) for r in history_rows])
currency = route_df["currency"].dropna().iloc[0] if route_df["currency"].notna().any() else "NZD"

st.caption(
    f"{city_name(dept)} to {city_name(arrv)} · {departure_date} · captured {short_ts(selected_scrape)}"
)

metric_cols = st.columns(4)
metric_cols[0].metric("Lowest price", money(route_df["price"].min(), currency))
metric_cols[1].metric("Itineraries", len(route_df))
metric_cols[2].metric("Price points", len(history_df))
metric_cols[3].metric("Latest capture", short_ts(all_df["scrape_ts"].max()))

chart_left, chart_right = st.columns((1.15, 1))

with chart_left:
    st.subheader("Prices by departure time")
    price_by_time = go.Figure()
    price_by_time.add_trace(
        go.Scatter(
            x=route_df["itinerary"],
            y=route_df["price"],
            mode="lines+markers",
            customdata=route_df[["arrival_time", "flight_number", "duration", "stops"]].fillna(""),
            hovertemplate=(
                "Itinerary %{x}<br>"
                "Price %{y:.0f}<br>"
                "Arrives %{customdata[0]}<br>"
                "Flight %{customdata[1]}<br>"
                "Duration %{customdata[2]}<br>"
                "Stops %{customdata[3]}<extra></extra>"
            ),
        )
    )
    price_by_time.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Departure time and flight",
        yaxis_title=f"Price ({currency})",
        hovermode="x",
    )
    price_by_time.update_xaxes(tickangle=35, automargin=True)
    st.plotly_chart(price_by_time, width="stretch")

with chart_right:
    st.subheader("Selected flight price history")
    history_fig = go.Figure()
    if history_df.empty:
        history_fig.add_annotation(
            text="No history yet",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
        )
    else:
        history_df = history_df.sort_values("scrape_ts").reset_index(drop=True)
        history_fig.add_trace(
            go.Scatter(
                x=history_df["scrape_ts"].map(short_ts),
                y=history_df["price"],
                mode="lines+markers",
                fill="tozeroy",
                hovertemplate="Captured %{x}<br>Price %{y:.0f}<extra></extra>",
            )
        )
    history_fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Captured at",
        yaxis_title=f"Price ({currency})",
    )
    history_fig.update_xaxes(automargin=True)
    st.plotly_chart(history_fig, width="stretch")

st.subheader("Captured itineraries")
display_df = route_df[
    [
        "dept",
        "arrv",
        "date",
        "time",
        "arrival_time",
        "flight_number",
        "duration",
        "stops",
        "price",
        "currency",
        "scrape_ts",
    ]
].rename(
    columns={
        "dept": "From",
        "arrv": "To",
        "date": "Departure date",
        "time": "Departure",
        "arrival_time": "Arrival",
        "flight_number": "Flight",
        "duration": "Duration",
        "stops": "Stops",
        "price": "Price",
        "currency": "Currency",
        "scrape_ts": "Captured at",
    }
)
display_df["From"] = display_df["From"].map(city_label)
display_df["To"] = display_df["To"].map(city_label)
display_df["Captured at"] = display_df["Captured at"].map(short_ts)
st.dataframe(display_df, width="stretch", hide_index=True)

with st.expander("Database summary"):
    summary_cols = st.columns(3)
    summary_cols[0].metric("Total records", len(all_df))
    summary_cols[1].metric("Routes tracked", all_df[["dept", "arrv"]].drop_duplicates().shape[0])
    summary_cols[2].metric("Departure dates", all_df["date"].nunique())

    route_counts = all_df.groupby(["dept", "arrv"]).size().reset_index(name="records")
    route_counts["route"] = route_counts.apply(
        lambda row: f"{city_name(row['dept'])} -> {city_name(row['arrv'])}",
        axis=1,
    )
    route_fig = go.Figure(data=[go.Bar(x=route_counts["route"], y=route_counts["records"])])
    route_fig.update_layout(
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Route",
        yaxis_title="Records",
    )
    st.plotly_chart(route_fig, width="stretch")
