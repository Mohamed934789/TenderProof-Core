from common_schema import line_reference_schema
def verification_output_schema():
    properties = {
        "target_type": {"type": "string", "enum": ["ELIGIBILITY", "TECHNICAL", "BOQ"]},
        "target_id": {"type": "string"}, "evidence_found": {"type": "boolean"},
        "sources": {"type": "array", "items": line_reference_schema()},
        "assessment": {"type": "string", "enum": ["SUPPORTS", "CONTRADICTS", "UNCERTAIN"]},
        "explanation": {"type": "string"}, "expiry_date": {"type": ["string", "null"]},
        "offered_quantity": {"type": ["string", "null"]},
        "offered_unit": {"type": ["string", "null"]},
    }
    return {"type": "object", "properties": {
        "results": {"type": "array", "items": {"type": "object", "properties": properties,
                    "required": list(properties), "additionalProperties": False}}},
        "required": ["results"], "additionalProperties": False}