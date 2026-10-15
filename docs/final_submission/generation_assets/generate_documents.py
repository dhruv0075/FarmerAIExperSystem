"""Generate the four AgriWise AI submission documents from checked evidence.

Run from the repository root with the project's configured Python environment:
    python docs/final_submission/generation_assets/generate_documents.py
"""

from __future__ import annotations

import json
import math
import re
import textwrap
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "final_submission"
ASSETS = OUT / "generation_assets"
ASSETS.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

GREEN = "1D5B45"
DARK = "173A32"
GOLD = "C58A3A"
PALE = "EAF2EC"
GREY = "59645F"
WHITE = "FFFFFF"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shade = OxmlElement("w:shd")
    shade.set(qn("w:fill"), fill)
    tc_pr.append(shade)


def repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_margins(cell, top=70, start=85, bottom=70, end=85) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_field(paragraph, field: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = f" {field} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    result = OxmlElement("w:t")
    result.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, separate, result, end])


def add_toc(document: Document) -> None:
    p = document.add_paragraph()
    r = p.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Open this document in Word and update the table of contents."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    r._r.extend([begin, instruction, separate, placeholder, end])


def set_update_fields(document: Document) -> None:
    settings = document.settings._element
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    settings.append(update)


def setup_document(title: str, short_title: str, *, ieee=False) -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin = Inches(0.72 if ieee else 0.78)
    sec.bottom_margin = Inches(0.72 if ieee else 0.75)
    sec.left_margin = Inches(0.68 if ieee else 0.9)
    sec.right_margin = Inches(0.68 if ieee else 0.82)
    sec.header_distance = Inches(0.35)
    sec.footer_distance = Inches(0.35)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5 if ieee else 10.2)
    normal.font.color.rgb = RGBColor.from_string(DARK)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.09
    for name, size, color in (
        ("Title", 26, DARK),
        ("Heading 1", 16, GREEN),
        ("Heading 2", 12.5, DARK),
        ("Heading 3", 10.5, GREEN),
    ):
        style = styles[name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size if not ieee else max(9, size - 4))
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 8)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True

    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run(f"AGRIWISE AI  |  {short_title.upper()}")
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor.from_string(GREY)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Academic project documentation  •  ").font.size = Pt(8)
    footer.add_run("Page ")
    add_field(footer, "PAGE")
    footer.add_run(" of ")
    add_field(footer, "NUMPAGES")
    for run in footer.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor.from_string(GREY)

    doc.core_properties.title = title
    doc.core_properties.subject = "Evidence-grounded AgriWise AI project submission"
    doc.core_properties.author = "AgriWise AI project team — student details to be completed"
    doc.core_properties.keywords = "AgriWise AI, agriculture, decision support, machine learning"
    set_update_fields(doc)
    return doc


def add_cover(doc: Document, title: str, document_name: str, version="1.0") -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(82)
    r = p.add_run("AGRIWISE AI")
    r.bold = True
    r.font.name = "Aptos Display"
    r.font.size = Pt(30)
    r.font.color.rgb = RGBColor.from_string(GREEN)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    r = p.add_run("An Intelligent Crop Lifecycle\nDecision Support System for Sustainable Agriculture")
    r.font.size = Pt(17)
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(DARK)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(25)
    r = p.add_run(title)
    r.font.size = Pt(21)
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(GREEN)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(26)
    p.add_run(f"{document_name}\nVersion {version}  |  15 October 2026").font.size = Pt(11)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(48)
    p.add_run(
        "Student name: [FILL IN]    Roll number: [FILL IN]\n"
        "Institution / Department: [FILL IN]\n"
        "Project supervisor: [FILL IN]\n"
        "Submission term / academic year: [FILL IN]"
    ).font.size = Pt(10)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(32)
    rr = p.add_run("Evidence-grounded edition — implementation claims are qualified by verification status.")
    rr.italic = True
    rr.font.size = Pt(9)
    rr.font.color.rgb = RGBColor.from_string(GREY)
    doc.add_page_break()


def add_toc_page(doc: Document) -> None:
    doc.add_heading("Contents", level=1)
    add_toc(doc)
    doc.add_paragraph(
        "The contents field is updateable in Microsoft Word: select the contents and choose "
        "Update Field → Update entire table. Headings are real Word heading styles."
    )
    doc.add_page_break()


def add_paragraphs(doc: Document, paragraphs: Iterable[str], *, style=None) -> None:
    for text in paragraphs:
        p = doc.add_paragraph(style=style)
        p.add_run(text)


def add_bullets(doc: Document, items: Iterable[str]) -> None:
    for text in items:
        doc.add_paragraph(text, style="List Bullet")


def add_numbered(doc: Document, items: Iterable[str]) -> None:
    for text in items:
        doc.add_paragraph(text, style="List Number")


def add_table(doc: Document, headers: list[str], rows: Iterable[Iterable[str]], widths=None) -> None:
    rows = [list(map(str, row)) for row in rows]
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    header = table.rows[0]
    repeat_table_header(header)
    for i, label in enumerate(headers):
        cell = header.cells[i]
        cell.text = str(label)
        set_cell_shading(cell, GREEN)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        for p in cell.paragraphs:
            p.paragraph_format.space_after = Pt(1)
            for run in p.runs:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(8)
    for row_data in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row_data):
            cells[i].text = str(value)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            set_cell_margins(cells[i])
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for run in p.runs:
                    run.font.size = Pt(7.5)
                    run.font.color.rgb = RGBColor.from_string(DARK)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def add_caption(doc: Document, label: str, title: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(f"{label}. {title}")
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor.from_string(GREY)


def add_figure(doc: Document, path: Path, label: str, caption: str, width=6.25) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_together = True
    p.add_run().add_picture(str(path), width=Inches(width))
    add_caption(doc, label, caption)


def draw_flow(name: str, title: str, boxes: list[str], subtitle: str = "") -> Path:
    path = ASSETS / f"{name}.png"
    count = len(boxes)
    fig, ax = plt.subplots(figsize=(max(9, count * 2.35), 2.7), dpi=190)
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, count)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.94, title, transform=ax.transAxes, ha="center", va="top",
            fontsize=14, fontweight="bold", color=f"#{DARK}")
    if subtitle:
        ax.text(0.5, 0.80, subtitle, transform=ax.transAxes, ha="center", va="top",
                fontsize=8.5, color=f"#{GREY}")
    for i, label in enumerate(boxes):
        x = i + 0.08
        patch = plt.Rectangle((x, 0.27), 0.82, 0.35, facecolor=f"#{PALE}",
                              edgecolor=f"#{GREEN}", linewidth=1.5, joinstyle="round")
        ax.add_patch(patch)
        ax.text(x + 0.41, 0.445, textwrap.fill(label, 19), ha="center", va="center",
                fontsize=8.5, color=f"#{DARK}", fontweight="semibold")
        if i < count - 1:
            ax.annotate("", xy=(x + 1.02, 0.445), xytext=(x + 0.84, 0.445),
                        arrowprops={"arrowstyle": "->", "color": f"#{GOLD}", "lw": 1.5})
    fig.tight_layout(pad=0.4)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def draw_er() -> Path:
    path = ASSETS / "database_er_overview.png"
    nodes = {
        "users": (0, 4), "farms": (1.5, 4), "soil_records": (3.1, 5.2),
        "crop_recommendations": (3.1, 4.3), "crop_cycles": (3.1, 3.4),
        "crop_stages": (4.7, 3.9), "weather_records": (3.1, 2.4),
        "advisories": (4.8, 2.7), "notifications": (1.5, 2.4),
        "farm_activities": (6.4, 3.0), "disease_reports": (4.8, 1.5),
        "disease_predictions": (6.4, 1.5), "fertilizer_recommendations": (4.8, 0.5),
        "farm_expenses": (6.4, 0.5), "sales": (8, 0.5),
        "market_prices": (8, 4.9), "market_forecasts": (9.7, 4.9),
        "mandis": (8, 5.8), "resources": (9.7, 3.1),
        "resource_prices": (11.3, 3.1), "what_if_runs": (8, 2.3),
        "risk_snapshots": (9.7, 2.0), "recommendation_feedback": (1.5, 0.9),
    }
    edges = [
        ("users", "farms"), ("users", "notifications"), ("users", "what_if_runs"),
        ("users", "recommendation_feedback"), ("farms", "soil_records"),
        ("farms", "crop_recommendations"), ("farms", "crop_cycles"),
        ("farms", "weather_records"), ("farms", "advisories"),
        ("farms", "notifications"), ("farms", "farm_activities"),
        ("farms", "disease_reports"), ("farms", "fertilizer_recommendations"),
        ("farms", "farm_expenses"), ("farms", "sales"), ("farms", "what_if_runs"),
        ("farms", "risk_snapshots"), ("crop_cycles", "crop_stages"),
        ("crop_cycles", "advisories"), ("crop_cycles", "farm_activities"),
        ("crop_cycles", "disease_reports"), ("crop_cycles", "farm_expenses"),
        ("crop_cycles", "sales"), ("advisories", "farm_activities"),
        ("disease_reports", "disease_predictions"), ("resources", "resource_prices"),
    ]
    fig, ax = plt.subplots(figsize=(13, 6.6), dpi=180)
    ax.set_facecolor("white")
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    nx.draw_networkx_edges(graph, nodes, ax=ax, arrows=True, arrowsize=10,
                           width=0.85, edge_color=f"#{GOLD}", connectionstyle="arc3,rad=0.035",
                           min_source_margin=15, min_target_margin=17)
    nx.draw_networkx_nodes(graph, nodes, ax=ax, node_size=2050,
                           node_color=f"#{PALE}", edgecolors=f"#{GREEN}", linewidths=1.2)
    nx.draw_networkx_labels(graph, nodes, ax=ax, font_size=6.1, font_weight="bold",
                            font_color=f"#{DARK}", font_family="DejaVu Sans")
    ax.set_title("SQLite schema relationships (all 23 application tables)", fontsize=14,
                 color=f"#{DARK}", pad=14, fontweight="bold")
    ax.text(0.5, -0.04, "Arrows indicate declared foreign-key direction. Standalone market entities are not linked by a declared FK.",
            transform=ax.transAxes, ha="center", fontsize=8, color=f"#{GREY}")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def build_diagrams() -> dict[str, Path]:
    return {
        "architecture": draw_flow("system_architecture", "AgriWise AI: implemented component path",
                                  ["Browser / Jinja UI", "Flask routes + session / CSRF", "Domain services",
                                   "SQLite + local model artifacts", "Weather / geocoding / conditional market APIs"],
                                  "External integrations are conditional; market live-data success is unverified."),
        "dataflow": draw_flow("overall_data_flow", "Representative farm decision-support data flow",
                              ["Farmer inputs + farm records", "Validation + state assembly", "Model / rules / providers",
                               "Explanation + persisted result", "Dashboard / plans / reports"]),
        "crop": draw_flow("crop_recommendation_workflow", "Crop recommendation workflow",
                          ["7 numeric inputs", "Validate feature bounds", "Random Forest artifact inference",
                           "Candidate / explanation", "Store and render result"],
                          "Artifact metrics are benchmark results; recommendation is not field-validated advice."),
        "problem_report": draw_flow("problem_report_workflow", "Problem report and reference-photo workflow",
                                    ["Farmer symptoms + optional photo", "Validate and privately store", "Rule-based inspection guidance",
                                     "Store symptoms and photo reference", "Expert review for confirmation"],
                                    "The saved photo is reference material only; it is not sent to an image model."),
        "training": draw_flow("ml_training_pipeline", "Crop classifier training and evaluation path",
                              ["2,200-row CSV", "Clean + stratified 80/20 split", "4 candidate classifiers + training-fold CV",
                               "Choose by held-out macro-F1", "Save model / metrics / confusion matrix"],
                              "The held-out split is used for winner selection; it is not an untouched final test."),
        "method": draw_flow("research_methodology", "Evidence-grounded project research methodology",
                            ["Inspect source + artifacts", "Define verified claims", "Run software tests / record evidence",
                             "Separate limitations", "Plan external validation"]),
        "testing": draw_flow("software_testing_workflow", "Software test workflow and evidence boundary",
                             ["Pytest cases", "Controlled fixtures / temp DBs", "Route + service assertions",
                              "164 passed in current run", "No proof of field efficacy or live provider uptime"]),
        "i18n": draw_flow("multilingual_translation_flow", "Translation resource lookup flow",
                          ["Language selector", "Validated en / mr / hi session", "UTF-8 JSON key lookup",
                           "English fallback", "Rendered template; model IDs unchanged"]),
        "er": draw_er(),
    }


