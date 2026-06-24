import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import os

# === CORRECCIÓN CLAVE PARA MATPLOTLIB EN LA WEB ===
import matplotlib
matplotlib.use('Agg')  # Fuerza a matplotlib a renderizar en segundo plano
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CONFIGURACIÓN DE COORDENADAS (MENDOZA)
# ==========================================
FINCAS_MENDOZA = {
    'Gualtallary (Tupungato)': {'lat': -33.38, 'lon': -69.18, 'cultivo': 'Malbec (Brotación)', 'umbral': -1.5},
    'Vista Flores (San Carlos)': {'lat': -33.65, 'lon': -69.15, 'cultivo': 'Chardonnay (Hojas Desplegadas)', 'umbral': -1.0},
    'Agrelo (Luján de Cuyo)': {'lat': -33.11, 'lon': -68.89, 'cultivo': 'Cabernet Sauv. (Yema Hinchada)', 'umbral': -3.0},
    'Rama Caída (San Rafael)': {'lat': -34.69, 'lon': -68.38, 'cultivo': 'Ciruelo (Floración)', 'umbral': -2.2}
}

# ==========================================
# 2. FUNCIÓN PARA CONSUMIR OPEN-METEO API
# ==========================================
def obtener_datos_clima(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "cloud_cover"],
        "timezone": "America/Argentina/Mendoza",
        "forecast_days": 3 # Ventana crítica de 72 horas
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception("Error al conectar con la API de Open-Meteo")
        
    data = response.json()
    hourly_data = data['hourly']
    
    df = pd.DataFrame({
        'fecha_hora': pd.to_datetime(hourly_data['time']),
        'temp_aire': hourly_data['temperature_2m'],
        'humedad': hourly_data['relative_humidity_2m'],
        'punto_rocio': hourly_data['dew_point_2m'],
        'nubosidad': hourly_data['cloud_cover']
    })
    return df

# ==========================================
# 3. DISEÑO DE LA INTERFAZ CON DASH (UI)
# ==========================================
app = dash.Dash(__name__)

app.layout = html.Div(style={'backgroundColor': '#f4f6f9', 'fontFamily': 'sans-serif', 'padding': '20px'}, children=[
    html.Div(style={'textAlign': 'center', 'marginBottom': '30px'}, children=[
        html.H1("Monitor de Riesgo de Heladas - Mendoza", style={'color': '#1a365d', 'fontWeight': 'bold'}),
        html.P("Predicción e inversión térmica basada en telemetría satelital y modelos numéricos (Open-Meteo)", style={'color': '#4a5568'})
    ]),
    
    html.Div(style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}, children=[
        html.Div(style={'flex': '1', 'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            html.Label("Seleccione la Finca / Región a Monitorear:", style={'fontWeight': 'bold', 'color': '#2d3748'}),
            dcc.Dropdown(
                id='dropdown-finca',
                options=[{'label': k, 'value': k} for k in FINCAS_MENDOZA.keys()],
                value='Gualtallary (Tupungato)', 
                clearable=False,
                style={'marginTop': '10px'}
            )
        ]),
        html.Div(id='kpi-temperatura', style={'flex': '1'}),
        html.Div(id='kpi-riesgo', style={'flex': '1'})
    ]),
    
    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}, children=[
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='grafico-curva-enfriamiento')
        ]),
        html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}, children=[
            dcc.Graph(id='grafico-distribucion-nubes')
        ])
    ])
])

