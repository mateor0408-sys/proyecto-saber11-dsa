"""Tablero «Monitor de Riesgo Académico Saber 11».

Pestañas (según la maqueta de la Entrega 1):
  1. Diagnóstico territorial: dónde y en quién se concentra el riesgo.
  2. Predicción de riesgo: probabilidad, puntaje estimado y factores para un perfil de estudiante.
  3. Priorización por lotes: predicción para un CSV de estudiantes y descarga de la lista priorizada.

Uso: python dashboard/app.py   (http://localhost:8050)
El modelo se carga desde models/ (exportado de MLflow con src/select_best.py).
"""
import base64
import io
import json
import sys
from functools import lru_cache
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import FEATURE_SETS, MISSING, NUMERIC, prepare_X  # noqa: E402

DATA = ROOT / "data" / "processed" / "saber11_clean.parquet"
MODELS = ROOT / "models"
FEATURES = FEATURE_SETS["todas"]

BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#8a8984", "#e4e3df"
NATIONAL_RISK = 25.0
FONT = '-apple-system, "Segoe UI", Roboto, sans-serif'

LABELS = {
    "fami_educacionmadre": "Educación de la madre", "fami_educacionpadre": "Educación del padre",
    "fami_estratovivienda": "Estrato de la vivienda", "fami_tieneinternet": "Internet en casa",
    "fami_tienecomputador": "Computador en casa", "fami_tieneautomovil": "Automóvil en el hogar",
    "fami_tienelavadora": "Lavadora en el hogar", "fami_personashogar": "Personas en el hogar",
    "fami_cuartoshogar": "Cuartos en el hogar", "cole_naturaleza": "Naturaleza del colegio",
    "cole_area_ubicacion": "Zona del colegio", "cole_jornada": "Jornada", "cole_calendario": "Calendario",
    "cole_bilingue": "Colegio bilingüe", "cole_caracter": "Carácter del colegio",
    "cole_genero": "Género del colegio", "cole_depto_ubicacion": "Departamento del colegio",
    "estu_genero": "Género del estudiante", "edad": "Edad",
}
ORDERS = {
    "fami_estratovivienda": ["Sin estrato", "Estrato 1", "Estrato 2", "Estrato 3", "Estrato 4", "Estrato 5", "Estrato 6"],
    "fami_educacionmadre": ["Ninguno", "Primaria incompleta", "Primaria completa",
                            "Secundaria (Bachillerato) incompleta", "Secundaria (Bachillerato) completa",
                            "Técnica o tecnológica incompleta", "Técnica o tecnológica completa",
                            "Educación profesional incompleta", "Educación profesional completa", "Postgrado",
                            "No sabe", "No Aplica"],
    "fami_personashogar": ["1 a 2", "3 a 4", "5 a 6", "7 a 8", "9 o más"],
    "fami_cuartoshogar": ["Uno", "Dos", "Tres", "Cuatro", "Cinco", "Seis o mas"],
    "cole_jornada": ["COMPLETA", "UNICA", "MAÑANA", "TARDE", "SABATINA", "NOCHE"],
}
ORDERS["fami_educacionpadre"] = ORDERS["fami_educacionmadre"]
FACTOR_OPTIONS = ["fami_educacionmadre", "fami_estratovivienda", "fami_tieneinternet", "fami_tienecomputador",
                  "cole_jornada", "cole_naturaleza", "cole_area_ubicacion", "fami_personashogar"]