def section(doc, title: str, paragraphs: list[str] | None = None, level=1,
            bullets: list[str] | None = None):
    doc.add_heading(title, level=level)
    if paragraphs:
        add_paragraphs(doc, paragraphs)
    if bullets:
        add_bullets(doc, bullets)


REFERENCES = [
    ("[1]", "S. P. Mohanty, D. P. Hughes, and M. Salathé, “Using Deep Learning for Image-Based Plant Disease Detection,” Frontiers in Plant Science, vol. 7, art. 1419, 2016, doi: 10.3389/fpls.2016.01419."),
    ("[2]", "D. P. Hughes and M. Salathé, “An open access repository of images on plant health to enable the development of mobile disease diagnostics,” arXiv:1511.08060 [cs.CY], 2015. [Online]. Available: https://arxiv.org/abs/1511.08060"),
    ("[3]", "G. Chauhan and A. Chaudhary, “Crop Recommendation System using Machine Learning Algorithms,” in 2021 10th International Conference on System Modeling & Advancement in Research Trends (SMART), 2021, pp. 109–112, doi: 10.1109/SMART52563.2021.9676210."),
    ("[4]", "J. M. McKinion and H. E. Lemmon, “Expert systems for agriculture,” Computers and Electronics in Agriculture, vol. 1, no. 1, pp. 31–40, 1985, doi: 10.1016/0168-1699(85)90004-3."),
    ("[5]", "Open-Meteo, “Weather Forecast API,” official documentation, accessed 15 Oct. 2026. [Online]. Available: https://open-meteo.com/en/docs"),
    ("[6]", "Food and Agriculture Organization of the United Nations, “e-Agriculture,” accessed 15 Oct. 2026. [Online]. Available: https://www.fao.org/e-agriculture/"),
    ("[7]", "World Bank, World Development Indicators, “Agriculture, forestry, and fishing, value added (% of GDP),” indicator NV.AGR.TOTL.ZS, accessed 15 Oct. 2026. [Online]. Available: https://data.worldbank.org/indicator/NV.AGR.TOTL.ZS"),
    ("[8]", "World Wide Web Consortium (W3C), Web Content Accessibility Guidelines (WCAG) 2.2, W3C Recommendation, 5 Oct. 2023, Success Criterion 3.1.1. [Online]. Available: https://www.w3.org/TR/WCAG22/#language-of-page"),
    ("[9]", "S. I. Ertaza and S. K. A. Hossain, “Smart Crop Recommendation System Using Machine Learning and Explainable AI,” in 2024 27th International Conference on Computer and Information Technology (ICCIT), 2024, doi: 10.1109/ICCiT64611.2024.11021774. Abstract-level evidence accessed."),
    ("[10]", "J. Sexton, “Development of an online weather and irrigation forecast decision support tool using an action learning process,” in MODSIM2023, 25th International Congress on Modelling and Simulation, 2023, doi: 10.36334/modsim.2023.sexton."),
    ("[11]", "L. Madaan, A. Sharma, P. Khandelwal, S. Goel, P. Singla, and A. Seth, “Price forecasting & anomaly detection for agricultural commodities in India,” in Proceedings of the 2nd ACM SIGCAS Conference on Computing and Sustainable Societies (COMPASS ’19), 2019, pp. 52–64, doi: 10.1145/3314344.3332488. Abstract-level evidence accessed."),
    ("[12]", "R. L. Manogna and A. K. Mishra, “Forecasting spot prices of agricultural commodities in India: Application of deep-learning models,” Intelligent Systems in Accounting, Finance and Management, vol. 28, no. 1, pp. 72–83, 2021, doi: 10.1002/isaf.1487. Deposited-abstract evidence accessed."),
    ("[13]", "X. J. Tan, W. L. Cheor, K. S. Yeo, and W. Z. Leow, “Expert systems in oil palm precision agriculture: A decade systematic review,” Journal of King Saud University – Computer and Information Sciences, vol. 34, no. 4, pp. 1569–1594, 2022, doi: 10.1016/j.jksuci.2022.02.006. Abstract-level evidence accessed."),
    ("[14]", "P. Rajkhowa and M. Qaim, “Personalized digital extension services and agricultural performance: Evidence from smallholder farmers in India,” PLOS ONE, vol. 16, no. 10, e0259319, 2021, doi: 10.1371/journal.pone.0259319."),
    ("[15]", "Pallets Projects, Flask Documentation, “Application Factories” and “The Request Context.” [Online]. Available: https://flask.palletsprojects.com/en/stable/patterns/appfactories/"),
    ("[16]", "scikit-learn developers, “Model evaluation: quantifying the quality of predictions,” official documentation. [Online]. Available: https://scikit-learn.org/stable/modules/model_evaluation.html"),
    ("[17]", "SQLite Consortium, “SQLite Foreign Key Support,” official documentation. [Online]. Available: https://www.sqlite.org/foreignkeys.html"),
]


DOSSIER = [
    ("Executive summary", [
        "AgriWise AI is a Flask/Jinja and SQLite software prototype that brings farm records, crop classification, weather-aware workflows, rule-based advisories, lifecycle tracking, problem reporting, and financial/market pages into one application. Its purpose is decision support and record organization, not autonomous agronomy.",
        "Repository evidence establishes that the crop classifier is trained on a balanced 2,200-row, 22-label CSV with seven numeric features and that the checked-in metrics artifact reports Random Forest held-out accuracy and macro-F1 of 0.9955. The source provider, license, geography, and collection period are not established. The held-out split is used to select the candidate model, so these numbers are development-benchmark evidence rather than independent field accuracy.",
        "Problem Report stores farmer-entered symptoms and an optional private reference photo. Other outputs are a mixture of crop classification, deterministic rules, statistical calculations, provider data, and farmer records.",
        "The full project test run recorded on 15 October 2026 completed with 164 passed, one Windows joblib warning, and zero failures. That verifies covered software behavior only. The project has not established improved yields, farmer outcomes, operational live market history, or field efficacy."
    ]),
    ("Problem statement and motivation", [
        "Agricultural decisions are coupled: soil and climate conditions influence crop choice, weather changes the timing of operations, crop stage shapes monitoring needs, and farmers need a durable record of what was planned and completed. Disconnected applications can force users to repeat data entry and make it difficult to trace why a suggestion appeared.",
        "AgriWise AI addresses this information-coordination problem for a prototype user workflow. It stores a farm profile and soil readings, exposes model and rule outputs, tracks an active crop cycle and activities, and presents supporting weather and market pages. It does not measure whether a recommendation improves a farm outcome. The distinction is important because an integrated interface is not itself evidence of agronomic validity [6], [7].",
        "The intended user is a farmer or demonstrator who can enter or obtain soil and farm data and interpret decision-support outputs. Deployment with real users requires local agronomic review, user research, consent and privacy practices, accessibility evaluation, and field validation."
    ]),
    ("Research objectives and questions", [
        "Completed engineering objective: implement a web application that connects farmer/farm records with crop classification, lifecycle workflows, rules, and selected external data adapters. Evidence is in routes, services, templates, database schema and tests.",
        "Completed engineering objective: preserve a farmer-entered Problem Report workflow with optional private reference-photo storage. Photos are not classified and reports are not diagnoses.",
        "Partially completed objective: provide reusable English/Marathi/Hindi translation infrastructure and translated screens. Locale resources, selection persistence and fallback exist, but complete page-by-page and dynamic-message coverage is not certified.",
        "Research questions for an empirical follow-up are: (RQ1) How does crop classification generalize under geographically and temporally independent evaluation? (RQ2) Does coordinated lifecycle/weather/task display reduce missed operations or improve decision traceability? These questions are not answered by the available benchmark or software tests."
    ]),
    ("Literature review", [
        "Crop recommendation using soil and weather-related inputs is represented in prior work; Chauhan and Chaudhary describe Random Forest and Decision Tree approaches [3]. Ertaza and Hossain report soil/climate features and SHAP/LIME explanations in an abstract-level record [9]. Neither paper validates AgriWise's classifier.",
        "Weather-and-irrigation decision support is represented by Sexton's Opticane work, which discusses forecast scale and local-climate fit [10]. India-specific price forecasting examples include onion/potato market forecasting and anomaly detection [11] and daily NCDEX commodity price comparisons among ARIMA, TDNN and LSTM models [12]. These are research precedents, not evidence that AgriWise's provider or price forecast is operational.",
        "Tan et al. review agricultural expert systems across crop, water and soil management categories [13]. Rajkhowa and Qaim report associations between personalized digital extension and agricultural performance for Indian smallholders, using matching methods to address selection concerns [14]. This does not establish causal impact or local-language performance for AgriWise.",
        "Machine-learning evaluation metrics are conditional on sampling and protocol. Accuracy and macro-F1 are summaries; they do not alone establish calibration, distributional robustness, utility or causal impact [16]. FAO and the World Bank provide digital-agriculture and economic context [6], [7], not validation of this prototype."
    ]),
    ("Literature comparison matrix", [
        "The table summarizes the role of selected publications and documentation. Research findings are attributed to those works; AgriWise-specific statements are separately identified as repository evidence."
    ]),
    ("Existing-system analysis and research gap", [
        "Existing research addresses focused tasks such as image classification, prediction, sensing, and automation. AgriWise's engineering contribution is an integrated prototype workflow: user-owned farm records connect to a crop recommendation page, lifecycle planning, deterministic rules, Problem Report, and supporting data pages.",
        "The defensible gap for this project is not that earlier work lacks these components. Rather, the prototype demonstrates how such workflows are wired together while making evidence boundaries visible. Whether that integration is novel, more usable, more accurate, or beneficial has not been established by comparative research.",
        "Unresolved research gaps include external validation of the crop classifier, calibrated uncertainty, farmer-centered usability and accessibility, a measured effect on decision quality, and successful live market-history acquisition."
    ]),
    ("Proposed contributions and evidence", [
        "Contribution A — implemented software integration: Flask routes and services coordinate farm inputs, model inference, rules, records, and browser pages. Evidence: source inspection and the recorded automated test suite. Not proven: production scalability or improved agricultural outcomes.",
        "Contribution B — reference-only symptom reporting: Problem Report stores farmer-reported symptoms and optional private photos without image inference or a diagnosis. Evidence: route/service implementation and regression tests.",
        "Contribution C — reusable localization: UTF-8 JSON resources, supported language validation, session persistence, and English fallback. Evidence: service and selected rendered-route tests. Not proven: total translation coverage or native-speaker acceptance.",
        "Contribution D — measured crop model benchmark: stored comparison of four classifiers on a balanced CSV. Evidence: model_metrics.json and training procedure. Not proven: independent generalization because the held-out set selects the winner and dataset provenance is unresolved."
    ]),
    ("Dataset analysis", [
        "The primary recommendation dataset is data/Crop_recommendation.csv. It contains 2,200 rows: 100 for each of 22 labels. Predictors are N, P, K, temperature, humidity, ph, and rainfall; label is the crop class. recommendationData.csv is byte-identical in the audited checkout and must not be counted as extra evidence. Repository evidence does not establish the original author/provider, license, collection protocol, period, units documentation, or geography.",
        "The class balance is exact in the saved artifact. A stratified 80/20 split with random_state=42 yields 1,760 training and 440 held-out records; five-fold stratified cross-validation is applied to the training partition. Invalid and exact duplicate rows are filtered by the training utility.",
        "Problem Report records farmer-entered symptoms and may retain a private reference photo. Crop recommendation remains on the original tabular dataset and predicts crop labels.",
        "Validity risks include source/near-duplicate leakage, non-independent rows, unknown geography and measurement units, label construction, selection on the held-out test set, and differences between benchmark features and actual farm constraints. An external, grouped geographic/temporal split and prospective field data are required."
    ]),
    ("Methodology", [
        "The software-development methodology is evidence-first source inspection followed by test execution and bounded claims. The crop training path loads and validates tabular data, coerces numerical features, filters invalid records, splits stratified data, evaluates candidate classifiers, compares held-out macro-F1, and writes artifacts. K-nearest neighbors uses a StandardScaler pipeline. Metric definitions and averaging behavior follow the scikit-learn evaluation reference [16].",
        "At application inference, the crop route validates seven input fields and calls the saved model through the crop service, then builds an explanation and persists the recommendation. Problem Report validates and privately stores optional reference photos; it does not perform image inference.",
        "The broader application composes weather adapters, deterministic rules, lifecycle calculations, user records, and conditional market analysis. Open-Meteo documents weather-model forecasts, not sensor readings [5]. These methods are not interchangeable: a rule engine is not a trained predictor; external weather is not a sensor; a price forecast is not a guaranteed offer."
    ]),
    ("Experimental results", [
        "The stored crop metrics artifact reports Random Forest as selected with accuracy 0.9955, macro precision 0.9957, macro recall 0.9955 and macro-F1 0.9955. Its training-fold five-fold CV accuracy is 0.9943 ± 0.0051. Decision Tree reports 0.9818 accuracy / 0.9817 macro-F1; KNN 0.9795 / 0.9793; Gradient Boosting 0.9886 / 0.9886.",
        "These values are artifact-reported, not regenerated in this documentation task. The model-selection procedure uses held-out macro-F1, so the held-out score is optimistic as a final unbiased estimate. It must not be described as field accuracy, regional accuracy, or expected harvest success.",
        "No current live market-data record set, market-forecast accuracy, field trial, inference-latency benchmark, coverage estimate, or user study was established. The full project test run recorded 164 passed, one environment warning, zero failures."
    ]),
    ("Discussion", [
        "The evidence demonstrates a functioning software prototype with a measurable crop benchmark and test-covered workflows. It demonstrates engineering feasibility and selected interface/service contracts. It does not establish that the crop model is suitable for Maharashtra or that users benefit.",
        "A 99.55% score on a balanced, provenance-limited random split can coexist with poor real-world generalization. Field measurements may differ in scale, season, instrumentation, crop variety and management. Likewise, high softmax scores are not calibrated probabilities, and a closed-set image model may confidently assign an unsupported image to a known class.",
        "The integrated presentation can improve traceability if the user can see input, source and caveat. That usability proposition must be tested with farmers and agricultural experts."
    ]),
    ("Threats to validity", [
        "Construct validity: benchmark crop labels may encode a synthetic/curated recommendation task rather than field outcomes.",
        "Internal validity: selection on the held-out test set and potential source-level duplication may bias reported crop performance.",
        "External validity: no independent location, season, cultivar, device, field, or farmer evaluation exists. API reliability and market histories vary with network, key and provider conditions.",
        "Reproducibility: training code exists, but original dataset provenance is unresolved; model artifacts and recorded metrics were not retrained in the latest audit. The full test suite's module-level import may initialize the configured database, so the recorded test run cannot be called database-side-effect-free.",
        "Operational validity: browser visual auditing, accessibility, load testing, penetration testing, deployment smoke testing and user studies were not performed in the audit represented here."
    ]),
    ("Future research", [
        "Priority 1: identify and license a traceable agronomic dataset covering the intended crop classes and define feature units/collection contexts before any retraining.",
        "Priority 2: use nested model selection or a sealed independent test set; split by source, site, time or farm where identifiers permit; report confidence intervals and per-class metrics.",
        "Priority 4: conduct farmer-centered usability and accessibility studies with consent, a prespecified protocol, local-language review and appropriate ethics approval.",
        "Priority 5: verify external API contracts with bounded live tests; monitor freshness, provenance and failure behavior; add independent audit logs and operational metrics without exposing secrets."
    ]),
]