# ==========================================
# 4. LÓGICA DE DETECCIÓN Y GRÁFICOS (CALLBACKS)
# ==========================================
@app.callback(
    [Output('kpi-temperatura', 'children'),
     Output('kpi-riesgo', 'children'),
     Output('grafico-curva-enfriamiento', 'figure'),
     Output('grafico-distribucion-nubes', 'figure')],
    [Input('dropdown-finca', 'value')]
)
def actualizar_dashboard(nombre_finca):
    try:
        finca = FINCAS_MENDOZA[nombre_finca]
        umbral = finca['umbral']
        cultivo = finca['cultivo']
        
        df = obtener_datos_clima(finca['lat'], finca['lon'])
        
        if df.empty:
            raise ValueError("La API de Open-Meteo no devolvió datos.")

        df['riesgo_helada'] = np.select(
            [
                (df['temp_aire'] <= umbral),
                (df['temp_aire'] <= (umbral + 2.0)) & (df['nubosidad'] < 25),
            ],
            ['CRÍTICO', 'ALTO'],
            default='BAJO'
        )
        
        temp_actual = df['temp_aire'].iloc[0]
        nubosidad_actual = df['nubosidad'].iloc[0]
        riesgo_actual = df['riesgo_helada'].iloc[0]
        
        color_alerta = '#e53e3e' if riesgo_actual == 'CRÍTICO' else ('#dd6b20' if riesgo_actual == 'ALTO' else '#319795')
        
        card_temp = html.Div(style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Estado del Cultivo", style={'margin': '0', 'color': '#718096', 'fontSize': '14px'}),
            html.H4(cultivo, style={'color': '#2d3748', 'margin': '5px 0'}),
            html.H2(f"{temp_actual} °C", style={'color': '#1a365d', 'fontSize': '32px', 'margin': '5px 0'})
        ])
        
        card_riesgo = html.Div(style={'backgroundColor': color_alerta, 'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Nivel de Riesgo Actual", style={'margin': '0', 'color': 'white', 'opacity': '0.9', 'fontSize': '14px'}),
            html.H2(riesgo_actual, style={'color': 'white', 'fontSize': '36px', 'fontWeight': 'bold', 'margin': '10px 0'}),
            html.P(f"Umbral de daño: {umbral} °C | Nubosidad: {nubosidad_actual}%", style={'color': 'white', 'margin': '0', 'fontSize': '12px'})
        ])
        
        fig_curva = go.Figure()
        fig_curva.add_trace(go.Scatter(x=df['fecha_hora'], y=df['temp_aire'], name='Temp. Aire (2m)', line=dict(color='#3182ce', width=3)))
        fig_curva.add_trace(go.Scatter(x=df['fecha_hora'], y=df['punto_rocio'], name='Punto de Rocío', line=dict(color='#805ad5', dash='dash')))
        fig_curva.add_shape(type="line", x0=df['fecha_hora'].min(), y0=umbral, x1=df['fecha_hora'].max(), y1=umbral, line=dict(color="Red", width=2, dash="dot"))
        fig_curva.update_layout(title="Evolución Térmica Proyectada - Próximas 72 Horas", xaxis_title="Fecha y Hora", yaxis_title="Temperatura (°C)", template="plotly_white", hovermode="x unified")
        
        fig_nubes = px.bar(df, x='fecha_hora', y='nubosidad', title='Porcentaje de Nubosidad Estimada (Radiación Nocturna)', color='nubosidad', color_continuous_scale='Blues_r')
        fig_nubes.update_layout(template="plotly_white", yaxis_title="% Cobertura Nubosa")

        # Bloque Matplotlib (Protegido para que no rompa la app)
        try:
            if not os.path.exists('assets'):
                os.makedirs('assets')
            plt.figure(figsize=(4, 3))
            sns.heatmap(df[['temp_aire', 'humedad', 'punto_rocio', 'nubosidad']].corr(), annot=True, cmap='coolwarm', fmt=".2f")
            plt.title("Matriz de Correlación")
            plt.tight_layout()
            plt.savefig('assets/correlacion_reporte.png', dpi=100)
            plt.close()
        except Exception as e_mat:
            print(f"Advertencia (Matplotlib): {e_mat}")

        return card_temp, card_riesgo, fig_curva, fig_nubes

    except Exception as e:
        print(f"\n[!!!] ERROR CRÍTICO EN EL CALLBACK: {e}\n")
        error_card = html.Div(children=[html.H3("Error de Conexión", style={'color':'red'}), html.P(str(e))])
        fig_vacia = go.Figure().update_layout(title="Datos no disponibles")
        return error_card, error_card, fig_vacia, fig_vacia

# ==========================================
# 5. INICIALIZACIÓN DEL SERVIDOR LOCAL
# ==========================================
if __name__ == '__main__':
    if not os.path.exists('assets'):
        os.makedirs('assets') 
        
    # Usando app.run() compatible con versiones Dash 3.0+ para entorno local
    app.run(debug=True, port=8050)
