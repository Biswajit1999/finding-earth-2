"""Build the research-led Finding Earth 2 major-upgrade decision report."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "finding-earth-2-major-upgrade-report.pdf"
FIGURES = ROOT / "paper" / "figures"

INK = colors.HexColor("#10263A")
MUTED = colors.HexColor("#536A7A")
CYAN = colors.HexColor("#00A7C4")
PALE = colors.HexColor("#EAF7FA")
LINE = colors.HexColor("#C9DCE3")
PAPER = colors.HexColor("#FAFCFD")
WHITE = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=28, leading=31, textColor=INK, alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "kicker": ParagraphStyle(
            "Kicker", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=8.5, leading=11, textColor=CYAN, tracking=1.2,
            spaceAfter=7,
        ),
        "deck": ParagraphStyle(
            "Deck", parent=base["Normal"], fontName="Helvetica",
            fontSize=12, leading=17, textColor=MUTED, spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=20, leading=24, textColor=INK, spaceBefore=5, spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13.5, leading=17, textColor=INK, spaceBefore=8, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.2, leading=13.6, textColor=INK, spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.7, leading=10.5, textColor=MUTED, spaceAfter=3,
        ),
        "card_title": ParagraphStyle(
            "CardTitle", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=10, leading=13, textColor=INK, spaceAfter=3,
        ),
        "card_body": ParagraphStyle(
            "CardBody", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.4, leading=12, textColor=MUTED,
        ),
        "metric": ParagraphStyle(
            "Metric", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=18, leading=20, textColor=CYAN, alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=7.2, leading=9.5, textColor=INK, alignment=TA_CENTER,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["BodyText"], fontName="Helvetica-Oblique",
            fontSize=7.3, leading=10, textColor=MUTED, spaceBefore=3, spaceAfter=7,
        ),
        "ref": ParagraphStyle(
            "Reference", parent=base["BodyText"], fontName="Helvetica",
            fontSize=7.2, leading=10, textColor=INK, spaceAfter=4,
        ),
    }


S = _styles()


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def card(number: str, title: str, body: str) -> Table:
    content = [P(number, "metric"), P(title, "card_title"), P(body, "card_body")]
    table = Table([[content]], colWidths=[164 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def metric_row(items: list[tuple[str, str]]) -> Table:
    cells = [[P(value, "metric"), P(label, "metric_label")] for value, label in items]
    table = Table([cells], colWidths=[41 * mm] * len(cells), hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def figure(name: str, caption: str, width: float = 164 * mm):
    path = FIGURES / name
    image = Image(str(path), width=width, height=width * 0.56)
    return KeepTogether([image, P(caption, "caption")])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"<bullet>-</bullet>{text}", ParagraphStyle(
        "Bullet", parent=S["body"], leftIndent=12, firstLineIndent=-7,
        bulletIndent=2, spaceAfter=4,
    ))


def page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(INK)
    canvas.rect(0, h - 12 * mm, w, 12 * mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.setFillColor(WHITE)
    canvas.drawString(20 * mm, h - 7.7 * mm, "FINDING EARTH 2  /  MAJOR UPGRADE RESEARCH")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(w - 20 * mm, 11 * mm, f"28 AUGUST 2026   |   {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 15 * mm, w - 20 * mm, 15 * mm)
    canvas.restoreState()


def build() -> Path:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4, rightMargin=23 * mm, leftMargin=23 * mm,
        topMargin=22 * mm, bottomMargin=22 * mm,
        title="Finding Earth 2: research-led major upgrade",
        author="Biswajit Jana",
        subject="Evidence-backed scientific and product upgrade decision report",
    )
    story = []

    story += [Spacer(1, 19 * mm), P("EVIDENCE-LED DECISION REPORT", "kicker")]
    story += [P("Finding Earth 2:<br/>a research-led major upgrade", "title")]
    story += [P(
        "How to strengthen scientific integrity, expose observation readiness, and turn the long-form article into a complete visual research workspace.",
        "deck",
    )]
    story += [Spacer(1, 6 * mm), metric_row([
        ("6,354", "CONFIRMED PLANETS"),
        ("16", "REPRODUCIBLE FIGURES"),
        ("4", "FOLLOW-UP LANES"),
        ("1", "OPEN METHODOLOGY"),
    ]), Spacer(1, 10 * mm)]
    story += [P(
        "Decision: preserve the complete NASA composite catalogue, disclose its source coherence, keep observation feasibility separate from Earth-likeness, and make every visual asset verifiably deployable under the GitHub Pages base path.",
        "deck",
    )]
    story += [Spacer(1, 12 * mm), P("Prepared for", "kicker"), P("Biswajit Jana", "h2")]
    story += [P("Decision date: 28 August 2026<br/>Scope: science, provenance, follow-up utility, accessibility, performance, and static deployment", "small")]
    story += [PageBreak()]

    story += [P("Executive answer", "h1")]
    story += [P(
        "The strongest upgrade is not another opaque habitability score. It is an evidence-integrity and observation-readiness release built around three connected outcomes.",
    )]
    story += [card("01", "Disclose source coherence", "Compare NASA's complete composite row with its coherent default published solution. Report source count, overlap, coverage, and parameter differences without treating multiple sources as an automatic penalty."), Spacer(1, 4 * mm)]
    story += [card("02", "Separate follow-up pathways", "Expose transit timing, atmospheric screening, radial-velocity amplitude, and reflected-light geometry as distinct diagnostics. None changes the default Earth-2 ranking."), Spacer(1, 4 * mm)]
    story += [card("03", "Build a visual evidence workspace", "Make figures base-path safe, expand the article to all reproducible visuals, use productive desktop rails, reflow on mobile, and verify the static export automatically."), Spacer(1, 7 * mm)]
    story += [P("Guardrails", "h2")]
    for text in [
        "Preserve a fully static GitHub Pages export; no runtime backend.",
        "Use public first-party archives and original papers; no paid data source.",
        "Never infer evidence of life, confirmed habitability, or proposal-grade feasibility.",
        "Keep observation feasibility out of the default Earth-likeness ranking.",
        "Label every assumption and preserve prior successful live-source products on catalogue-only rebuilds.",
    ]:
        story.append(bullet(text))
    story += [PageBreak()]

    story += [P("1  Source coherence is the highest-impact scientific gap", "h1")]
    story += [P(
        "NASA documents two different data roles. The Planetary Systems table (ps) contains self-consistent published solution rows. The Planetary Systems Composite Parameters table (pscomppars) maximizes completeness by selecting values across references; a composite row can therefore be internally or physically inconsistent.",
    )]
    story += [P(
        "Decision: retain pscomppars as the catalogue spine, then disclose composite source count, whether parameters mix sources, coherent-default coverage and overlap, and the median symmetric fractional difference between overlapping values. This is context, not proof that a planet or source is wrong.",
    )]
    story += [figure("data_coverage.png", "Figure 1. Archive coverage after the 28 August 2026 synchronized build. Every public product is generated from the same manifests and transformation ledger.")]
    story += [P("Why this matters", "h2")]
    story += [P(
        "Derived properties such as equilibrium temperature, density, habitable-zone position, and Earth similarity can combine inputs published under different assumptions. The new disclosure makes that boundary visible while retaining catalogue breadth. A later research phase should propagate competing coherent solutions as a mixture, but the archive generally lacks the cross-parameter covariance required for a complete hierarchical treatment.",
    )]
    story += [PageBreak()]

    story += [P("2  Observation readiness needs four separate lanes", "h1")]
    story += [P(
        "A planet can be Earth-like in bulk properties and still be impractical for a particular observation. Conversely, a non-Earth-like planet can be exceptionally valuable for atmospheric or orbital work. Combining these into one score would hide the scientific question.",
    )]
    lanes = [
        ("Transit timing", "Propagate period and epoch uncertainty to 2030-01-01. Flag transit timing variations and disclose that covariance is unavailable."),
        ("Atmospheres", "Show TSM and ESM as Kempton-style screening proxies, not exposure-time forecasts or guaranteed detections."),
        ("Radial velocity", "Estimate the Keplerian semi-amplitude while separating it from stellar activity, cadence, and instrument noise."),
        ("Reflected light", "Show maximum angular separation and an Ag=0.30 Lambertian quadrature contrast scenario; never label it instrument-detectable."),
    ]
    table_data = [[P(a, "card_title"), P(b, "card_body")] for a, b in lanes]
    t = Table(table_data, colWidths=[38 * mm, 126 * mm], repeatRows=0)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (0, -1), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [t, Spacer(1, 7 * mm)]
    story += [figure("top_candidates.png", "Figure 2. The candidate ranking remains a bulk-property evidence synthesis. Follow-up lanes are displayed independently in the Observation Follow-up Lab.")]
    story += [PageBreak()]

    story += [P("3  The visual failure was deterministic", "h1")]
    story += [P(
        "The article's figures existed, but root-relative image paths ignored the deployed /finding-earth-2 base path. Next.js requires the configured base path to be reflected in local Image sources. The blank image frames were therefore a routing defect, not missing scientific output.",
    )]
    story += [P("The implemented response", "h2")]
    for text in [
        "Centralize public-asset URL construction and migrate images, fetch calls, and internal anchors.",
        "Check every exported local src and href against the production output in CI.",
        "Expand the article from seven visuals to the complete set of sixteen reproducible figures.",
        "Use a three-region desktop layout: section navigation, readable article measure, and contextual evidence rail.",
        "Collapse to one column on narrow screens and retain captions, text alternatives, keyboard access, and visible focus.",
    ]:
        story.append(bullet(text))
    story += [figure("ranking_distribution.png", "Figure 3. A titleless publication figure used by both the paper and the web narrative, preventing duplicated or clipped headings in responsive containers.")]
    story += [PageBreak()]

    story += [P("4  Delivered upgrade architecture", "h1")]
    story += [metric_row([
        ("6,371+", "STATIC ROUTES CHECKED"),
        ("250", "TOP ROWS PER LANE"),
        ("16", "ARTICLE FIGURES"),
        ("0", "RANKING PENALTIES FROM SOURCE MIX"),
    ]), Spacer(1, 7 * mm)]
    delivered = [
        ("Asset integrity", "Base-path-safe images, fetches, routes, and export verification."),
        ("Research workspace", "Sticky contents, readable center measure, evidence rail, full-width stages, and mobile reflow."),
        ("Scientific disclosure", "Composite/default coherence metrics with nullable control flags and no automatic penalty."),
        ("Observation Follow-up Lab", "Searchable, lane-specific static tables for timing, atmospheres, RV, and reflected light."),
        ("Data resilience", "Catalogue-only rebuilds preserve successful archived MAST and DACE analyses with explicit provenance."),
        ("Reproducible visuals", "All sixteen figures regenerated; titleless paper variants avoid duplicate web headings."),
    ]
    for title, body in delivered:
        story += [KeepTogether([P(title, "h2"), P(body)])]
    story += [figure("uncertainty.png", "Figure 4. Uncertainty remains part of the evidence, not a decorative confidence badge. Nullable values and unavailable pathways stay explicit.")]
    story += [PageBreak()]

    story += [P("5  Limitations and next scientific phase", "h1")]
    limitations = [
        ("Composite rows", "Source mixing is a documented risk signal, not evidence that a row is wrong."),
        ("Ephemerides", "Linear propagation omits period-epoch covariance and cannot model unreported transit timing variations."),
        ("TSM and ESM", "Screening metrics cannot replace current ephemerides, visibility checks, saturation limits, or instrument simulators."),
        ("Reflected light", "Albedo and phase are scenario assumptions. HWO architecture remains under trade study."),
        ("Accessibility", "Automated tools catch only a subset of defects; keyboard, reflow, and scientific-description review remain manual gates."),
    ]
    for title, body in limitations:
        story += [card("", title, body), Spacer(1, 3 * mm)]
    story += [P("Recommended next phase", "h2")]
    story += [P(
        "Model competing coherent ps solutions as an explicit mixture, quantify rank stability across solution choices, add homogeneous stellar-activity context where defensible, and connect each follow-up lane to instrument-specific simulators only when their assumptions can be recorded and reproduced.",
    )]
    story += [PageBreak()]

    story += [P("Claim-to-source ledger", "h1")]
    story += [P("Primary and official sources converged on the selected priorities. Links below were accessed 28 August 2026 unless a publication date is stated.", "small")]
    refs = [
        ("NASA Exoplanet Archive", "Composite-parameter calculation notes; pscomppars may mix references while ps provides coherent published solutions.", "https://exoplanetarchive.ipac.caltech.edu/docs/pscp_calc.html"),
        ("NASA Exoplanet Archive", "Planetary Systems column definitions and TAP-accessible timing, orbital, and uncertainty fields.", "https://exoplanetarchive.ipac.caltech.edu/docs/API_PS_columns.html"),
        ("Kempton et al. (2018)", "TSM and ESM atmospheric-characterisation screening framework.", "https://arxiv.org/abs/1805.03671"),
        ("Dragomir et al. (2020 revision)", "TESS ephemeris maintenance and the rapid growth of timing uncertainty.", "https://arxiv.org/abs/1906.02197"),
        ("Martins et al. (2013)", "Reflected-light contrast dependence on radius, separation, albedo, and phase.", "https://academic.oup.com/mnras/article/436/2/1215/1125472"),
        ("NASA Science", "Habitable Worlds Observatory goals and current trade-study status.", "https://science.nasa.gov/astrophysics/programs/habitable-worlds-observatory/"),
        ("Next.js", "Production basePath behavior and static export constraints.", "https://nextjs.org/docs/pages/api-reference/config/next-config-js/basePath"),
        ("W3C", "WCAG 2.2 normative requirements and structured alternatives for complex images.", "https://www.w3.org/TR/WCAG22/"),
        ("W3C WAI", "Complex Images tutorial.", "https://www.w3.org/WAI/tutorials/images/complex/"),
        ("Microsoft Playwright", "Automated accessibility testing limitations and workflow.", "https://playwright.dev/docs/accessibility-testing"),
        ("Wilkinson et al. (2016)", "FAIR principles for machine-readable metadata and provenance.", "https://doi.org/10.1038/sdata.2016.18"),
    ]
    for i, (publisher, claim, url) in enumerate(refs, start=1):
        story.append(P(f"<b>{i}. {publisher}.</b> {claim}<br/><link href='{url}' color='#007F98'>{url}</link>", "ref"))
    story += [Spacer(1, 5 * mm), P("Research stop rationale", "h2")]
    story += [P(
        "Further broad searching was unlikely to change the first-release scope. Remaining gaps - archive covariance, homogeneous stellar-activity data, instrument-specific noise, and final HWO parameters - are explicit research boundaries rather than inputs to speculative modeling.",
    )]

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return OUT


if __name__ == "__main__":
    print(build())