LITERATURE_MATRIX = [
    ["Mohanty et al. (2016) [1]", "Plant disease; CNNs on 54,306 PlantVillage images / 38 classes", "Reported 99.35% best dataset accuracy; just above 31% on different-condition images", "Demonstrates domain sensitivity in that experiment; not AgriWise performance"],
    ["Hughes & Salathé (2015) [2]", "Open plant-health image repository", "Describes over 50,000 curated images and diagnostic research motivation", "Dataset context only; does not identify AgriWise checkpoint provenance"],
    ["Chauhan & Chaudhary (2021) [3]", "Crop recommendation; soil/weather inputs; RF/DT", "Conference abstract/DOI metadata checked; detailed evaluation not verified", "Method precedent; no same-data comparison"],
    ["McKinion & Lemmon (1985) [4]", "Agricultural expert systems", "Title and bibliographic record verified; full text not reviewed", "Historical research anchor; no specific findings attributed"],
    ["Ertaza & Hossain (2024) [9]", "Crop recommendation; soil/climate features; SHAP/LIME", "Abstract-level evidence; no verified evaluation details in this audit", "Feature explanations differ from calibrated uncertainty; no AgriWise comparison"],
    ["Sexton (2023) [10]", "Weather + irrigation decision support (Opticane)", "Conference abstract describes sugarcane tool and local forecast-scale concern", "Supports design precedent only; not transferable outcome evidence"],
    ["Madaan et al. (2019) [11]", "India onion/potato prices and anomaly detection", "Abstract describes wholesale arrivals and retail prices; anomaly events include hoarding", "Related Indian market research; not evidence of AgriWise live data"],
    ["Manogna & Mishra (2021) [12]", "Indian NCDEX commodity price forecasting", "Deposited abstract compares ARIMA, TDNN and LSTM on five commodities", "Abstract reports directional-price performance; not an AgriWise comparison"],
    ["Tan et al. (2022) [13]", "Oil-palm precision-agriculture expert systems", "Abstract reports review of 108 papers from 2011–2020; crop/water/soil categories", "Review context; does not validate AgriWise rules"],
    ["Rajkhowa & Qaim (2021) [14]", "Personalized digital extension in India", "Full PLOS ONE article/abstract; association analysis with propensity-score matching", "Relevant user-context evidence; not proof of causality or AgriWise impact"],
]


MANUAL = [
    ("Product overview and boundaries", [
        "AgriWise AI is a local-first Flask application with a server-rendered Jinja interface and SQLite persistence. It is intended to organize farm information and present crop-classifier outputs, lifecycle estimates, weather context, configurable rule-based advice, and records. It is a prototype; it is not a certified agronomic, diagnostic, financial, or emergency service.",
        "Crop recommendation is a supervised tabular classifier. Lifecycle and expert-system features use configured profiles and rules. Problem Report stores farmer-entered symptoms and optional reference photos. Weather and geocoding depend on external providers. Market retrieval is conditional and live usable responses remain unverified."
    ]),
    ("Technology stack", [
        "Verified runtime dependencies include Python 3.12.4 in the project environment, Flask 3.0.3, SQLite, pandas 2.2.2, NumPy 2.0.2, scikit-learn 1.5.1, joblib 1.4.2, requests 2.32.3, Pillow 11.3.0, and python-dotenv. HTML is rendered with Jinja; Bootstrap and icon/chart/map assets may be loaded from CDNs. Render configuration uses Gunicorn.",
        "The dependency manifest is the authoritative installation source; the exact runtime inventory may vary by environment. The project `.venv` is not required to be committed or copied to production."
    ]),
    ("Architecture and request flow", [
        "The application factory in app.py configures Flask, middleware-like request hooks, CSRF behavior, session settings and routes. Flask's factory pattern allows differently configured instances for tests and applications [9]. Routes perform request validation and call domain services. Services contain classification, lifecycle, weather, market, risk, rules, reporting, resources and finance logic. Templates display results. SQLite stores user and operational records. Model artifacts are loaded from local paths. External calls are made through provider adapters.",
        "The database has 23 tables. Core declared relationships include users→farms; farms→soil, recommendations, cycles, weather, advisories, notifications, activities, problem reports, fertilizer records, expenses, sales, what-if runs and risk snapshots; cycles→stages, activities, advisories, problem reports, expenses and sales; resources→resource prices. Market prices, forecasts and mandis are standalone in the declared FK graph."
    ]),
    ("Crop recommendation implementation", [
        "The route accepts seven numeric features: N, P, K, temperature, humidity, pH and rainfall. It validates input, invokes services/crop_service.py to load the saved ml/crop_model.pkl artifact, generates a class suggestion and explanation, and persists the result and submitted context. ml/train_model.py calls the active candidate evaluation path in services/crop_ml_service.py.",
        "The dataset contains 2,200 balanced rows and 22 labels. The artifact's best candidate is Random Forest; recorded held-out accuracy and macro-F1 are both 0.9955. Candidate selection itself uses that held-out score, so these values are development results. No regional holdout or field outcome is present. Model probabilities are not calibrated field confidence.",
        "Do not run the training command casually: it writes model, metric and confusion-matrix artifacts. Preserve a copy and use explicit temporary output paths for experiments."
    ]),
    ("Lifecycle, activities and rules", [
        "Crop cycles, stages and activities are persisted with farm ownership and status. Lifecycle dates/stages are computed from configured crop profiles and calendar rules, not observed plant phenology. Activity tasks may be suggested or manually entered; completion is a farmer-confirmed event.",
        "The expert system uses deterministic IF/THEN production rules over a working set of farm, soil, weather, crop-stage and confirmed-action facts. Conflict resolution and safety priorities are code logic. It is not a trained AI model and its rule base requires local agricultural validation."
    ]),
    ("Weather and geocoding", [
        "Weather calls Open-Meteo using farm coordinates, an 8-second request timeout and a 30-minute in-memory cache; a prior cached result can be surfaced as stale when refresh fails. The provider documentation describes forecast time series assembled from weather-model sources; this output is not an on-farm sensor [5]. A prior successful request is historical evidence only, not a current uptime guarantee. Weather-aware irrigation research likewise emphasizes local forecast context [10].",
        "Reverse geocoding attempts Nominatim with a five-second timeout and a 24-hour in-memory cache, then BigDataCloud, then coordinate text. Both providers receive coordinates. Network failure or rate limits can reduce location detail."
    ]),
    ("Market, sales and finance", [
        "The official market adapter targets data.gov.in/Agmarknet resource 9ef84268-d588-465a-a308-a864a43d0070 and reads DATA_GOV_IN_API_KEY from the environment. It validates records, uses bounded retries/cooldowns/cache and requests at most ten records per query. Historical diagnostics do not establish a current successful response, key acceptance or usable price history.",
        "Market forecast code requires at least 20 distinct daily observations from one market/variety series. It uses a simple time regression and a chronological holdout, bounds point movement, and labels its range as heuristic rather than a confidence interval. No live usable series or measured forecast error is established.",
        "Profit and expense screens combine estimates and user-entered transactions. They are not yield guarantees, verified offers, or investment advice."
    ]),
    ("Fertilizer, resources and safe agronomy", [
        "Fertilizer and resource services present configured reference logic, nutrient status and directory information. Their existence does not prove that underlying rates, products, local availability, or efficacy are validated. Community-listed resource entries may be stale or inaccurate.",
        "Any fertilizer/pesticide dosage requires crop-, stage-, soil-, product-label- and region-specific evidence and qualified local review."
    ]),
    ("Multilingual support", [
        "English is the default/fallback; Marathi and Hindi are supported by UTF-8 JSON resources in locales/en.json, mr.json and hi.json. Jinja translation helpers resolve dotted keys and missing strings fall back to English. The language POST route validates codes and stores the choice in the Flask session; its return path is constrained to a local destination.",
        "Translations are applied to selected templates, not guaranteed throughout every static phrase or dynamic advisory. Crop/model identifiers and user-entered text remain machine-readable/original. Rendered page tests cover selected screens only; this should not be described as complete app-wide localization. WCAG's page-language criterion supports exposing the predominant language to assistive technologies; it does not assess translation accuracy [8]."
    ]),
    ("Database and persistence", [
        "SQLite is initialized through db.py with foreign-key enforcement, table creation, indexes, and compatibility migrations. Operational records are associated with users/farms where the schema declares ownership. SQLite foreign keys enforce declared parent-child relationships only when enabled for each connection [17]. SQLite is convenient for a single-instance educational prototype but writes and file locking require care under concurrent production traffic. Render's blueprint specifies one instance/worker and persistent disk.",
        "Use a backed-up copy for schema experiments. The test suite imports app.py, which constructs a module-level application and initializes the configured database; the audited full test run did not establish that the configured database was untouched. Isolate AGRIWISE_DATA_DIR before Python imports for future test execution."
    ]),
    ("Security and privacy", [
        "Source inspection finds Werkzeug password hashing, user/session auth tokens, session rotation on password change, HttpOnly/SameSite cookie settings, Secure cookies for production when configured, a session CSRF token checked with constant-time comparison, selected security headers, parameterized SQLite calls in inspected paths, and authenticated private image access. These are observed controls, not security certification.",
        "Uploads are allowlisted and decoded, size/pixel limited, named with a secure filename plus UUID, and served through an ownership-checked route. API keys are environment variables and .env is ignored; never include secret values in deliverables. A comprehensive penetration test, dependency audit, rate-limit review and full access-control proof were not performed."
    ]),
    ("Installation and local run (Windows)", [
        "From the repository root in PowerShell, create/use the project Python 3.12 environment, install the runtime requirements, and start the Flask application. Commands below match repository paths; consult README.md and deployment docs if manifests change. This project also constructs a module-level app at import time."
    ]),
    ("Testing and verification record", [
        "Recorded result on 2026-10-15: 164 passed, one joblib Windows physical-core discovery warning, zero failures.",
        "Tests cover routes, core workflow, crop model contracts, problem-report photo storage, lifecycle, rules, weather/market parsing with mocks, security regressions and selected localization. They do not measure field agronomic performance, live provider uptime, performance under load, accessibility, or all translation strings.",
        "The full suite imported app.py and triggered module-level app/database initialization. Because no pre-run database metadata or contents were collected, the run cannot be described as guaranteed not to touch existing local database state. The generator does not execute application tests."
    ]),
    ("Deployment and troubleshooting", [
        "render.yaml specifies a paid Starter web instance, one instance, Gunicorn one worker/four threads, a 120-second timeout, /healthz, a 1 GB persistent disk mounted at /var/data, production environment settings, generated secret and optional market API key. This is configuration only; no deployed service or live deployment check was verified.",
        "Vercel documentation describes ephemeral /tmp storage; SQLite and uploads in an ephemeral or multi-instance environment can be lost or inconsistent. The app's in-memory provider cache/lock is process-local. Do not claim serverless persistence without a durable shared database/storage design.",
        "If crop prediction fails, verify the saved artifact path and seven numeric inputs. For Problem Report, confirm that photos are treated as private reference material only. For weather, inspect coordinates/network and whether a cached result is stale. For market, verify secret configuration privately, provider response status and record count. Never print or paste an API key."
    ]),
    ("Developer handover and priorities", [
        "Key files: app.py (factory, routes, request/session flow); db.py (SQLite schema and migrations); services/crop_service.py and crop_ml_service.py (prediction/training paths); services/disease_service.py (Problem Report guidance); services/weather_service.py, official_market_service.py, decision_orchestrator.py, expert_system.py, lifecycle_service.py and i18n_service.py; locales/*.json; templates/*.html; tests/*.py; render.yaml.",
        "Priority sequence: establish dataset provenance/license; make model selection unbiased and evaluate geographically; complete localization and native review; isolate test databases; verify APIs and deployment; then conduct accessibility, security, load and farmer field studies."
    ]),
]


