import streamlit as st
import pandas as pd
import requests
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Elite Alt-Hunter Terminal", layout="wide", page_icon="⚡")
st_autorefresh(interval=30 * 1000, key="data_refresh")

# Estilo visual mejorado
st.markdown("""
    <style>
    .metric-card {
        background-color: #121212;
        padding: 15px;
        border-radius: 8px;
        border-top: 3px solid #4CAF50;
        text-align: center;
    }
    .stDataFrame { border: 1px solid #333; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

def get_live_prices(symbols):
    try:
        sym_list = '["' + '","'.join(symbols) + '"]'
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={sym_list}"
        res = requests.get(url, timeout=5).json()
        return {item['symbol']: {"p": float(item['lastPrice']), "c": float(item['priceChangePercent'])} for item in res}
    except: return {}

# --- HEADER ---
st.title("⚡ Elite Alt-Hunter Terminal")
PARES = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT"]
live_data = get_live_prices(PARES)

if live_data:
    cols = st.columns(len(PARES))
    for i, symbol in enumerate(PARES):
        d = live_data.get(symbol, {"p": 0, "c": 0})
        cols[i].metric(symbol.replace("USDT", ""), f"${d['p']:,.2f}", f"{d['c']}%")

st.divider()

# --- PROCESAMIENTO DE BITÁCORA ---
ARCHIVO = "bitacora_multimoneda.csv"

if os.path.exists(ARCHIVO):
    df = pd.read_csv(ARCHIVO)
    if not df.empty:
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        # --- FILA DE MÉTRICAS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Señales", len(df))
        m2.metric("Tendencia BTC", df.iloc[-1]['Macro_BTC'], delta_color="normal")
        m3.metric("Última Alerta", df.iloc[-1]['Par'])
        m4.metric("Win Rate Est. (Longs)", f"{(len(df[df['Tipo']=='LONG'])/len(df)*100):.1f}%")

        # --- SECCIÓN DE HEATMAP (NUEVO) ---
        st.subheader("🔥 Mapa de Calor: Actividad del Bot por Hora")
        
        # Preparar datos para el Heatmap
        df['Hora'] = df['Fecha'].dt.hour
        df['Día'] = df['Fecha'].dt.day_name()
        
        # Crear matriz de actividad
        heatmap_data = df.groupby(['Día', 'Hora']).size().reset_index(name='Señales')
        
        # Ordenar días de la semana
        dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        fig_heat = px.density_heatmap(
            heatmap_data, 
            x="Hora", 
            y="Día", 
            z="Señales",
            category_orders={"Día": dias_orden},
            color_continuous_scale="Viridis",
            text_auto=True,
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
        

        # --- HISTORIAL Y DISTRIBUCIÓN ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("📜 Historial Reciente")
            def color_row(val):
                return 'color: #00ff00' if val == 'LONG' else 'color: #ff4b4b'
            
            st.dataframe(
                df.sort_values(by="Fecha", ascending=False).head(15).style.applymap(color_row, subset=['Tipo']),
                use_container_width=True
            )
            
        with c2:
            st.subheader("📊 Distribución")
            fig_pie = px.pie(df, names='Par', hole=0.4, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("Esperando datos del bot...")
else:
    st.warning("Archivo de bitácora no encontrado.")