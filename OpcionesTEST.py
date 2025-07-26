import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- Configuración de la Página ---
st.set_page_config(page_title="Selector de Opciones", layout="wide")
st.title("🔎 Selector Interactivo de Opciones Financieras")

# --- Funciones Auxiliares ---

# Esta función es rápida y no necesita caché.
def get_ticker_object(ticker_simbolo):
    """Obtiene el objeto Ticker de yfinance."""
    return yf.Ticker(ticker_simbolo)

# La función cacheada ahora devuelve directamente las tablas de datos (DataFrames),
# que sí son compatibles con el sistema de caché.
@st.cache_data(ttl=3600)
def get_option_dataframes(_ticker, fecha):
    """
    Obtiene la cadena de opciones y devuelve los DataFrames de calls y puts.
    Esta es la operación lenta que se beneficia de la caché.
    """
    chain = _ticker.option_chain(fecha)
    return chain.calls, chain.puts

# NUEVA FUNCIÓN: Cachea el historial de un contrato de opción específico.
@st.cache_data(ttl=3600)
def get_option_history(contract_symbol):
    """
    Obtiene el historial de precios del último mes para un contrato de opción.
    """
    try:
        option_ticker = yf.Ticker(contract_symbol)
        return option_ticker.history(period="1mo")
    except Exception:
        return pd.DataFrame() # Devuelve un DataFrame vacío si hay un error

# --- Interfaz de Usuario ---

# 1. ENTRADA DEL TICKER
ticker_simbolo = st.text_input("Introduce el ticker de la acción (ej. AAPL, MSFT, GOOGL):", "AAPL").upper()

if ticker_simbolo:
    accion = get_ticker_object(ticker_simbolo)
    
    # Comprobar si el ticker es válido
    try:
        precio_actual = accion.history(period="1d")['Close'].iloc[-1]
    except IndexError:
        st.error(f"El ticker '{ticker_simbolo}' no es válido o no se encontraron datos.")
        st.stop() # Detiene la ejecución si el ticker no es válido

    st.success(f"El precio de cierre más reciente de **{ticker_simbolo}** es: **${precio_actual:.2f}**")

    # Columnas para organizar las selecciones
    col1, col2, col3 = st.columns(3)

    # 2. SELECCIÓN DEL PRECIO STRIKE
    with col1:
        st.subheader("1. Elige el Strike")
        strike_central = st.number_input("Introduce un strike de referencia:", value=round(precio_actual, -1), step=1.0)
        
        strikes_disponibles = [round(strike_central + (i - 10) * 0.5, 2) for i in range(21)]
        strike_elegido = st.selectbox("Selecciona un precio strike:", strikes_disponibles, index=10)

    # 3. SELECCIÓN DE LA FECHA DE VENCIMIENTO
    with col2:
        st.subheader("2. Elige el Vencimiento")
        todas_las_fechas = accion.options
        if not todas_las_fechas:
            st.warning(f"No se encontraron opciones para {ticker_simbolo}.")
            fecha_elegida = None
        else:
            fechas_a_mostrar = list(todas_las_fechas[:10])
            if len(todas_las_fechas) > 10:
                fechas_lejanas = todas_las_fechas[10:]
                paso = max(1, len(fechas_lejanas) // 10)
                for i in range(0, len(fechas_lejanas), paso):
                    if len(fechas_a_mostrar) < 20:
                        fechas_a_mostrar.append(fechas_lejanas[i])
            
            fecha_elegida = st.selectbox("Selecciona una fecha de vencimiento:", fechas_a_mostrar)
    
    # 4. SELECCIÓN DEL TIPO DE OPCIÓN
    with col3:
        st.subheader("3. Elige el Tipo")
        tipo_opcion_elegido = st.selectbox("Selecciona el tipo de opción:", ["Call", "Put"])

    # 5. BOTÓN PARA BUSCAR Y MOSTRAR RESULTADOS
    if st.button("📊 Buscar Opción", use_container_width=True) and fecha_elegida:
        st.info(f"Buscando opción **{tipo_opcion_elegido}** para **{ticker_simbolo}** con vencimiento el **{fecha_elegida}** y strike **${strike_elegido}**...")

        try:
            # La función ahora devuelve dos DataFrames: calls y puts
            calls, puts = get_option_dataframes(accion, fecha_elegida)
            
            datos = calls if tipo_opcion_elegido == "Call" else puts
            
            opcion_seleccionada = datos[datos['strike'] == strike_elegido]

            if opcion_seleccionada.empty:
                st.warning("No se encontró una opción que coincida exactamente con los criterios seleccionados.")
            else:
                st.success("¡Opción Encontrada!")
                st.dataframe(opcion_seleccionada)
                
                st.subheader("Métricas Clave")
                col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
                col_metric1.metric("Último Precio", f"${opcion_seleccionada['lastPrice'].iloc[0]:.2f}")
                col_metric2.metric("Bid", f"${opcion_seleccionada['bid'].iloc[0]:.2f}")
                col_metric3.metric("Ask", f"${opcion_seleccionada['ask'].iloc[0]:.2f}")
                col_metric4.metric("Volatilidad Implícita", f"{opcion_seleccionada['impliedVolatility'].iloc[0]:.2%}")

                # --- NUEVA SECCIÓN: GRÁFICO HISTÓRICO ---
                st.subheader("📈 Historial de Precio (Último Mes)")
                
                # Obtenemos el símbolo único del contrato de opción
                contract_symbol = opcion_seleccionada['contractSymbol'].iloc[0]
                
                # Llamamos a la nueva función para obtener el historial
                history_df = get_option_history(contract_symbol)

                if not history_df.empty:
                    # Mostramos el gráfico de línea con el precio de cierre
                    st.line_chart(history_df['Close'])
                else:
                    st.warning("No se encontraron datos históricos para este contrato de opción.")


        except Exception as e:
            st.error(f"Ocurrió un error al obtener los datos de la opción: {e}")

st.markdown("---")
st.write("Aplicación desarrollada como parte del TFM.")