TECHNOLOGY_ROWS = [
    ["Web/backend", "Python 3.12.4; Flask 3.0.3; Jinja templates", "Current environment/requirements", "Source exists; route tests pass"],
    ["Database", "SQLite via sqlite3; 23 tables", "db.py DDL", "Local persistence; production concurrency constrained"],
    ["Crop ML", "pandas, NumPy, scikit-learn, joblib; Random Forest artifact", "ml/ and services/", "Stored benchmark metrics; no field validation"],
    ["Weather", "Open-Meteo HTTP adapter, requests", "services/weather_service.py", "Historical single live observation; mocked tests"],
    ["Market", "data.gov.in adapter; optional API key", "services/official_market_service.py", "Live usable records unverified"],
    ["Deployment", "Gunicorn; Render blueprint", "render.yaml", "Configuration inspected, not deployed"],
]


SETUP_COMMANDS = [
    "py -3.12 -m venv .venv",
    ".\\.venv\\Scripts\\Activate.ps1",
    "python -m pip install --upgrade pip",
    "python -m pip install -r requirements.txt",
    "Copy-Item .env.example .env  # optional local provider settings; do not commit secrets",
    "python app.py",
    "Start-Process http://127.0.0.1:5000/",
]


IEEE_SECTIONS = [
    ("I. INTRODUCTION", [
        "Farm decision support often spans data entry, crop choice, crop-stage tracking, weather context and operational records. AgriWise AI is a Flask-based prototype designed to connect these workflows while presenting distinct ML, rule-based and provider-derived outputs. Digital agriculture is a broad and context-sensitive area; ICT for sustainable agriculture is discussed by FAO, while the World Bank indicator supplies economic context rather than an impact measure [6], [7].",
        "This paper reports the implementation and evidence boundaries of the prototype. It does not claim a novel classifier, field efficacy or farmer outcome improvement. Its concrete engineering contribution is an integrated workflow combining supervised crop recommendation, deterministic rules, external weather/market adapters and farm records."
    ]),
    ("II. RELATED WORK", [
        "Crop recommendation using soil and weather-related inputs has been studied with machine-learning algorithms [3], while agricultural expert systems have a documented history [4].",
        "Explainable crop recommendation with SHAP/LIME features is described in an abstract-level publication [9]. Weather-and-irrigation decision support [10], Indian commodity price forecasting [11], [12], and agricultural expert-system reviews [13] provide further component-level context. A personalized extension study in India reports associations, not direct evidence about this prototype [14].",
        "Evaluation must be interpreted against sampling, target definition and split design. Standard metrics such as accuracy, precision, recall and F1 are summaries of a defined sample; they cannot by themselves demonstrate calibration, regional generalization or user utility [16]."
    ]),
    ("III. RESEARCH GAP AND CONTRIBUTIONS", [
        "The study addresses an engineering question: how can a web prototype connect crop classification, farm records, lifecycle tasks and contextual decision support while preserving distinct evidence and safety boundaries? The repository demonstrates an implementation of this integration. It does not establish scientific novelty or superiority over a comparator.",
        "Contributions are (1) a source-auditable, multi-workflow implementation; (2) a crop-classifier benchmark reporting its selection caveat; (3) farmer-entered symptom reporting with optional private reference-photo storage; and (4) a reusable multilingual resource layer with selected-page testing. The last contribution is partial because not every page/dynamic message is verified in all languages."
    ]),
    ("IV. SYSTEM AND METHODS", [
        "The application uses Flask routes and Jinja templates, domain services, SQLite and local artifacts [15], [17]. Crop recommendation consumes seven numeric fields (N, P, K, temperature, humidity, pH and rainfall) and calls the saved Random Forest model. Explanatory text and records are generated/stored in the application. Weather calls the Open-Meteo forecast adapter [5]; market data uses a bounded official-data adapter but live usable records are unverified.",
        "The crop training utility reads a balanced 2,200-row CSV with 22 labels, applies data cleaning, uses a stratified 80/20 split (random_state=42), compares four classifiers, computes five-fold stratified accuracy on the training portion, and selects by held-out macro-F1. This split is consequently part of model selection, not an independent untouched test.",
    ]),
    ("V. DATASET AND EXPERIMENTAL SETUP", [
        "The crop CSV has 2,200 rows, 22 balanced classes and seven numeric features. The duplicate recommendationData.csv has the same SHA-256 in the audited checkout and is not an independent dataset. Dataset publisher, license, collection geography, period, units and collection protocol are not established. A random row split cannot exclude source-level leakage or prove geographic/temporal independence.",
        "The checked-in metrics artifact reports 1,760 training and 440 test examples. Candidate values are: Decision Tree 98.18% accuracy, 98.17% macro-F1; Random Forest 99.55%, 99.55%; KNN 97.95%, 97.93%; Gradient Boosting 98.86%, 98.86%. Random Forest five-fold training-split CV accuracy is 99.43% ± 0.51%. Values are recorded artifacts and were not reproduced in this documentation run.",
        "No live market forecast error, field trial or usability study is available. The current project test suite completed with 164 passes and one environment warning; software tests do not measure agronomic efficacy. WCAG's page-language guidance is relevant to assistive technology but does not verify translation quality [8]."
    ]),
    ("VI. RESULTS AND DISCUSSION", [
        "The tabular benchmark shows strong separability under its recorded random-split protocol. Because the held-out score selects the winning candidate, an independent test set is needed to estimate final performance. Unknown dataset provenance also prevents confident claims about target-population fit. The result should be treated as a software/model-development benchmark only.",
        "Problem Report stores farmer-described symptoms and optional reference photos.",
        "The application test record supports covered route/service behavior. The market adapter's existence does not prove API success; the current usable-data state remains unverified. Therefore the paper reports an implemented prototype rather than a validated farm decision system."
    ]),
    ("VII. LIMITATIONS AND FUTURE WORK", [
        "Threats include undocumented dataset provenance, selection bias in the crop test protocol, possible source-level data dependence, no external regional data, no calibrated confidence, unverified market data, network dependency, and no farmer-outcome study. Multilingual rendering is tested on selected screens but not certified across the whole application; page language metadata supports assistive technology but does not assure translation quality [8].",
        "Future work should establish licensed representative crop data, use nested or sealed geographic/time holdouts, conduct local-language review, and perform a prespecified farmer study with ethics and consent. API and deployment claims need reproducible live tests."
    ]),
    ("VIII. CONCLUSION", [
        "AgriWise AI is an integrated agricultural decision-support prototype whose source and tests show multiple connected workflows. Its crop classifier has a recorded benchmark score under a development split, but no independent field validation. Market-provider success remains unverified. The defensible conclusion is software integration feasibility and a clear research agenda—not proven agronomic impact."
    ]),
]


def add_references(doc: Document):
    doc.add_heading("References", level=1)
    for number, citation in REFERENCES:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.22)
        p.add_run(f"{number} {citation}")


