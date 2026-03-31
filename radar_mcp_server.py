"""
RADAR MCP Server
Exposes the RADAR SQLite DB as tools for the Impact Analysis Agent.

Tools:
  1. get_regulation          — full detail on one regulation by ID
  2. get_report_system_map   — which system handles which reports for a regulation
  3. get_system_capabilities — what a system can and cannot do
  4. find_regulations        — search regulations by keyword or regulator
  5. get_all_systems         — list all systems in inventory
  6. get_pending_ia          — list all reports with status Pending IA

Run:
  python3 radar_mcp_server.py

The agent connects to this server via stdio transport.
"""

import sqlite3
import json
from mcp.server.fastmcp import FastMCP

DB_PATH = "/home/ec2-user/environment/applications/regai-poc/radar.db"

mcp = FastMCP("RADAR")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── TOOL 1: Get full regulation detail ──────────────────────────────────────

@mcp.tool()
def get_regulation(regulation_id: str) -> str:
    """
    Get full details of a regulation by its ID (e.g. REG-005).
    Returns regulation metadata, associated reports, and system mappings.
    """
    conn = get_conn()
    cur = conn.cursor()

    reg = cur.execute(
        "SELECT * FROM regulations WHERE regulation_id = ?",
        (regulation_id,)
    ).fetchone()

    if not reg:
        return json.dumps({"error": f"Regulation {regulation_id} not found"})

    reports = cur.execute(
        """
        SELECT r.report_id, r.report_name, r.report_code, r.frequency,
               r.sla_days, r.sla_description, r.format,
               m.status as system_status, s.system_name
        FROM reports r
        LEFT JOIN report_system_map m ON r.report_id = m.report_id
        LEFT JOIN systems s ON m.system_id = s.system_id
        WHERE r.regulation_id = ?
        """,
        (regulation_id,)
    ).fetchall()

    regulator = cur.execute(
        "SELECT * FROM regulators WHERE regulator_id = ?",
        (reg["regulator_id"],)
    ).fetchone()

    replaces = None
    if reg["replaces_id"]:
        replaces = cur.execute(
            "SELECT regulation_id, regulation_name, status FROM regulations WHERE regulation_id = ?",
            (reg["replaces_id"],)
        ).fetchone()

    conn.close()

    result = {
        "regulation_id":    reg["regulation_id"],
        "regulation_name":  reg["regulation_name"],
        "regulation_code":  reg["regulation_code"],
        "description":      reg["description"],
        "effective_date":   reg["effective_date"],
        "status":           reg["status"],
        "regulator": {
            "id":           regulator["regulator_id"],
            "name":         regulator["name"],
            "full_name":    regulator["full_name"],
            "jurisdiction": regulator["jurisdiction"],
            "region":       regulator["region"],
        } if regulator else None,
        "replaces": {
            "regulation_id":   replaces["regulation_id"],
            "regulation_name": replaces["regulation_name"],
            "status":          replaces["status"],
        } if replaces else None,
        "reports": [
            {
                "report_id":      r["report_id"],
                "report_name":    r["report_name"],
                "report_code":    r["report_code"],
                "frequency":      r["frequency"],
                "sla_days":       r["sla_days"],
                "sla_description":r["sla_description"],
                "format":         r["format"],
                "system_name":    r["system_name"],
                "system_status":  r["system_status"],
            }
            for r in reports
        ]
    }

    return json.dumps(result, indent=2)


# ── TOOL 2: Get report-system map for a regulation ───────────────────────────

@mcp.tool()
def get_report_system_map(regulation_id: str) -> str:
    """
    Get the mapping of reports to systems for a given regulation ID.
    Shows which system currently handles each report and its status.
    Useful for understanding what needs to change when a new regulation arrives.
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT r.report_id, r.report_name, r.frequency, r.sla_description,
               s.system_id, s.system_name, s.system_type,
               m.status, m.go_live_date, m.notes
        FROM reports r
        JOIN report_system_map m ON r.report_id = m.report_id
        JOIN systems s ON m.system_id = s.system_id
        WHERE r.regulation_id = ?
        """,
        (regulation_id,)
    ).fetchall()

    conn.close()

    if not rows:
        return json.dumps({"message": f"No report-system mappings found for {regulation_id}"})

    return json.dumps([dict(r) for r in rows], indent=2)


# ── TOOL 3: Get system capabilities ─────────────────────────────────────────

