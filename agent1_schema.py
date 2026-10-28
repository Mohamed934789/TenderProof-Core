from common_schema import line_reference_schema
def eligibility_output_schema():
    properties = {
        "requirement_id": {"type": "string"}, "text": {"type": "string"},
        "category": {"type": "string", "enum": ["REGISTRATION", "LICENSE", "EXPERIENCE",
                                                  "ADMINISTRATIVE", "FINANCIAL", "OTHER"]},
        "needs_review": {"type": "boolean"},
        "review_reasons": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": line_reference_schema()},
    }
    return {
        "type": "object", "properties": {
            "requirements": {"type": "array", "items": {
                "type": "object", "properties": properties, "required": list(properties),
                "additionalProperties": False}},
            "warnings": {"type": "array", "items": {"type": "string"}},
        }, "required": ["requirements", "warnings"], "additionalProperties": False,
    }