VIVA_GROUPS = {
    "Project foundations": [
        ("What is AgriWise AI?", "It is a Flask/Jinja and SQLite agricultural decision-support prototype. It combines farm records, crop-classification suggestions, lifecycle tracking, rule-based guidance, weather context, and symptom reporting."),
        ("What problem does it address?", "It coordinates several farm workflows that otherwise may be disconnected: entering farm context, reviewing a crop suggestion, tracking a crop cycle, recording activities, and viewing contextual data. It has not been proven to improve yields or income."),
        ("Who are the intended users?", "Farmers and project demonstrators who can provide farm and soil information. Real-world use requires local-language, accessibility, agronomic and privacy validation."),
        ("Why did you select this project?", "It provides a concrete application of web engineering and machine learning to a significant domain, while making it possible to study how data, models, rules and user workflows interact."),
        ("What are the main objectives?", "Build connected farm workflows, expose a crop classifier, track lifecycle and activities, add contextual services, and preserve clear limitations. The system objectives are implemented to varying verification levels; research outcomes such as farmer benefit remain unproven."),
        ("What are the major modules?", "Authentication/farm profile, crop recommendation, lifecycle/activities, dashboard/plans, expert rules/advisories, weather/location, Problem Report, market/finance, resources/fertilizer, reports, and localization."),
        ("Is it an autonomous farming system?", "No. It presents decision-support information and records. It does not operate equipment, guarantee outcomes or replace a farmer or qualified agronomist."),
        ("What is outside the scope?", "Pesticide prescription, guaranteed yield/profit, national suitability, continuous sensor ingestion, and autonomous farm control."),
        ("What is the strongest evidence of completion?", "Source implementation and the recorded 164-pass automated software test run support that covered workflows execute as tested. This is not evidence of agricultural effectiveness."),
        ("What is the weakest area?", "Independent empirical validity: crop data provenance and external generalization are unresolved; market live usable data is unverified; no field/user study exists."),
    ],
    "Research and contribution": [
        ("What is the research gap?", "The project explores engineering integration of farm records, classification, lifecycle and contextual guidance with explicit boundaries. It does not claim that prior work lacks these components or that this prototype is novel without comparative evidence."),
        ("What is your contribution?", "A working, source-auditable multi-workflow software prototype, a documented crop benchmark protocol and a separated suggestion/report interaction. Contribution is engineering integration, not a newly invented learning algorithm."),
        ("How did you identify the gap?", "By reviewing relevant agricultural ML and decision-support literature and auditing the code and data. The evidence supports an integration opportunity, not a universal claim that existing systems fail."),
        ("Why is the project research-worthy?", "It raises measurable questions about independent generalization, safe model communication, translation coverage, and workflow utility. The prototype itself is a platform for those studies."),
        ("Have you proved novelty?", "No. Novelty requires systematic literature comparison and a clearly differentiated method/result. Integrating known modules is not sufficient."),
        ("Have you proved farmer benefit?", "No. There is no controlled farmer study or measured outcome comparison."),
        ("What is a threat to validity?", "A condition that could make the inference from an experiment unreliable. Here, unknown dataset provenance and selecting a model on the held-out test set threaten generalization claims."),
        ("Why not claim superiority over existing systems?", "No head-to-head evaluation with equivalent data, metrics and users was performed."),
        ("What is your hypothesis?", "A future testable hypothesis could be that a coordinated workflow improves task completion or decision traceability relative to disconnected tools. It remains a proposal until tested."),
    ],
    "Architecture and software engineering": [
        ("Why Flask?", "The project uses Flask's lightweight routing and Jinja templating to serve the prototype with a relatively direct Python stack. It is appropriate for this scale, but this choice is not a benchmarked performance claim."),
        ("What is a request-response lifecycle?", "The browser sends an HTTP request; Flask matches a route, validates inputs, invokes services, may read/write SQLite or call a provider, renders a template or JSON, and returns an HTTP response."),
        ("What is an application factory?", "A function that constructs and configures a Flask app. Here create_app supports configuration, including test setup, although app.py also constructs a module-level app."),
        ("What is a route?", "A mapping from a URL and HTTP method to a Python view function."),
        ("Why separate routes and services?", "Routes handle HTTP concerns while services hold domain operations such as model inference or weather processing. Separation improves reuse and testing, although some legacy parallel paths remain."),
        ("What does Jinja do?", "It renders HTML templates using server-side context, control structures and escaped values."),
        ("Where are static assets?", "Shared CSS, JavaScript, icons and related assets live under static/. Templates are under templates/."),
        ("How are errors handled?", "Routes validate inputs and return error pages/status codes; adapters may use stale cached results or unavailable states. Provider errors do not prove the service is down."),
        ("How would FastAPI differ?", "FastAPI emphasizes typed request/response models and asynchronous APIs. Migrating would change route and template integration; there is no evidence it is necessary for the current prototype."),
        ("What limits scalability?", "SQLite write concurrency, process-local caches/locks, model memory, single-instance deployment assumptions, and external provider rate/latency constraints."),
    ],
    "Python and web fundamentals": [
        ("GET versus POST?", "GET retrieves a representation and should not mutate state. POST submits or changes state. The application uses POST for language selection and form updates, and GET for page views."),
        ("What is an HTTP status code?", "A numeric response category: 2xx success, 3xx redirection, 4xx client/request issue, and 5xx server failure. For example, invalid submitted language returns 400."),
        ("What is a session?", "Server-side logical state associated with a browser, commonly identified by a signed cookie. This app stores user and language state in the Flask session."),
        ("What is JSON?", "A text format for structured key-value and array data, used by locale resources and selected API payloads."),
        ("What is REST?", "A style for resource-oriented HTTP interfaces that use methods and status codes consistently. Not every route in this app is a strict REST resource."),
        ("Why validate on the server?", "Browser checks can be bypassed. Server validation protects state and gives a reliable contract before database writes or model calls."),
        ("What is an environment variable?", "Configuration provided to a process at runtime, useful for secrets and deployment-specific settings without hard-coding them."),
        ("What is a dependency manifest?", "A file declaring software packages and versions required to install/run the project; here requirements files serve that purpose."),
        ("What is template escaping?", "Encoding untrusted text so it is rendered as text rather than executable HTML. It helps mitigate injection when used correctly."),
        ("What is an API timeout?", "A bound on waiting for a remote operation. The weather adapter uses an 8-second request timeout; timeout handling supports reliability but cannot guarantee provider availability."),
    ],
    "Database and SQL": [
        ("Why SQLite?", "It is simple and file-based, requiring no separate database server. It suits a local prototype, but concurrent production writes and multi-instance deployment need stronger shared persistence."),
        ("How many tables are defined?", "The current db.py creates 23 application tables, including users, farms, soil, recommendations, cycles, activities, weather, market, problem reports and finance records."),
        ("What is a primary key?", "A column or column set that uniquely identifies a row. The main entities use integer primary keys."),
        ("What is a foreign key?", "A constraint linking a child record to a parent row, helping enforce referential integrity when enabled."),
        ("What is normalization?", "Organizing relational data to reduce unwanted duplication and update anomalies. The schema separates users, farms, cycles and related records."),
        ("What is SQL injection?", "An attack where untrusted input changes query structure. Parameter binding, which is used in inspected query paths, prevents values from being parsed as SQL syntax."),
        ("What is an index?", "A data structure that can speed lookups at the cost of storage and write overhead. db.py defines indexes for common farm/activity/notification/finance queries."),
        ("What is a transaction?", "A group of database operations treated atomically. SQLite transaction behavior is used through connection context management in initialization and database code."),
        ("SQLite versus PostgreSQL?", "SQLite is embedded and file-based; PostgreSQL is a server database designed for concurrent multi-user workloads and richer operational deployment. A migration would require schema and query adaptation."),
        ("How should backups work?", "Use consistent snapshots/backups, test restore procedures, protect them like user data, and avoid copying a live DB file without accounting for journaling/WAL state."),
    ],
    "Machine-learning fundamentals": [
        ("AI versus ML versus deep learning?", "AI is the broad area of machine decision behavior; ML learns patterns from data; deep learning is ML using multi-layer neural networks. AgriWise uses a tabular crop classifier and non-ML rules."),
        ("Classification versus regression?", "Classification predicts a category, such as crop label; regression predicts a numeric value, such as a price trend."),
        ("What are features and labels?", "Features are input variables; a label is the target class. The crop model uses seven numeric features and a crop-name label."),
        ("Training, validation and test sets?", "Training data fits parameters; validation data supports choices; a final test set estimates generalization after choices are fixed. In this project, the held-out score is used for candidate selection, so it is not a pristine final test."),
        ("What is overfitting?", "Learning dataset-specific patterns that do not generalize. It can be detected using independent data or train-versus-test gaps, but current provenance limits interpretation."),
        ("What is data leakage?", "Information from outside the allowed training process influences model fitting or evaluation, inflating apparent performance."),
        ("What is cross-validation?", "Repeated train/validation folds to estimate variability. The reported crop CV uses five stratified folds on the training split."),
        ("Accuracy formula?", "Accuracy = (TP + TN) / (TP + TN + FP + FN) in binary classification, or correct predictions / all examples in multiclass classification."),
        ("Precision formula?", "Precision = TP / (TP + FP). Of predicted positives, the fraction that are correct."),
        ("Recall formula?", "Recall = TP / (TP + FN). Of actual positives, the fraction detected."),
        ("F1 formula?", "F1 = 2 × precision × recall / (precision + recall). It is the harmonic mean of precision and recall."),
        ("Macro versus weighted F1?", "Macro F1 computes F1 per class then averages equally; weighted F1 weights each class by support. The crop classes are balanced in the file, but both still summarize only the evaluation sample."),
        ("What is a confusion matrix?", "A table of true versus predicted classes showing where errors occur. The repository includes a crop-model confusion matrix artifact."),
        ("Why use a baseline?", "A baseline makes it possible to judge whether a complex model improves on a simple reference under the same data and split."),
        ("What is model drift?", "Changes over time in input distributions or target relationships that can reduce performance after deployment."),
    ],
    "Crop recommendation model": [
        ("Which dataset is used?", "data/Crop_recommendation.csv, 2,200 rows, 22 classes, 100 rows per class. Dataset origin, license, collection period and geography are unverified."),
        ("What features does it use?", "N, P, K, temperature, humidity, pH and rainfall, plus the crop label as target."),
        ("What is the split?", "A stratified 80/20 split with random_state=42: 1,760 training rows and 440 held-out rows in the recorded metrics artifact."),
        ("Which model was selected?", "The artifact names Random Forest as best, selected using held-out macro-F1."),
        ("What is the recorded score?", "Accuracy and macro-F1 are 0.9955 in the saved metrics. It is a development benchmark, not field accuracy."),
        ("Why is the held-out result not independent?", "The same held-out set is used to compare candidates and select the winner. Final reporting should use a sealed independent evaluation after model choices are fixed."),
        ("Does it represent Maharashtra?", "That is unknown. The repository does not establish dataset geography, collection methods or units, so regional representativeness cannot be claimed."),
        ("Is the probability a success chance?", "No. It is a model class score and is not calibrated to probability of suitability, yield, profit or successful harvest."),
        ("How can it be improved?", "Establish provenance, validate units, obtain representative regional data, use nested/sealed evaluation and report site/time holdouts and class-wise uncertainty."),
        ("Why retain the original crop dataset?", "Crop recommendation continues to use the original data/Crop_recommendation.csv file; its provenance and license still require verification."),
    ],
    "Other decision-support logic": [
        ("Which modules use trained ML?", "The crop classifier. A simple conditional market regression exists when sufficient history is available."),
        ("What is an expert system?", "A knowledge-based system that applies explicit rules to facts. AgriWise's expert system is deterministic IF/THEN logic, not a trained neural model."),
        ("What is explainability here?", "The app can present input context and rule/explanation text. This is not a formal guarantee that every model decision is causally explained."),
        ("How should contradictions be handled?", "Show the conflicting context and uncertainty, avoid unsafe automatic action, and request qualified human review. Rule priorities are code-defined and require domain validation."),
        ("Is every automated output AI?", "No. Some outputs are direct calculations, fixed rules, stored data or external API responses. Calling every automated feature AI would be inaccurate."),
        ("What is a decision-support system?", "A system that organizes information and offers suggestions while leaving the decision to a human user."),
        ("How is lifecycle tracked?", "The application stores crop cycles and stages and calculates dates from configured profiles; stages are estimates, not field sensor observations."),
        ("Are activities automatically confirmed?", "No. Completion is recorded from farmer/user confirmation."),
        ("Can recommendations be reported as ground truth?", "No. They are model or rule outputs; confirmed outcomes require independently recorded observations."),
        ("What does Problem Report store?", "Farmer-described symptoms and an optional private reference photo for later review."),
    ],
    "Weather, market and finance": [
        ("How is weather fetched?", "The weather service requests Open-Meteo forecast data using farm coordinates, with an 8-second timeout and 30-minute in-memory cache."),
        ("Is weather a sensor reading?", "No. It is provider model/forecast data for coordinates."),
        ("What happens if weather refresh fails?", "A prior cached result may be returned and labeled stale; otherwise the route may show an unavailable state."),
        ("Which market source is configured?", "The adapter targets data.gov.in/Agmarknet and reads an API key from environment configuration."),
        ("Does live market data work?", "Current key acceptance and usable records are unverified. The adapter's existence is not evidence of a successful live transaction."),
        ("How many market rows are fetched per query?", "The adapter bounds an individual request to at most ten records, so it does not guarantee complete coverage."),
        ("How does price forecasting work?", "The code conditionally fits a simple time regression when at least 20 distinct observations exist for one market/variety series; no live accuracy is established."),
        ("Is the forecast interval a confidence interval?", "No. The range is a heuristic based on error and floor values and is not a statistically guaranteed interval."),
        ("What is profit estimation?", "A calculation based on available costs/prices or entered transactions. It is an estimate, not an offer, yield guarantee or financial advice."),
        ("How should provider failure be communicated?", "Show unavailable or stale status, retain source/freshness context and avoid inventing replacement values."),
    ],
    "Multilingual support": [
        ("Which languages are supported?", "English (default/fallback), Marathi and Hindi through JSON translation resources."),
        ("How is language selected?", "A shared selector submits a supported code to POST /language; the code is validated and stored in the Flask session."),
        ("What happens for a missing key?", "The i18n helper tries English; if missing there too it returns the key instead of a blank string."),
        ("Does translation change model output?", "No. Translation changes displayed copy only. Crop class IDs and prediction calculations are language-independent."),
        ("How is Devanagari supported?", "Locale resources are UTF-8 JSON and templates render Unicode strings; browser/system fonts handle glyph presentation."),
        ("Is the entire app translated?", "No. Some hard-coded and dynamic strings remain. Selected screens have rendered tests, but there is no full-app coverage certification."),
        ("Are stored advisories translated?", "Not necessarily. Generated/stored text and user-entered values may remain in their source language."),
        ("Are agricultural translations approved?", "No independent native-speaker/agronomist review is documented for every term."),
        ("Is an external translation API required?", "No. Normal use reads local resource files."),
        ("How would you verify translation?", "Test locale validation/persistence/fallback, render key workflows for each language, audit missing keys, and review safety/terminology with native agricultural experts."),
    ],
    "Testing and quality assurance": [
        ("What is unit testing?", "Testing a small function or component in isolation, often with controlled dependencies."),
        ("What is integration testing?", "Testing interactions among multiple modules, such as route-to-service/database behavior."),
        ("What is black-box testing?", "Testing observable inputs and outputs without relying on internal implementation details."),
        ("What is white-box testing?", "Testing informed by internal paths, branches and logic."),
        ("What is boundary-value analysis?", "Testing values near valid limits, such as image size, numeric range or empty values."),
        ("What is mocking?", "Replacing an external dependency with a controlled substitute so tests are deterministic and do not require live services."),
        ("What is the latest recorded test outcome?", "164 passed, one joblib environment warning, zero failures on 15 October 2026. This is the recorded audit run, not a newly executed run during document generation."),
        ("Does pytest prove model accuracy?", "No. Software tests verify contracts/logic. Model validity requires a labeled independent evaluation design."),
        ("Was coverage measured?", "No coverage report was generated in the cited audit."),
        ("Were live APIs tested in that run?", "No. Provider behavior was tested with mocks/fixtures; live market/weather checks were not part of that run."),
    ],
    "Security, privacy and deployment": [
        ("How are passwords stored?", "The source uses Werkzeug password hashing helpers, not plaintext password storage."),
        ("Authentication versus authorization?", "Authentication verifies identity; authorization checks permission for a requested resource. Farm-owned data access must be checked at route level."),
        ("What is CSRF?", "Cross-site request forgery tricks a logged-in browser into submitting an unwanted action. The app uses a per-session token for state-changing requests."),
        ("How are uploads validated?", "Problem Report accepts validated reference photos, which are stored privately and accessed through authenticated, owner-checked routes."),
        ("How are API keys protected?", "Keys are read from environment settings and excluded from committed files. Never log or share the actual value."),
        ("Is the app penetration-tested?", "No comprehensive penetration test is established. Observed source controls are not a security certification."),
        ("What does Render config specify?", "One Starter instance, one Gunicorn worker/four threads, 120-second timeout, health endpoint and 1 GB persistent disk, plus environment settings."),
        ("Is deployment verified?", "No. Configuration exists, but a hosted deployment smoke test was not performed."),
        ("What are privacy implications?", "The app stores account/farm records and optional private report photos; weather/geocoding calls can transmit coordinates to providers. User notice and retention controls matter."),
        ("How should backups be treated?", "Protect them as sensitive data, encrypt/limit access where feasible, and regularly test restoration."),
    ],
    "Challenging faculty questions": [
        ("Why should farmers trust this application?", "They should not be asked to trust it uncritically. The app should show sources, dates, limitations and uncertainty; independent agronomic evaluation and local expert review are prerequisites for stronger claims."),
        ("How do you know the model generalizes to farms?", "We do not know from the current benchmark. A geographic/time-held-out dataset collected under a documented protocol is required."),
        ("What is genuinely novel?", "No formal novelty claim is established. The verified contribution is an integrated prototype and an explicit evidence/safety boundary; novelty needs literature and comparator review."),
        ("What happens if the network is unavailable?", "Local pages/model may continue where dependencies are present; provider-dependent weather/geocoding/market features can show cached, stale or unavailable states. It is not an offline-complete system."),
        ("What happens when training data are biased?", "The model can systematically misclassify underrepresented contexts. We need documented sampling, stratified and subgroup evaluation, geographic external tests and feedback mechanisms."),
        ("How would you run a Maharashtra field evaluation?", "Define target crops and sites; obtain ethics/consent; collect measured inputs and expert adjudication across seasons; seal site/time groups; pre-register outcomes; report uncertainty and safety; involve local agricultural experts."),
        ("What would you improve with six months?", "First obtain licensed data and independent evaluations; then improve uncertainty/abstention, complete translation, conduct accessibility/usability studies, verify deployment/API operations, and publish reproducible results."),
        ("What are the ethical risks?", "Misleading confidence, inequitable performance, privacy exposure, poor translation of safety advice, and users treating suggestions as guarantees. Mitigate with evidence labels, human oversight, consent, security and careful evaluation."),
        ("What cannot you prove?", "Field accuracy, yield or income improvement, national suitability, model calibration, live market integration success, complete multilingual coverage, and scientific novelty."),
    ],
    "Live demonstration and rapid revision": [
        ("How would you demonstrate registration?", "Use a test account; show validation and successful login without exposing real user data. Relevant routes are register/login in app.py; a common failure is stale local DB state."),
        ("How would you demonstrate crop recommendation?", "Use plausible test inputs, submit the form, show the suggested class and caveat, then point to the model artifact and documented split limitation."),
        ("How would you demonstrate Problem Report?", "Record symptoms and optionally attach a private reference photo; explain that the workflow stores the information but does not provide a confirmed diagnosis."),
        ("How would you demonstrate lifecycle?", "Create/select a crop cycle and show estimated stages and activity state; clarify that these are configured date estimates, not sensor-observed phenology."),
        ("How would you demonstrate language support?", "Select Marathi/Hindi and show a tested page and shared navigation. State that the entire app is not certified as fully localized."),
        ("How would you demonstrate weather?", "Show the displayed coordinate/context, timestamp/cache state and provider data. Do not call it a local sensor."),
        ("How would you demonstrate market data?", "Show cached/provider freshness and failure state if available. Do not promise a live result; current usable integration is unverified."),
        ("What is a one-minute explanation?", "AgriWise AI is a web-based agricultural decision-support prototype. It stores farm context, gives a crop-classification suggestion from seven soil/climate inputs, tracks a crop cycle and activities, and shows rule-based and provider-derived context. The software workflows are tested, but model generalization and farm benefit still need independent validation."),
        ("What mistakes should you avoid in viva?", "Do not quote benchmark accuracy as field accuracy, imply a live API worked without evidence, claim every module uses ML, or say all screens are translated."),
        ("What should you verify before demo day?", "Use a disposable test account/database, confirm model assets and dependencies, check network-dependent pages, prepare a fallback screenshot/workflow diagram, avoid secret display, and rehearse the limitation statements."),
    ],
}


