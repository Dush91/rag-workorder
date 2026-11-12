"""Generate the demo corpus: three deliberately awkward PDFs for a fictional pump.

- AquaDyne_HF300_OM_Manual.pdf  ruled tables, an exploded-view drawing, and a chart
                                whose zone limits exist only in the image
- AquaDyne_SB-2026-014.pdf      a "scanned" service bulletin with no text layer that
                                supersedes a part number and a torque value in the manual
- Westfield_SSP-07_Rotating_Equipment.pdf  the site's safety rules for the same work

Everything is fictional, so no confidential or copyrighted material is involved.
"""
import io
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image as RLImage,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOCS = Path(__file__).parent / "docs"
STYLES = getSampleStyleSheet()
H1, H2, BODY = STYLES["Heading1"], STYLES["Heading2"], STYLES["BodyText"]


def table(rows, widths):
    t = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde4ee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def wrap(rows):
    """Wrap long cell text so ReportLab flows it inside the column."""
    style = STYLES["BodyText"].clone("cell", fontSize=8.5, leading=10)
    return [rows[0]] + [[Paragraph(str(c), style) for c in r] for r in rows[1:]]


def fig_to_image(fig, width_mm):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    w, h = Image.open(buf).size
    buf.seek(0)
    return RLImage(buf, width=width_mm * mm, height=width_mm * mm * h / w)


