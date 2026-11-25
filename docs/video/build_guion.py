"""Genera el guion del video (Word) a partir de guion.json, la misma fuente de las notas de la presentación.

Uso: python docs/video/build_guion.py  ->  docs/video/guion_video.docx
"""
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
G = json.loads((HERE / "guion.json").read_text(encoding="utf-8"))
NAVY, TEAL, GREY = RGBColor(0x0B, 0x25, 0x45), RGBColor(0x00, 0x8C, 0x9B), RGBColor(0x50, 0x60, 0x70)
COLORS = {"Mateo": "E6F4F5", "Harol": "EFE8F5", "Sebastian": "E8EDF3"}


def shade(cell, hex_color):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    cell._tc.get_or_add_tcPr().append(shd)


def para(doc_or_cell, text="", size=11, bold=False, italic=False, color=None, after=4):
    p = doc_or_cell.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if text:
        r = p.add_run(text)
        r.font.size, r.bold, r.italic = Pt(size), bold, italic
        if color:
            r.font.color.rgb = color
    return p


def mmss(sec):
    return f"{sec // 60}:{sec % 60:02d}"


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Cm(2)
    sec.top_margin = sec.bottom_margin = Cm(1.8)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Calibri", Pt(11)

    para(doc, G["titulo"], size=18, bold=True, color=NAVY, after=2)
    total = sum(d["segundos"] for d in G["diapositivas"])
    para(doc, f"Duración estimada: {mmss(total)} (máximo 10:00) · Presentación: docs/video/presentacion_video.pptx "
              "(las notas del orador de cada diapositiva tienen este mismo texto).", size=10, italic=True, color=GREY)

    para(doc, "Reparto y tiempos", size=13, bold=True, color=TEAL, after=2)
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(["#", "Diapositiva", "Presenta", "Tiempo (inicio–fin)"]):
        t.rows[0].cells[i].text = h
        t.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    start = 0
    for d in G["diapositivas"]:
        cells = t.add_row().cells
        for i, v in enumerate([str(d["n"]), d["titulo"], d["presenta"],
                               f"{mmss(start)}–{mmss(start + d['segundos'])}"]):
            cells[i].text = v
        shade(cells[2], COLORS.get(d["presenta"].split()[0], "FFFFFF"))
        start += d["segundos"]
    for row in t.rows:
        for i, w in enumerate([1.0, 7.5, 4.5, 4.0]):
            row.cells[i].width = Cm(w)

    para(doc, "", after=2)
    para(doc, "Antes de grabar", size=13, bold=True, color=TEAL, after=2)
    for item in G["indicaciones"]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(item.replace("`", ""))

    para(doc, "Guion por diapositiva", size=13, bold=True, color=TEAL, after=2)
    start = 0
    for d in G["diapositivas"]:
        tb = doc.add_table(rows=1, cols=1)
        tb.style = "Table Grid"
        cell = tb.rows[0].cells[0]
        shade(cell, COLORS.get(d["presenta"].split()[0], "F3F5F9"))
        cell.paragraphs[0].add_run(
            f"{d['n']}. {d['titulo']}  ·  {d['presenta']}  ·  {mmss(start)}–{mmss(start + d['segundos'])}"
        ).bold = True
        p = para(cell, "", size=10, after=4)
        r = p.add_run("En pantalla: ")
        r.bold, r.font.size = True, Pt(10)
        r = p.add_run(d["pantalla"].replace("`", ""))
        r.font.size, r.italic = Pt(10), True
        para(cell, d["texto"], size=11, after=6)
        para(doc, "", after=2)
        start += d["segundos"]

    out = HERE / "guion_video.docx"
    doc.save(out)
    print("Guardado", out)


if __name__ == "__main__":
    main()