ADVICE = {
    "fami_tieneinternet": "acompañamiento de conectividad", "fami_tienecomputador": "acceso a equipos de cómputo",
    "fami_educacionmadre": "acompañamiento familiar", "fami_educacionpadre": "acompañamiento familiar",
    "cole_jornada": "refuerzo extracurricular según la jornada", "cole_area_ubicacion": "programas para zona rural",
    "cole_depto_ubicacion": "programas territoriales del departamento",
}
DEFAULT_PROFILE = {
    "cole_depto_ubicacion": "LA GUAJIRA", "cole_naturaleza": "OFICIAL", "cole_area_ubicacion": "RURAL",
    "cole_jornada": "MAÑANA", "cole_calendario": "A", "cole_bilingue": "N", "cole_caracter": "ACADÉMICO",
    "cole_genero": "MIXTO", "fami_educacionmadre": "Primaria incompleta", "fami_educacionpadre": "Primaria completa",
    "fami_estratovivienda": "Estrato 1", "fami_personashogar": "5 a 6", "fami_cuartoshogar": "Dos",
    "fami_tieneinternet": "No", "fami_tienecomputador": "No", "fami_tieneautomovil": "No",
    "fami_tienelavadora": "No", "estu_genero": "F", "edad": 17,
}


# ----------------------------------------------------------------------------- datos y modelos
def load_data():
    cols = ["cole_mcpio_ubicacion", "cole_cod_dane_establecimiento", "cole_nombre_establecimiento",
            "punt_global", "riesgo_bajo_desempeno"]
    df = pd.read_parquet(DATA, columns=list(dict.fromkeys(FEATURES + cols)))
    X = prepare_X(df, FEATURES)
    for c in X.columns:
        df[c] = X[c].astype("category") if c not in NUMERIC else X[c]
    return df


DF = load_data()
CLF = mlflow.sklearn.load_model(str(MODELS / "riesgo"))
REG = mlflow.sklearn.load_model(str(MODELS / "puntaje"))
SELECTION = json.loads((MODELS / "seleccion.json").read_text())
THRESHOLD = SELECTION["riesgo"]["metricas"]["umbral"]
REFERENCE = {c: (DF[c].median() if c in NUMERIC else DF[c].mode()[0]) for c in FEATURES}


def options_for(col):
    values = [v for v in DF[col].cat.categories if v != MISSING]
    order = ORDERS.get(col)
    values = sorted(values, key=lambda v: order.index(v) if order and v in order else len(order or []) + 0) \
        if order else sorted(values)
    return [{"label": v.title() if col.endswith("ubicacion") and col != "cole_area_ubicacion" else v, "value": v}
            for v in values]


def risk_level(p):
    if p >= 0.5:
        return "alto"
    return "medio" if p >= THRESHOLD else "bajo"


def predict_frame(X: pd.DataFrame) -> pd.DataFrame:
    X = prepare_X(X, FEATURES)
    proba = CLF.predict_proba(X)[:, 1]
    return pd.DataFrame({"prob_riesgo": proba.round(3), "nivel": [risk_level(p) for p in proba],
                         "puntaje_estimado": REG.predict(X).round(0).astype(int)})


def contributions(profile: dict) -> pd.Series:
    """Oclusión: cambio de la probabilidad al llevar cada variable a su valor de referencia (moda)."""
    base = pd.DataFrame([profile])
    rows = [base]
    for c in FEATURES:
        alt = base.copy()
        alt[c] = REFERENCE[c]
        rows.append(alt)
    proba = CLF.predict_proba(prepare_X(pd.concat(rows, ignore_index=True), FEATURES))[:, 1]
    return pd.Series(proba[0] - proba[1:], index=FEATURES)


# ----------------------------------------------------------------------------- utilidades de UI
def fmt(x, dec=0):
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def base_layout(fig, height=320, **kw):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=30), paper_bgcolor="white",
                      plot_bgcolor="white", font=dict(size=11, color=INK, family=FONT), showlegend=False, **kw)
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def risk_bars(tbl, label_col, height=None):
    tbl = tbl.iloc[::-1]
    fig = go.Figure(go.Bar(
        x=tbl.tasa, y=tbl[label_col], orientation="h", marker_color=ORANGE, marker_cornerradius=3,
        text=[f"{t:.0f} %" for t in tbl.tasa], textposition="outside", cliponaxis=False,
        customdata=np.stack([tbl.n, tbl.punt], axis=-1),
        hovertemplate="<b>%{y}</b><br>Riesgo: %{x:.1f} %<br>Evaluados: %{customdata[0]:,}"
                      "<br>Puntaje medio: %{customdata[1]:.0f}<extra></extra>"))
    fig.add_vline(x=NATIONAL_RISK, line_dash="dash", line_color=INK, line_width=1)
    base_layout(fig, height or max(260, 22 * len(tbl) + 40))
    fig.update_xaxes(title_text="% de estudiantes en riesgo (puntaje global < 210)", range=[0, max(tbl.tasa.max() * 1.18, 30)])
    return fig


