"""
Generate mock regulatory documents for @RCI Knowledge Base
Produces 3 PDFs:
  1. basel_iii_market_risk_var.pdf     — historical regulation (being replaced)
  2. frtb_consultation_paper.pdf       — historical consultation paper
  3. frtb_final_rule_2024.pdf          — new regulation (Artifact Z)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
import os

OUTPUT_DIR = "/home/claude/rci_docs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Title'],
    fontSize=18,
    spaceAfter=12,
    textColor=colors.HexColor('#1F3864')
)
h1_style = ParagraphStyle(
    'CustomH1',
    parent=styles['Heading1'],
    fontSize=14,
    spaceBefore=18,
    spaceAfter=8,
    textColor=colors.HexColor('#1F3864')
)
h2_style = ParagraphStyle(
    'CustomH2',
    parent=styles['Heading2'],
    fontSize=12,
    spaceBefore=12,
    spaceAfter=6,
    textColor=colors.HexColor('#2E75B6')
)
body_style = ParagraphStyle(
    'CustomBody',
    parent=styles['Normal'],
    fontSize=10,
    spaceAfter=8,
    leading=16
)
meta_style = ParagraphStyle(
    'Meta',
    parent=styles['Normal'],
    fontSize=9,
    textColor=colors.HexColor('#666666'),
    spaceAfter=4
)


def hr():
    return HRFlowable(width="100%", thickness=0.5,
                      color=colors.HexColor('#2E75B6'), spaceAfter=12)


def spacer(h=12):
    return Spacer(1, h)


# ── DOCUMENT 1: Basel III Market Risk (VaR) — Historical ─────────────────────

def build_doc1():
    path = os.path.join(OUTPUT_DIR, "basel_iii_market_risk_var.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    story = []

    story.append(Paragraph("Basel III — Minimum Capital Requirements for Market Risk", title_style))
    story.append(Paragraph("Regulatory Circular | BCBS | Document Ref: BCBS-MR-2016", meta_style))
    story.append(Paragraph("Effective Date: 1 January 2016 | Status: Under Review (to be superseded by FRTB)", meta_style))
    story.append(hr())
    story.append(spacer())

    story.append(Paragraph("1. Introduction and Scope", h1_style))
    story.append(Paragraph(
        "This circular sets out the minimum capital requirements for market risk under the Basel III framework. "
        "It applies to all internationally active banks and covers positions in the trading book and foreign exchange "
        "and commodity positions in the banking book. The framework uses Value-at-Risk (VaR) as the primary risk measure "
        "for internal model approaches.",
        body_style))

    story.append(Paragraph("2. Risk Measurement — Value-at-Risk Framework", h1_style))

    story.append(Paragraph("2.1 Internal Models Approach (IMA)", h2_style))
    story.append(Paragraph(
        "Banks using the Internal Models Approach must calculate VaR using the following parameters: "
        "confidence level of 99 percent on a one-tailed basis, a minimum holding period of 10 trading days, "
        "and a historical observation period of at least one year. The VaR measure must be calculated on a "
        "daily basis. Banks must also calculate a stressed VaR (sVaR) based on a continuous 12-month period "
        "of significant financial stress.",
        body_style))

    story.append(Paragraph("2.2 Standardised Approach (SA)", h2_style))
    story.append(Paragraph(
        "Banks not approved for IMA must use the Standardised Approach. The SA calculates capital charges "
        "separately for each risk category: interest rate risk, equity risk, foreign exchange risk, commodity "
        "risk, and options risk. Capital charges are summed with limited recognition of offsets between "
        "different risk categories.",
        body_style))

    story.append(Paragraph("3. Reporting Requirements", h1_style))

    data = [
        ["Report", "Frequency", "SLA", "Format"],
        ["Market Risk VaR Report (FFIEC 102)", "Quarterly", "Q+45 calendar days", "XML"],
        ["Stressed VaR Disclosure", "Quarterly", "Q+45 calendar days", "XML"],
        ["IMA Model Approval Status", "Annual", "Year+60 days", "PDF"],
    ]
    t = Table(data, colWidths=[6*cm, 3*cm, 4*cm, 2*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3864')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(spacer())

    story.append(Paragraph("4. Data Requirements", h1_style))
    story.append(Paragraph(
        "Banks must maintain at least one year of historical price data for all risk factors included in the "
        "IMA perimeter. Data must be updated at minimum every three months and reassessed whenever market "
        "prices are subject to material changes. Banks must have documented processes for data quality "
        "management and gap filling procedures.",
        body_style))

    story.append(Paragraph("5. Backtesting Requirements", h1_style))
    story.append(Paragraph(
        "Banks must backtest their VaR models by comparing daily VaR estimates against actual and hypothetical "
        "profit and loss outcomes. Backtesting must be performed at the firm-wide level using both actual and "
        "hypothetical P&L. Results must be reported to supervisors quarterly. Banks with excessive exceptions "
        "may be subject to additional capital add-ons.",
        body_style))

    story.append(Paragraph("6. Relationship to FRTB", h1_style))
    story.append(Paragraph(
        "This circular will be superseded by the Fundamental Review of the Trading Book (FRTB) framework "
        "effective 1 January 2026. Banks should begin parallel run activities from July 2025. Key changes "
        "under FRTB include replacement of VaR with Expected Shortfall, introduction of desk-level model "
        "approval, and more granular treatment of non-modellable risk factors. See BCBS-2024-FRTB-REV3 "
        "for the full FRTB framework.",
        body_style))

    doc.build(story)
    print(f"Created: {path}")
    return path


# ── DOCUMENT 2: FRTB Consultation Paper — Historical ─────────────────────────

def build_doc2():
    path = os.path.join(OUTPUT_DIR, "frtb_consultation_paper_2019.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    story = []

    story.append(Paragraph(
        "Fundamental Review of the Trading Book — Consultation Paper",
        title_style))
    story.append(Paragraph(
        "Consultative Document | BCBS | Document Ref: BCBS-FRTB-CP-2019",
        meta_style))
    story.append(Paragraph(
        "Issued: March 2019 | Consultation Period: March 2019 — June 2019",
        meta_style))
    story.append(hr())
    story.append(spacer())

    story.append(Paragraph("Executive Summary", h1_style))
    story.append(Paragraph(
        "The Basel Committee on Banking Supervision is consulting on proposed revisions to the Fundamental "
        "Review of the Trading Book framework originally published in January 2016. This consultation paper "
        "sets out targeted amendments based on industry feedback and quantitative impact studies conducted "
        "between 2016 and 2019. Key areas of revision include the Expected Shortfall calibration, "
        "the P&L attribution test methodology, and the treatment of non-modellable risk factors.",
        body_style))

    story.append(Paragraph("1. Background", h1_style))
    story.append(Paragraph(
        "The FRTB framework was first published in January 2016 as part of the Basel III post-crisis reforms. "
        "Following publication, the Committee conducted extensive quantitative impact studies with participating "
        "banks across multiple jurisdictions. The studies revealed that certain aspects of the framework "
        "produced unintended consequences, particularly in the treatment of securitisation positions and "
        "the operational requirements for the P&L attribution test.",
        body_style))

    story.append(Paragraph("2. Proposed Revisions to Expected Shortfall", h1_style))
    story.append(Paragraph(
        "The Committee proposes to maintain the Expected Shortfall confidence level at 97.5 percent "
        "for the internal models approach. However, the liquidity horizon scaling methodology is being "
        "revised to reduce cliff effects at liquidity horizon boundaries. Banks will be permitted to use "
        "a simplified approach for calculating ES across liquidity horizons where the full methodology "
        "produces disproportionate operational burden.",
        body_style))

    story.append(Paragraph("3. P&L Attribution Test Revisions", h1_style))
    story.append(Paragraph(
        "The P&L attribution test (PLAT) methodology is being revised to address concerns raised by "
        "industry participants. The proposed revisions include: (a) widening the thresholds for the "
        "unexplained P&L ratio from 10 percent to 20 percent, (b) introducing a traffic light approach "
        "with amber and red zones rather than a binary pass/fail, and (c) allowing a 12-month observation "
        "window rather than a 250-day window for the mean ratio test.",
        body_style))

    story.append(Paragraph("4. Non-Modellable Risk Factors", h1_style))
    story.append(Paragraph(
        "The treatment of non-modellable risk factors (NMRFs) has been identified as a significant source "
        "of complexity and capital volatility. The consultation proposes a revised bucketing methodology "
        "for NMRFs that reduces the number of required stress scenarios and allows greater use of "
        "historical data where available. Banks with limited NMRF exposure may qualify for a simplified "
        "treatment subject to supervisory approval.",
        body_style))

    story.append(Paragraph("5. Implementation Timeline Considerations", h1_style))
    story.append(Paragraph(
        "Respondents to the 2016 framework consistently raised concerns about implementation timelines. "
        "The Committee acknowledges that the operational changes required — particularly desk-level P&L "
        "systems, risk factor eligibility processes, and historical data infrastructure — require "
        "substantial investment. The Committee is considering a phased implementation approach with "
        "a mandatory parallel run period prior to full implementation.",
        body_style))

    story.append(Paragraph("6. Questions for Consultation", h1_style))
    story.append(Paragraph(
        "The Committee invites responses to the following questions: (1) Are the proposed revisions to "
        "the ES calibration appropriate and operationally feasible? (2) Do the PLAT revisions adequately "
        "address the concerns raised in the QIS? (3) Are there additional simplifications to the NMRF "
        "treatment that would reduce operational burden without compromising risk sensitivity? "
        "Responses should be submitted by 30 June 2019.",
        body_style))

    doc.build(story)
    print(f"Created: {path}")
    return path


# ── DOCUMENT 3: FRTB Final Rule 2024 — New Regulation (Artifact Z) ───────────

def build_doc3():
    path = os.path.join(OUTPUT_DIR, "frtb_final_rule_2024.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=2.5*cm, rightMargin=2.5*cm,
                            topMargin=2.5*cm, bottomMargin=2.5*cm)
    story = []

    story.append(Paragraph(
        "Basel IV — Fundamental Review of the Trading Book (FRTB)",
        title_style))
    story.append(Paragraph(
        "Final Rule | BCBS | Document Ref: BCBS-2024-FRTB-REV3",
        meta_style))
    story.append(Paragraph(
        "Effective Date: 1 January 2026 | First Submission: 31 January 2026 | Status: Pending Implementation",
        meta_style))
    story.append(hr())
    story.append(spacer())

    story.append(Paragraph("1. Scope and Objective", h1_style))
    story.append(Paragraph(
        "This circular revises the minimum capital requirements for market risk under the Fundamental "
        "Review of the Trading Book. It replaces the existing Value-at-Risk (VaR) framework with an "
        "Expected Shortfall (ES) measure to better capture tail risk under stress conditions. This "
        "document supersedes BCBS-MR-2016 in its entirety with effect from 1 January 2026.",
        body_style))

    story.append(Paragraph("2. Key Changes from Prior Framework", h1_style))

    story.append(Paragraph("2.1 Risk Measure — VaR replaced by Expected Shortfall", h2_style))
    story.append(Paragraph(
        "The primary risk measure for the Internal Models Approach (IMA) changes from Value-at-Risk "
        "at 99 percent confidence to Expected Shortfall at 97.5 percent confidence level. Expected "
        "Shortfall better captures tail risk by measuring the average loss in the worst 2.5 percent "
        "of scenarios rather than the threshold loss at the 99th percentile. Banks must upgrade their "
        "risk calculation infrastructure to support ES at the specified confidence level.",
        body_style))

    story.append(Paragraph("2.2 Desk-Level Model Approval", h2_style))
    story.append(Paragraph(
        "A new trading desk-level approval process is introduced for IMA eligibility. Each trading desk "
        "must pass both the P&L attribution test (PLAT) and backtesting requirements independently to "
        "qualify for IMA treatment. Desks that fail these tests must use the Standardised Approach for "
        "their positions. Desk-level approval must be reviewed and reconfirmed annually.",
        body_style))

    story.append(Paragraph("2.3 P&L Attribution Test", h2_style))
    story.append(Paragraph(
        "Banks must perform P&L attribution testing at the trading desk level on a monthly basis. "
        "The PLAT compares the risk-theoretical P&L (RTPL) produced by the risk model against the "
        "hypothetical P&L (HPL) produced by the front office pricing system. Desks must pass both "
        "the mean ratio test and the variance ratio test. A traffic light system applies: green zone "
        "indicates full IMA eligibility, amber zone triggers capital add-ons, red zone requires "
        "reversion to Standardised Approach.",
        body_style))

    story.append(Paragraph("2.4 Non-Modellable Risk Factors", h2_style))
    story.append(Paragraph(
        "Risk factors that do not meet the modellability criteria must be capitalised separately as "
        "non-modellable risk factors (NMRFs). A risk factor is modellable if the bank can demonstrate "
        "at least 24 real price observations per year, with no gap longer than one month. NMRFs are "
        "capitalised using a stress scenario approach based on the most severe 12-month stress period "
        "available. NMRF capital is additive to the ES-based IMA capital.",
        body_style))

    story.append(Paragraph("3. Reporting Requirements", h1_style))

    data = [
        ["Report", "Code", "Frequency", "SLA", "Format"],
        ["FRTB Standardised Approach", "FRTB-SA", "Monthly", "M+15 business days", "XBRL"],
        ["FRTB Internal Model — ES", "FRTB-IMA", "Monthly", "M+15 business days", "XBRL"],
        ["Non-Modellable Risk Factors", "NMRF-Q", "Quarterly", "Q+30 calendar days", "XML"],
        ["Desk-Level Approval Status", "DESK-ANN", "Annual", "Year+60 calendar days", "PDF"],
    ]
    t = Table(data, colWidths=[4.5*cm, 2.5*cm, 2.5*cm, 4*cm, 2*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3864')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(spacer())

    story.append(Paragraph("4. Data Requirements", h1_style))
    story.append(Paragraph(
        "Banks must maintain a minimum of 10 years of historical price data for all risk factors "
        "in the IMA perimeter. This represents an increase from the one-year minimum under the "
        "current VaR framework. Real-time P&L data feeds from front office systems are required "
        "to support the PLAT. Risk factor eligibility determination must be documented, reviewed, "
        "and submitted to the supervisor quarterly.",
        body_style))

    story.append(Paragraph("5. Standardised Approach Capital Floor", h1_style))
    story.append(Paragraph(
        "The FRTB Standardised Approach serves dual purposes: as a standalone capital charge for "
        "banks not approved for IMA, and as an output floor for IMA banks. IMA capital charges "
        "must not fall below 72.5 percent of the SA capital charge at the aggregate level. Banks "
        "must therefore calculate both SA and IMA charges regardless of their approved approach.",
        body_style))

    story.append(Paragraph("6. Implementation Timeline", h1_style))

    data2 = [
        ["Milestone", "Date"],
        ["Parallel run begins — calculate both old and new framework", "1 July 2025"],
        ["Final FRTB framework go-live", "1 January 2026"],
        ["First FRTB-SA monthly submission due", "31 January 2026"],
        ["First FRTB-IMA monthly submission due (if approved)", "31 January 2026"],
        ["First NMRF quarterly submission due", "30 April 2026"],
        ["First desk-level approval annual disclosure", "31 March 2027"],
    ]
    t2 = Table(data2, colWidths=[12*cm, 4*cm])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F3864')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#F5F5F5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(spacer())

    story.append(Paragraph("7. Transition from VaR Framework", h1_style))
    story.append(Paragraph(
        "Banks currently using BCBS-MR-2016 must transition all systems, processes, and governance "
        "frameworks to the FRTB requirements by 1 January 2026. Key transition activities include: "
        "(a) upgrading risk calculation engines to support ES at 97.5 percent confidence, "
        "(b) building PLAT infrastructure including real-time P&L feeds and comparison logic, "
        "(c) extending historical data infrastructure from one year to ten years, "
        "(d) implementing desk-level reporting and approval workflows, and "
        "(e) developing NMRF identification and capitalisation processes. "
        "Banks should submit transition plans to their national supervisor by 31 December 2024.",
        body_style))

    doc.build(story)
    print(f"Created: {path}")
    return path


# ── RUN ALL ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating @RCI KB documents...\n")
    p1 = build_doc1()
    p2 = build_doc2()
    p3 = build_doc3()
    print(f"\nAll documents created in: {OUTPUT_DIR}")
    print("\nFiles ready to upload to @RCI KB:")
    print(f"  1. {os.path.basename(p1)}  — historical (current VaR framework)")
    print(f"  2. {os.path.basename(p2)}  — historical (FRTB consultation paper)")
    print(f"  3. {os.path.basename(p3)}  — new regulation (Artifact Z / FRTB final rule)")
