import sqlite3
import os

DB_PATH = "/home/ec2-user/environment/applications/regai-poc/radar.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ── SCHEMA ──────────────────────────────────────────────────────────────────

cur.executescript("""

-- 1. Regulators
CREATE TABLE IF NOT EXISTS regulators (
    regulator_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    full_name       TEXT,
    jurisdiction    TEXT,
    region          TEXT,
    website         TEXT
);

-- 2. Regulations
CREATE TABLE IF NOT EXISTS regulations (
    regulation_id       TEXT PRIMARY KEY,
    regulator_id        TEXT NOT NULL,
    regulation_name     TEXT NOT NULL,
    regulation_code     TEXT,
    description         TEXT,
    effective_date      TEXT,
    status              TEXT,   -- Active | Superseded | Pending | Under Review
    replaces_id         TEXT,   -- FK to regulations.regulation_id
    FOREIGN KEY (regulator_id) REFERENCES regulators(regulator_id),
    FOREIGN KEY (replaces_id)  REFERENCES regulations(regulation_id)
);

-- 3. Reports  (one regulation can have multiple reports)
CREATE TABLE IF NOT EXISTS reports (
    report_id           TEXT PRIMARY KEY,
    regulation_id       TEXT NOT NULL,
    report_name         TEXT NOT NULL,
    report_code         TEXT,
    frequency           TEXT,   -- Daily | Monthly | Quarterly | Annual
    sla_days            INTEGER,
    sla_description     TEXT,
    format              TEXT,   -- XML | CSV | XBRL | PDF
    FOREIGN KEY (regulation_id) REFERENCES regulations(regulation_id)
);

-- 4. Systems  (applications that process regulatory reports)
CREATE TABLE IF NOT EXISTS systems (
    system_id       TEXT PRIMARY KEY,
    system_name     TEXT NOT NULL,
    system_type     TEXT,   -- Strategic | Legacy | Vendor | Decommissioned
    owner_team      TEXT,
    technology      TEXT,
    notes           TEXT
);

-- 5. Report-System mapping  (which system handles which report)
CREATE TABLE IF NOT EXISTS report_system_map (
    map_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id       TEXT NOT NULL,
    system_id       TEXT NOT NULL,
    status          TEXT,   -- Live | In Development | Pending Impact Analysis | Decommissioned
    go_live_date    TEXT,
    notes           TEXT,
    FOREIGN KEY (report_id)  REFERENCES reports(report_id),
    FOREIGN KEY (system_id)  REFERENCES systems(system_id)
);

-- 6. System capabilities
CREATE TABLE IF NOT EXISTS system_capabilities (
    capability_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id           TEXT NOT NULL,
    capability_name     TEXT NOT NULL,
    supported           TEXT,   -- Yes | Partial | No
    details             TEXT,
    FOREIGN KEY (system_id) REFERENCES systems(system_id)
);

-- 7. Impact analysis log  (track what has been analysed)
CREATE TABLE IF NOT EXISTS impact_analysis_log (
    analysis_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    regulation_id       TEXT NOT NULL,
    analysis_date       TEXT,
    analyst             TEXT,
    artifact1_path      TEXT,
    artifact2_path      TEXT,
    status              TEXT,   -- Draft | In Review | Complete
    notes               TEXT,
    FOREIGN KEY (regulation_id) REFERENCES regulations(regulation_id)
);

""")

# ── SEED DATA ────────────────────────────────────────────────────────────────

# Regulators
regulators = [
    ("BCBS",  "BCBS",  "Basel Committee on Banking Supervision", "Global",    "Global",  "https://www.bis.org/bcbs"),
    ("FRB",   "FRB",   "Federal Reserve Board",                  "USA",       "Americas","https://www.federalreserve.gov"),
    ("PRA",   "PRA",   "Prudential Regulation Authority",        "UK",        "EMEA",    "https://www.bankofengland.co.uk/pra"),
    ("ESMA",  "ESMA",  "European Securities and Markets Authority","EU",      "EMEA",    "https://www.esma.europa.eu"),
    ("OCC",   "OCC",   "Office of the Comptroller of the Currency","USA",     "Americas","https://www.occ.treas.gov"),
    ("MAS",   "MAS",   "Monetary Authority of Singapore",        "Singapore", "APAC",    "https://www.mas.gov.sg"),
]
cur.executemany(
    "INSERT OR IGNORE INTO regulators VALUES (?,?,?,?,?,?)",
    regulators
)

