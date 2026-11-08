"""Genera resumen verificable y figuras a partir de resultados ya calculados."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

out = Path('reports/modeling')
c = pd.read_csv(out/'classification_validation.csv')
r = pd.read_csv(out/'regression_validation.csv')
t = json.loads((out/'classification_test.json').read_text())
rt = json.loads((out/'regression_test.json').read_text())
m = t['test']
fig, ax = plt.subplots(figsize=(9,4))
c.set_index('model')[['auc','precision','recall']].plot.bar(ax=ax, ylim=(0,1), rot=15)
ax.set_title('Comparacion en validacion - umbral elegido para recall >= 0.70')
ax.set_xlabel(''); ax.set_ylabel('Metrica'); fig.tight_layout()
fig.savefig(out/'comparacion_clasificadores.png', dpi=160); plt.close(fig)
imp = pd.read_csv(out/'feature_importance.csv').head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9,5))
ax.barh(imp.feature, imp.auc_decrease, xerr=imp['std'])
ax.set_xlabel('Disminucion de AUC al permutar'); ax.set_title('Importancia en validacion (5.000 casos)')
fig.tight_layout(); fig.savefig(out/'importancia_variables.png', dpi=160); plt.close(fig)

def table(df, cols):
    rows = ['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for _, row in df.iterrows():
        rows.append('| '+' | '.join(f'{row[k]:.4f}' if isinstance(row[k],float) else str(row[k]) for k in cols)+' |')
    return '\n'.join(rows)

text = f'''# Resultados del aporte de modelado

## Clasificacion

{table(c, ['model','auc','average_precision','precision','recall','f1','threshold'])}

Comparacion anterior realizada en validacion. Seleccion: **{t['selected_model']}**. Umbral: **{t['threshold']:.4f}**.

Evaluacion final en prueba: AUC **{m['auc']:.4f}**, recall **{m['recall']:.4f}**, precision **{m['precision']:.4f}**, F1 **{m['f1']:.4f}** y average precision **{m['average_precision']:.4f}**.

Metas de AUC >= 0.75 y recall >= 0.70 en prueba: **{'cumplidas' if t['targets_met'] else 'no cumplidas en su totalidad'}**. No se ajusto el umbral mirando prueba.

Matriz de confusion: verdaderos negativos {m['tn']}, falsos positivos {m['fp']}, falsos negativos {m['fn']}, verdaderos positivos {m['tp']}.

El recall mide la fraccion de estudiantes con riesgo que se identifica; la precision mide cuantos de los marcados realmente presentan bajo puntaje. Los falsos negativos representan casos que el sistema dejaria sin priorizar, y los falsos positivos consumen capacidad de revision/refuerzo. Deben interpretarse juntos.

## Puntaje estimado

{table(r, ['model','mae','rmse','r2'])}

Modelo seleccionado: **{rt['selected_model']}**. Prueba: MAE **{rt['test']['mae']:.2f} puntos**, RMSE **{rt['test']['rmse']:.2f} puntos**, R2 **{rt['test']['r2']:.4f}**. El MAE es un error promedio; no es un intervalo de confianza individual.

## Alcance y evidencia

Datos historicos del periodo 20224. Particion estratificada 60/20/20; no hay validacion temporal ni prueba sobre colegios completamente nuevos. No inferir causalidad de las importancias. Ver GUIA_HAROL.md para metodologia y limitaciones.

Los CSV conservan los run IDs de MLflow. Estos resultados se registraron localmente. Aun faltan experimentos y capturas en EC2 para cumplir ese soporte de la guia, integracion con API/tablero y reporte final del equipo.
'''
(out/'RESULTADOS_HAROL.md').write_text(text, encoding='utf-8')
print(text)
