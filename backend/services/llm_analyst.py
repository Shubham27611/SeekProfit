"""LLM analyst wrapper — Claude Sonnet 4.6 via emergentintegrations.

Grounding contract:
- The LLM never invents transactions, customers, vendors, invoices, payments,
  savings, recovered amounts, prior actions, or business processes.
- It reasons ONLY over the structured JSON brief the caller assembles from
  Mongo, which includes an explicit currency + symbol.
- Confidence != confirmation. High confidence is described as
  "high-confidence finding" or "potential/likely", not "confirmed".
- Missing information must be stated explicitly ("No prior recovery amount is
  available in the current dataset.") — never filled with assumptions.
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

from services.finance import currency_symbol, format_amount_exact


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

def build_system_prompt(currency: str) -> str:
    sym = currency_symbol(currency)
    code = (currency or "USD").upper()
    return (
        "You are SeekProfit's senior financial analyst. You reason ONLY over "
        "the structured JSON brief the user provides. "
        "\n\n"
        "STRICT GROUNDING RULES — FOLLOW WITHOUT EXCEPTION:\n"
        "1. Every named amount, count, customer, vendor, invoice, payment, "
        "date, or business fact MUST come directly from the brief. Do NOT "
        "invent transactions, savings, recovered amounts, prior actions, or "
        "customer behaviour that is not in the brief.\n"
        "2. NEVER claim money has already been recovered, saved, actioned, or "
        "acted upon UNLESS a signal in the brief has status='resolved' with "
        "an impact_amount. If the user asks about prior recovery, respond: "
        "'No prior recovery amount is available in the current dataset.'\n"
        "3. Confidence != confirmation. Do NOT use the word 'confirmed' or "
        "'definitively' for pattern-detected findings. Use phrases like "
        "'potential', 'likely', 'high-confidence finding', or 'requires "
        "review'. A 90% confidence detection is a HIGH-CONFIDENCE FINDING, "
        "not a CONFIRMED duplicate.\n"
        f"4. Currency: every amount in the brief is in {code}. Use the "
        f"symbol '{sym}' in your answer. NEVER use another currency symbol.\n"
        "5. When calculating recoverable amounts for duplicate-style "
        "findings, use only the excess (e.g. two identical payments of "
        f"{sym}27,500 imply a recoverable {sym}27,500 — not {sym}55,000).\n"
        "6. Prefer visibly-grounded phrasing: 'Based on N transactions in "
        "the dataset...' rather than unqualified claims.\n"
        "7. When information is missing say so explicitly (e.g. 'No payment "
        "record was found for this invoice.', 'Insufficient data to "
        "determine whether this is a confirmed duplicate.'). Never fill "
        "missing data with assumptions.\n"
        "\n"
        "STYLE: concise CFO tone. Short paragraphs. No emojis, no markdown "
        "headings, no **bold**, no bullet dashes. NEVER mention 'the brief', "
        "'the JSON', 'dataset_facts', 'prior_recovery_available', or any "
        "internal field name — refer to the data as 'the current dataset' "
        "or 'the imported records'."
    )


def build_ask_system(currency: str) -> str:
    return (
        build_system_prompt(currency)
        + "\n\nCITATIONS: When answering, cite the specific record_ids you "
        "used, formatted as `[rec:record_id]` inline. Only cite values from "
        "the `sample_records` list — NEVER cite signal_ids or any other "
        "identifier. Refer to signals by their title, not their id."
    )


# ---------------------------------------------------------------------------
# LlmChat helpers
# ---------------------------------------------------------------------------

def _chat(session_id: str, system: str) -> LlmChat:
    key = os.environ["EMERGENT_LLM_KEY"]
    return LlmChat(
        api_key=key,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6")


async def _collect(chat: LlmChat, prompt: str) -> str:
    parts: List[str] = []
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            parts.append(ev.content)
        elif isinstance(ev, StreamDone):
            break
    return "".join(parts).strip()


# ---------------------------------------------------------------------------
# Signal explanation
# ---------------------------------------------------------------------------

async def explain_signal(
    session_id: str,
    signal: dict,
    evidence: List[dict],
    currency: str = "USD",
) -> dict:
    """Return {"explanation": str, "recommended_action": str} for a signal."""
    brief = {
        "currency": {"code": (currency or "USD").upper(), "symbol": currency_symbol(currency)},
        "signal": {
            "title": signal["title"],
            "category": signal["category"],
            "detector": signal["detector"],
            "impact_amount": signal["impact_amount"],
            "impact_display": format_amount_exact(signal["impact_amount"], currency),
            "amount_type": signal["amount_type"],
            "confidence": signal["confidence"],
            "urgency": signal["urgency"],
        },
        "evidence_records": evidence[:10],
    }
    prompt = (
        "Write a concise financial-analyst explanation and a concrete "
        "recommended action for the following signal. Cite specific "
        "record_ids from `evidence_records`. Respect the grounding rules "
        "in your system message: no invented facts, no 'confirmed' unless "
        "explicitly verified, use the currency symbol from `currency.symbol`.\n"
        "Return ONLY valid JSON with keys `explanation` and "
        "`recommended_action` — no prose outside JSON.\n\n"
        "Brief:\n" + json.dumps(brief, indent=2)
    )
    chat = _chat(session_id, build_system_prompt(currency))
    try:
        raw = await _collect(chat, prompt)
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
        return _fallback_explanation(signal, evidence, currency)


def _fallback_explanation(
    signal: dict, evidence: List[dict], currency: str = "USD"
) -> dict:
    detector = signal["detector"]
    ids = ", ".join(r.get("record_id", "?") for r in evidence[:3])
    n_ev = len(evidence)
    impact_disp = format_amount_exact(signal.get("impact_amount", 0), currency)
    templates = {
        "duplicate_vendor_payment": (
            (
                f"Based on {n_ev} vendor bills in the dataset, we identified a "
                f"potential duplicate payment pattern — the same vendor was "
                f"charged the same amount within a 3-day window. Records {ids} "
                f"support the finding. This is a high-confidence detection, "
                f"not a confirmed duplicate; the recoverable amount is the "
                f"excess only ({impact_disp})."
            ),
            "Review the referenced records with AP, verify that no legitimate second invoice was issued for the same service, and request a vendor credit for the excess payment.",
        ),
        "overlapping_subscription": (
            f"Based on {n_ev} vendor bills, the same vendor was billed more than once per month at the same seat price — see {ids}. This is a likely subscription overlap.",
            "Audit active subscription seats against actual users and consolidate to a single billing account.",
        ),
        "unbilled_services": (
            f"A recurring contract exists but at least one expected invoice period is missing. Contract and adjacent invoices: {ids}.",
            "Generate and send the missing invoice for the affected period(s); reconcile against the customer's payment plan.",
        ),
        "late_paying_customer": (
            f"This customer's average time-to-pay has drifted past the 45-day threshold across the payments in the dataset — evidence in {ids}.",
            "Send a payment-terms reminder, tighten the next contract cycle, and consider offering a small early-pay discount.",
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
# Ask-anything Q&A
# ---------------------------------------------------------------------------

def _brief_for_ask(
    kpis: dict,
    signals: List[dict],
    records: List[dict],
    currency: str = "USD",
) -> dict:
    code = (currency or "USD").upper()
    sym = currency_symbol(currency)

    # Deterministic aggregates the model can rely on without re-computing.
    resolved_recovery = sum(
        float(s.get("impact_amount", 0))
        for s in signals
        if s.get("status") == "resolved"
        and s.get("category") == "revenue_recovery"
    )
    open_recovery = sum(
        float(s.get("impact_amount", 0))
        for s in signals
        if s.get("status") == "open" and s.get("category") == "revenue_recovery"
    )
    open_leak = sum(
        float(s.get("impact_amount", 0))
        for s in signals
        if s.get("status") == "open" and s.get("category") == "profit_leak"
    )
    open_opp = sum(
        float(s.get("impact_amount", 0))
        for s in signals
        if s.get("status") == "open" and s.get("category") == "opportunity"
    )

    return {
        "currency": {"code": code, "symbol": sym},
        "dataset_facts": {
            "records_count": len(records),
            "signals_count": len(signals),
            "prior_recovery_amount": resolved_recovery,
            "prior_recovery_display": format_amount_exact(resolved_recovery, currency),
            "prior_recovery_available": resolved_recovery > 0,
            "open_recovery_display": format_amount_exact(open_recovery, currency),
            "open_leak_display": format_amount_exact(open_leak, currency),
            "open_opportunity_display": format_amount_exact(open_opp, currency),
        },
        "kpis": kpis,
        "top_signals": [
            {
                "signal_id": s.get("signal_id"),
                "title": s.get("title"),
                "category": s.get("category"),
                "impact_amount": s.get("impact_amount"),
                "impact_display": format_amount_exact(s.get("impact_amount", 0), currency),
                "amount_type": s.get("amount_type"),
                "confidence": s.get("confidence"),
                "urgency": s.get("urgency"),
                "priority_score": s.get("priority_score"),
                "status": s.get("status", "open"),
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
                "amount_display": format_amount_exact(r.get("amount", 0), currency),
                "counterparty": r["counterparty"],
                "status": r.get("status"),
                "memo": r.get("memo"),
            }
            for r in records[:120]
        ],
    }


async def stream_ask(
    session_id: str,
    question: str,
    kpis: dict,
    signals: List[dict],
    records: List[dict],
    currency: str = "USD",
) -> AsyncIterator[str]:
    brief = _brief_for_ask(kpis, signals, records, currency)
    prompt = (
        "Answer the CFO's question using ONLY the brief below. Cite record_ids "
        "inline as [rec:<id>]. Keep the answer under ~180 words unless the "
        "question demands more. Remember: the brief's `dataset_facts` block "
        "contains the ONLY prior-recovery figure that exists — if "
        "`prior_recovery_available` is false, do not claim any money has been "
        "recovered previously.\n\n"
        f"Question: {question}\n\n"
        f"Brief:\n{json.dumps(brief)[:80_000]}"
    )
    chat = _chat(session_id, build_ask_system(currency))
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


# ---------------------------------------------------------------------------
# Back-compat exports (older modules import these names)
# ---------------------------------------------------------------------------

SYSTEM_ANALYST = build_system_prompt("USD")
ASK_SYSTEM = build_ask_system("USD")