def make_viva_questions():
    groups = list(VIVA_GROUPS.items())
    # Add fundamental follow-ups with tailored, evidence-grounded answers to reach
    # a broad oral-exam set without padding with duplicate phrasings.
    extensions = {
        "Project foundations": [
            ("What is the difference between a feature and a module?", "A feature is a user-visible capability; a module is a code or product boundary that may implement several features."),
            ("Why integrate multiple workflows?", "Shared farm context can reduce repeated entry and connect planning to records, but the usability benefit must be measured."),
            ("What is a system boundary?", "It defines what the application controls versus external providers, users, and agronomic realities. Weather APIs, user decisions and field outcomes lie partly outside the application."),
        ],
        "Research and contribution": [
            ("What is a primary source?", "An original paper, dataset description, official API specification or official record that directly supports the claim."),
            ("Why report negative or missing evidence?", "It prevents overclaiming and lets others reproduce, assess risk and design the next experiment."),
            ("What is an ablation study?", "A controlled experiment removing or changing one component to measure its contribution. No ablation of integrated workflows is currently reported."),
            ("What is external validation?", "Evaluation on data independent from model development, ideally from different sites, time periods or collection sources."),
        ],
        "Architecture and software engineering": [
            ("What is dependency injection?", "Providing a component's dependencies externally rather than constructing them implicitly, which makes testing and configuration easier."),
            ("What is technical debt in this project?", "Parallel/legacy crop-model paths and incomplete evidence coverage are examples of areas that need consolidation and documentation."),
            ("What is a health check?", "A lightweight endpoint indicating process or dependency readiness. /healthz checks local database connectivity, not model or provider health."),
        ],
        "Python and web fundamentals": [
            ("What is middleware?", "Request/response processing that applies across routes, such as security headers or CSRF checks."),
            ("What is a cookie flag HttpOnly?", "It prevents normal browser JavaScript from reading the cookie, reducing exposure in some script-injection scenarios."),
            ("What is idempotency?", "Repeating an operation has the same effect as performing it once. Read-only GET requests are generally expected to be idempotent."),
        ],
        "Database and SQL": [
            ("What does ON DELETE CASCADE mean?", "Deleting a parent row automatically deletes linked child rows for that declared relation; this must be designed carefully."),
            ("What is referential integrity?", "Ensuring linked records refer to valid parent records and relationships remain consistent."),
            ("Why enable SQLite foreign keys on each connection?", "SQLite enforcement is connection-configured; enabling it ensures declared constraints are applied for that connection."),
        ],
        "Machine-learning fundamentals": [
            ("What is stratification?", "Preserving approximate class proportions across a split or fold, useful for classification."),
            ("What is a confidence interval?", "A statistical interval procedure quantifying uncertainty in an estimate under assumptions. The market page's heuristic band is not such an interval."),
            ("What is calibration?", "Agreement between predicted probabilities and empirical frequencies, assessed with representative independent data."),
            ("What is an OOD sample?", "An input outside the distribution/classes the model was trained to handle. A closed-set classifier may still assign it a known class."),
        ],
        "Crop recommendation model": [
            ("How many classes are in the crop dataset?", "Twenty-two, with 100 rows each in the audited CSV."),
            ("Why use macro-F1 for selection?", "It gives equal weight to each class's F1, avoiding large classes dominating the selection metric. The file is balanced, but the choice still defines selection."),
            ("What does random_state=42 do?", "It makes the pseudo-random split reproducible under the same data/code/library behavior; it does not eliminate sampling bias."),
        ],
        "Other decision-support logic": [
            ("What is conflict resolution in rules?", "A strategy to choose among simultaneously matched rules, often based on priorities. The configured priority scheme requires agricultural validation."),
            ("What is a heuristic?", "A practical rule or approximation that may be useful but is not guaranteed optimal or empirically validated."),
            ("What is human-in-the-loop?", "A workflow in which a person reviews or confirms system output. AgriWise leaves decisions and activity completion to users."),
        ],
        "Weather, market and finance": [
            ("What is cache TTL?", "Time to live, the period a cached item is treated as fresh before refresh is considered; cached values may become stale."),
            ("What is reverse geocoding?", "Converting latitude/longitude coordinates into a human-readable place description."),
            ("Why is 20 observations needed for the forecast?", "That is a code-level minimum threshold for one time series; meeting it alone does not prove a reliable forecast."),
        ],
        "Multilingual support": [
            ("What is a fallback locale?", "A default language used when a selected locale or key is unavailable; English is the fallback here."),
            ("Why keep class IDs untranslated?", "Downstream code and model output depend on stable identifiers. Only display strings should be localized."),
            ("What is locale persistence?", "Remembering the user's selected language across requests, here via Flask session state."),
        ],
        "Testing and quality assurance": [
            ("What is regression testing?", "Re-running tests after changes to ensure previously working behavior remains intact."),
            ("What is equivalence partitioning?", "Grouping inputs expected to behave alike, then testing representative values from each group."),
            ("Why use temporary databases?", "They isolate test writes from real user data and make test state reproducible; module-level app initialization still needs special care."),
        ],
        "Security, privacy and deployment": [
            ("What is least privilege?", "Give users and services only the permissions needed for their task."),
            ("What does SameSite=Lax do?", "It restricts some cross-site cookie sending while retaining common top-level navigation behavior; it is one layer, not a full CSRF defense."),
            ("Why persistent disk?", "SQLite files and private uploads need durable storage across process restarts; ephemeral storage can be lost."),
        ],
        "Challenging faculty questions": [
            ("Could a 99.55% model be unsafe?", "Yes. It may reflect a narrow or leaked benchmark and says nothing about calibrated field performance or consequences of errors."),
            ("What would make you withdraw a claim?", "Evidence that invalidates its data source, evaluation protocol or reproduction; claims should be revised to match the newest evidence."),
            ("How do you distinguish software correctness from agricultural validity?", "Software correctness means the implementation follows its defined contract; agricultural validity means outputs are appropriate and beneficial under real agronomic conditions. The former does not imply the latter."),
            ("What is your evaluation endpoint?", "For software, routes/services and regression behavior. For agronomic efficacy, a prespecified independent field outcome is still needed."),
        ],
        "Live demonstration and rapid revision": [
            ("What if the selected language misses a string?", "The lookup falls back to English; note that a key absent in all resources can display its key, which is why catalog auditing matters."),
            ("What is the difference between a recommendation and a prediction?", "A prediction is a model output for a target label; a recommendation implies decision relevance. The UI should not imply that the label is a validated agronomic action."),
        ],
    }
    out = []
    for title, qa in groups:
        out.append((title, qa + extensions.get(title, [])))
    return out