def agg(frame, by):
    g = frame.groupby(by, observed=True).agg(n=("punt_global", "size"), punt=("punt_global", "mean"),
                                             tasa=("riesgo_bajo_desempeno", "mean")).reset_index()
    g["tasa"] *= 100
    return g


def filtered(depto, mpio, nat, zona, jornada):
    m = pd.Series(True, index=DF.index)
    for col, val in (("cole_depto_ubicacion", depto), ("cole_mcpio_ubicacion", mpio), ("cole_naturaleza", nat),
                     ("cole_area_ubicacion", zona), ("cole_jornada", jornada)):
        if val:
            m &= DF[col] == val
    return DF[m]


def kpi(label, value, detail, alert=False):
    return html.Div([html.Div(label, className="l"), html.Div(value, className="v alert" if alert else "v"),
                     html.Div(detail, className="d")], className="card kpi")


def dropdown(id_, col, placeholder="Todos", **kw):
    return dcc.Dropdown(id=id_, options=options_for(col), placeholder=placeholder, **kw)


# ----------------------------------------------------------------------------- layout
app = Dash(__name__, title="Monitor Saber 11")
server = app.server

tab_diag = html.Div([
    html.Div([
        html.Div([html.Label("Departamento"), dropdown("f-depto", "cole_depto_ubicacion")], className="filter"),
        html.Div([html.Label("Municipio"), dcc.Dropdown(id="f-mpio", placeholder="Todos")], className="filter"),
        html.Div([html.Label("Naturaleza"), dropdown("f-nat", "cole_naturaleza")], className="filter"),
        html.Div([html.Label("Zona"), dropdown("f-zona", "cole_area_ubicacion")], className="filter"),
        html.Div([html.Label("Jornada"), dropdown("f-jor", "cole_jornada")], className="filter"),
    ], className="filters"),
    html.Div([
        html.Div(id="kpis", className="kpis"),
        html.Div([
            html.Div([html.H3(id="bar-title"), dcc.Graph(id="bar-territorio", config={"displayModeBar": False}),
                      html.Div("Clic en un departamento para filtrar el tablero. Línea punteada: 25 % nacional.",
                               className="note")], className="card"),
            html.Div([html.H3(["¿Qué factores concentran el riesgo? ", html.Small("· % de estudiantes en riesgo")]),
                      dcc.Dropdown(id="f-factor", value="fami_educacionmadre", clearable=False,
                                   options=[{"label": LABELS[c], "value": c} for c in FACTOR_OPTIONS]),
                      dcc.Graph(id="bar-factor", config={"displayModeBar": False})], className="card"),
        ], className="grid2"),
        html.Div([
            html.Div([html.H3(id="table-title"),
                      dash_table.DataTable(id="tabla-prioridad", page_size=10, sort_action="native",
                                           style_as_list_view=True,
                                           style_header={"fontWeight": "600", "backgroundColor": "#fafaf8"},
                                           style_cell={"fontFamily": FONT, "fontSize": 12, "padding": "6px",
                                                       "textAlign": "left"},
                                           style_data_conditional=[{"if": {"filter_query": "{% riesgo} >= 50",
                                                                           "column_id": "% riesgo"},
                                                                    "color": "#a23c12", "fontWeight": "700"}])],
                     className="card"),
            html.Div([html.H3(["Riesgo por estrato × naturaleza del colegio ", html.Small("· % en riesgo")]),
                      dcc.Graph(id="heatmap", config={"displayModeBar": False})], className="card"),
        ], className="grid2"),
    ], className="body"),
])

