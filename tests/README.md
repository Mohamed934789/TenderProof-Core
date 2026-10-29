# Tests

From the repository root, after installing `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp tmp/pytest
```

The suite includes unittest and pytest tests, Arabic PDF fixtures, all three agents,
invalid citations, date/quantity grounding, uncertainty and complete pipeline tests.
All automated AI calls use fake clients and cost nothing. Fake tests validate
integration and guards, not real model extraction accuracy.

`test_pipeline.py` uses private local `fixtures/ida-335.pdf` if available, checking
quantities 104, 2 and 1 on page 6. Its review artifact is ignored by Git:
`output/integration-fake-ai-report.json`. The private PDF is never committed.

`test_agent2_integration.py` is a manual paid experiment, invoked explicitly with
`python tests/test_agent2_integration.py`; pytest discovery does not run its main.