def add_metric_tables(doc: Document):
    metrics = json.loads((ROOT / "ml" / "model_metrics.json").read_text(encoding="utf-8"))
    rows = []
    for item in metrics["models_evaluated"]:
        rows.append([
            item["model_name"],
            f'{item["accuracy"]:.4f}',
            f'{item["macro_precision"]:.4f}',
            f'{item["macro_recall"]:.4f}',
            f'{item["macro_f1"]:.4f}',
            f'{item["cv_accuracy_mean"]:.4f} ± {item["cv_accuracy_std"]:.4f}',
        ])
    add_table(doc, ["Model", "Accuracy", "Macro-P", "Macro-R", "Macro-F1", "5-fold CV accuracy"], rows)
    add_caption(doc, "Table 1", "Reported crop-model metrics from ml/model_metrics.json; not independently reproduced here.")


def build_research_dossier(diagrams: dict[str, Path]) -> Path:
    doc = setup_document("AgriWise AI Research Dossier", "Research Dossier")
    add_cover(doc, "Research Dossier", "Research foundation, evidence and limitations")
    add_toc_page(doc)
    for title, paras in DOSSIER:
        doc.add_heading(title, level=1)
        add_paragraphs(doc, paras)
        if title == "Literature comparison matrix":
            add_table(doc, ["Source", "Problem", "Method / data", "Evaluation / reported scope", "Finding supported", "Relevance / limit"], LITERATURE_MATRIX)
            add_caption(doc, "Table 1", "Selected literature and evidence boundaries.")
        if title == "Dataset analysis":
            add_table(doc, ["Item", "Verified evidence", "Limitation"], [
                ["Recommendation data", "2,200 rows; 22 labels; 7 predictors; 100 rows/class", "Provider, license, geography, period and units unresolved"],
                ["Duplicate copy", "recommendationData.csv has identical SHA-256", "Not an independent sample"],
            ])
            add_caption(doc, "Table 2", "Dataset inventory based on repository evidence.")
        if title == "Methodology":
            add_figure(doc, diagrams["method"], "Figure 1", "Evidence-oriented research and software audit workflow.")
        if title == "Experimental results":
            add_metric_tables(doc)
            cm = ROOT / "ml" / "confusion_matrix.png"
            if cm.exists():
                add_figure(doc, cm, "Figure 2", "Repository confusion matrix artifact. It is included as a reported artifact, not newly reproduced.")
    doc.add_heading("References", level=1)
    for number, ref in REFERENCES:
        doc.add_paragraph(f"{number} {ref}")
    doc.add_heading("Evidence register and academic completion checklist", level=1)
    add_table(doc, ["Claim area", "Evidence state", "What would strengthen it"], [
        ["Crop classifier benchmark", "Artifact-reported; selection split caveat", "Sealed geographic/time holdout; repeated reproduction"],
        ["Weather", "Adapter and mocked tests; historical single live observation", "Current controlled integration checks and freshness logging"],
        ["Market", "Adapter configured; live usable data unverified", "Verified key/resource response, complete series and forecast evaluation"],
        ["Localization", "Infrastructure and selected-screen tests", "Complete per-template/dynamic audit and native reviewer acceptance"],
        ["Farm benefit", "No user/field study", "Prospective controlled study with consent/ethics and outcome measures"],
    ])
    add_caption(doc, "Table 3", "Evidence gaps that constrain conclusions.")
    path = OUT / "01_AgriWise_AI_Research_Dossier.docx"
    doc.save(path)
    return path


def build_manual(diagrams: dict[str, Path]) -> Path:
    doc = setup_document("AgriWise AI Technical and Product Manual", "Technical Manual")
    add_cover(doc, "Technical and Product Manual", "Architecture, operations and developer handover")
    add_toc_page(doc)
    for title, paras in MANUAL:
        doc.add_heading(title, level=1)
        add_paragraphs(doc, paras)
        if title == "Technology stack":
            add_table(doc, ["Layer", "Technology", "Evidence", "Status"], TECHNOLOGY_ROWS)
            add_caption(doc, "Table 1", "Technologies observed in source and project environment.")
        if title == "Architecture and request flow":
            add_figure(doc, diagrams["architecture"], "Figure 1", "Implemented component chain. Provider connectivity is not guaranteed.")
            add_figure(doc, diagrams["dataflow"], "Figure 2", "Representative end-to-end data flow.")
            add_figure(doc, diagrams["er"], "Figure 3", "Declared foreign-key relationships across all application tables.")
            add_table(doc, ["Entity group", "Tables", "Relationship note"], [
                ["Identity and farm", "users, farms", "Each farm references a user."],
                ["Agronomic observations", "soil_records, weather_records", "Each record references a farm."],
                ["Crop planning", "crop_recommendations, crop_cycles, crop_stages", "Cycles belong to farms; stages belong to cycles."],
                ["Operations", "advisories, notifications, farm_activities", "Activities may reference farm, cycle and advisory."],
                ["Problem reports", "disease_reports", "Farmer-entered problem reports can reference farm/cycle."],
                ["Finance", "farm_expenses, sales", "Records may reference farm/cycle; expenses may link activity."],
                ["Market and resources", "market_prices, market_forecasts, mandis, resources, resource_prices", "Resource prices reference resources; market entities have no declared FK in current DDL."],
                ["Decision outputs", "fertilizer_recommendations, what_if_runs, risk_snapshots, recommendation_feedback", "Farm/user scope follows declared DDL; see db.py for exact columns."],
            ])
            add_caption(doc, "Table 2", "Database entity groups; consult db.py for authoritative columns and constraints.")
        if title == "Crop recommendation implementation":
            add_figure(doc, diagrams["crop"], "Figure 4", "Crop recommendation inference path.")
            add_figure(doc, diagrams["training"], "Figure 5", "Training and candidate selection path.")
            add_metric_tables(doc)
        if title == "Multilingual support":
            add_figure(doc, diagrams["i18n"], "Figure 7", "Language selection and resource fallback.")
        if title == "Testing and verification record":
            add_figure(doc, diagrams["testing"], "Figure 8", "Software test evidence and what it does not establish.")
        if title == "Installation and local run (Windows)":
            for command in SETUP_COMMANDS:
                p = doc.add_paragraph()
                r = p.add_run(command)
                r.font.name = "Consolas"
                r.font.size = Pt(8.5)
        if title == "Deployment and troubleshooting":
            add_table(doc, ["Symptom", "Likely cause", "Diagnostic / action"], [
                ["Crop prediction unavailable", "Artifact missing, invalid inputs or import/runtime issue", "Check artifact path and server logs; verify all seven finite numeric fields."],
                ["Weather stale/unavailable", "Provider timeout, connectivity, coordinates", "Check farm coordinates and freshness label; do not relabel stale data as live."],
                ["No market prices", "Key/resource/provider response unverified or no usable records", "Check sanitized diagnostic privately; never expose key or fabricate rows."],
                ["Language partly English", "Missing key or hard-coded/dynamic content", "Check locale key lookup and template; English fallback is expected for missing keys."],
                ["Data disappears after deploy", "Ephemeral storage or wrong mount path", "Use a configured durable disk/database and test restart/restore behavior."],
            ])
            add_caption(doc, "Table 3", "Troubleshooting based on observed architecture and known limitations.")
    doc.add_heading("Operational feature verification matrix", level=1)
    add_table(doc, ["Feature", "Status", "Evidence / boundary"], [
        ["Registration/login", "Implemented; route/security tests", "Source and tests; not a full security audit"],
        ["Crop recommendation", "Implemented; artifact benchmark", "Split selection caveat; no field validity"],
        ["Lifecycle and activities", "Implemented; tests cover core behavior", "Stage timings are configured estimates"],
        ["Weather", "Implemented adapter; mocked tests", "Historical single live response only"],
        ["Market prices", "Adapter implemented; live data unverified", "At most 10 records/query"],
        ["Multilingual", "Partial app coverage", "Selected screens tested; do not claim whole-app completeness"],
    ])
    add_caption(doc, "Table 4", "Feature status as supported by current source/test evidence.")
    path = OUT / "02_AgriWise_AI_Technical_and_Product_Manual.docx"
    doc.save(path)
    return path


def enable_two_columns(section_obj):
    sect_pr = section_obj._sectPr
    cols = sect_pr.xpath("./w:cols")
    if cols:
        cols[0].set(qn("w:num"), "2")
        cols[0].set(qn("w:space"), "360")
    else:
        node = OxmlElement("w:cols")
        node.set(qn("w:num"), "2")
        node.set(qn("w:space"), "360")
        sect_pr.append(node)


