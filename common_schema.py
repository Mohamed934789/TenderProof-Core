def line_reference_schema():
    return {
        "type": "object",
        "properties": {
            "line_id": {"type": "string"},
        },
        "required": ["line_id"],
        "additionalProperties": False,
    }