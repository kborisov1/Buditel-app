# Management form data for an Entry admin POST with no inline rows.
INLINE_PREFIXES = [
    "track_items",
    "gate_requirements",
    "relations",
    "images",
    "sources",
    "questions",
]
EMPTY_INLINES = {
    f"{prefix}-{kind}_FORMS": 0 for prefix in INLINE_PREFIXES for kind in ["TOTAL", "INITIAL"]
}
