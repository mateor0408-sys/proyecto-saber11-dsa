// Presentación de apoyo para el video de la Entrega final, con el formato MIAD / Uniandes
// (fondos, tipografía, colores y disposición tomados de la plantilla de la universidad).
// Las notas del orador salen de guion.json (el mismo guion que se entrega al equipo).
// Uso: NODE_PATH=<carpeta con pptxgenjs>/node_modules node docs/video/build_deck.js
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.join(__dirname, "presentacion_video.pptx");
const G = JSON.parse(fs.readFileSync(path.join(__dirname, "guion.json"), "utf8"));
const SEL = JSON.parse(fs.readFileSync(path.join(ROOT, "models", "seleccion.json"), "utf8"));
const R = (p) => path.join(ROOT, p);
const A = (p) => path.join(__dirname, "assets", p);

// Paleta y tipografía de la plantilla de la universidad
const NAVY = "0B2545", TEAL = "008C9B", PURPLE = "704398", GREY = "506070", CARD = "F0F5F7",
      MUTE = "C9D3DA", WHITE = "FFFFFF", ORANGE = "E8892B";
const FONT = "Aptos";
const TOTAL = G.diapositivas.length;
const FOOTER = "Entrega final · Monitor de Riesgo Académico Saber 11";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13,333 × 7,5 in, como la plantilla
pres.title = "Monitor de Riesgo Académico Saber 11 — Entrega final";
pres.author = "Mateo Ríos, Harol Perafan, Sebastian Vivas";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({ title: "PORTADA", background: { path: A("fondo_portada.png") } });
pres.defineSlideMaster({
  title: "CONTENIDO", background: { path: A("fondo_contenido.png") },
  objects: [{ text: { text: FOOTER, options: { x: 0.72, y: 6.76, w: 7.3, h: 0.3, fontSize: 10, color: GREY,
                                               fontFace: FONT, margin: 0 } } }],
});

// ------------------------------------------------------------------------------------------- utilidades
const T = (s, text, o) => s.addText(text, { fontFace: FONT, color: NAVY, margin: 0, valign: "top", isTextBox: true,
                                            ...o });
const notes = (s, n) => {
  const d = G.diapositivas.find((x) => x.n === n);
  s.addNotes(`[${d.presenta} · ~${d.segundos} s]\n\n${d.texto}\n\nEn pantalla: ${d.pantalla}`);
};
const content = (n, title, subtitle) => {
  const s = pres.addSlide({ masterName: "CONTENIDO" });
  T(s, title, { x: 0.72, y: 1.05, w: 11.9, h: 0.55, fontSize: 30, bold: true, valign: "middle" });
  T(s, subtitle, { x: 0.74, y: 1.65, w: 11.8, h: 0.45, fontSize: 17, color: GREY });
  T(s, `${String(n).padStart(2, "0")} / ${TOTAL}`, { x: 11.55, y: 6.63, w: 0.9, h: 0.28, fontSize: 11, color: GREY,
                                                     align: "right" });
  notes(s, n);
  return s;
};
const card = (s, x, y, w, h, accent) => {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: CARD }, line: { type: "none" }, rectRadius: 0.08 });
  if (accent) s.addShape(pres.ShapeType.rect, { x, y, w: 0.07, h, fill: { color: accent }, line: { type: "none" } });
};
// Tarjeta con título de color y texto (como «Necesidad / Restricción / Oportunidad»)
const textCard = (s, x, y, w, h, accent, head, body, bodySize = 17) => {
  card(s, x, y, w, h, accent);
  T(s, head, { x: x + 0.2, y: y + 0.17, w: w - 0.4, h: 0.5, fontSize: 21, bold: true, color: accent });
  T(s, body, { x: x + 0.2, y: y + 0.72, w: w - 0.4, h: h - 0.85, fontSize: bodySize });
};
// Tarjeta de cifra (como «75 / 16,1 % / 19,0 %»)
const statCard = (s, x, y, w, h, value, label, color) => {
  card(s, x, y, w, h);
  T(s, value, { x: x + 0.15, y: y + 0.14, w: w - 0.3, h: 0.7, fontSize: 36, bold: true, color });
  T(s, label, { x: x + 0.15, y: y + 0.88, w: w - 0.3, h: h - 0.95, fontSize: 15 });
};
const pic = (s, file, x, y, w, ratio) => { s.addImage({ path: R(file), x, y, w, h: w / ratio }); return y + w / ratio; };
const note = (s, text, x, y, w) => T(s, text, { x, y, w, h: 0.3, fontSize: 10, color: GREY });
const MR = SEL.riesgo.metricas, MP = SEL.puntaje.metricas;
const pct = (v) => `${Math.round(v * 100)} %`;
const dec = (v, d = 2) => v.toFixed(d).replace(".", ",");