form_fields = [c for c in ["cole_depto_ubicacion", "cole_naturaleza", "cole_area_ubicacion", "cole_jornada",
                           "fami_educacionmadre", "fami_educacionpadre", "fami_estratovivienda",
                           "fami_personashogar", "fami_tieneinternet", "fami_tienecomputador",
                           "fami_tieneautomovil", "fami_cuartoshogar", "cole_caracter", "estu_genero"]]
pred_help = html.Div([
    html.H3(["Cómo usar esta pestaña ", html.Small("· estimación del riesgo para un perfil de estudiante")]),
    html.Ol([
        html.Li("Elija en «Perfil del estudiante» las características que se conocen antes de la prueba."),
        html.Li(["Pulse ", html.B("Calcular riesgo"), "."]),
        html.Li("Lea la probabilidad, el nivel de riesgo, el puntaje estimado y los factores que más pesan."),
    ]),
    html.Div([
        html.Span([html.Span("BAJO", className="pill bajo"), f"menos de {fmt(THRESHOLD * 100, 1)} %"]),
        html.Span([html.Span("MEDIO", className="pill medio"), f"de {fmt(THRESHOLD * 100, 1)} % a menos de 50 %"]),
        html.Span([html.Span("ALTO", className="pill alto"), "50 % o más"]),
    ], className="help-levels"),
    html.Div("La probabilidad es la de obtener un puntaje global menor a 210. El resultado sirve para priorizar "
             "apoyos de refuerzo; no es un diagnóstico de ningún estudiante.", className="note"),
], className="card help")

tab_pred = html.Div(html.Div([
    pred_help,
    html.Div([
        html.Div([
            html.H3(["Perfil del estudiante ", html.Small("· variables conocidas antes de la prueba")]),
            html.Div([html.Div([html.Label(LABELS[c]), dcc.Dropdown(id=f"p-{c}", options=options_for(c),
                                                                    value=DEFAULT_PROFILE[c], clearable=False)],
                               className="field") for c in form_fields]
                     + [html.Div([html.Label("Edad"), dcc.Input(id="p-edad", type="number", value=17, min=13,
                                                                max=60, style={"width": "100%", "padding": "7px"})],
                                 className="field")], className="form"),
            html.Div(html.Button("Calcular riesgo", id="btn-predict", className="btn"), style={"marginTop": 12}),
        ], className="card"),
        html.Div([html.H3("Resultado del modelo"), dcc.Graph(id="gauge", config={"displayModeBar": False}),
                  html.Div(id="pred-text")], className="card"),
        html.Div([html.H3(["Factores que más pesan en esta predicción ", html.Small("· puntos de probabilidad")]),
                  dcc.Graph(id="contrib", config={"displayModeBar": False}),
                  html.Div("Cambio en la probabilidad de riesgo frente al perfil más común en Colombia "
                           "(naranja: aumenta el riesgo; azul: lo reduce).", className="note")], className="card"),
    ], className="grid3"),
    html.Div(id="model-card", className="card"),
], className="body"))

tab_batch = html.Div(html.Div([
    html.Div([
        html.H3(["Predicción por lotes ", html.Small("· para rectores y secretarías de educación")]),
        dcc.Upload(id="upload", children=html.Div(["Arrastre o ", html.B("seleccione un CSV"),
                                                    " con los estudiantes de grado 11"]), className="upload"),
        html.Div([html.Button("Descargar plantilla CSV", id="btn-template", className="btn secondary"),
                  html.Button("Descargar resultados", id="btn-download", className="btn secondary",
                              style={"marginLeft": 8})], style={"marginTop": 10}),
        html.Div(id="batch-msg", className="note"),
        dcc.Download(id="dl-template"), dcc.Download(id="dl-results"), dcc.Store(id="batch-store"),
    ], className="card"),
    html.Div([html.H3("Estudiantes priorizados (mayor riesgo primero)"),
              dash_table.DataTable(id="batch-table", page_size=15, sort_action="native", style_as_list_view=True,
                                   style_header={"fontWeight": "600", "backgroundColor": "#fafaf8"},
                                   style_cell={"fontFamily": FONT, "fontSize": 12, "padding": "6px",
                                               "textAlign": "left"},
                                   style_data_conditional=[
                                       {"if": {"filter_query": '{nivel} = "alto"'}, "backgroundColor": "#fdf3ee"}])],
             className="card"),
], className="body"))