def build_ieee(diagrams: dict[str, Path]) -> Path:
    doc = setup_document("AgriWise AI: An Intelligent Crop Lifecycle Decision Support System", "IEEE Manuscript", ieee=True)
    sec = doc.sections[0]
    sec.top_margin = Inches(0.62)
    sec.bottom_margin = Inches(0.62)
    sec.left_margin = Inches(0.58)
    sec.right_margin = Inches(0.58)
    # One-column title/abstract region; IEEE-like two-column body follows.
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(6)
    title.paragraph_format.space_after = Pt(4)
    r = title.add_run("AgriWise AI: An Intelligent Crop Lifecycle\nDecision Support System for Sustainable Agriculture")
    r.bold = True
    r.font.name = "Aptos Display"
    r.font.size = Pt(19)
    authors = doc.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.add_run("[Author Name], [Department], [Institution], [City, Country]\n[Email / ORCID — fill in]").font.size = Pt(9)
    doc.add_heading("Abstract", level=2)
    doc.add_paragraph(
        "This paper describes AgriWise AI, a Flask-based agricultural decision-support prototype integrating farm records, crop classification, lifecycle tracking, deterministic rules, weather context and symptom reporting. The crop classifier uses seven numeric features from a 2,200-row, 22-class CSV. The checked-in metrics artifact reports a Random Forest held-out accuracy and macro-F1 of 0.9955 under a stratified 80/20 split. Because the held-out score is used to select the winning candidate and dataset provenance is unresolved, this result is a development benchmark rather than independent or field accuracy. Automated software tests recorded 164 passes, one environment warning and zero failures; these tests do not establish agronomic efficacy. The work demonstrates a connected software prototype and identifies the independent data and user studies required before field claims."
    )
    p = doc.add_paragraph()
    p.add_run("Index Terms—").bold = True
    p.add_run("agricultural decision support, crop classification, lifecycle management, model evaluation, multilingual interface.")
    sec2 = doc.add_section(WD_SECTION.CONTINUOUS)
    sec2.page_width, sec2.page_height = Inches(8.27), Inches(11.69)
    sec2.top_margin, sec2.bottom_margin = Inches(0.62), Inches(0.62)
    sec2.left_margin, sec2.right_margin = Inches(0.58), Inches(0.58)
    enable_two_columns(sec2)
    for title_text, paras in IEEE_SECTIONS:
        doc.add_heading(title_text, level=1)
        add_paragraphs(doc, paras)
        if title_text == "IV. SYSTEM AND METHODS":
            add_figure(doc, diagrams["architecture"], "Fig. 1", "Implemented component path.", width=3.15)
        if title_text == "V. DATASET AND EXPERIMENTAL SETUP":
            add_table(doc, ["Model", "Acc.", "Macro-F1", "CV μ±σ"], [
                ["Decision Tree", "0.9818", "0.9817", "0.9841±0.0073"],
                ["Random Forest", "0.9955", "0.9955", "0.9943±0.0051"],
                ["KNN", "0.9795", "0.9793", "0.9653±0.0121"],
                ["Gradient Boosting", "0.9886", "0.9886", "0.9926±0.0043"],
            ])
            add_caption(doc, "Table I", "Recorded crop benchmark metrics; winner selection uses the held-out set.")
            add_figure(doc, diagrams["crop"], "Fig. 2", "Crop recommendation pipeline.", width=3.15)
    doc.add_heading("REFERENCES", level=1)
    for number, ref in REFERENCES:
        doc.add_paragraph(f"{number} {ref}")
    doc.add_paragraph(
        "Manuscript status: IEEE-style conference layout for further review, not an official template, acceptance, certification or publication guarantee. Adapt to the chosen venue's current author instructions."
    )
    path = OUT / "03_AgriWise_AI_IEEE_Research_Paper.docx"
    doc.save(path)
    return path


def build_viva() -> Path:
    doc = setup_document("AgriWise AI Comprehensive Viva Questions and Answers", "Viva Study Guide")
    add_cover(doc, "Comprehensive Viva Questions and Answers", "Presentation, demonstration and research study guide")
    add_toc_page(doc)
    doc.add_heading("How to use this guide", level=1)
    add_paragraphs(doc, [
        "Answers are intentionally honest and concise enough to speak aloud. For implementation-specific claims, cite the repository artifact or test and state the evidence limit. If asked about missing evidence, say so directly and propose the experiment needed.",
        "Do not claim that the crop benchmark is field accuracy, that live market data was successfully fetched, or that every page is fully translated."
    ])
    total = 0
    for group, items in make_viva_questions():
        doc.add_heading(group, level=1)
        for i, (question, answer) in enumerate(items, start=1):
            total += 1
            q = doc.add_paragraph()
            q.paragraph_format.keep_with_next = True
            qr = q.add_run(f"Q{total}. {question}")
            qr.bold = True
            qr.font.color.rgb = RGBColor.from_string(GREEN)
            a = doc.add_paragraph()
            a.paragraph_format.left_indent = Inches(0.18)
            a.add_run("Answer: ").bold = True
            a.add_run(answer)
    doc.add_heading("Key formulas for revision", level=1)
    add_table(doc, ["Metric", "Formula / meaning"], [
        ["Accuracy", "(correct predictions) / (all predictions)"],
        ["Precision", "TP / (TP + FP)"],
        ["Recall", "TP / (TP + FN)"],
        ["F1", "2 × Precision × Recall / (Precision + Recall)"],
        ["Macro-F1", "Unweighted mean of class-wise F1 values"],
        ["Weighted-F1", "Support-weighted mean of class-wise F1 values"],
        ["MAE", "Mean absolute error: mean(|y − ŷ|)"],
        ["RMSE", "Square root of mean squared error: sqrt(mean((y − ŷ)^2))"],
    ])
    add_caption(doc, "Table 1", "Frequently asked evaluation formulas.")
    doc.add_heading("30 rapid-revision prompts with answers", level=1)
    rapid = [
        ("Framework?", "Flask with Jinja templates."),
        ("Database?", "SQLite; 23 application tables are defined."),
        ("Crop model?", "Random Forest is the selected saved artifact."),
        ("Crop dataset size?", "2,200 rows, 22 classes."),
        ("Crop inputs?", "N, P, K, temperature, humidity, pH and rainfall."),
        ("Recorded best accuracy?", "0.9955 held-out artifact metric; not field accuracy."),
        ("Selection caveat?", "The held-out score selects the winner."),
        ("Weather provider?", "Open-Meteo forecast API."),
        ("Market provider?", "data.gov.in/Agmarknet adapter; live usable records unverified."),
        ("Expert system?", "Deterministic IF/THEN rules."),
        ("Lifecycle timing?", "Configured estimates, not sensor-observed stages."),
        ("Language codes?", "en, mr, hi."),
        ("Language fallback?", "English."),
        ("Test result?", "Recorded 164 passed, 1 warning, 0 failures."),
        ("Field trial?", "Not established."),
        ("Training data provenance?", "Unresolved in repository evidence."),
        ("Recommendation-data duplicate?", "recommendationData.csv is byte-identical in the audited checkout."),
        ("CSRF control?", "Per-session token for state-changing requests."),
        ("Password storage?", "Werkzeug password hashing helpers."),
        ("Upload maximum?", "5 MiB; also a 24-million-pixel ceiling."),
        ("Problem report?", "Stores farmer-entered symptoms and optional private reference photos."),
        ("Render storage?", "Persistent disk configured in blueprint; not proof of deployment."),
        ("Offline?", "Not fully; provider features depend on network."),
        ("Farmer outcome evidence?", "None established."),
        ("Novel algorithm?", "No novel algorithm claim is made."),
        ("Top future priority?", "Licensed independent data and external validation."),
    ]
    for i, (qtext, atext) in enumerate(rapid, 1):
        p = doc.add_paragraph()
        p.paragraph_format.keep_with_next = True
        p.add_run(f"{i}. {qtext} ").bold = True
        p.add_run(atext)
    doc.add_heading("One-minute project explanation", level=1)
    doc.add_paragraph(
        "AgriWise AI is a web-based agricultural decision-support prototype. It stores farm context, provides a crop-classification suggestion from seven soil and climate inputs, tracks crop cycles and activities, and presents rule-based and provider-derived context. The application is built with Flask, Jinja and SQLite. The crop model's recorded benchmark is high, but its dataset provenance is unresolved and the held-out data selected the model. Field benefit is unmeasured. The project demonstrates connected software workflows, while independent agronomic validation remains future work."
    )
    doc.add_heading("Three-minute project explanation and five-minute presentation outline", level=1)
    add_paragraphs(doc, [
        "Three-minute version: introduce the coordination problem; show the actual architecture; explain the crop model's seven inputs and evidence caveat; distinguish rules, weather and market data from ML; demonstrate Problem Report, lifecycle and records; finish with the test record and external-validation priorities.",
        "Five-minute outline: 0:00–0:35 problem and objectives; 0:35–1:15 system architecture; 1:15–2:00 crop recommendation and dataset; 2:00–2:40 lifecycle/rules/weather; 2:40–3:20 Problem Report and privacy boundaries; 3:20–4:00 multilingual interface and data persistence; 4:00–4:35 tests and measured metrics; 4:35–5:00 limitations and next experiments."
    ])
    doc.add_heading("Demonstration checklist", level=1)
    add_table(doc, ["Workflow", "Demonstrate", "Dependency / common failure", "Follow-up answer"], [
        ["Registration/login", "Create a disposable test user; log in/out", "Local DB / session; avoid real user data", "Password hashing is observed; not a full security audit."],
        ["Farm setup", "Save farm context and location", "Geocoding/network may fail", "Coordinate text fallback can be used; provider success varies."],
        ["Crop recommendation", "Submit seven finite numeric inputs", "Model artifact / input validation", "Metric is a development benchmark, not field accuracy."],
        ["Lifecycle/activity", "Create cycle; view stages; mark an activity", "Configured profiles and database state", "Dates are estimates; completion is user confirmed."],
        ["Problem Report", "Record symptoms and optionally attach a reference photo", "Keep reference photos private", "The workflow records symptoms; it does not provide a diagnosis."],
        ["Language", "Switch to Marathi/Hindi on a tested page", "Missing strings fall back to English", "Not all pages/dynamic content are fully translated."],
        ["Weather", "Show forecast and freshness context", "Internet/API timeout", "Model forecast, not sensor observation."],
        ["Market", "Show returned/cached/unavailable state", "API key/provider response", "Live usable data is unverified; no fabricated prices."],
        ["Persistence", "Show saved history/records", "SQLite path and test data", "Use disposable local database for demo."],
    ])
    add_caption(doc, "Table 2", "Live demonstration sequence and honest failure handling.")
    doc.add_heading("Viva-day checklist", level=1)
    add_bullets(doc, [
        "Run the app from a disposable test profile and verify local model artifacts before the panel arrives.",
        "Prepare a backup demonstration path for network-dependent weather/market screens.",
        "Never display API keys, .env contents, real farmer records or personal photos.",
        "Explain the 0.9955 crop metric with its dataset provenance and test-selection caveats.",
        "Do not present the crop-model benchmark as field performance.",
        "Clearly distinguish ML, deterministic rules, external data and user-entered records.",
        "State incomplete translation coverage and the English fallback.",
        "Answer unknowns with the experiment or documentation needed to resolve them.",
    ])
    path = OUT / "04_AgriWise_AI_Comprehensive_Viva_Questions_and_Answers.docx"
    doc.save(path)
    return path


def extract_docx_text(path: Path) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(
        cell.text for table in doc.tables for row in table.rows for cell in row.cells
    )


def write_readme(paths: list[Path], viva_count: int) -> None:
    entries = "\n".join(f"- [{p.name}](./{p.name})" for p in paths)
    (OUT / "README.md").write_text(
        "# AgriWise AI final submission documents\n\n"
        "Generated on 2026-10-15 from repository evidence. These are genuine Word "
        "Open XML `.docx` documents, not renamed text files.\n\n"
        f"{entries}\n\n"
        "## Supporting assets and regeneration\n\n"
        "- `generation_assets/generate_documents.py` builds the documents and diagrams.\n"
        "- Generated diagrams and the source crop confusion-matrix image are stored under `generation_assets/`.\n"
        "- Regenerate from the repository root with the project Python environment after installing `python-docx`, `matplotlib`, and `networkx`.\n"
        f"- The viva guide contains {viva_count} answered oral-exam questions, plus a separate 30-item rapid-revision set.\n\n"
        "## Academic completion notes\n\n"
        "- Replace only the clearly marked student, institution, supervisor, email/ORCID and term placeholders.\n"
        "- Update the Word table-of-contents field in Microsoft Word before submission.\n"
        "- The IEEE-style manuscript is a conference-layout draft, not an official venue template or publication guarantee.\n"
        "- Metrics and test outcomes are reported with their evidence date and limitations. No field study, live market success, or complete app-wide localization is claimed.\n"
        "- Inspect all pages in Word/LibreOffice and adapt the final format to institutional and venue requirements.\n",
        encoding="utf-8",
    )


def main() -> None:
    diagrams = build_diagrams()
    outputs = [
        build_research_dossier(diagrams),
        build_manual(diagrams),
        build_ieee(diagrams),
        build_viva(),
    ]
    viva_doc = Document(outputs[-1])
    viva_count = sum(1 for p in viva_doc.paragraphs if re.match(r"Q\d+\.", p.text))
    write_readme(outputs, viva_count)
    for path in outputs:
        if not zipfile.is_zipfile(path):
            raise RuntimeError(f"Invalid DOCX package: {path}")
        text = extract_docx_text(path)
        if len(text.split()) < 1500:
            raise RuntimeError(f"Document is unexpectedly short: {path}")
    print(json.dumps({
        "documents": [
            {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
             "words": len(extract_docx_text(p).split())}
            for p in outputs
        ],
        "viva_questions": viva_count,
        "diagrams": len(diagrams),
        "output_directory": str(OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
