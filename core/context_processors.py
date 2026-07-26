WORKSPACE_RECORD_TYPES = {
    "article", "journal", "note", "centralpoint",
    "strategy", "decision", "goal",
}


def workspace_record_type(request):
    """Expose the active record type to the shared workspace sidebar."""
    match = getattr(request, "resolver_match", None)
    if match is None:
        return {}

    url_name = match.url_name or ""
    record_type = match.kwargs.get("record_type")
    if not record_type:
        record_type = "article" if url_name == "index" else url_name.split("_", 1)[0]

    if record_type not in WORKSPACE_RECORD_TYPES:
        return {}
    return {
        "workspace_record_type": record_type,
        "workspace_is_record_form": url_name.endswith(("_create", "_edit")),
        "workspace_is_single": url_name.endswith("_single"),
    }
