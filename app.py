
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

st.set_page_config(page_title="UPTREND Market Dashboard", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp {background:#0b0f14;color:#e8edf2;}
[data-testid="stSidebar"] {background:#111820;}
[data-testid="stMetric"] {background:#151d27;border:1px solid #263241;padding:14px;border-radius:12px;}
h1,h2,h3 {color:#f4f7fa;}
div[data-testid="stDataFrame"] {border:1px solid #263241;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

DATA = Path(__file__).parent / "uptrend_history.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA)
    df["Snapshot Date"] = pd.to_datetime(df["Snapshot Date"])
    return df

def save_data(df):
    df.to_csv(DATA, index=False)
    load_data.clear()

def add_signals(df):
    d=df.copy()
    e10="Exponential moving average, 10, 1 day"; e20="Exponential moving average, 20, 1 day"
    e50="Exponential moving average, 50, 1 day"; e200="Exponential moving average, 200, 1 day"
    for c in [e10,e20,e50,e200,"Price"]:
        d[c]=pd.to_numeric(d[c], errors="coerce")
    d["Strong Trend"]=(d["Price"]>d[e10])&(d[e10]>=d[e20])&(d[e20]>=d[e50])&(d[e50]>=d[e200])
    d["MACD Daily Bullish"]=pd.to_numeric(d["Moving average convergence divergence, 12,26, 1 day, Level"],errors="coerce") >= pd.to_numeric(d["Moving average convergence divergence, 12,26, 1 day, Signal"],errors="coerce")
    d["MACD Weekly Bullish"]=pd.to_numeric(d["Moving average convergence divergence, 12,26, 1 week, Level"],errors="coerce") >= pd.to_numeric(d["Moving average convergence divergence, 12,26, 1 week, Signal"],errors="coerce")
    d["Trend Score"]=d["Strong Trend"].astype(int)*2+d["MACD Daily Bullish"].astype(int)+d["MACD Weekly Bullish"].astype(int)
    return d

df=add_signals(load_data())

with st.sidebar:
    st.title("UPTREND")
    st.caption("Daily market trend dashboard")
    page=st.radio("Navigation",["Overview","Sector Analysis","Stock Explorer","Daily Changes","Upload Data"])
    st.divider()
    dates=sorted(df["Snapshot Date"].dt.date.unique())
    selected_dates=st.multiselect("Snapshot date",dates,default=dates)
    sectors=sorted(df["Sector"].dropna().unique())
    selected_sectors=st.multiselect("Sector",sectors)
    exchanges=sorted(df["Exchange"].dropna().unique())
    selected_exchanges=st.multiselect("Exchange",exchanges)

f=df[df["Snapshot Date"].dt.date.isin(selected_dates)]
if selected_sectors: f=f[f["Sector"].isin(selected_sectors)]
if selected_exchanges: f=f[f["Exchange"].isin(selected_exchanges)]

latest=max(selected_dates) if selected_dates else df["Snapshot Date"].dt.date.max()
latest_df=f[f["Snapshot Date"].dt.date==latest]
prev_dates=[x for x in dates if x<latest]
prev_df=f[f["Snapshot Date"].dt.date==max(prev_dates)] if prev_dates else f.iloc[0:0]

if page=="Overview":
    st.title("UPTREND Market Dashboard")
    st.caption(f"Latest snapshot: {latest:%d %b %Y}  •  Dark Power BI-style view")
    new=set(latest_df["Symbol"])-set(prev_df["Symbol"])
    removed=set(prev_df["Symbol"])-set(latest_df["Symbol"])
    c1,c2,c3,c4,c5,c6=st.columns(6)
    c1.metric("Uptrend Stocks",len(latest_df))
    c2.metric("New Entries",len(new))
    c3.metric("Removed",len(removed))
    c4.metric("Strong Trend",int(latest_df["Strong Trend"].sum()))
    c5.metric("Avg 1D Return",f'{pd.to_numeric(latest_df["Price change %, 1 day"],errors="coerce").mean():.2f}%')
    c6.metric("Avg 1M Return",f'{pd.to_numeric(latest_df["Price change %, 1 month"],errors="coerce").mean():.2f}%')
    a,b=st.columns((1.2,1))
    counts=f.groupby("Snapshot Date")["Symbol"].nunique().reset_index(name="Stocks")
    fig=px.line(counts,x="Snapshot Date",y="Stocks",markers=True,title="Uptrend Universe Over Time",template="plotly_dark")
    a.plotly_chart(fig,use_container_width=True)
    sector=latest_df.groupby("Sector")["Symbol"].nunique().sort_values(ascending=True).tail(12).reset_index(name="Stocks")
    fig=px.bar(sector,x="Stocks",y="Sector",orientation="h",title="Top Sectors by Uptrend Stocks",template="plotly_dark")
    b.plotly_chart(fig,use_container_width=True)
    a,b=st.columns(2)
    top=latest_df.assign(Return=pd.to_numeric(latest_df["Price change %, 1 day"],errors="coerce")).nlargest(10,"Return")
    fig=px.bar(top,x="Symbol",y="Return",hover_data=["Description"],title="Top 10 Daily Performers",template="plotly_dark")
    a.plotly_chart(fig,use_container_width=True)
    trend=latest_df["Trend Score"].value_counts().sort_index().reset_index()
    trend.columns=["Trend Score","Stocks"]
    fig=px.pie(trend,names="Trend Score",values="Stocks",hole=.55,title="Trend Strength Mix",template="plotly_dark")
    b.plotly_chart(fig,use_container_width=True)

elif page=="Sector Analysis":
    st.title("Sector & Industry Analysis")
    metric=st.selectbox("Performance metric",["Price change %, 1 day","Price change %, 1 week","Price change %, 1 month","Performance %, 3 months","Performance %, 1 year"])
    s=latest_df.copy(); s["Metric"]=pd.to_numeric(s[metric],errors="coerce")
    sector=s.groupby("Sector").agg(Stocks=("Symbol","nunique"),Average_Return=("Metric","mean")).reset_index().sort_values("Average_Return")
    st.plotly_chart(px.bar(sector,x="Average_Return",y="Sector",orientation="h",color="Stocks",title=f"Sector Average: {metric}",template="plotly_dark"),use_container_width=True)
    industry=s.groupby(["Sector","Industry"]).agg(Stocks=("Symbol","nunique"),Average_Return=("Metric","mean")).reset_index().sort_values("Average_Return",ascending=False)
    st.dataframe(industry,use_container_width=True,hide_index=True)

elif page=="Stock Explorer":
    st.title("Stock Explorer")
    search=st.text_input("Search symbol or company")
    x=f.copy()
    if search:
        x=x[x["Symbol"].astype(str).str.contains(search,case=False,na=False)|x["Description"].astype(str).str.contains(search,case=False,na=False)]
    cols=["Snapshot Date","Symbol","Description","Price","Price change %, 1 day","Price change %, 1 week","Price change %, 1 month","Sector","Industry","Exchange","Volume, 1 day","Market capitalization","Trend Score","Strong Trend","MACD Daily Bullish","MACD Weekly Bullish"]
    st.dataframe(x[cols].sort_values(["Snapshot Date","Trend Score"],ascending=[False,False]),use_container_width=True,hide_index=True)

elif page=="Daily Changes":
    st.title("Daily Changes")
    if prev_df.empty:
        st.info("Upload at least two daily snapshots to compare changes.")
    else:
        a,b=st.columns(2)
        a.subheader(f"New entries ({len(new)})")
        a.dataframe(latest_df[latest_df["Symbol"].isin(new)][["Symbol","Description","Sector","Price","Price change %, 1 day"]],use_container_width=True,hide_index=True)
        b.subheader(f"Removed ({len(removed)})")
        b.dataframe(prev_df[prev_df["Symbol"].isin(removed)][["Symbol","Description","Sector","Price","Price change %, 1 day"]],use_container_width=True,hide_index=True)

else:
    st.title("Upload Daily CSV")
    st.write("Upload a file named like `UPTREND_YYYY-MM-DD_xxxxx.csv`. Existing dates will be replaced.")
    up=st.file_uploader("Choose CSV",type="csv")
    if up is not None:
        incoming=pd.read_csv(up)
        m=re.search(r"UPTREND_(\d{4}-\d{2}-\d{2})_",up.name)
        date=st.date_input("Snapshot date",value=pd.to_datetime(m.group(1)).date() if m else pd.Timestamp.today().date())
        if st.button("Import and Refresh",type="primary"):
            incoming["Snapshot Date"]=pd.to_datetime(date)
            old=load_data()
            old=old[old["Snapshot Date"].dt.date!=date]
            combined=pd.concat([old,incoming],ignore_index=True)
            save_data(combined)
            st.success(f"Imported {len(incoming):,} rows for {date}. Refresh the page to view updated visuals.")
