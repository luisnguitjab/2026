import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests

# === CONFIGURACIÓN CLAVE PARA MATPLOTLIB EN LA WEB ===
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CONFIGURACIÓN DE COORDENADAS (MENDOZA)
# ==========================================
FINCAS_MENDOZA = {
    'Gualtallary (Tupungato)': {'lat': -33.38, 'lon': -69.18, 'cultivo': 'Malbec (Brotación)', 'umbral': -1.5},
    'Vista Flores (San Carlos)': {'lat': -33.65, 'lon': -69.15, 'cultivo': 'Chardonnay (Hojas)', 'umbral': -1.0},
    'Agrelo (Luján de Cuyo)': {'lat': -33.11, 'lon': -68.89, 'cultivo': 'Cabernet Sauv. (Yema)', 'umbral': -3.0},
    'Perdriel (Maipú)': {'lat': -33.07, 'lon': -68.88, 'cultivo': 'Malbec (Brotación)', 'umbral': -1.8},
    'Costa de Araujo (Lavalle)': {'lat': -32.74, 'lon': -68.32, 'cultivo': 'Uva de Mesa (Yema)', 'umbral': -2.5},
    'Alto Verde (San Martín)': {'lat': -33.08, 'lon': -68.46, 'cultivo': 'Bonarda (Brotación)', 'umbral': -1.5},
    'Las Catitas (Santa Rosa)': {'lat': -33.27, 'lon': -68.04, 'cultivo': 'Criolla (Hojas)', 'umbral': -1.2},
    'Rama Caída (San Rafael)': {'lat': -34.69, 'lon': -68.38, 'cultivo': 'Ciruelo (Floración)', 'umbral': -2.2},
    'Ciudad (General Alvear)': {'lat': -34.96, 'lon': -67.69, 'cultivo': 'Durazno (Floración)', 'umbral': -2.5}
}

# ==========================================
# 2. FUNCIÓN PARA CONSUMIR OPEN-METEO API
# ==========================================
def obtener_datos_clima(lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", "cloud_cover",
            "wind_speed_10m", "wind_direction_10m", "soil_temperature_0cm",
            "soil_moisture_0_to_1cm", "et0_fao_evapotranspiration"
        ],
        "timezone": "America/Argentina/Mendoza",
        "forecast_days": 3 
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Error en API Open-Meteo. Código: {response.status_code}")
        
    data = response.json()
    hourly_data = data['hourly']
    
    df = pd.DataFrame({
        'fecha_hora': pd.to_datetime(hourly_data['time']),
        'temp_aire': hourly_data['temperature_2m'],
        'humedad': hourly_data['relative_humidity_2m'],
        'punto_rocio': hourly_data['dew_point_2m'],
        'nubosidad': hourly_data['cloud_cover'],
        'vel_viento': hourly_data['wind_speed_10m'],
        'dir_viento': hourly_data['wind_direction_10m'],
        'temp_suelo': hourly_data['soil_temperature_0cm'],
        'hum_suelo': hourly_data['soil_moisture_0_to_1cm'],
        'evapotranspiracion': hourly_data['et0_fao_evapotranspiration']
    })
    return df

# ==========================================
# 3. DISEÑO DE LA INTERFAZ (ALTO CONTRASTE)
# ==========================================
app = dash.Dash(__name__)
server = app.server
app.config.suppress_callback_exceptions = True