app.layout = html.Div([
    html.Div([html.H1("Monitor de Riesgo Académico · Saber 11"),
              html.Span("Secretarías de educación · Periodo 20224 · Datos: ICFES / datos.gov.co")], className="header"),
    dcc.Location(id="url"),
    dcc.Tabs(id="tabs", value="diag", children=[
        dcc.Tab(tab_diag, label="1. Diagnóstico territorial", value="diag", className="tab",
                selected_className="tab--selected"),
        dcc.Tab(tab_pred, label="2. Predicción de riesgo", value="pred", className="tab",
                selected_className="tab--selected"),
        dcc.Tab(tab_batch, label="3. Priorización por lotes", value="lotes", className="tab",
                selected_className="tab--selected"),
    ], className="tabs-bar"),
    html.Div("Riesgo = puntaje global por debajo del percentil 25 nacional (210 puntos). "
             f"Modelo: {SELECTION['riesgo']['run_name']} (MLflow, versión {SELECTION['riesgo']['version_registro']}).",
             className="footer"),
], className="app")


# ----------------------------------------------------------------------------- callbacks: diagnóstico
@app.callback(Output("tabs", "value"), Input("url", "search"))
def tab_from_url(search):
    """Permite abrir una pestaña directamente con ?tab=diag|pred|lotes."""
    tab = dict(p.split("=", 1) for p in (search or "").lstrip("?").split("&") if "=" in p).get("tab")
    return tab if tab in ("diag", "pred", "lotes") else "diag"


@app.callback(Output("f-mpio", "options"), Output("f-mpio", "value"), Input("f-depto", "value"))
def municipios(depto):
    if not depto:
        return [], None
    mpios = sorted(DF.loc[DF.cole_depto_ubicacion == depto, "cole_mcpio_ubicacion"].dropna().unique())
    return [{"label": m.title(), "value": m} for m in mpios], None


@app.callback(Output("f-depto", "value"), Input("bar-territorio", "clickData"), State("f-depto", "value"),
              prevent_initial_call=True)
def click_depto(click, depto):
    if depto or not click:
        return no_update
    return click["points"][0]["y"].upper()


@app.callback(
    Output("kpis", "children"), Output("bar-title", "children"), Output("bar-territorio", "figure"),
    Output("bar-factor", "figure"), Output("table-title", "children"), Output("tabla-prioridad", "data"),
    Output("tabla-prioridad", "columns"), Output("heatmap", "figure"),
    Input("f-depto", "value"), Input("f-mpio", "value"), Input("f-nat", "value"), Input("f-zona", "value"),
    Input("f-jor", "value"), Input("f-factor", "value"))
