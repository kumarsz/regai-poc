"""
POC 3 — Summarisation Chain
Input  : Artifact Z (new regulation PDF) + Summarisation Template
Process: Read regulation -> Answer template questions -> Tag each answer
Output : Artifact 1 (structured JSON + summary)

Usage:
  python3.11 summarisation_chain.py \
    --artifact_z frtb_final_rule_2024.pdf \
    --output artifact1_output.json
"""

import boto3
import json
import argparse
import os
import sys
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

AWS_REGION   = "us-east-1"
MODEL_ID     = "us.anthropic.claude-sonnet-4-20250514-v1:0"
KB_ID_RCI    = "4IERGQ3ERC"
MAX_TOKENS   = 4096

# ── SUMMARISATION TEMPLATE ────────────────────────────────────────────────────
# These are the standard questions the BA needs answered for every new regulation

SUMMARISATION_TEMPLATE = [
    # Identification
    {"id": "Q01", "section": "Identification",  "question": "What is the full name of the regulation?"},
    {"id": "Q02", "section": "Identification",  "question": "What is the document reference or circular number?"},
    {"id": "Q03", "section": "Identification",  "question": "Who is the regulator issuing this regulation?"},
    {"id": "Q04", "section": "Identification",  "question": "What jurisdiction or region does this regulation apply to?"},

    # Timeline
    {"id": "Q05", "section": "Timeline",        "question": "What is the effective date of this regulation?"},
    {"id": "Q06", "section": "Timeline",        "question": "When is the first submission due?"},
    {"id": "Q07", "section": "Timeline",        "question": "Is there a parallel run period? If so, when does it start and end?"},

    # Scope
    {"id": "Q08", "section": "Scope",           "question": "What risk domain or business area does this regulation cover?"},
    {"id": "Q09", "section": "Scope",           "question": "Does this regulation replace or supersede an existing regulation? If so, which one?"},
    {"id": "Q10", "section": "Scope",           "question": "What are the key changes from the prior framework?"},

    # Reporting
    {"id": "Q11", "section": "Reporting",       "question": "What reports must be submitted? List each report with its frequency and SLA."},
    {"id": "Q12", "section": "Reporting",       "question": "What format are the reports required in (XML, XBRL, CSV, PDF)?"},

    # Data
    {"id": "Q13", "section": "Data",            "question": "What data is required to produce the reports? Are there specific data retention requirements?"},
    {"id": "Q14", "section": "Data",            "question": "Are there new calculation methodologies required? If so, describe them."},

    # Impact indicators
    {"id": "Q15", "section": "Impact",          "question": "What business areas or teams are likely to be affected?"},
    {"id": "Q16", "section": "Impact",          "question": "What systems are likely to be affected based on the regulation description?"},
    {"id": "Q17", "section": "Impact",          "question": "What is the estimated impact level — High, Medium, or Low — and why?"},
]

# ── AWS CLIENTS ───────────────────────────────────────────────────────────────

bedrock_runtime = boto3.client("bedrock-runtime",          region_name=AWS_REGION)
bedrock_kb      = boto3.client("bedrock-agent-runtime",    region_name=AWS_REGION)


# ── STEP 1: READ ARTIFACT Z ───────────────────────────────────────────────────

def read_pdf_as_base64(pdf_path: str) -> str:
    import base64
    with open(pdf_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


# ── STEP 2: QUERY @RCI KB FOR HISTORICAL CONTEXT ──────────────────────────────

def query_rci_kb(query: str, num_results: int = 3) -> str:
    try:
        response = bedrock_kb.retrieve(
            knowledgeBaseId=KB_ID_RCI,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {"numberOfResults": num_results}
            }
        )
        chunks = []
        for r in response.get("retrievalResults", []):
            text = r.get("content", {}).get("text", "")
            score = r.get("score", 0)
            if text:
                chunks.append(f"[Relevance: {score:.2f}]\n{text}")
        return "\n\n---\n\n".join(chunks) if chunks else "No relevant historical context found."
    except Exception as e:
        return f"KB query failed: {str(e)}"


