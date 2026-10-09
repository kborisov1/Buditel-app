# Management form data for an Entry admin POST with no inline rows.
EMPTY_INLINES = {
    f"{prefix}-{kind}_FORMS": 0
    for prefix in ["relations", "images", "sources", "questions"]
    for kind in ["TOTAL", "INITIAL"]
}
