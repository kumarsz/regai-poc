"""
POC 3 — Impact Analysis Agent
Input  : Artifact 1 (JSON) + Artifact Z (PDF) + IA Template
         On demand: @SK KB, @RCI KB, RADAR MCP tools
Process: Agentic loop — reads inputs, calls tools as needed, fills IA template
Output : Artifact 2 (Impact Analysis Document — JSON)

Usage:
  python3.11 impact_analysis_agent.py \
    --artifact1 artifact1_output.json \
    --artifact_z RIC_KB/frtb_final_rule_2024.pdf \
    --output artifact2_output.json
"""

import boto3
import json
import argparse
import os
import sys
import sqlite3
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

AWS_REGION  = "us-east-1"
MODEL_ID    = "us.anthropic.claude-sonnet-4-20250514-v1:0"
KB_ID_RCI   = "4IERGQ3ERC"
KB_ID_SK    = "1GN5EJNAGE"
RADAR_DB    = "/home/ec2-user/environment/applications/regai-poc/poc3/radar.db"
MAX_TOKENS  = 4096
MAX_TURNS   = 20  # max agentic loop iterations

# ── IA TEMPLATE ───────────────────────────────────────────────────────────────

IA_TEMPLATE = [
    # Regulation context
    {"id": "IA01", "section": "Regulation Context",
     "question": "What is the regulation and what does it require at a high level?"},
    {"id": "IA02", "section": "Regulation Context",
     "question": "Which existing regulation in RADAR does this replace or overlap with?"},

    # Systems impact
    {"id": "IA03", "section": "Systems Impact",
     "question": "Which systems in RADAR are affected by this regulation?"},
    {"id": "IA04", "section": "Systems Impact",
     "question": "For each affected system, what specific changes are required?"},
    {"id": "IA05", "section": "Systems Impact",
     "question": "Are there any systems gaps — capabilities required by the regulation that no current system supports?"},

    # Data impact
    {"id": "IA06", "section": "Data Impact",
     "question": "What data gaps exist between what the regulation requires and what is currently available?"},
    {"id": "IA07", "section": "Data Impact",
     "question": "Are there data retention requirements that exceed current capabilities?"},

    # Effort and timeline
    {"id": "IA08", "section": "Effort and Timeline",
     "question": "What is the estimated effort for each work stream — Low (under 1 month), Medium (1-3 months), High (over 3 months)?"},
    {"id": "IA09", "section": "Effort and Timeline",
     "question": "Is the implementation timeline feasible given the effective date and current system state?"},

    # Risk
    {"id": "IA10", "section": "Risk",
     "question": "What are the key delivery risks for this regulation?"},
    {"id": "IA11", "section": "Risk",
     "question": "What happens if this regulation is not implemented on time?"},

    # Open questions
    {"id": "IA12", "section": "Open Questions",
     "question": "What questions must be resolved with the business before development can begin?"},
    {"id": "IA13", "section": "Open Questions",
     "question": "What external dependencies exist — vendors, regulators, other teams?"},
]

# ── AWS CLIENTS ───────────────────────────────────────────────────────────────

bedrock_runtime = boto3.client("bedrock-runtime",       region_name=AWS_REGION)
bedrock_kb      = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)


# ── RADAR DB TOOLS ────────────────────────────────────────────────────────────