# ── STEP 3: ANSWER TEMPLATE QUESTIONS ─────────────────────────────────────────

def answer_questions(pdf_b64: str, pdf_name: str) -> dict:

    system_prompt = """You are a regulatory analyst assistant specialising in financial services regulation.

You are given a regulatory circular document. Your job is to answer a set of standard questions about this regulation accurately and precisely.

For each question, you must:
1. Answer based primarily on the regulation document provided
2. If the answer is clearly stated in the document — answer confidently
3. If the answer requires inference or is partially stated — note this
4. If the answer cannot be determined from the document — say so explicitly

You must respond in valid JSON only. No preamble, no explanation outside the JSON.

Response format for each question:
{
  "id": "Q01",
  "question": "the question text",
  "answer": "your answer here",
  "tag": "Confirmed" | "TBC" | "Not Known",
  "tag_reason": "brief reason for the tag",
  "needs_historical_context": true | false,
  "historical_query": "search query for historical KB if needed, else null"
}

Tag definitions:
- Confirmed: Answer clearly stated in the regulation document
- TBC: Answer inferred or partially stated — BA must verify
- Not Known: Cannot be determined from available information
"""

    # First pass — answer all questions from Artifact Z alone
    questions_text = json.dumps(SUMMARISATION_TEMPLATE, indent=2)

    user_message = f"""Here is the regulatory circular document to analyse.
Document name: {pdf_name}

Please answer all the following template questions based on this document.
For questions where historical context might help, set needs_historical_context to true
and provide a historical_query to search for.

Questions to answer:
{questions_text}

Respond with a JSON array of answers, one object per question.
"""

    print("  Step 1: Sending regulation to model for first-pass analysis...")

    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "system": system_prompt,
            "messages": [
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
                            "text": user_message
                        }
                    ]
                }
            ]
        })
    )

    result = json.loads(response["body"].read())
    raw_text = result["content"][0]["text"].strip()

    # Clean JSON if wrapped in markdown
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    answers = json.loads(raw_text)

    # Second pass — enrich TBC answers with historical KB context
    print("  Step 2: Enriching TBC answers with @RCI KB historical context...")
    enriched = []
    for ans in answers:
        if ans.get("needs_historical_context") and ans.get("historical_query"):
            print(f"    Querying @RCI KB: {ans['historical_query'][:60]}...")
            historical_context = query_rci_kb(ans["historical_query"])

            # Re-ask with historical context
            enrich_prompt = f"""You previously answered this question about a new regulation:

Question: {ans['question']}
Your answer: {ans['answer']}
Your tag: {ans['tag']}

Here is relevant historical context from prior regulations:
{historical_context}

Based on this additional context, update your answer if needed.
Respond with a single JSON object in the same format as before.
If your answer improves from TBC to Confirmed — update the tag.
"""
            enrich_response = bedrock_runtime.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": enrich_prompt}]
                })
            )
            enrich_result = json.loads(enrich_response["body"].read())
            enrich_text = enrich_result["content"][0]["text"].strip()

            if enrich_text.startswith("```"):
                enrich_text = enrich_text.split("```")[1]
                if enrich_text.startswith("json"):
                    enrich_text = enrich_text[4:]
            enrich_text = enrich_text.strip()

            try:
                updated_ans = json.loads(enrich_text)
                updated_ans["historical_context_used"] = True
                enriched.append(updated_ans)
            except Exception:
                ans["historical_context_used"] = True
                enriched.append(ans)
        else:
            ans["historical_context_used"] = False
            enriched.append(ans)

    return enriched


# ── STEP 4: GENERATE REGULATION SUMMARY ───────────────────────────────────────