def exploded_view():
    fig, ax = plt.subplots(figsize=(7, 3))
    parts = [  # (x, y, w, h, callout)
        (0.2, 1.0, 1.6, 2.0, 1), (2.2, 1.4, 0.9, 1.2, 2), (3.5, 1.6, 0.5, 0.8, 3),
        (4.3, 1.75, 0.6, 0.5, 4), (5.3, 1.5, 0.7, 1.0, 5), (7.6, 1.5, 0.7, 1.0, 6),
        (5.0, 1.9, 3.8, 0.2, 7), (1.95, 1.0, 0.12, 2.0, 8),
    ]
    for x, y, w, h, n in parts:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                    fc="#cfd8e3", ec="black", lw=1))
        ax.annotate(str(n), xy=(x + w / 2, y + h), xytext=(x + w / 2, 3.6),
                    ha="center", fontsize=11, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", lw=0.7))
    ax.set_xlim(0, 9.2)
    ax.set_ylim(0.5, 4)
    ax.axis("off")
    ax.set_title("HF-300 back pull-out assembly (exploded view)", fontsize=10)
    return fig


def vibration_chart():
    zones = [("A", 0, 2.8, "#4caf50", "New\nmachines"),
             ("B", 2.8, 4.5, "#cddc39", "Long-term\noperation"),
             ("C", 4.5, 7.1, "#ff9800", "Restricted -\nplan\nmaintenance"),
             ("D", 7.1, 11.0, "#f44336", "Damage likely -\nstop the pump")]
    fig, ax = plt.subplots(figsize=(7, 2.4))
    for z, lo, hi, c, label in zones:
        ax.barh(0, hi - lo, left=lo, color=c, edgecolor="black")
        ax.text((lo + hi) / 2, 0, f"Zone {z}\n{label}", ha="center", va="center", fontsize=7)
    ax.set_xlim(0, 11)
    ax.set_xticks([0, 2.8, 4.5, 7.1, 11])
    ax.set_yticks([])
    ax.set_xlabel("Vibration velocity, mm/s RMS (measured on bearing housings)")
    ax.set_title("Figure 3 - HF-300 vibration severity zones", fontsize=10)
    return fig


def build_manual():
    s = [
        Paragraph("AquaDyne HF-300 End-Suction Centrifugal Pump", H1),
        Paragraph("Operation &amp; Maintenance Manual - Document AQ-OM-300, Revision D", BODY),
        Spacer(1, 6),
        Paragraph("1. Specifications", H2),
        Paragraph("The HF-300 is a back pull-out pump: the rotating assembly can be removed "
                  "without disturbing the casing or pipework. Bearing temperatures are measured "
                  "on the housing surface.", BODY),
        table(wrap([
            ["Parameter", "Value"],
            ["Rated flow / head", "300 m3/h at 45 m"],
            ["Speed / motor", "1480 rpm, 55 kW, 400 V"],
            ["Bearing housing temperature", "Normal up to 70 C; alarm 80 C; trip 90 C"],
            ["Back pull-out assembly mass", "68 kg (lifting equipment required)"],
            ["Seal flush", "Plan 11 from pump discharge; never run dry"],
        ]), [70, 100]),
        Paragraph("2. Parts identification", H2),
        fig_to_image(exploded_view(), 160),
        Paragraph("Figure 2 - Exploded view. Item numbers refer to the parts list below.", BODY),
        table(wrap([
            ["Item", "Part No.", "Description", "Qty"],
            ["1", "HF3-101", "Volute casing", "1"],
            ["2", "HF3-210", "Impeller, 5-vane, 330 mm", "1"],
            ["3", "HF3-450", "Mechanical seal, component type", "1"],
            ["4", "HF3-455", "Shaft sleeve", "1"],
            ["5", "HF3-512", "Drive-end bearing 6312-C3", "1"],
            ["6", "HF3-510", "Non-drive-end bearing 6310-C3", "1"],
            ["7", "HF3-300", "Shaft", "1"],
            ["8", "HF3-120", "Casing gasket (replace whenever casing is opened)", "1"],
        ]), [14, 26, 110, 14]),
        PageBreak(),
        Paragraph("3. Condition monitoring", H2),
        Paragraph("Measure vibration velocity on both bearing housings every week. Classify the "
                  "highest reading using Figure 3 and act on the zone it falls in.", BODY),
        fig_to_image(vibration_chart(), 160),
        Paragraph("4. Troubleshooting", H2),
        table(wrap([
            ["Symptom", "Probable cause", "Corrective action"],
            ["Leakage at shaft seal", "Worn or cracked seal faces; seal run dry; shaft "
             "misalignment", "Replace mechanical seal (5.2). Check alignment (5.4)."],
            ["High vibration", "Misalignment; bearing wear; impeller imbalance or damage; "
             "cavitation", "Check alignment (5.4). Inspect bearings and impeller. Check NPSH."],
            ["High bearing temperature", "Over-greasing; bearing wear; misalignment",
             "Check grease quantity. Replace bearings (5.3) if worn. Check alignment (5.4)."],
            ["Low flow or head", "Worn impeller; air in suction; closed valve",
             "Inspect impeller and wear rings. Vent the casing."],
        ]), [38, 62, 70]),
        PageBreak(),
        Paragraph("5. Maintenance procedures", H2),
        Paragraph("5.2 Mechanical seal replacement. (1) Isolate and drain the pump. (2) Remove "
                  "the back pull-out assembly. (3) Remove the impeller nut and impeller. (4) "
                  "Withdraw the seal and sleeve; inspect the sleeve for scoring. (5) Fit the new "
                  "seal and a new casing gasket. (6) Tighten all fasteners to Table 5.", BODY),
        Paragraph("5.3 Bearing replacement. Replace both bearings as a pair when either shows "
                  "wear, noise or high temperature.", BODY),
        Paragraph("5.4 Shaft alignment. Use a laser alignment tool after any work that moves "
                  "the motor or the bearing housing. Tolerances: parallel offset 0.05 mm, "
                  "angular 0.05 mm per 100 mm.", BODY),
        Paragraph("Table 5 - Tightening torques (lightly oiled threads)", BODY),
        table([
            ["Fastener", "Size", "Torque (Nm)"],
            ["Casing bolts", "M16", "210"],
            ["Impeller nut", "M24", "160"],
            ["Seal gland nuts", "M10", "25"],
            ["Bearing housing bolts", "M12", "85"],
        ], [70, 30, 40]),
        Spacer(1, 6),
        Paragraph("Table 6 - Standard labour times", BODY),
        table([
            ["Task", "Hours", "Technicians"],
            ["Mechanical seal replacement", "4.0", "2"],
            ["Bearing replacement (pair)", "6.0", "2"],
            ["Laser alignment", "1.5", "1"],
        ], [80, 30, 30]),
    ]
    SimpleDocTemplate(str(DOCS / "AquaDyne_HF300_OM_Manual.pdf"), pagesize=A4,
                      title="AquaDyne HF-300 O&M Manual").build(s)


def build_bulletin():
    """Draw the bulletin as a skewed, noisy page image: a PDF with no text layer."""
    W, H = 1240, 1754
    img = Image.new("L", (W, H), 245)
    d = ImageDraw.Draw(img)
    try:
        big = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 44)
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except OSError:
        big = font = ImageFont.load_default()
    y = 110
    d.text((100, y), "AquaDyne Pumps Ltd", font=big, fill=20)
    y += 60
    d.text((100, y), "SERVICE BULLETIN SB-2026-014", font=big, fill=20)
    y += 90
    for line in [
        "Issued: 14 March 2026        Applies to: HF-300 pumps, serial HF3-22000 and above",
        "",
        "Subject: Mechanical seal superseded",
        "",
        "Field returns show early failure of component seal HF3-450 on pumps built",
        "from serial HF3-22000, caused by a revised sleeve tolerance. On these pumps:",
        "",
        "  1. Do NOT fit HF3-450. Use cartridge seal HF3-450B instead.",
        "  2. HF3-450B is pre-set: no sleeve measurement is needed.",
        "  3. Seal gland nut torque for HF3-450B is 30 Nm (was 25 Nm).",
        "  4. Replace shaft sleeve HF3-455 if scoring exceeds 0.1 mm depth.",
        "",
        "Pumps below serial HF3-22000 continue to use HF3-450 and Table 5 of the manual.",
    ]:
        d.text((100, y), line, font=font, fill=25)
        y += 48
    y += 30
    rows = [("Item", "Old part", "New part", "Gland torque"),
            ("Mechanical seal", "HF3-450", "HF3-450B", "30 Nm")]
    xs = [100, 400, 650, 900, 1140]
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            d.rectangle([xs[c], y, xs[c + 1], y + 60], outline=30, width=2)
            d.text((xs[c] + 12, y + 14), cell, font=font, fill=25)
        y += 60
    d.text((100, y + 80), "Authorised: R. Okafor, Product Engineering", font=font, fill=25)
    random.seed(7)
    for _ in range(9000):  # scanner speckle
        d.point((random.randrange(W), random.randrange(H)), fill=random.randrange(120, 200))
    img = img.rotate(0.9, expand=False, fillcolor=235).filter(ImageFilter.GaussianBlur(0.6))
    img.convert("RGB").save(DOCS / "AquaDyne_SB-2026-014.pdf", resolution=150)