# Regulations
regulations = [
    ("REG-001","BCBS","Basel III LCR",      "BCBS-LCR-2013",
     "Liquidity Coverage Ratio — short-term liquidity standard",
     "2015-01-01","Active",None),

    ("REG-002","BCBS","Basel III NSFR",     "BCBS-NSFR-2014",
     "Net Stable Funding Ratio — longer-term stable funding standard",
     "2018-01-01","Active",None),

    ("REG-003","BCBS","Basel III Market Risk (VaR)","BCBS-MR-2016",
     "Market risk capital requirements using Value-at-Risk framework",
     "2016-01-01","Under Review",None),

    ("REG-004","ESMA","EMIR Trade Reporting","EMIR-2012",
     "Derivatives trade reporting to trade repositories",
     "2014-02-12","Active",None),

    ("REG-005","BCBS","FRTB Standardised Approach","BCBS-2024-FRTB-REV3",
     "FRTB — SA capital charge by risk class, replaces VaR SA",
     "2026-01-01","Pending","REG-003"),

    ("REG-006","BCBS","FRTB Internal Model Approach","BCBS-2024-FRTB-REV3",
     "FRTB — IMA using Expected Shortfall at 97.5%, replaces VaR IMA",
     "2026-01-01","Pending","REG-003"),

    ("REG-007","MAS","MAS 610 — Statistical Reporting","MAS610-2021",
     "Statistical returns on assets, liabilities, and off-balance sheet items",
     "2021-04-01","Active",None),
]
cur.executemany(
    "INSERT OR IGNORE INTO regulations VALUES (?,?,?,?,?,?,?,?)",
    regulations
)

# Reports
reports = [
    ("RPT-001","REG-001","LCR Daily Report",    "FR2052a",  "Daily",    1,  "T+1 09:00 EST",  "XML"),
    ("RPT-002","REG-002","NSFR Quarterly Report","FSA047",  "Quarterly",30, "Q+30 calendar days","XBRL"),
    ("RPT-003","REG-003","Market Risk VaR Report","FFIEC102","Quarterly",45,"Q+45 calendar days","XML"),
    ("RPT-004","REG-004","EMIR Trade Report",    "EMIR-GTR","Daily",    1,  "T+1 12:00 UTC",   "XML"),
    ("RPT-005","REG-005","FRTB-SA Monthly",      "FRTB-SA", "Monthly",  15, "M+15 business days","XBRL"),
    ("RPT-006","REG-006","FRTB-IMA Monthly",     "FRTB-IMA","Monthly",  15, "M+15 business days","XBRL"),
    ("RPT-007","REG-006","NMRF Quarterly",       "NMRF-Q",  "Quarterly",30, "Q+30 calendar days","XML"),
    ("RPT-008","REG-006","Desk Approval Annual", "DESK-ANN","Annual",   60, "Year+60 calendar days","PDF"),
    ("RPT-009","REG-007","MAS 610 Monthly",      "MAS610",  "Monthly",  20, "M+20 business days","XML"),
]
cur.executemany(
    "INSERT OR IGNORE INTO reports VALUES (?,?,?,?,?,?,?,?)",
    reports
)

# Systems
systems = [
    ("SYS-001","GRACE",    "Strategic","RegTech Bengaluru",
     "Java / Oracle Exadata",
     "Strategic regulatory reporting platform — primary system for all new regulations"),

    ("SYS-002","Legacy-App-1","Legacy","RegTech Bengaluru",
     "Java / Oracle 11g",
     "Handles LCR daily submissions — migration to GRACE in backlog"),

    ("SYS-003","Legacy-App-2","Legacy","RegTech Bengaluru",
     "Java / Oracle 11g",
     "Handles NSFR quarterly — migration to GRACE in backlog"),

    ("SYS-004","Legacy-App-3","Legacy","RegTech Bengaluru",
     "Java / Sybase",
     "Handles EMIR trade reporting — vendor dependency"),

    ("SYS-005","Legacy-App-4","Legacy","RegTech Bengaluru",
     "Python / Oracle 11g",
     "Handles MAS 610 — APAC submissions"),

    ("SYS-006","Risk-Engine","Strategic","Market Risk Technology",
     "C++ / kdb+",
     "Core risk calculation engine — produces VaR, ES, sensitivities"),
]
cur.executemany(
    "INSERT OR IGNORE INTO systems VALUES (?,?,?,?,?,?)",
    systems
)