def radar_get_regulation(regulation_id: str) -> str:
    try:
        conn = sqlite3.connect(RADAR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        reg = cur.execute(
            "SELECT * FROM regulations WHERE regulation_id = ?",
            (regulation_id,)
        ).fetchone()
        if not reg:
            return json.dumps({"error": f"Regulation {regulation_id} not found"})
        reports = cur.execute(
            """SELECT r.report_name, r.frequency, r.sla_description, r.format,
                      s.system_name, m.status
               FROM reports r
               LEFT JOIN report_system_map m ON r.report_id = m.report_id
               LEFT JOIN systems s ON m.system_id = s.system_id
               WHERE r.regulation_id = ?""",
            (regulation_id,)
        ).fetchall()
        conn.close()
        return json.dumps({
            "regulation": dict(reg),
            "reports": [dict(r) for r in reports]
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def radar_get_system_capabilities(system_name: str) -> str:
    try:
        conn = sqlite3.connect(RADAR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        system = cur.execute(
            "SELECT * FROM systems WHERE system_name = ?", (system_name,)
        ).fetchone()
        if not system:
            return json.dumps({"error": f"System {system_name} not found"})
        caps = cur.execute(
            """SELECT capability_name, supported, details
               FROM system_capabilities WHERE system_id = ?""",
            (system["system_id"],)
        ).fetchall()
        conn.close()
        return json.dumps({
            "system": dict(system),
            "capabilities": {
                "yes":     [dict(c) for c in caps if c["supported"] == "Yes"],
                "partial": [dict(c) for c in caps if c["supported"] == "Partial"],
                "no":      [dict(c) for c in caps if c["supported"] == "No"],
            }
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def radar_find_regulations(keyword: str = "", status: str = "") -> str:
    try:
        conn = sqlite3.connect(RADAR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        query = """SELECT r.regulation_id, r.regulation_name, r.status,
                          r.effective_date, r.replaces_id, rg.name as regulator
                   FROM regulations r
                   JOIN regulators rg ON r.regulator_id = rg.regulator_id
                   WHERE 1=1"""
        params = []
        if keyword:
            query += " AND (r.regulation_name LIKE ? OR r.description LIKE ?)"
            params += [f"%{keyword}%", f"%{keyword}%"]
        if status:
            query += " AND r.status = ?"
            params.append(status)
        rows = cur.execute(query, params).fetchall()
        conn.close()
        return json.dumps([dict(r) for r in rows], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def radar_get_pending_ia() -> str:
    try:
        conn = sqlite3.connect(RADAR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            """SELECT r.report_name, r.frequency, r.sla_description,
                      reg.regulation_name, reg.effective_date, m.notes
               FROM report_system_map m
               JOIN reports r ON m.report_id = r.report_id
               JOIN regulations reg ON r.regulation_id = reg.regulation_id
               WHERE m.status = 'Pending IA'"""
        ).fetchall()
        conn.close()
        return json.dumps([dict(r) for r in rows], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def radar_get_all_systems() -> str:
    try:
        conn = sqlite3.connect(RADAR_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT system_id, system_name, system_type, owner_team, technology, notes FROM systems"
        ).fetchall()
        conn.close()
        return json.dumps([dict(r) for r in rows], indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ── KB TOOLS ──────────────────────────────────────────────────────────────────

def query_kb(kb_id: str, kb_name: str, query: str, num_results: int = 3) -> str:
    try:
        response = bedrock_kb.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": num_results}
            }
        )
        chunks = []
        for r in response.get("retrievalResults", []):
            text  = r.get("content", {}).get("text", "")
            score = r.get("score", 0)
            if text:
                chunks.append(f"[{kb_name} | score:{score:.2f}]\n{text}")
        return "\n\n---\n\n".join(chunks) if chunks else "No relevant content found."
    except Exception as e:
        return f"KB query failed: {str(e)}"


# ── TOOL DEFINITIONS FOR THE AGENT ───────────────────────────────────────────

TOOLS = [
    {
        "name": "query_sk_kb",
        "description": "Query the System Knowledge KB (@SK KB) for information about "
                       "GRACE system capabilities, data architecture, effort estimates, "
                       "and prior impact analysis examples. Use this to understand "
                       "what systems can and cannot do.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — e.g. 'GRACE Expected Shortfall capability'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "query_rci_kb",
        "description": "Query the Regulatory Circular Information KB (@RCI KB) for "
                       "historical regulations, prior circulars, and regulatory context. "
                       "Use this to understand what changed from prior frameworks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — e.g. 'Basel III VaR data retention requirements'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "radar_get_regulation",
        "description": "Get full details of an existing regulation from RADAR by its ID "
                       "(e.g. REG-003). Returns regulation metadata, reports, and system mappings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "regulation_id": {
                    "type": "string",
                    "description": "The regulation ID — e.g. REG-003"
                }
            },
            "required": ["regulation_id"]
        }
    },
    {
        "name": "radar_get_system_capabilities",
        "description": "Get the capabilities of a system in RADAR by name "
                       "(e.g. GRACE, Risk-Engine). Returns what the system supports, "
                       "partially supports, and does not support.",
        "input_schema": {
            "type": "object",
            "properties": {
                "system_name": {
                    "type": "string",
                    "description": "System name — e.g. GRACE or Risk-Engine"
                }
            },
            "required": ["system_name"]
        }
    },
    {
        "name": "radar_find_regulations",
        "description": "Search for regulations in RADAR by keyword or status. "
                       "Use this to find related or superseded regulations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Search keyword"},
                "status":  {"type": "string", "description": "Status filter — Active, Pending, Under Review"}
            }
        }
    },
    {
        "name": "radar_get_all_systems",
        "description": "Get the full inventory of systems in RADAR. "
                       "Use this to understand what systems exist before assessing impact.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "radar_get_pending_ia",
        "description": "Get all reports currently pending impact analysis in RADAR. "
                       "These are the reports that need to be assessed for this regulation.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]


# ── TOOL DISPATCHER ───────────────────────────────────────────────────────────

def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    print(f"    [Tool] {tool_name}({json.dumps(tool_input)})")
    if tool_name == "query_sk_kb":
        return query_kb(KB_ID_SK, "SK-KB", tool_input["query"])
    elif tool_name == "query_rci_kb":
        return query_kb(KB_ID_RCI, "RCI-KB", tool_input["query"])
    elif tool_name == "radar_get_regulation":
        return radar_get_regulation(tool_input["regulation_id"])
    elif tool_name == "radar_get_system_capabilities":
        return radar_get_system_capabilities(tool_input["system_name"])
    elif tool_name == "radar_find_regulations":
        return radar_find_regulations(
            tool_input.get("keyword", ""),
            tool_input.get("status", "")
        )
    elif tool_name == "radar_get_all_systems":
        return radar_get_all_systems()
    elif tool_name == "radar_get_pending_ia":
        return radar_get_pending_ia()
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ── AGENTIC LOOP ──────────────────────────────────────────────────────────────

def run_impact_analysis_agent(artifact1: dict, pdf_b64: str, pdf_name: str) -> list:

    system_prompt = """You are a senior regulatory impact analysis specialist at a major bank.

You have been given:
1. Artifact 1 — a structured summary of a new regulation with template questions answered
2. The original regulation document (Artifact Z) for detailed reference
3. Access to tools to query system knowledge, regulatory history, and the RADAR system inventory

Your job is to produce a complete Impact Analysis by answering all IA template questions.

For each question you must:
- Use the tools available to gather the information you need
- Cross-reference Artifact 1 findings with system capabilities from RADAR and @SK KB
- Identify specific gaps between what the regulation requires and what systems currently support
- Provide concrete, specific answers — not generic statements
- Tag each answer: Confirmed (backed by tool data), TBC (inferred, needs verification), Not Known

Be systematic:
1. Start by reviewing Artifact 1 to understand the regulation
2. Query RADAR to understand existing systems and regulations
3. Query @SK KB to understand system capabilities and data architecture
4. Use the information gathered to answer each IA template question

Respond with a JSON array of IA answers when you have gathered enough information.
Each answer must follow this format:
{
  "id": "IA01",
  "section": "section name",
  "question": "the question",
  "answer": "detailed answer",
  "tag": "Confirmed" | "TBC" | "Not Known",
  "tag_reason": "why this tag",
  "tools_used": ["list of tools called to answer this question"]
}
"""

    ia_template_text = json.dumps(IA_TEMPLATE, indent=2)
    artifact1_text   = json.dumps(artifact1, indent=2)

    initial_message = f"""Please perform a complete impact analysis for the following regulation.

ARTIFACT 1 — Regulation Summary:
{artifact1_text}

IA TEMPLATE — Questions to answer:
{ia_template_text}

Instructions:
1. Review Artifact 1 to understand what the regulation requires
2. Use the available tools to query RADAR and knowledge bases
3. Answer all 13 IA template questions with specific, concrete answers
4. Tag each answer appropriately

Start by calling radar_get_all_systems and radar_get_pending_ia to understand the current landscape,
then proceed to answer each IA question using the tools as needed.
"""

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": pdf_b64
                    }
                },
                {
                    "type": "text",
                    "text": initial_message
                }
            ]
        }
    ]

    turn = 0
    final_answers = None

    while turn < MAX_TURNS:
        turn += 1
        print(f"\n  [Agent turn {turn}]")

        response = bedrock_runtime.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "tools": TOOLS,
                "messages": messages
            })
        )

        result      = json.loads(response["body"].read())
        stop_reason = result.get("stop_reason")
        content     = result.get("content", [])

        print(f"    Stop reason: {stop_reason}")

        # Add assistant response to messages
        messages.append({"role": "assistant", "content": content})

        # If agent wants to use tools
        if stop_reason == "tool_use":
            tool_results = []
            for block in content:
                if block.get("type") == "tool_use":
                    tool_name   = block["name"]
                    tool_input  = block["input"]
                    tool_use_id = block["id"]

                    tool_result = dispatch_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result
                    })

            # Nudge agent to conclude if running low on turns
            if turn >= MAX_TURNS - 3:
                tool_results.append({
                    "type": "text",
                    "text": (
                        "IMPORTANT: You have gathered sufficient information. "
                        "Do NOT call any more tools. "
                        "Produce the final JSON array of all 13 IA answers NOW. "
                        "Use everything you have gathered so far."
                    )
                })

            # Add tool results back into messages
            messages.append({
                "role": "user",
                "content": tool_results
            })

        # If agent is done
        elif stop_reason == "end_turn":
            # Extract final text response
            for block in content:
                if block.get("type") == "text":
                    raw_text = block["text"].strip()
                    # Try to parse JSON from response
                    if "[" in raw_text:
                        start = raw_text.find("[")
                        end   = raw_text.rfind("]") + 1
                        json_str = raw_text[start:end]
                        try:
                            final_answers = json.loads(json_str)
                            print(f"    Agent produced {len(final_answers)} IA answers")
                        except Exception as e:
                            print(f"    JSON parse error: {e}")
                            print(f"    Raw text: {raw_text[:200]}")
            break

        else:
            print(f"    Unexpected stop reason: {stop_reason}")
            break

    return final_answers or []