def build_safety():
    s = [
        Paragraph("Westfield Water Treatment Works", H1),
        Paragraph("Site Safety Procedure SSP-07: Work on Rotating Equipment (Rev 3)", H2),
        Paragraph("This procedure applies to all pumps, fans and mixers on site. A work order "
                  "must list every control below that applies to the task.", BODY),
        Spacer(1, 6),
        table(wrap([
            ["Task", "Required controls"],
            ["Any work inside a pump or on its seal",
             "Electrical isolation and lock-out/tag-out (LOTO) at the MCC; mechanical isolation "
             "of suction and discharge valves; line-break permit (drain and vent first)"],
            ["Lifting a component heavier than 25 kg",
             "Lifting plan signed by the shift supervisor; certified lifting equipment"],
            ["Work on chemically dosed lines", "Chemical goggles and nitrile gloves"],
            ["Vibration in the manufacturer's highest severity zone",
             "Stop the machine immediately and notify the reliability engineer before restart"],
            ["Bearing temperature above the manufacturer's alarm limit",
             "Raise a priority-1 work order within the shift"],
        ]), [60, 110]),
        Spacer(1, 8),
        Paragraph("Pumps P-101 to P-106 on the filtered-water line are chemically dosed "
                  "(sodium hypochlorite).", BODY),
    ]
    SimpleDocTemplate(str(DOCS / "Westfield_SSP-07_Rotating_Equipment.pdf"), pagesize=A4,
                      title="SSP-07 Rotating Equipment").build(s)


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    build_manual()
    build_bulletin()
    build_safety()
    print("Wrote", sorted(p.name for p in DOCS.glob("*.pdf")))
