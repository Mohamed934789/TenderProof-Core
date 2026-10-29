from common_schema import line_reference_schema
def technical_output_schema():
    line_ref = line_reference_schema()

    references = {
        "type": "array",
        "items": line_ref,
    }

    quantity = {
        "type": "object",
        "properties": {
            "raw_text": {"type": "string"},
            "decimal_value": {
                "type": ["string", "null"],
            },
            "sources": references,
        },
        "required": [
            "raw_text",
            "decimal_value",
            "sources",
        ],
        "additionalProperties": False,
    }

    boq_item = {
        "type": "object",
        "properties": {
            "boq_item_id": {"type": "string"},
            "description": {"type": "string"},
            "quantity": quantity,
            "unit": {"type": ["string", "null"]},
            "unit_normalized": {
                "type": ["string", "null"],
            },
            "table_id": {"type": ["string", "null"]},
            "needs_review": {"type": "boolean"},
            "review_reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "sources": references,
        },
        "required": [
            "boq_item_id",
            "description",
            "quantity",
            "unit",
            "unit_normalized",
            "table_id",
            "needs_review",
            "review_reasons",
            "sources",
        ],
        "additionalProperties": False,
    }

    technical_requirement = {
        "type": "object",
        "properties": {
            "technical_id": {"type": "string"},
            "text": {"type": "string"},
            "category": {
                "type": "string",
                "enum": [
                    "SPECIFICATION",
                    "MODEL",
                    "EXECUTION_DEADLINE",
                    "OTHER",
                ],
            },
            "needs_review": {"type": "boolean"},
            "review_reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "sources": references,
        },
        "required": [
            "technical_id",
            "text",
            "category",
            "needs_review",
            "review_reasons",
            "sources",
        ],
        "additionalProperties": False,
    }

    return {
        "type": "object",
        "properties": {
            "boq_status": {
                "type": "string",
                "enum": [
                    "FOUND",
                    "NOT_FOUND",
                    "NEEDS_REVIEW",
                ],
            },
            "boq_review_reasons": {
                "type": "array",
                "items": {"type": "string"},
            },
            "boq_items": {
                "type": "array",
                "items": boq_item,
            },
            "technical_requirements": {
                "type": "array",
                "items": technical_requirement,
            },
        },
        "required": [
            "boq_status",
            "boq_review_reasons",
            "boq_items",
            "technical_requirements",
        ],
        "additionalProperties": False,
    }
# Compatibility with the stable SDK and its tests.
agent2_output_schema = technical_output_schema
