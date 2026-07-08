"""Generación de PDF de reportes y movimientos con reportlab (Python puro)."""
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, String
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#211F1A")
SECONDARY = colors.HexColor("#7A756C")
ACCENT = colors.HexColor("#12898F")
GREEN = colors.HexColor("#3FA65C")
RED = colors.HexColor("#E2574C")
TRACK = colors.HexColor("#F0EDE6")
PALETTE = [colors.HexColor(h) for h in
           ("#12898F", "#D9932E", "#3FA65C", "#D3775A", "#6B5B95", "#4A79D9", "#C2555B", "#8A8F5C")]

_styles = getSampleStyleSheet()
TITLE = ParagraphStyle("t", parent=_styles["Title"], fontName="Helvetica-Bold", fontSize=20, textColor=INK, spaceAfter=2, alignment=0)
SUB = ParagraphStyle("s", parent=_styles["Normal"], fontName="Helvetica", fontSize=10, textColor=SECONDARY, spaceAfter=10)
H = ParagraphStyle("h", parent=_styles["Normal"], fontName="Helvetica-Bold", fontSize=12, textColor=INK, spaceBefore=8, spaceAfter=6)


def _doc(title_meta: str):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=title_meta)
    return buf, doc


def _kpi_table(kpis: list[dict]):
    if not kpis:
        return None
    header = [Paragraph(f'<font size=8 color="#7A756C">{k["label"]}</font>', _styles["Normal"]) for k in kpis]
    values = [Paragraph(f'<font size=13><b>{k["value"]}</b></font>', _styles["Normal"]) for k in kpis]
    t = Table([header, values], colWidths=[(174 / len(kpis)) * mm] * len(kpis))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAF9F6")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E3DB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E7E3DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _data_table(columns: list[str], rows: list[list], aligns=None):
    head = [Paragraph(f'<font size=8 color="#7A756C"><b>{c.upper()}</b></font>', _styles["Normal"]) for c in columns]
    body = [[Paragraph(f'<font size=9>{c}</font>', _styles["Normal"]) for c in r] for r in rows]
    t = Table([head] + body, repeatRows=1)
    style = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#D8D3C9")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#EEEAE1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in (aligns or []):
        style.append(("ALIGN", (i, 0), (i, -1), "RIGHT"))
    t.setStyle(TableStyle(style))
    return t


def _bar_drawing(series: list[dict]):
    d = Drawing(480, 200)
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 30, 30, 420, 150
    chart.data = [[s["income"] for s in series], [s["expense"] for s in series]]
    chart.categoryAxis.categoryNames = [s["label"] for s in series]
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dy = -4
    chart.bars[0].fillColor = GREEN
    chart.bars[1].fillColor = RED
    chart.valueAxis.labels.fontSize = 6
    d.add(chart)
    return d


def _line_drawing(values: list[float], labels: list[str], color=ACCENT):
    d = Drawing(480, 200)
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 30, 30, 420, 150
    lp.data = [list(enumerate(values))]
    lp.lines[0].strokeColor = color
    lp.lines[0].strokeWidth = 2
    lp.joinedLines = 1
    lp.xValueAxis.valueMin = 0
    lp.xValueAxis.valueMax = len(values) - 1 if len(values) > 1 else 1
    lp.xValueAxis.valueSteps = list(range(len(values)))
    lp.xValueAxis.labelTextFormat = lambda v: labels[int(v)] if 0 <= int(v) < len(labels) else ""
    lp.xValueAxis.labels.fontSize = 6
    lp.xValueAxis.labels.angle = 30
    d.add(lp)
    return d


def _pie_drawing(names: list[str], values: list[float]):
    d = Drawing(460, 200)
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 20, 20, 160, 160
    pie.data = values
    pie.labels = None
    pie.innerRadiusFraction = 0.55
    for i in range(len(values)):
        pie.slices[i].fillColor = PALETTE[i % len(PALETTE)]
        pie.slices[i].strokeColor = colors.white
    d.add(pie)
    legend = Legend()
    legend.x, legend.y = 210, 175
    legend.fontSize = 8
    legend.dxTextSpace = 5
    legend.deltay = 12
    legend.colorNamePairs = [(PALETTE[i % len(PALETTE)], names[i]) for i in range(len(names))]
    d.add(legend)
    return d


def build_report_pdf(title, subtitle="", kpis=None, table=None, bars=None,
                     line=None, pie=None, note="") -> bytes:
    buf, doc = _doc(title)
    story = [Paragraph(title, TITLE)]
    if subtitle:
        story.append(Paragraph(subtitle, SUB))
    kt = _kpi_table(kpis or [])
    if kt:
        story += [kt, Spacer(1, 12)]
    if bars:
        story.append(_bar_drawing(bars))
    if line:
        story.append(_line_drawing(line["values"], line["labels"], line.get("color", ACCENT)))
    if pie:
        story.append(_pie_drawing(pie["names"], pie["values"]))
    if table:
        story += [Spacer(1, 6), _data_table(table["columns"], table["rows"], table.get("right", []))]
    if note:
        story += [Spacer(1, 10), Paragraph(f'<font size=9 color="#7A756C">{note}</font>', _styles["Normal"])]
    doc.build(story)
    return buf.getvalue()


def build_transactions_pdf(title, rows, total_label=None) -> bytes:
    """rows: [{date, profile, category, note, amount}] con amount ya formateado y signo."""
    buf, doc = _doc(title)
    story = [Paragraph(title, TITLE), Paragraph("Movimientos", SUB)]
    columns = ["Fecha", "Perfil", "Categoría", "Nota", "Importe"]
    data = [[r["date"], r["profile"], r["category"], r["note"], r["amount"]] for r in rows]
    story.append(_data_table(columns, data, aligns=[4]))
    if total_label:
        story += [Spacer(1, 8), Paragraph(f'<font size=10><b>Neto: {total_label}</b></font>', _styles["Normal"])]
    doc.build(story)
    return buf.getvalue()
