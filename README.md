# TenderProof AI

Python 3.12+. One PDF reader, three agents, one orchestrator. No backend required.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe -m pytest -q --basetemp tmp/pytest
```

Run locally without an API key (MOCK is a dry run; it does not extract real findings):

```powershell
.\.venv\Scripts\python.exe orchestrator.py --tender tests/fixtures/arabic_table.pdf --company tests/fixtures/01_company_profile.pdf tests/fixtures/04_previous_work.pdf --reference-date 2026-10-26 --mode MOCK --output output/report.json
```

For real extraction, copy `.env.example` to `.env`, set `OPENAI_API_KEY` and
`OPENAI_MODEL`, then use `--mode AI`. This makes paid API requests (one per agent;
verification is skipped when there are no targets). All agents use the injected
`LLMClient` and the same `OpenAIAdapter`. No automatic retries or fallback.
Automated tests use local fake clients, including tests of the AI path; no API calls.
`tests/test_agent2_integration.py` is an explicitly invoked paid experiment only.

Input: Tender PDF + Company PDFs -> Reader -> Agent 1 + Agent 2 -> Validation ->
Agent 3 -> Validation -> JSON Report (`core-draft-0.2`). The required reference date
is explicit; no date is guessed.

Core files:
- `models.py`: shared data contracts (unchanged).
- `pdf_reader.py`: native PDF text, physical page numbers and reading warnings.
- `agent1.py`: eligibility, registration, licenses and supporting tender citations.
- `agent2.py`, `agent2_schema.py`: technical requirements and BOQ with line citations.
- `agent3.py`: company evidence, missing/uncertain findings, date and quantity checks.
- `validation.py`: contract, citation, target coverage and report validation.
- `llm_client.py`, `openai_adapter.py`: shared provider interface and API adapter.
- `orchestrator.py`: complete pipeline and CLI above.

Readability describes extracted text, not document completeness or table quality.
Clear Arabic lines can support findings even on a page with a separate uncertain line.
`TEXT_LINE:<n>:` identifies an affected line; `TABLE:` notes keep unverified BOQ
relationships under review without blocking clear prose. Other reading warnings
remain material. OCR and table reconstruction are not implemented.

`MISSING_EVIDENCE` requires a confirmed complete, readable company document set.
Use `--company-documents-complete` ONLY when all company documents were supplied;
the default stays UNKNOWN. This confirmation never overrides text corruption.
Review citations against the original PDFs before making eligibility decisions.

Optional local fixture `tests/fixtures/ida-335.pdf` is private and ignored by Git.
When present, the free integration test checks page 6 quantities 104, 2 and 1 and
retains `NEEDS_REVIEW`; fake responses verify integration, not model accuracy.
Learning files `practice_*.py` and local debug results stay on disk and outside Git.

Integration sources: Agent 1 from `feature/eligibility-agent` (`10baee1`), Agent 3
from `feature/evidence-agent` (`28551d6`), on local PDF/Agent 2 work at `7ab5d0c`.