@mcp.tool()
def get_system_capabilities(system_name: str) -> str:
    """
    Get the capabilities of a system by name (e.g. GRACE, Risk-Engine).
    Returns what the system supports, partially supports, and does not support.
    Use this to identify gaps when a new regulation requires specific capabilities.
    """
    conn = get_conn()
    cur = conn.cursor()

    system = cur.execute(
        "SELECT * FROM systems WHERE system_name = ?",
        (system_name,)
    ).fetchone()

    if not system:
        return json.dumps({"error": f"System '{system_name}' not found"})

    caps = cur.execute(
        """
        SELECT capability_name, supported, details
        FROM system_capabilities
        WHERE system_id = ?
        ORDER BY supported DESC
        """,
        (system["system_id"],)
    ).fetchall()

    conn.close()

    result = {
        "system_id":   system["system_id"],
        "system_name": system["system_name"],
        "system_type": system["system_type"],
        "owner_team":  system["owner_team"],
        "technology":  system["technology"],
        "notes":       system["notes"],
        "capabilities": {
            "yes":     [{"name": c["capability_name"], "details": c["details"]} for c in caps if c["supported"] == "Yes"],
            "partial": [{"name": c["capability_name"], "details": c["details"]} for c in caps if c["supported"] == "Partial"],
            "no":      [{"name": c["capability_name"], "details": c["details"]} for c in caps if c["supported"] == "No"],
        }
    }

    return json.dumps(result, indent=2)


# ── TOOL 4: Find regulations by keyword or regulator ────────────────────────

@mcp.tool()
def find_regulations(keyword: str = "", regulator_id: str = "", status: str = "") -> str:
    """
    Search for regulations by keyword (searches name and description),
    regulator ID (e.g. BCBS, ESMA), or status (Active, Pending, Under Review).
    All parameters are optional — combine them to narrow results.
    """
    conn = get_conn()
    cur = conn.cursor()

    query = """
        SELECT r.regulation_id, r.regulation_name, r.regulation_code,
               r.effective_date, r.status, r.replaces_id,
               reg.name as regulator_name, reg.jurisdiction
        FROM regulations r
        JOIN regulators reg ON r.regulator_id = reg.regulator_id
        WHERE 1=1
    """
    params = []

    if keyword:
        query += " AND (r.regulation_name LIKE ? OR r.description LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]

    if regulator_id:
        query += " AND r.regulator_id = ?"
        params.append(regulator_id)

    if status:
        query += " AND r.status = ?"
        params.append(status)

    rows = cur.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return json.dumps({"message": "No regulations found matching criteria"})

    return json.dumps([dict(r) for r in rows], indent=2)


# ── TOOL 5: Get all systems ──────────────────────────────────────────────────

@mcp.tool()
def get_all_systems() -> str:
    """
    Get the full inventory of systems in RADAR.
    Returns system name, type (Strategic/Legacy/Vendor), owner team, and technology.
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT system_id, system_name, system_type, owner_team, technology, notes FROM systems"
    ).fetchall()

    conn.close()
    return json.dumps([dict(r) for r in rows], indent=2)


# ── TOOL 6: Get all reports pending impact analysis ──────────────────────────

@mcp.tool()
def get_pending_ia() -> str:
    """
    Get all reports that are currently pending impact analysis.
    These are the reports where a system has not yet been confirmed
    and analysis is required before development can begin.
    """
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT r.report_id, r.report_name, r.frequency, r.sla_description,
               reg.regulation_name, reg.effective_date,
               rg.name as regulator_name,
               m.notes
        FROM report_system_map m
        JOIN reports r ON m.report_id = r.report_id
        JOIN regulations reg ON r.regulation_id = reg.regulation_id
        JOIN regulators rg ON reg.regulator_id = rg.regulator_id
        WHERE m.status = 'Pending IA'
        ORDER BY reg.effective_date ASC
        """
    ).fetchall()

    conn.close()

    if not rows:
        return json.dumps({"message": "No reports pending impact analysis"})

    return json.dumps([dict(r) for r in rows], indent=2)


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting RADAR MCP Server...")
    print(f"DB: {DB_PATH}")
    print("Tools: get_regulation, get_report_system_map, get_system_capabilities,")
    print("       find_regulations, get_all_systems, get_pending_ia")
    mcp.run(transport="stdio")
