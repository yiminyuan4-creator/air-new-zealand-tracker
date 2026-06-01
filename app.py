import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from db import get_route_data, get_flight_history, get_all

st.set_page_config(page_title="Flight Tracker", layout="wide")
st.title("✈️ Air NZ Flight Prices")

menu = st.sidebar.radio("Menu", ["Route Prices", "Flight History", "Stats"])

if menu == "Route Prices":
    st.header("Route Price Trends")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dept = st.selectbox("From", ["AKL", "SYD", "WLG"])
    with col2:
        arrv = st.selectbox("To", ["CSX", "SYD", "MEL", "NYC"])
    with col3:
        date = st.date_input("Date")
    
    if st.button("Search"):
        rows = get_route_data(dept, arrv, str(date))
        if rows:
            data = {}
            for r in rows:
                t = r['time']
                if t not in data:
                    data[t] = []
                data[t].append((r['ts'], r['price']))
            
            fig = go.Figure()
            for time, prices in data.items():
                ts, p = zip(*prices)
                fig.add_trace(go.Scatter(x=ts, y=p, mode='lines+markers', name=f"{time}"))
            
            fig.update_layout(
                title=f"{dept} → {arrv} Prices",
                xaxis_title="Time",
                yaxis_title="Price (NZD)",
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

elif menu == "Flight History":
    st.header("Flight Price History")
    flights = get_all()
    if flights:
        unique = list(set((f['dept'], f['arrv'], f['date'], f['time']) for f in flights))
        flight = st.selectbox(
            "Select Flight",
            unique,
            format_func=lambda x: f"{x[0]}->{x[1]} {x[2]} {x[3]}"
        )
        
        if flight:
            dept, arrv, date, time = flight
            rows = get_flight_history(dept, arrv, date, time)
            if rows:
                df = pd.DataFrame([{'Time': r['ts'], 'Price': r['price']} for r in rows])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df['Time'], y=df['Price'], mode='lines+markers', fill='tozeroy'))
                fig.update_layout(
                    title=f"{flight[0]}->{flight[1]} {flight[2]} {flight[3]}",
                    xaxis_title="Checked At",
                    yaxis_title="Price (NZD)"
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df, use_container_width=True)

else:  # Stats
    st.header("Database Stats")
    flights = get_all()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Records", len(flights))
    with col2:
        routes = len(set((f['dept'], f['arrv']) for f in flights))
        st.metric("Routes", routes)
    with col3:
        st.metric("Last Update", flights[0]['ts'][:10] if flights else "N/A")
    
    st.subheader("Records by Route")
    route_data = {}
    for f in flights:
        k = f"{f['dept']}->{f['arrv']}"
        route_data[k] = route_data.get(k, 0) + 1
    
    df = pd.DataFrame([(k, v) for k, v in route_data.items()], columns=['Route', 'Count'])
    fig = go.Figure(data=[go.Bar(x=df['Route'], y=df['Count'])])
    st.plotly_chart(fig, use_container_width=True)