def generate_summary(pdf_b64: str, pdf_name: str) -> str:
    print("  Step 3: Generating regulation summary...")

    response = bedrock_runtime.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
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
                            "text": """Write a concise executive summary of this regulatory circular in 150-200 words.
Structure it as:
- What the regulation is
- What it changes from the prior framework
- Key deadlines
- Who is affected
Write in plain English suitable for a business analyst."""
                        }
                    ]
                }
            ]
        })
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"].strip()


# ── STEP 5: BUILD ARTIFACT 1 ──────────────────────────────────────────────────

def build_artifact1(answers: list, summary: str, pdf_name: str) -> dict:

    confirmed  = [a for a in answers if a.get("tag") == "Confirmed"]
    tbc        = [a for a in answers if a.get("tag") == "TBC"]
    not_known  = [a for a in answers if a.get("tag") == "Not Known"]

    artifact1 = {
        "artifact_type":    "Artifact1_RegulationSummary",
        "source_document":  pdf_name,
        "generated_at":     datetime.utcnow().isoformat() + "Z",
        "model_used":       MODEL_ID,
        "kb_rci_used":      KB_ID_RCI,
        "summary": summary,
        "statistics": {
            "total_questions":    len(answers),
            "confirmed":          len(confirmed),
            "tbc":                len(tbc),
            "not_known":          len(not_known),
            "enriched_from_kb":   sum(1 for a in answers if a.get("historical_context_used"))
        },
        "answers": answers
    }
    return artifact1


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="POC3 Summarisation Chain")
    parser.add_argument("--artifact_z", required=True,
                        help="Path to the new regulation PDF (Artifact Z)")
    parser.add_argument("--output", default="artifact1_output.json",
                        help="Output path for Artifact 1 JSON")
    args = parser.parse_args()

    if not os.path.exists(args.artifact_z):
        print(f"Error: File not found — {args.artifact_z}")
        sys.exit(1)

    pdf_name = os.path.basename(args.artifact_z)
    print(f"\n=== POC 3 — Summarisation Chain ===")
    print(f"Artifact Z : {pdf_name}")
    print(f"Output     : {args.output}")
    print(f"Model      : {MODEL_ID}")
    print(f"@RCI KB    : {KB_ID_RCI}")
    print()

    # Read PDF
    print("Reading Artifact Z...")
    pdf_b64 = read_pdf_as_base64(args.artifact_z)
    print(f"  PDF loaded — {len(pdf_b64) // 1024} KB (base64)")

    # Answer questions
    print("\nAnswering template questions...")
    answers = answer_questions(pdf_b64, pdf_name)

    # Generate summary
    print("\nGenerating regulation summary...")
    summary = generate_summary(pdf_b64, pdf_name)

    # Build Artifact 1
    artifact1 = build_artifact1(answers, summary, pdf_name)

    # Save output
    with open(args.output, "w") as f:
        json.dump(artifact1, f, indent=2)

    # Print results
    print(f"\n=== ARTIFACT 1 COMPLETE ===")
    print(f"Questions answered : {artifact1['statistics']['total_questions']}")
    print(f"  Confirmed        : {artifact1['statistics']['confirmed']}")
    print(f"  TBC              : {artifact1['statistics']['tbc']}")
    print(f"  Not Known        : {artifact1['statistics']['not_known']}")
    print(f"  Enriched from KB : {artifact1['statistics']['enriched_from_kb']}")
    print(f"\nSummary:\n{summary}")
    print(f"\nOutput saved to: {args.output}")

    # Print TBC and Not Known for quick review
    tbc_items = [a for a in answers if a.get("tag") == "TBC"]
    nk_items  = [a for a in answers if a.get("tag") == "Not Known"]

    if tbc_items:
        print(f"\n--- TBC items (BA must verify) ---")
        for a in tbc_items:
            print(f"  {a['id']}: {a['question']}")
            print(f"       Reason: {a.get('tag_reason', '')}")

    if nk_items:
        print(f"\n--- Not Known items ---")
        for a in nk_items:
            print(f"  {a['id']}: {a['question']}")
            print(f"       Reason: {a.get('tag_reason', '')}")


if __name__ == "__main__":
    main()