app.layout = html.Div(style={'backgroundColor': '#cbd5e1', 'fontFamily': 'sans-serif', 'padding': '15px'}, children=[
    
    html.Div(style={'textAlign': 'center', 'marginBottom': '25px', 'padding': '10px'}, children=[
        html.H1("Monitor y DSS de Riesgo de Heladas - Mendoza", 
                style={'color': '#0f172a', 'fontWeight': '900', 'fontSize': 'calc(18px + 1.5vw)', 'margin': '0 0 10px 0'}),
        html.P("Predicción, inversión térmica e indicadores de defensa activa en fincas (Open-Meteo)", 
                style={'color': '#1e293b', 'fontWeight': 'bold', 'fontSize': 'calc(12px + 0.3vw)'})
    ]),
    
    html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'marginBottom': '20px'}, children=[
        
        html.Div(style={
            'flex': '1 1 250px', 'backgroundColor': 'white', 'padding': '20px', 
            'borderRadius': '8px', 'border': '2px solid #475569', 'boxSizing': 'border-box'
        }, children=[
            html.Label("Seleccione la Finca / Región a Monitorear:", style={'fontWeight': '900', 'color': '#0f172a'}),
            dcc.Dropdown(
                id='dropdown-finca',
                options=[{'label': k, 'value': k} for k in FINCAS_MENDOZA.keys()],
                value='Gualtallary (Tupungato)', 
                clearable=False,
                style={'marginTop': '10px', 'color': '#0f172a', 'fontWeight': 'bold'}
            )
        ]),
        
        html.Div(id='kpi-temperatura', style={'flex': '1 1 200px', 'boxSizing': 'border-box'}),
        html.Div(id='kpi-riesgo', style={'flex': '1 1 200px', 'boxSizing': 'border-box'}),
        html.Div(id='kpi-viento-horas', style={'flex': '1 1 200px', 'boxSizing': 'border-box'}),
        html.Div(id='kpi-suelo-et0', style={'flex': '1 1 200px', 'boxSizing': 'border-box'})
    ]),
    
    html.Div(style={'display': 'flex', 'flexDirection': 'column', 'gap': '20px'}, children=[
        
        html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'overflow': 'hidden'}, children=[
            dcc.Graph(id='grafico-curva-enfriamiento', config={'displayModeBar': False, 'displaylogo': False})
        ]),
        
        html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'overflow': 'hidden'}, children=[
            dcc.Graph(id='grafico-viento-et0', config={'displayModeBar': False, 'displaylogo': False})
        ]),
        
        html.Div(style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '20px'}, children=[
            html.Div(style={'flex': '1 1 400px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'overflow': 'hidden'}, children=[
                dcc.Graph(id='grafico-distribucion-nubes', config={'displayModeBar': False, 'displaylogo': False})
            ]),
            html.Div(style={'flex': '1 1 400px', 'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'overflow': 'hidden'}, children=[
                dcc.Graph(id='grafico-matriz-correlacion', config={'displayModeBar': False, 'displaylogo': False})
            ])
        ])
    ])
])