// ------------------------------------------------------------------------------------------- 1 portada
{
  const s = pres.addSlide({ masterName: "PORTADA" });
  T(s, "Monitor de Riesgo Académico Saber 11: modelos, API y tablero desplegados en AWS",
    { x: 6.48, y: 0.95, w: 6.05, h: 2.05, fontSize: 29, bold: true, valign: "bottom" });
  T(s, "Proyecto · Entrega final", { x: 6.5, y: 3.32, w: 5.75, h: 0.55, fontSize: 23, bold: true, color: TEAL });
  T(s, "Mateo Ríos · Harol Perafan\nSebastian Vivas", { x: 6.5, y: 4.03, w: 5.75, h: 1.18, fontSize: 19 });
  T(s, "MIID 4304 · Despliegue de Soluciones Analíticas\nMaestría en Inteligencia Analítica de Datos\nNoviembre de 2026",
    { x: 6.5, y: 5.37, w: 5.9, h: 1.1, fontSize: 16, color: GREY });
  notes(s, 1);
}

// ------------------------------------------------------------------------------------------- 2 problema
{
  const s = content(2, "Las brechas en Saber 11 se atienden tarde", "Contexto y relevancia");
  statCard(s, 0.8, 2.35, 3.75, 1.55, "61 %", "de los estudiantes de Chocó en el cuartil más bajo del país", PURPLE);
  statCard(s, 4.8, 2.35, 3.75, 1.55, "12 %", "en Bogotá: brecha territorial de 5 a 1", TEAL);
  statCard(s, 8.8, 2.35, 3.75, 1.55, "0–500", "puntaje global que define el acceso a la universidad y a becas", NAVY);
  textCard(s, 0.8, 4.2, 5.75, 1.75, NAVY, "Hoy", "El refuerzo se focaliza con resultados del año anterior, cuando el estudiante ya presentó la prueba.");
  textCard(s, 6.8, 4.2, 5.75, 1.75, TEAL, "Con el monitor", "Se prioriza antes de la prueba, con datos del hogar y del colegio que ya se conocen.");
}

// ------------------------------------------------------------------------------------------- 3 pregunta y datos
{
  const s = content(3, "¿Quién está en riesgo antes de la prueba?", "Pregunta de negocio, alcance y datos");
  card(s, 0.8, 2.3, 11.75, 1.45, NAVY);
  T(s, "¿Qué estudiantes, colegios y municipios tienen mayor riesgo de obtener un puntaje global menor a 210 "
       + "(percentil 25 nacional), según sus características socioeconómicas y del colegio, para priorizar refuerzo?",
    { x: 1.05, y: 2.45, w: 11.3, h: 1.2, fontSize: 20, bold: true, valign: "middle" });
  statCard(s, 0.8, 4.05, 3.75, 1.55, "532.788", "estudiantes únicos · ICFES, datos.gov.co, periodo 20224", TEAL);
  statCard(s, 4.8, 4.05, 3.75, 1.55, "19", "variables conocidas antes de la prueba: hogar, colegio y estudiante", PURPLE);
  statCard(s, 8.8, 4.05, 3.75, 1.55, "1 de 4", "estudiantes bajo el umbral de 210 puntos (clase en riesgo)", NAVY);
  T(s, "Alcance: modelos supervisados empaquetados + API de inferencia + tablero, desplegados con Docker en AWS. "
       + "Datos y modelos versionados con DVC en S3.", { x: 0.85, y: 5.85, w: 11.65, h: 0.6, fontSize: 16, color: GREY });
}

