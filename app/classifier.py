from __future__ import annotations

import re
from collections import Counter

CATEGORY_TERMS = {
    "Billing": {"bill", "billing", "invoice", "refund", "charge", "charged", "payment", "subscription", "price", "pricing", "receipt", "credit"},
    "Technical Support": {"bug", "error", "crash", "broken", "issue", "technical", "login", "password", "slow", "failed", "failure", "not working", "cannot", "can't", "unable", "app", "website"},
    "Account Access": {"account", "access", "locked", "verification", "verify", " sign in", "signin", "password", "username", "two factor", "2fa"},
    "Shipping & Delivery": {"shipping", "delivery", "delivered", "shipment", "tracking", "package", "parcel", "courier", "late", "lost", "dispatch"},
    "Returns & Warranty": {"return", "exchange", "warranty", "replacement", "replace", "damaged", "defective", "broken", "cancel", "cancellation"},
    "Product Information": {"feature", "product", "specification", "compatible", "compatibility", "availability", "recommend", "how do", "question"},
}

POSITIVE = {"thank", "thanks", "great", "good", "excellent", "love", "helpful", "resolved", "perfect", "happy", "quick", "appreciate"}
NEGATIVE = {"angry", "annoyed", "bad", "broken", "disappointed", "frustrated", "hate", "issue", "problem", "terrible", "unacceptable", "urgent", "worst", "failed", "failure", "refund", "late"}
URGENT = {"urgent", "asap", "immediately", "emergency", "outage", "down", "security", "fraud", "data loss", "cannot access", "can't access", "business stopped"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def analyze_ticket(subject: str, description: str) -> dict[str, str | float]:
    text = f"{subject} {description}".lower()
    tokens = _tokens(text)
    counts = Counter(tokens)
    scores: dict[str, int] = {}
    for category, terms in CATEGORY_TERMS.items():
        scores[category] = sum((text.count(term) if " " in term else counts[term]) for term in terms)
    best_score = max(scores.values(), default=0)
    category = max(scores, key=scores.get) if best_score else "General Inquiry"
    confidence = round(min(0.98, 0.5 + best_score * 0.1), 2) if best_score else 0.35

    positive_hits = sum(counts[word] for word in POSITIVE)
    negative_hits = sum(counts[word] for word in NEGATIVE)
    if positive_hits == negative_hits:
        sentiment = "Neutral"
    else:
        sentiment = "Positive" if positive_hits > negative_hits else "Negative"

    if any(term in text for term in URGENT) or any(word in text for word in ("fraud", "security", "data loss")):
        priority = "Critical"
    elif negative_hits >= 2 or any(word in text for word in ("can't", "cannot", "unable", "failed", "failure")):
        priority = "High"
    elif sentiment == "Negative" or any(word in text for word in ("soon", "waiting", "delay")):
        priority = "Medium"
    else:
        priority = "Low"
    return {"category": category, "priority": priority, "sentiment": sentiment, "confidence": confidence}
