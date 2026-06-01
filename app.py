import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import ROUTES
from db import get_all, get_dates, get_flight_history, get_route_data, get_routes, get_scrape_times, init_db


st.set_page_config(page_title="Air NZ Flight Price Tracker", layout="wide")
st.title("Air NZ Flight Price Tracker")

init_db()
flights = get_all()

if not flights:
    st.info("No flight prices have been saved yet. Run `python scraper.py` first.")
    st.stop()

route_rows = get_routes()
route_options = [(r["dept"], r["arrv"]) for r in route_rows] or [(r["dept"], r["arrv"]) for r in ROUTES]

view = st.sidebar.radio("Chart", ["Route departure times", "Flight price history", "Database stats"])

if view == "Route departure times":
    st.header("Same route, different departure times")
    col1, col2, col3 = st.columns(3)
    with col1:
        route = st.selectbox("Route", route_options, format_func=lambda x: f"{x[0]} -> {x[1]}")
    dept, arrv = route
    dates = get_dates(dept, arrv)
    with col2:
        departure_date = st.selectbox("Departure date", dates)
    scrape_times = get_scrape_times(dept, arrv, departure_date)
    with col3:
        selected_scrape = st.selectbox("Captured at", scrape_times)

    rows = get_route_data(dept, arrv, departure_date, selected_scrape)
    df = pd.DataFrame([dict(r) for r in rows])

    if df.empty:
        st.warning("No rows match this selection.")
    else:
        label = df["time"].astype(str)
        if "flight_number" in df:
            label = label + " " + df["flight_number"].fillna("")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=label,
            y=df["price"],
            mode="lines+markers",
            text=df.get("arrival_time"),
            hovertemplate="Depart %{x}<br>Price %{y:.2f}<br>Arrive %{text}<extra></extra>",
        ))
        fig.update_layout(
            title=f"{dept} -> {arrv} on {departure_date}",
            xaxis_title="Departure time",
            yaxis_title=f"Price ({df['currency'].iloc[0]})",
            hovermode="x",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

elif view == "Flight price history":
    st.header("Same flight, different check times")
    unique = sorted(set(
        (
            f["dept"],
            f["arrv"],
            f["date"],
            f["time"],
            f["arrival_time"],
            f["flight_number"],
            f["duration"],
        )
        for f in flights
    ))
    selected = st.selectbox(
        "Flight",
        unique,
        format_func=lambda x: f"{x[0]} -> {x[1]} | {x[2]} {x[3]}-{x[4] or '?'} | {x[5] or 'flight'} | {x[6] or ''}",
    )
    dept, arrv, departure_date, departure_time, arrival_time, flight_number, duration = selected
    rows = get_flight_history(dept, arrv, departure_date, departure_time, arrival_time, flight_number, duration)
    df = pd.DataFrame([dict(r) for r in rows])

    if df.empty:
        st.warning("No history found for this flight.")
    else:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["scrape_ts"],
            y=df["price"],
            mode="lines+markers",
            fill="tozeroy",
            hovertemplate="Checked %{x}<br>Price %{y:.2f}<extra></extra>",
        ))
        fig.update_layout(
            title=f"{dept} -> {arrv} | {departure_date} {departure_time}-{arrival_time or '?'}",
            xaxis_title="Check timestamp",
            yaxis_title=f"Price ({df['currency'].iloc[0]})",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

else:
    st.header("Database stats")
    df = pd.DataFrame([dict(f) for f in flights])
    col1, col2, col3 = st.columns(3)
    col1.metric("Records", len(df))
    col2.metric("Routes", df[["dept", "arrv"]].drop_duplicates().shape[0])
    col3.metric("Last capture", df["scrape_ts"].max())

    route_counts = df.groupby(["dept", "arrv"]).size().reset_index(name="records")
    route_counts["route"] = route_counts["dept"] + " -> " + route_counts["arrv"]
    fig = go.Figure(data=[go.Bar(x=route_counts["route"], y=route_counts["records"])])
    fig.update_layout(xaxis_title="Route", yaxis_title="Records")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True)