// ------------------------------------------------------------------------------------------- 4 modelos
{
  const s = content(4, "Gradient boosting supera a los demás modelos", "Experimentos en MLflow sobre AWS EC2 · AUC-PR en validación");
  const rows = [["Solo colegio (ablación)", 0.5133], ["Solo hogar (ablación)", 0.5307], ["Regresión logística", 0.5463],
                ["Bosque aleatorio", 0.5497], ["Gradient boosting", 0.5893]];
  s.addChart(pres.ChartType.bar, [{ name: "AUC-PR", labels: rows.map((r) => r[0]), values: rows.map((r) => r[1]) }], {
    x: 0.7, y: 2.25, w: 7.2, h: 4.2, barDir: "bar",
    chartColors: rows.map((r) => (r[0] === "Gradient boosting" ? TEAL : MUTE)),
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", dataLabelFontSize: 14,
    dataLabelColor: NAVY, dataLabelFontFace: FONT,
    catAxisLabelColor: NAVY, catAxisLabelFontSize: 14, catAxisLabelFontFace: FONT,
    valAxisHidden: true, valAxisMinVal: 0.45, valAxisMaxVal: 0.62,
    valGridLine: { style: "none" }, catGridLine: { style: "none" }, showLegend: false, barGapWidthPct: 50,
  });
  // Evidencia de MLflow en EC2 (la IP del servidor queda visible en la barra del navegador)
  const end = pic(s, "reports/capturas_e2/mlflow_experimentos.png", 8.2, 2.3, 4.35, 1.595);
  note(s, "Runs del experimento saber11-riesgo en MLflow sobre EC2 (http://54.242.29.105:5000)", 8.2, end + 0.05, 4.35);
  textCard(s, 8.2, end + 0.45, 4.35, 6.45 - end - 0.45, TEAL, "13+ runs en MLflow",
           "Partición 70/15/15 · AUC-PR · umbral con recall ≥ 0,70", 14);
}

// ------------------------------------------------------------------------------------------- 5 resultados
{
  const s = content(5, "El modelo prioriza casi 2 veces mejor que el azar", "Modelo campeón hgb-lr0.05-l63 en el conjunto de prueba");
  statCard(s, 0.8, 2.35, 3.2, 1.55, dec(MR.test_auc_roc), "AUC-ROC (criterio de éxito ≥ 0,75)", NAVY);
  statCard(s, 4.2, 2.35, 3.2, 1.55, pct(MR.test_recall), "de los estudiantes en riesgo se detectan", TEAL);
  statCard(s, 0.8, 4.15, 3.2, 1.55, pct(MR.test_precision), `de los priorizados están en riesgo (${dec(MR.test_precision / 0.25, 1)}× el azar)`, PURPLE);
  statCard(s, 4.2, 4.15, 3.2, 1.55, `± ${Math.round(MP.test_rmse)}`, "puntos de error al estimar el puntaje global", NAVY);
  T(s, "Validación y prueba coinciden: sin sobreajuste.", { x: 0.85, y: 5.9, w: 6.6, h: 0.4, fontSize: 15, color: GREY });
  card(s, 7.7, 2.3, 4.85, 4.15);
  T(s, "Lo que más pesa: departamento, edad (extraedad) y jornada", { x: 7.9, y: 2.4, w: 4.45, h: 0.6, fontSize: 15, bold: true });
  pic(s, "reports/modelos/mejor_riesgo_importancia_permutacion.png", 8.55, 3.0, 3.1, 0.896);
}

// ------------------------------------------------------------------------------------------- 6 API
{
  const s = content(6, "Una API sirve el modelo a cualquier cliente", "FastAPI con los modelos exportados de MLflow");
  const eps = [["GET", "/health", "estado del servicio"], ["GET", "/features", "las 19 variables del modelo"],
               ["GET", "/modelo", "run, versión, métricas y umbral"],
               ["POST", "/predict", "hasta 1.000 estudiantes → probabilidad, nivel y puntaje"]];
  card(s, 0.8, 2.3, 5.9, 4.15, TEAL);
  eps.forEach(([m, p, d], i) => {
    const y = 2.5 + i * 0.95;
    s.addText(m, { x: 1.05, y: y + 0.05, w: 0.85, h: 0.4, fontSize: 13, bold: true, color: WHITE, fontFace: FONT,
                   align: "center", valign: "middle", shape: pres.ShapeType.roundRect, rectRadius: 0.08,
                   fill: { color: m === "POST" ? TEAL : NAVY }, margin: 0, isTextBox: true });
    T(s, [{ text: p, options: { bold: true, breakLine: true } }, { text: d, options: { color: GREY } }],
      { x: 2.05, y, w: 4.5, h: 0.85, fontSize: 15 });
  });
  pic(s, "reports/evidencias_entrega3/16_api_desplegada_ec2.png", 6.95, 2.3, 5.6, 2.182);
  card(s, 6.95, 5.0, 5.6, 1.45, PURPLE);
  T(s, [{ text: "Respuesta de /predict", options: { bold: true, color: PURPLE, breakLine: true } },
        { text: '{"prob_riesgo": 0.4521, "nivel": "medio", "puntaje_estimado": 222}', options: { fontFace: "Courier New" } }],
    { x: 7.2, y: 5.15, w: 5.2, h: 1.2, fontSize: 14 });
}

