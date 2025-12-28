import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import requests
from datetime import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Elite Alt-Hunter Cloud", layout="wide", page_icon="⚡")
st_autorefresh(interval=30 * 1000, key="data_refresh")

# 2. CONEXIÓN CON GOOGLE SHEETS (Usando Secrets)
def conectar_google_sheets():
    # Cargamos las credenciales desde los Secrets de Streamlit
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    # Abrimos la hoja por su nombre
    sheet = client.open("Trading_Log").sheet1
    return sheet

def obtener_datos_live(symbols):
    try:
        sym_list = '["' + '","'.join(symbols) + '"]'
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbols={sym_list}"
        res = requests.get(url, timeout=5).json()
        return {item['symbol']: {"p": float(item['lastPrice']), "c": float(item['priceChangePercent'])} for item in res}
    except: return {}

# --- RENDERIZADO DEL DASHBOARD ---
st.title("⚡ Elite Alt-Hunter: Cloud Terminal")
st.caption(f"Sincronizado con Google Sheets | {datetime.now().strftime('%H:%M:%S')}")

# Ticker en vivo
PARES = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT"]
live_data = obtener_datos_live(PARES)

if live_data:
    cols = st.columns(len(PARES))
    for i, symbol in enumerate(PARES):
        d = live_data.get(symbol, {"p": 0, "c": 0})
        cols[i].metric(symbol.replace("USDT", ""), f"${d['p']:,.2f}", f"{d['c']}%")

st.divider()

# CARGAR DATOS DESDE LA HOJA
try:
    sheet = conectar_google_sheets()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df['Fecha'] = pd.to_datetime(df['Fecha'])

        # MÉTRICAS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Señales", len(df))
        m2.metric("Tendencia BTC", df.iloc[-1]['Macro_BTC'])
        m3.metric("Última Moneda", df.iloc[-1]['Par'])
        m4.metric("RSI Promedio", f"{df['RSI'].mean():.1f}")

        # HEATMAP HORARIO
        st.subheader("🔥 Mapa de Calor: Actividad Horaria")
        df['Hora'] = df['Fecha'].dt.hour
        df['Día'] = df['Fecha'].dt.day_name()
        heatmap_data = df.groupby(['Día', 'Hora']).size().reset_index(name='Señales')
        dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        fig_heat = px.density_heatmap(
            heatmap_data, x="Hora", y="Día", z="Señales",
            category_orders={"Día": dias_orden},
            color_continuous_scale="Viridis", text_auto=True, template="plotly_dark"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # TABLA Y PIE CHART
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("📜 Historial en la Nube")
            st.dataframe(df.sort_values(by="Fecha", ascending=False), use_container_width=True)
        with c2:
            st.subheader("📊 Distribución de Cartera")
            fig_pie = px.pie(df, names='Par', hole=0.4, template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Conectado a Google Sheets, pero la hoja está vacía. El bot aún no ha enviado señales.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.info("Asegúrate de haber compartido la hoja 'Trading_Log' con el correo de la Service Account.")