# ── BUILD ARTIFACT 2 ──────────────────────────────────────────────────────────

def build_artifact2(artifact1: dict, ia_answers: list, pdf_name: str) -> dict:

    confirmed = [a for a in ia_answers if a.get("tag") == "Confirmed"]
    tbc       = [a for a in ia_answers if a.get("tag") == "TBC"]
    not_known = [a for a in ia_answers if a.get("tag") == "Not Known"]

    # Collect all tools used
    all_tools_used = set()
    for a in ia_answers:
        for t in a.get("tools_used", []):
            all_tools_used.add(t)

    artifact2 = {
        "artifact_type":       "Artifact2_ImpactAnalysis",
        "source_artifact1":    artifact1.get("source_document"),
        "generated_at":        datetime.utcnow().isoformat() + "Z",
        "model_used":          MODEL_ID,
        "kb_rci_used":         KB_ID_RCI,
        "kb_sk_used":          KB_ID_SK,
        "radar_db_used":       RADAR_DB,
        "tools_invoked":       list(all_tools_used),
        "regulation_summary":  artifact1.get("summary", ""),
        "statistics": {
            "total_questions": len(ia_answers),
            "confirmed":       len(confirmed),
            "tbc":             len(tbc),
            "not_known":       len(not_known),
        },
        "ia_answers": ia_answers,
        "artifact1_reference": {
            "confirmed": artifact1.get("statistics", {}).get("confirmed"),
            "tbc":       artifact1.get("statistics", {}).get("tbc"),
            "not_known": artifact1.get("statistics", {}).get("not_known"),
        }
    }
    return artifact2


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="POC3 Impact Analysis Agent")
    parser.add_argument("--artifact1",  required=True,
                        help="Path to Artifact 1 JSON")
    parser.add_argument("--artifact_z", required=True,
                        help="Path to Artifact Z PDF (original regulation)")
    parser.add_argument("--output",     default="artifact2_output.json",
                        help="Output path for Artifact 2 JSON")
    args = parser.parse_args()

    # Validate inputs
    for path in [args.artifact1, args.artifact_z]:
        if not os.path.exists(path):
            print(f"Error: File not found — {path}")
            sys.exit(1)

    if not os.path.exists(RADAR_DB):
        print(f"Error: RADAR DB not found — {RADAR_DB}")
        print("Run radar_db_setup.py first.")
        sys.exit(1)

    # Load Artifact 1
    with open(args.artifact1) as f:
        artifact1 = json.load(f)

    # Load Artifact Z as base64
    import base64
    with open(args.artifact_z, "rb") as f:
        pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    pdf_name = os.path.basename(args.artifact_z)

    print(f"\n=== POC 3 — Impact Analysis Agent ===")
    print(f"Artifact 1 : {args.artifact1}")
    print(f"Artifact Z : {pdf_name}")
    print(f"Output     : {args.output}")
    print(f"Model      : {MODEL_ID}")
    print(f"@SK KB     : {KB_ID_SK}")
    print(f"@RCI KB    : {KB_ID_RCI}")
    print(f"RADAR DB   : {RADAR_DB}")
    print(f"Max turns  : {MAX_TURNS}")
    print()

    # Run agent
    print("Starting Impact Analysis Agent...")
    ia_answers = run_impact_analysis_agent(artifact1, pdf_b64, pdf_name)

    if not ia_answers:
        print("Error: Agent did not produce answers. Check logs above.")
        sys.exit(1)

    # Build Artifact 2
    artifact2 = build_artifact2(artifact1, ia_answers, pdf_name)

    # Save
    with open(args.output, "w") as f:
        json.dump(artifact2, f, indent=2)

    # Print results
    print(f"\n=== ARTIFACT 2 COMPLETE ===")
    print(f"IA Questions answered : {artifact2['statistics']['total_questions']}")
    print(f"  Confirmed           : {artifact2['statistics']['confirmed']}")
    print(f"  TBC                 : {artifact2['statistics']['tbc']}")
    print(f"  Not Known           : {artifact2['statistics']['not_known']}")
    print(f"Tools invoked         : {', '.join(artifact2['tools_invoked'])}")
    print(f"\nOutput saved to: {args.output}")

    # Print TBC and Not Known
    tbc_items = [a for a in ia_answers if a.get("tag") == "TBC"]
    nk_items  = [a for a in ia_answers if a.get("tag") == "Not Known"]

    if tbc_items:
        print(f"\n--- TBC items (BA must verify) ---")
        for a in tbc_items:
            print(f"  {a.get('id','?')}: {a.get('question','')}")
            print(f"       {a.get('tag_reason','')}")

    if nk_items:
        print(f"\n--- Not Known items ---")
        for a in nk_items:
            print(f"  {a.get('id','?')}: {a.get('question','')}")
            print(f"       {a.get('tag_reason','')}")


if __name__ == "__main__":
    main()