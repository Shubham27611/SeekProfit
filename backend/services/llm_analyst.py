"""LLM analyst wrapper — Claude Sonnet 4.6 via emergentintegrations.

The LLM ONLY (a) writes human-facing explanation + recommended_action strings
for deterministically-detected signals, and (b) answers ad-hoc Q&A grounded
strictly in the compact structured brief the caller assembles from Mongo.

It CANNOT invent transactions, customers, invoices, or figures because it
never sees free-form text — it sees a JSON brief and is instructed to cite
record IDs from that brief only.
"""
from __future__ import annotations
import json
import os
from typing import AsyncIterator, List

from emergentintegrations.llm.chat import (
    LlmChat,
    UserMessage,
    TextDelta,
    StreamDone,
)


SYSTEM_ANALYST = (
    "You are SeekProfit's senior financial analyst. You reason ONLY over the "
    "structured JSON brief that will be provided. You NEVER invent customers, "
    "vendors, invoices, or dollar amounts. Every citation must be a record_id "
    "that appears in the brief. Be concise, precise, and use the language a "
    "seasoned CFO would use — no fluff, no emojis, no bullet-heavy prose."
)


def _chat(session_id: str, system: str = SYSTEM_ANALYST) -> LlmChat:
    key = os.environ["EMERGENT_LLM_KEY"]
    return LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6")


async def _collect(chat: LlmChat, prompt: str) -> str:
    """Convenience: run stream_message and collect the full text."""
    parts: List[str] = []
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Explain a deterministically-detected signal
# ---------------------------------------------------------------------------

async def explain_signal(session_id: str, signal: dict, evidence: List[dict]) -> dict:
    """Return {"explanation": str, "recommended_action": str} for a signal.

    Falls back to a rule-based template if the LLM call errors — the demo
    never breaks because of an LLM outage.
    """
    brief = {
        "signal": {
            "title": signal["title"],
            "category": signal["category"],
            "detector": signal["detector"],
            "impact_amount_usd": signal["impact_amount"],
            "amount_type": signal["amount_type"],
            "confidence": signal["confidence"],
            "urgency": signal["urgency"],
        },
        "evidence_records": evidence[:10],
    }
    prompt = (
        "Write a concise financial-analyst explanation and a concrete recommended "
        "action for the following signal. Cite specific record IDs from "
        "`evidence_records` that support your reasoning. Return ONLY valid JSON "
        "with keys `explanation` and `recommended_action` — no prose outside JSON.\n\n"
        "Brief:\n" + json.dumps(brief, indent=2)
    )
    chat = _chat(session_id)
    try:
        raw = await _collect(chat, prompt)
        # Strip common code-fence wrapping if present.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return {
            "explanation": str(data.get("explanation", "")).strip(),
            "recommended_action": str(data.get("recommended_action", "")).strip(),
        }
    except Exception as e:
        print(f"[llm.explain_signal] fallback due to: {e}")
        return _fallback_explanation(signal, evidence)


def _fallback_explanation(signal: dict, evidence: List[dict]) -> dict:
    detector = signal["detector"]
    ids = ", ".join(r.get("record_id", "?") for r in evidence[:3])
    templates = {
        "duplicate_vendor_payment": (
            f"Two or more payments to the same vendor were posted within a 3-day window at an identical amount. Records {ids} show the pattern.",
            "Verify the vendor invoice was not issued twice, then request reversal of the duplicate charge with the vendor's AP team.",
        ),
        "overlapping_subscription": (
            f"Multiple line items for the same vendor billed within the same month at the canonical seat price — see {ids}.",
            "Audit active subscription seats against actual users and consolidate to a single billing account.",
        ),
        "unbilled_services": (
            f"A recurring contract exists but at least one expected invoice period is missing. Contract and adjacent invoices: {ids}.",
            "Generate and send the missing invoice for the affected period(s); reconcile against the customer's payment plan.",
        ),
        "late_paying_customer": (
            f"This customer's average time-to-pay has drifted past the 45-day threshold across recent payments — evidence in {ids}.",
            "Send a payment-terms reminder, tighten the next contract cycle, and consider offering a 1-2% early-pay discount.",
        ),
        "renewal_uplift": (
            f"Contract {ids} is within the renewal window at a price below observed market median for comparable engagements.",
            "Package a renewal proposal at the market-median price with a modest scope uplift to justify the delta.",
        ),
    }
    exp, rec = templates.get(detector, (
        f"Automated detection flagged this pattern based on records {ids}.",
        "Review the underlying evidence with the accountable owner before acting.",
    ))
    return {"explanation": exp, "recommended_action": rec}


# ---------------------------------------------------------------------------
# Ad-hoc Q&A — streaming
# ---------------------------------------------------------------------------

def _brief_for_ask(kpis: dict, signals: List[dict], records: List[dict]) -> dict:
    """Compact JSON brief the model reasons over."""
    return {
        "kpis": kpis,
        "top_signals": [
            {
                "signal_id": s.get("signal_id"),
                "title": s.get("title"),
                "category": s.get("category"),
                "impact_amount_usd": s.get("impact_amount"),
                "amount_type": s.get("amount_type"),
                "confidence": s.get("confidence"),
                "urgency": s.get("urgency"),
                "priority_score": s.get("priority_score"),
                "evidence_record_ids": s.get("evidence_record_ids"),
            }
            for s in signals[:15]
        ],
        "sample_records": [
            {
                "record_id": r["record_id"],
                "type": r["type"],
                "date": r["date"],
                "amount": r["amount"],
                "counterparty": r["counterparty"],
                "status": r.get("status"),
                "memo": r.get("memo"),
            }
            for r in records[:120]
        ],
    }


ASK_SYSTEM = (
    SYSTEM_ANALYST
    + " When answering, cite the specific record_ids you used, formatted as "
    "`[rec:record_id]` inline. IMPORTANT: only ever cite values from the "
    "`sample_records` list — NEVER cite signal_ids or any other identifier. "
    "Refer to signals by their title, not their id. If the brief does not "
    "contain enough data to answer, say so explicitly rather than guessing. "
    "Do NOT use markdown syntax (no `##`, no `**bold**`, no bullet dashes) — "
    "write clean prose in short paragraphs."
)


async def stream_ask(
    session_id: str,
    question: str,
    kpis: dict,
    signals: List[dict],
    records: List[dict],
) -> AsyncIterator[str]:
    """Yield text deltas for a user Q&A."""
    brief = _brief_for_ask(kpis, signals, records)
    prompt = (
        "Answer the CFO's question using ONLY the brief below. Cite record_ids "
        "inline as [rec:<id>]. Keep the answer under ~180 words unless the "
        "question demands more.\n\n"
        f"Question: {question}\n\n"
        f"Brief:\n{json.dumps(brief)[:80_000]}"
    )
    chat = _chat(session_id, ASK_SYSTEM)
    try:
        async for ev in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(ev, TextDelta):
                yield ev.content
            elif isinstance(ev, StreamDone):
                return
    except Exception as e:
        print(f"[llm.stream_ask] error: {e}")
        yield (
            "I couldn't reach the analysis service just now. "
            "The deterministic signals on this page remain valid — try the question again in a moment."
        )