def update_diag(depto, mpio, nat, zona, jornada, factor):
    d = filtered(depto, mpio, nat, zona, jornada)
    if d.empty:
        empty = base_layout(go.Figure(), 200)
        return [kpi("Estudiantes evaluados", "0", "Sin datos para este filtro")], "Sin datos", empty, empty, "", [], [], empty

    cole = agg(d, "cole_cod_dane_establecimiento").query("n >= 20")
    kpis = [
        kpi("Estudiantes evaluados", fmt(len(d)),
            f"{fmt(d.cole_cod_dane_establecimiento.nunique())} colegios · "
            f"{fmt(len(d[['cole_depto_ubicacion', 'cole_mcpio_ubicacion']].drop_duplicates()))} municipios"),
        kpi("Puntaje global promedio", fmt(d.punt_global.mean()), f"Desv. estándar {fmt(d.punt_global.std())} · escala 0–500"),
        kpi("Estudiantes en riesgo (< 210 pts)", f"{fmt(d.riesgo_bajo_desempeno.mean() * 100, 1)} %",
            "Promedio nacional: 25,0 %", alert=d.riesgo_bajo_desempeno.mean() > 0.25),
        kpi("Colegios con ≥ 50 % en riesgo", fmt((cole.tasa >= 50).sum()),
            f"de {fmt(len(cole))} colegios con ≥ 20 evaluados", alert=True),
    ]

    if depto:
        terr = agg(d, "cole_mcpio_ubicacion").query("n >= 30").sort_values("tasa", ascending=False).head(25)
        terr["label"] = terr.cole_mcpio_ubicacion.str.title()
        bar_title = ["Tasa de riesgo por municipio ", html.Small(f"· {depto.title()} (≥ 30 evaluados, top 25)")]
    else:
        terr = agg(d, "cole_depto_ubicacion").query("n >= 100").sort_values("tasa", ascending=False)
        terr["label"] = terr.cole_depto_ubicacion.str.title()
        bar_title = ["Tasa de riesgo por departamento ", html.Small("· ordenado de mayor a menor")]
    bar = risk_bars(terr, "label", height=max(300, min(22 * len(terr) + 40, 760)))

    fac = agg(d, factor).query("n >= 30")
    order = ORDERS.get(factor)
    fac = fac.set_index(factor).reindex([o for o in (order or fac[factor]) if o in set(fac[factor])]).reset_index() \
        if order else fac.sort_values("tasa", ascending=False)
    fac[factor] = fac[factor].astype(str)
    fac_fig = risk_bars(fac, factor, height=max(260, 30 * len(fac) + 40))

    if mpio:
        t = agg(d, ["cole_cod_dane_establecimiento", "cole_nombre_establecimiento"]).query("n >= 10")
        t = t.sort_values("tasa", ascending=False).head(50)
        data = [{"Colegio": r.cole_nombre_establecimiento, "Evaluados": int(r.n), "Puntaje medio": round(r.punt),
                 "% riesgo": round(r.tasa, 1)} for r in t.itertuples()]
        title = ["Colegios prioritarios ", html.Small(f"· {mpio.title()} (≥ 10 evaluados)")]
    else:
        t = agg(d, ["cole_depto_ubicacion", "cole_mcpio_ubicacion"]).query(f"n >= {30 if depto else 100}")
        t = t.sort_values("tasa", ascending=False).head(50)
        data = [{"Municipio": r.cole_mcpio_ubicacion.title(), "Depto.": r.cole_depto_ubicacion.title(),
                 "Evaluados": int(r.n), "Puntaje medio": round(r.punt), "% riesgo": round(r.tasa, 1)}
                for r in t.itertuples()]
        title = ["Municipios prioritarios ", html.Small("· ordenados por tasa de riesgo")]
    columns = [{"name": k, "id": k} for k in (data[0].keys() if data else [])]

    est = ORDERS["fami_estratovivienda"]
    piv = (d[d.fami_estratovivienda.isin(est)]
           .pivot_table(index="fami_estratovivienda", columns="cole_naturaleza", values="riesgo_bajo_desempeno",
                        aggfunc="mean", observed=True).reindex([e for e in est]) * 100)
    heat = go.Figure(go.Heatmap(z=piv.values, x=[c.title() for c in piv.columns], y=piv.index,
                                colorscale=[[0, "#fdf6f2"], [1, ORANGE]], zmin=0, zmax=70,
                                text=np.where(np.isnan(piv.values), "", np.round(piv.values).astype("float").astype(str)),
                                texttemplate="%{z:.0f}", hovertemplate="%{y} · %{x}: %{z:.1f} %<extra></extra>",
                                colorbar=dict(title="% riesgo", thickness=10)))
    base_layout(heat, 320)
    heat.update_yaxes(autorange="reversed", gridcolor="white")
    heat.update_xaxes(gridcolor="white")
    return kpis, bar_title, bar, fac_fig, title, data, columns, heat