# Report-System map
report_system_map = [
    ("RPT-001","SYS-002","Live",        "2015-01-01","LCR via Legacy-App-1"),
    ("RPT-002","SYS-003","Live",        "2018-01-01","NSFR via Legacy-App-2"),
    ("RPT-003","SYS-001","Live",        "2020-06-01","VaR market risk via GRACE"),
    ("RPT-004","SYS-004","Live",        "2014-02-12","EMIR via Legacy-App-3"),
    ("RPT-005","SYS-001","Pending IA",  None,        "FRTB-SA — system TBD, GRACE candidate"),
    ("RPT-006","SYS-001","Pending IA",  None,        "FRTB-IMA — system TBD, GRACE candidate"),
    ("RPT-007","SYS-001","Pending IA",  None,        "NMRF — system TBD"),
    ("RPT-008","SYS-001","Pending IA",  None,        "Desk approval — system TBD"),
    ("RPT-009","SYS-005","Live",        "2021-04-01","MAS 610 via Legacy-App-4"),
]
cur.executemany(
    "INSERT OR IGNORE INTO report_system_map (report_id,system_id,status,go_live_date,notes) VALUES (?,?,?,?,?)",
    report_system_map
)

# System capabilities
system_capabilities = [
    # GRACE
    ("SYS-001","VaR calculation",               "Yes",     "Historical simulation, 99% confidence, 10-day horizon"),
    ("SYS-001","Expected Shortfall (ES)",        "Partial", "95% confidence supported. 97.5% requires Risk-Engine upgrade"),
    ("SYS-001","P&L Attribution Testing (PLAT)", "No",      "PLAT module not built — new development required"),
    ("SYS-001","Historical data depth",          "Partial", "5 years available in data warehouse. FRTB requires 10 years"),
    ("SYS-001","Desk-level reporting",           "Partial", "Firm-level aggregation only. Desk-level requires schema change"),
    ("SYS-001","NMRF identification",            "No",      "Not in scope for current GRACE version"),
    ("SYS-001","XBRL output format",             "Yes",     "XBRL taxonomy v2.1 supported"),
    ("SYS-001","XML output format",              "Yes",     "XML schema generation supported"),
    ("SYS-001","Backtesting",                    "Partial", "Firm-level backtesting available. Desk-level not supported"),

    # Risk Engine
    ("SYS-006","VaR calculation",                "Yes",     "Full VaR suite — historical, parametric, Monte Carlo"),
    ("SYS-006","Expected Shortfall (ES)",         "Yes",     "ES at any confidence level — upgrade available for 97.5%"),
    ("SYS-006","Sensitivity-based approach (SBA)","Yes",     "Delta, vega, curvature sensitivities available"),
    ("SYS-006","NMRF identification",             "Partial", "Risk factor bucketing exists — NMRF classification logic needed"),
    ("SYS-006","Historical data depth",           "Yes",     "10+ years of risk factor data available in kdb+"),
    ("SYS-006","P&L feed",                        "Yes",     "Real-time P&L from front office — integration exists"),

    # Legacy-App-1
    ("SYS-002","LCR calculation",                "Yes",     "Full LCR calculation and submission"),
    ("SYS-002","Daily submission",               "Yes",     "Automated T+1 submission to FRB"),

    # Legacy-App-3
    ("SYS-004","EMIR reporting",                 "Yes",     "Full EMIR GTR submission"),
    ("SYS-004","Vendor dependency",              "Yes",     "Vendor-managed — changes require vendor engagement"),
]
cur.executemany(
    "INSERT OR IGNORE INTO system_capabilities (system_id,capability_name,supported,details) VALUES (?,?,?,?)",
    system_capabilities
)

conn.commit()
conn.close()

print(f"RADAR DB created at: {DB_PATH}")
print("\nTables created and populated:")
print("  regulators          —", len(regulators), "rows")
print("  regulations         —", len(regulations), "rows")
print("  reports             —", len(reports), "rows")
print("  systems             —", len(systems), "rows")
print("  report_system_map   —", len(report_system_map), "rows")
print("  system_capabilities —", len(system_capabilities), "rows")
print("\nRADAR DB ready.")