// ------------------------------------------------------------------------------------------- 7 tablero
{
  const s = content(7, "Un tablero para diagnosticar, predecir y priorizar", "Dash; todas las predicciones se piden a la API");
  const h = 3.05, y = 2.3;
  const shots = [["reports/tablero/tab1_diagnostico.png", 0.791, TEAL, "1 · Diagnóstico territorial"],
                 ["reports/evidencias_entrega3/14_tablero_desplegado_ec2.png", 1.326, PURPLE, "2 · Predicción de riesgo"],
                 ["reports/evidencias_entrega3/13_tablero_lotes_via_api.png", 1.273, NAVY, "3 · Priorización por lotes"]];
  const ws = shots.map((t) => h * t[1]);
  const gap = (11.75 - ws.reduce((a, b) => a + b, 0)) / 2;
  let x = 0.8;
  const desc = ["Filtros, indicadores y municipios o colegios prioritarios",
                "Probabilidad, nivel, puntaje, recomendación y factores",
                "CSV de estudiantes → lista ordenada y descargable"];
  shots.forEach(([f, r, c, t], i) => {
    s.addImage({ path: R(f), x, y, w: ws[i], h });
    T(s, t, { x, y: y + h + 0.12, w: Math.max(ws[i], 3.2), h: 0.4, fontSize: 17, bold: true, color: c });
    T(s, desc[i], { x, y: y + h + 0.52, w: Math.max(ws[i], 3.2), h: 0.6, fontSize: 14 });
    x += ws[i] + gap;
  });
}

// ------------------------------------------------------------------------------------------- 8 arquitectura
{
  const s = content(8, "Dos contenedores Docker en AWS EC2", "Arquitectura de la solución");
  pic(s, "reports/arquitectura/arquitectura.png", 2.4, 2.2, 8.55, 2.126);
  T(s, "docker compose up -d --build · healthcheck en /health · el tablero llega a la API por la red interna "
       + "(API_URL=http://api:8000)", { x: 0.85, y: 6.35, w: 11.65, h: 0.3, fontSize: 13, color: GREY, align: "center" });
}

// ------------------------------------------------------------------------------------------- 9 recursos AWS
{
  const s = content(9, "Recursos desplegados en AWS", "Evidencia del despliegue en EC2 con Docker Compose");
  const end = pic(s, "reports/evidencias_entrega3/15_contenedores_compose_ec2.png", 0.8, 2.3, 11.75, 4.261);
  const tiles = [[TEAL, "EC2 · Ubuntu 24.04", "Docker y Compose; IP pública 35.153.80.5 (privada 172.31.42.190)"],
                 [PURPLE, "Grupo de seguridad", "SSH 22 · API 8000 · tablero 8050"],
                 [NAVY, "MLflow en EC2", "servidor de experimentos (puerto 5000) y Model Registry"]];
  tiles.forEach(([c, h, b], i) => textCard(s, 0.8 + i * 4.0, end + 0.3, 3.75, 6.45 - end - 0.3, c, h, b, 15));
}

// ------------------------------------------------------------------------------------------- 10 conclusiones
{
  const s = content(10, "Un prototipo útil para priorizar a tiempo", "Conclusiones");
  textCard(s, 0.8, 2.25, 3.78, 2.72, TEAL, "Lo logrado",
           "7 de cada 10 estudiantes en riesgo se detectan antes de la prueba, con casi 2× la eficiencia del azar.");
  textCard(s, 4.78, 2.25, 3.78, 2.72, NAVY, "Lo que muestra",
           "Territorio, extraedad y jornada concentran el riesgo: combinar programas territoriales y acompañamiento familiar.");
  textCard(s, 8.76, 2.25, 3.78, 2.72, PURPLE, "Lo que sigue",
           "Validar con otros periodos, monitorear el modelo, HTTPS y autenticación. Priorizar apoyo, nunca etiquetar.");
  T(s, "Muchas gracias", { x: 0.85, y: 5.48, w: 11.65, h: 0.75, fontSize: 28, bold: true, align: "center", valign: "middle" });
  T(s, "github.com/mateor0408-sys/proyecto-saber11-dsa", { x: 0.85, y: 6.15, w: 11.65, h: 0.35, fontSize: 14,
                                                            color: GREY, align: "center" });
}

pres.writeFile({ fileName: OUT }).then(() => console.log("Guardado", OUT));