# ==========================================
# 4. LÓGICA DE PROCESAMIENTO Y CALLBACKS
# ==========================================
@app.callback(
    [Output('kpi-temperatura', 'children'),
     Output('kpi-riesgo', 'children'),
     Output('kpi-viento-horas', 'children'),
     Output('kpi-suelo-et0', 'children'),
     Output('grafico-curva-enfriamiento', 'figure'),
     Output('grafico-viento-et0', 'figure'),
     Output('grafico-distribucion-nubes', 'figure'),
     Output('grafico-matriz-correlacion', 'figure')],
    [Input('dropdown-finca', 'value')]
)
def actualizar_dashboard(nombre_finca):
    try:
        finca = FINCAS_MENDOZA[nombre_finca]
        umbral = finca['umbral']
        cultivo = finca['cultivo']
        
        df = obtener_datos_clima(finca['lat'], finca['lon'])
        if df.empty:
            raise ValueError("La API no retornó registros.")

        df['riesgo_helada'] = np.select(
            [
                (df['temp_aire'] <= umbral),
                (df['temp_aire'] <= (umbral + 2.0)) & (df['nubosidad'] < 25),
            ],
            ['CRÍTICO', 'ALTO'],
            default='BAJO'
        )
        
        horas_bajo_umbral = len(df[df['temp_aire'] <= umbral])
        
        temp_actual = df['temp_aire'].iloc[0]
        nubosidad_actual = df['nubosidad'].iloc[0]
        riesgo_actual = df['riesgo_helada'].iloc[0]
        vel_viento_actual = df['vel_viento'].iloc[0]
        hum_suelo_actual = df['hum_suelo'].iloc[0]
        et0_actual = df['evapotranspiracion'].iloc[0]
        
        status_viento = "APTO" if vel_viento_actual <= 10 else "EXCESIVO"
        color_viento_texto = "#166534" if vel_viento_actual <= 10 else "#991b1b"
        
        color_card_riesgo = '#991b1b' if riesgo_actual == 'CRÍTICO' else ('#c2410c' if riesgo_actual == 'ALTO' else '#065f46')
        
        card_temp = html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Cultivo Monitoreado", style={'margin': '0', 'color': '#334155', 'fontSize': '13px', 'fontWeight': 'bold'}),
            html.H4(cultivo, style={'color': '#0f172a', 'margin': '4px 0', 'fontSize': '15px', 'fontWeight': '900'}),
            html.H2(f"{temp_actual} °C", style={'color': '#1e3a8a', 'fontSize': '28px', 'margin': '4px 0', 'fontWeight': '900'})
        ])
        
        card_riesgo = html.Div(style={'backgroundColor': color_card_riesgo, 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Riesgo de Helada", style={'margin': '0', 'color': 'white', 'opacity': '0.9', 'fontSize': '13px', 'fontWeight': 'bold'}),
            html.H2(riesgo_actual, style={'color': 'white', 'fontSize': '28px', 'fontWeight': '900', 'margin': '6px 0'}),
            html.P(f"Umbral de Daño: {umbral} °C", style={'color': 'white', 'margin': '0', 'fontSize': '13px', 'fontWeight': 'bold'})
        ])
        
        card_viento = html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Defensa Activa", style={'margin': '0', 'color': '#334155', 'fontSize': '13px', 'fontWeight': 'bold'}),
            html.H4(f"Viento: {vel_viento_actual} km/h ({status_viento})", style={'color': color_viento_texto, 'margin': '6px 0', 'fontSize': '14px', 'fontWeight': '900'}),
            html.P(f"Proyección Crítica: {horas_bajo_umbral} hs", style={'color': '#0f172a', 'fontWeight': '900', 'margin': '0', 'fontSize': '13px'})
        ])
        
        card_suelo = html.Div(style={'backgroundColor': 'white', 'padding': '15px', 'borderRadius': '8px', 'border': '2px solid #475569', 'textAlign': 'center', 'height': '100%'}, children=[
            html.H3("Suelo y Demanda", style={'margin': '0', 'color': '#334155', 'fontSize': '13px', 'fontWeight': 'bold'}),
            html.H4(f"Humedad Suelo: {int(hum_suelo_actual*100)}%", style={'color': '#1d4ed8', 'margin': '4px 0', 'fontSize': '15px', 'fontWeight': '900'}),
            html.P(f"Evapotranspiración: {et0_actual} mm/h", style={'color': '#0f172a', 'margin': '0', 'fontSize': '13px', 'fontWeight': 'bold'})
        ])
        
        # --- CONFIGURACIÓN DE GRILLAS NÍTIDAS ---
        grid_style = dict(showgrid=True, gridcolor='#94a3b8', zerolinecolor='#475569', tickfont=dict(color='#0f172a', size=11))
        
        # GRÁFICO 1: Curva Térmica
        fig_curva = go.Figure()
        fig_curva.add_trace(go.Scatter(x=df['fecha_hora'], y=df['temp_aire'], name='Temp. Aire (2m)', line=dict(color='#1d4ed8', width=3.5)))
        fig_curva.add_trace(go.Scatter(x=df['fecha_hora'], y=df['punto_rocio'], name='Punto de Rocío', line=dict(color='#6b21a8', dash='dash', width=2.5)))
        fig_curva.add_trace(go.Scatter(x=df['fecha_hora'], y=df['temp_suelo'], name='Temp. Suelo', line=dict(color='#b45309', width=2.5)))
        fig_curva.add_trace(go.Scatter(x=[df['fecha_hora'].min(), df['fecha_hora'].max()], y=[umbral, umbral], name='Umbral Crítico', mode='lines', line=dict(color='#b91c1c', width=3, dash='dot')))
        
        # CORRECCIÓN: Usando la estructura correcta de fuente para los títulos (title=dict(text="...", font=dict(...)))
        fig_curva.update_layout(
            title=dict(text="Dinámica de Enfrimiento (Aire vs Suelo)", font=dict(color='#0f172a', size=16, weight='bold')),
            xaxis=dict(title=dict(text="Fecha y Hora", font=dict(color='#0f172a')), **grid_style),
            yaxis=dict(title=dict(text="Temperatura (°C)", font=dict(color='#0f172a')), **grid_style),
            template="plotly_white", hovermode="x unified", margin=dict(l=45, r=15, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#0f172a', size=11))
        )
        
        # GRÁFICO 2: Viento y ET0
        fig_viento = go.Figure()
        fig_viento.add_trace(go.Scatter(x=df['fecha_hora'], y=df['vel_viento'], name='Vel. Viento (km/h)', line=dict(color='#b91c1c', width=2.5)))
        fig_viento.add_trace(go.Scatter(x=df['fecha_hora'], y=df['evapotranspiracion'], name='ET0 (mm/h)', yaxis="y2", line=dict(color='#047857', width=2.5, dash='dot')))
        
        fig_viento.update_layout(
            title=dict(text="Análisis de Viento y Evapotranspiración", font=dict(color='#0f172a', size=16, weight='bold')),
            xaxis=dict(title=dict(text="Fecha y Hora", font=dict(color='#0f172a')), **grid_style),
            yaxis=dict(title=dict(text="Velocidad Viento (km/h)", font=dict(color='#0f172a')), **grid_style),
            yaxis2=dict(title=dict(text="Evapotranspiración ET0 (mm/h)", font=dict(color='#0f172a')), overlaying="y", side="right", showgrid=False, tickfont=dict(color='#0f172a')),
            template="plotly_white", hovermode="x unified", margin=dict(l=45, r=45, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#0f172a', size=11))
        )
        
        # GRÁFICO 3: Nubosidad
        fig_nubes = px.bar(df, x='fecha_hora', y='nubosidad', title='Porcentaje de Nubosidad Estimada', color='nubosidad', color_continuous_scale='Blues')
        fig_nubes.update_layout(
            title=dict(font=dict(color='#0f172a', size=16, weight='bold')),
            xaxis=dict(title=dict(text="Fecha y Hora", font=dict(color='#0f172a')), **grid_style),
            yaxis=dict(title=dict(text="% Cobertura Nubosa", font=dict(color='#0f172a')), **grid_style),
            template="plotly_white", margin=dict(l=45, r=15, t=50, b=40), coloraxis_showscale=True
        )

        # GRÁFICO 4: Matriz de Correlación
        columnas_interes = ['temp_aire', 'punto_rocio', 'vel_viento', 'temp_suelo', 'evapotranspiracion', 'nubosidad']
        df_corr = df[columnas_interes].corr()
        df_corr.columns = ['Temp. Aire', 'Pto Rocío', 'Vel. Viento', 'Temp. Suelo', 'ET0', 'Nubosidad']
        df_corr.index = df_corr.columns
        
        fig_corr = px.imshow(
            df_corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", 
            title="Matriz de Correlación (Diagnóstico Físico)", labels=dict(color="Coeficiente")
        )
        fig_corr.update_layout(
            title=dict(font=dict(color='#0f172a', size=16, weight='bold')),
            margin=dict(l=45, r=15, t=50, b=40),
            xaxis=dict(tickfont=dict(color='#0f172a', size=11, weight='bold')),
            yaxis=dict(tickfont=dict(color='#0f172a', size=11, weight='bold'))
        )

        return card_temp, card_riesgo, card_viento, card_suelo, fig_curva, fig_viento, fig_nubes, fig_corr

    except Exception as e:
        print(f"\n[!!!] ERROR EN EL CALLBACK: {e}\n")
        error_card = html.Div(children=[html.H3("Error", style={'color':'#991b1b'}), html.P(str(e), style={'color': '#0f172a'})])
        fig_vacia = go.Figure().update_layout(title="Datos no disponibles")
        return error_card, error_card, error_card, error_card, fig_vacia, fig_vacia, fig_vacia, fig_vacia

# ==========================================
# 5. INICIALIZACIÓN (MODO LIMPIO)
# ==========================================
if __name__ == '__main__':
    app.run(debug=False, port=8050)