# ----------------------------------------------------------------------------- callbacks: predicción
@app.callback(Output("gauge", "figure"), Output("pred-text", "children"), Output("contrib", "figure"),
              Output("model-card", "children"), Input("btn-predict", "n_clicks"),
              [State(f"p-{c}", "value") for c in form_fields], State("p-edad", "value"))
def predict(_, *values):
    profile = dict(DEFAULT_PROFILE)
    profile.update(dict(zip(form_fields + ["edad"], values)))
    res = predict_frame(pd.DataFrame([profile])).iloc[0]
    p, level = float(res.prob_riesgo), res.nivel

    gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=p * 100, number={"suffix": " %", "font": {"size": 34}},
        gauge={"axis": {"range": [0, 100], "ticksuffix": "%"}, "bar": {"color": ORANGE if level != "bajo" else BLUE},
               "steps": [{"range": [0, THRESHOLD * 100], "color": "#eef5fd"},
                         {"range": [THRESHOLD * 100, 50], "color": "#fdf0cc"}, {"range": [50, 100], "color": "#fbe1d6"}],
               "threshold": {"line": {"color": INK, "width": 2}, "value": THRESHOLD * 100}}))
    base_layout(gauge, 210)
    gauge.update_layout(margin=dict(l=40, r=40, t=25, b=5))

    contrib = contributions(profile)
    top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(6)
    names = [f"{LABELS[c]}: {profile[c]}" for c in top.index]
    cfig = go.Figure(go.Bar(x=top.values * 100, y=names, orientation="h",
                            marker_color=[ORANGE if v > 0 else BLUE for v in top.values], marker_cornerradius=3,
                            text=[f"{v * 100:+.1f}" for v in top.values], textposition="outside", cliponaxis=False,
                            insidetextanchor="end",
                            hovertemplate="%{y}<br>%{x:+.1f} puntos de probabilidad<extra></extra>"))
    base_layout(cfig, 300)
    lo, hi = min(top.min() * 100, 0), max(top.max() * 100, 0)
    pad = max(hi - lo, 5) * 0.22
    cfig.update_yaxes(autorange="reversed")
    cfig.update_xaxes(title_text="Puntos de probabilidad", zeroline=True, zerolinecolor=MUTED,
                      range=[lo - pad if lo < 0 else 0, hi + pad])

    drivers = [c for c in top.index if top[c] > 0 and c in ADVICE]
    advice = ", ".join(dict.fromkeys(ADVICE[c] for c in drivers[:3])) or "seguimiento regular"
    depto_rate = DF.loc[DF.cole_depto_ubicacion == profile["cole_depto_ubicacion"], "riesgo_bajo_desempeno"].mean()
    text = [
        html.Div(["Probabilidad de puntaje global < 210 · ", html.Span(f"Riesgo {level}".upper(),
                                                                     className=f"pill {level}")],
                 className="result-line"),
        html.Div(["Puntaje global estimado: ", html.B(f"{res.puntaje_estimado}"),
                  f" (RMSE del modelo ≈ {SELECTION['puntaje']['metricas']['val_rmse']:.0f} puntos)"],
                 className="result-line"),
        html.Div(["Tasa de riesgo observada en su departamento: ", html.B(f"{fmt(depto_rate * 100, 1)} %")],
                 className="result-line"),
        html.Div(["Recomendación: ", html.B("priorizar" if level != "bajo" else "monitorear"),
                  f" — {advice}."], className="result-line"),
    ]

    m = SELECTION["riesgo"]["metricas"]
    card = [html.H3(["Acerca del modelo ", html.Small(f"· {SELECTION['riesgo']['run_name']} registrado en MLflow "
                                                      f"(versión {SELECTION['riesgo']['version_registro']})")]),
            html.Div([html.Div([html.B(f"{m['test_auc_roc']:.3f}"), "AUC-ROC (prueba)"]),
                      html.Div([html.B(f"{m['test_recall']:.2f}"), "Recall (prueba)"]),
                      html.Div([html.B(f"{m['test_precision']:.2f}"), "Precisión (prueba)"]),
                      html.Div([html.B(f"{THRESHOLD:.2f}"), "Umbral de decisión"]),
                      html.Div([html.B(f"{SELECTION['puntaje']['metricas']['test_rmse']:.1f}"), "RMSE puntaje (prueba)"])],
                     className="model-meta"),
            html.Div("Nivel: bajo si la probabilidad es menor al umbral; medio entre el umbral y 50 %; alto desde 50 %. "
                     "El umbral se eligió para detectar al menos 70 % de los estudiantes en riesgo.", className="note")]
    return gauge, text, cfig, card


