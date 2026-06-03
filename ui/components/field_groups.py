"""Smart field grouping — categorises any extracted key by name pattern."""

from __future__ import annotations

_GROUPS = {
    "📄 Document Info":     ["number", "invoice", "receipt", "order", "reference", "po_",
                              "date", "period", "terms", "due", "expiry", "issue", "bill_no"],
    "🏢 Vendor / Seller":   ["vendor", "supplier", "merchant", "seller", "company",
                              "issued_by", "billed_by", "from_", "provider"],
    "👤 Customer / Bill To":["customer", "client", "buyer", "billed_to", "bill_to",
                              "ship_to", "sold_to", "recipient", "payee"],
    "📍 Contact & Address": ["address", "street", "city", "state", "zip", "postal",
                              "country", "phone", "mobile", "tel", "fax", "email", "website"],
    "💰 Financials":        ["total", "subtotal", "sub_total", "net", "gross", "amount",
                              "tax", "vat", "gst", "hst", "discount", "price", "cost",
                              "currency", "rate", "balance", "payment", "charge", "fee"],
    "🏦 Banking":           ["iban", "account", "bank", "swift", "bic", "routing",
                              "sort_code", "branch", "ifsc"],
    "📝 Notes & Other":     [],  # catch-all — always last
}


def group_fields(fields: dict) -> dict[str, dict]:
    """
    Returns an ordered dict of {group_label: {field_key: value}}.
    Empty groups are omitted.
    """
    result: dict[str, dict] = {g: {} for g in _GROUPS}

    for key, value in fields.items():
        if value is None or value == "":
            continue
        assigned = False
        key_lower = key.lower()
        for group, keywords in _GROUPS.items():
            if group == "📝 Notes & Other":
                continue
            if any(kw in key_lower for kw in keywords):
                result[group][key] = value
                assigned = True
                break
        if not assigned:
            result["📝 Notes & Other"][key] = value

    return {g: v for g, v in result.items() if v}


def pretty_label(key: str) -> str:
    """Convert snake_case key to Title Case label."""
    return key.replace("_", " ").title()


def format_value(key: str, value) -> str:
    """Format a value for display — add $ for amount fields, keep rest as-is."""
    if value is None:
        return "—"
    key_lower = key.lower()
    is_amount = any(k in key_lower for k in
                    ["amount", "total", "subtotal", "tax", "price", "cost",
                     "balance", "discount", "fee", "charge", "net", "gross"])
    if is_amount:
        try:
            return f"${float(value):,.2f}"
        except (ValueError, TypeError):
            pass
    return str(value)