# ----------------------------------------------------------------------------- callbacks: lotes
@app.callback(Output("dl-template", "data"), Input("btn-template", "n_clicks"), prevent_initial_call=True)
def template(_):
    sample = DF[FEATURES].sample(10, random_state=1).astype(object)
    sample.insert(0, "id_estudiante", [f"EST-{i:04d}" for i in range(1, 11)])
    return dcc.send_data_frame(sample.to_csv, "plantilla_estudiantes.csv", index=False)


@app.callback(Output("batch-table", "data"), Output("batch-table", "columns"), Output("batch-msg", "children"),
              Output("batch-store", "data"), Input("upload", "contents"), Input("url", "search"),
              State("upload", "filename"))
def batch(contents, search, filename):
    if ctx.triggered_id != "upload":
        if "demo=1" not in (search or ""):
            return no_update, no_update, no_update, no_update
        # Modo demostración: 25 estudiantes de ejemplo tomados de los datos
        demo = DF[FEATURES].sample(25, random_state=7).astype(object)
        demo.insert(0, "id_estudiante", [f"EST-{i:04d}" for i in range(1, 26)])
        contents = "data:text/csv;base64," + base64.b64encode(demo.to_csv(index=False).encode()).decode()
        filename = "demo_estudiantes.csv"
    try:
        raw = base64.b64decode(contents.split(",", 1)[1])
        df = pd.read_csv(io.BytesIO(raw), dtype=str)
    except Exception:
        return [], [], "No fue posible leer el archivo. Verifique que sea un CSV.", None
    missing = [c for c in FEATURES if c not in df.columns]
    for c in missing:
        df[c] = np.nan
    out = pd.concat([df.drop(columns=[c for c in FEATURES if c in missing]).reset_index(drop=True),
                     predict_frame(df)], axis=1).sort_values("prob_riesgo", ascending=False)
    keep = [c for c in ["id_estudiante", "prob_riesgo", "nivel", "puntaje_estimado", "cole_depto_ubicacion",
                        "cole_jornada", "fami_educacionmadre", "fami_tieneinternet"] if c in out.columns]
    msg = f"{filename}: {len(out)} estudiantes · {(out.nivel == 'alto').sum()} en riesgo alto."
    if missing:
        msg += f" Columnas ausentes (se imputaron automáticamente): {', '.join(missing)}."
    names = {"id_estudiante": "Estudiante", "prob_riesgo": "Prob. riesgo", "nivel": "Nivel",
             "puntaje_estimado": "Puntaje estimado", **LABELS}
    return (out[keep].to_dict("records"), [{"name": names.get(c, c), "id": c} for c in keep], msg,
            out.to_json(orient="split"))


@app.callback(Output("dl-results", "data"), Input("btn-download", "n_clicks"), State("batch-store", "data"),
              prevent_initial_call=True)
def download(_, stored):
    if not stored:
        return no_update
    out = pd.read_json(io.StringIO(stored), orient="split")
    return dcc.send_data_frame(out.to_csv, "estudiantes_priorizados.csv", index=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
