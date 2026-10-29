"""Local HTTP adapter over the unchanged TenderProof orchestrator."""
import asyncio
import json
import hashlib
import logging
import os
import re
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path, PureWindowsPath
from typing import Annotated, Literal

ROOT = Path(__file__).resolve().parents[1]
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
# Optional Compose secret: runtime-only, never copied into the image or sent to the UI.
key_file = os.getenv("OPENAI_API_KEY_FILE")
KEY_FILE_ERROR = False
if key_file:
    try:
        secret = Path(key_file).read_text(encoding="utf-8").strip()
        if not secret:
            raise ValueError("Empty secret")
        os.environ["OPENAI_API_KEY"] = secret
    except (OSError, UnicodeError, ValueError):
        # Report a safe readiness reason; never expose file contents or exception text.
        KEY_FILE_ERROR = True
RUNTIME_ROOT = Path(os.getenv("TENDERPROOF_RUNTIME_DIR", str(ROOT / "runtime"))).resolve()
TEMP_ROOT = RUNTIME_ROOT / "uploads"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
if os.name == "nt" and TEMP_ROOT.resolve().drive.upper() != "D:":
    raise RuntimeError("Uploaded documents must use a temporary directory on D")
os.environ["TEMP"] = os.environ["TMP"] = str(TEMP_ROOT)
tempfile.tempdir = str(TEMP_ROOT)
logging.getLogger("pypdf").disabled = True
logging.getLogger("pypdf").setLevel(logging.CRITICAL)
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from models import Report
from orchestrator import analyze
from tracker import get_tracker, safe_log
from pdf_reader import read_pdf
from validation import validate_shape, validate_report

app = FastAPI(title="TenderProof AI", version="0.1.0", description="Local web adapter; existing Agents and Validation are unchanged.")
MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
DEMO_ROOT = Path(os.getenv("TENDERPROOF_DEMO_DIR", str(ROOT / "demo"))).resolve()
analysis_lock = asyncio.Lock()

AI_OUTPUT_LIMIT = 16384
AI_CALL_LIMIT = 3
AI_BUDGET_USD = 0.50
AI_AUDIT_ROOT = RUNTIME_ROOT / "real-ai-e2e"
AI_SINGLE_LOCK = AI_AUDIT_ROOT / "single-attempt.lock"

def ai_readiness():
    if os.getenv("TENDERPROOF_ALLOW_PAID_API", "0") != "1":
        return {"code": "DISABLED", "message": "Real AI مقفول بإعداد السيرفر. فعّل TENDERPROOF_ALLOW_PAID_API=1 وأعد تشغيل API، أو استخدم docker-compose.ai.yml حسب README."}
    if KEY_FILE_ERROR:
        return {"code": "SECRET_UNREADABLE", "message": "تعذر قراءة مفتاح OpenAI من ملف secret، أو الملف فارغ. راجع وجوده وصلاحية قراءته ثم أعد تشغيل API؛ لا ترسل المفتاح في الرسائل."}
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return {"code": "KEY_MISSING", "message": "مفتاح OpenAI غير موجود داخل عملية API. أضفه محليًا إلى .env، أو مرره كـDocker secret حسب README، ثم أعد تشغيل API."}
    if os.getenv("OPENAI_MODEL", "gpt-6-luna") != "gpt-6-luna":
        return {"code": "MODEL_UNSUPPORTED", "message": "إعداد الأمان الحالي يسمح بـgpt-6-luna فقط. اضبط OPENAI_MODEL=gpt-6-luna وأعد تشغيل API."}
    if os.getenv("TENDERPROOF_SINGLE_AI_RUN", "1") == "1" and AI_SINGLE_LOCK.exists():
        return {"code": "ATTEMPT_USED", "message": "محاولة Real AI الواحدة المصرح بها مستخدمة بالفعل. القفل محفوظ؛ لا تحذفه. أي جلسة جديدة تحتاج تفعيلًا صريحًا ومساحة runtime مستقلة حسب README."}
    return {"code": "READY", "message": "إعدادات Real AI جاهزة، مع ضرورة الموافقة على كل تشغيل. صلاحية المفتاح والرصيد لم يتم اختبارهما عبر OpenAI."}


def paid_enabled():
    return ai_readiness()["code"] == "READY"

def write_audit(audit):
    path = Path(audit["audit_path"])
    path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")

def limit_openai_adapter(adapter, audit):
    """Bound SDK transport only. Delegate all prompts/parsing to the original adapter."""
    if adapter.model != "gpt-6-luna" or str(adapter.client.base_url).rstrip("/") != "https://api.openai.com/v1":
        raise ValueError("Unexpected model or API endpoint")
    if adapter.client.max_retries != 0:
        raise ValueError("Automatic retries must be disabled")
    original_create = adapter.client.responses.create

    async def bounded_create(**request):
        if len(audit["calls"]) >= AI_CALL_LIMIT:
            raise PermissionError("Generation call limit reached")
        if request.get("model") != "gpt-6-luna" or request.get("tools"):
            raise PermissionError("Unexpected model or paid tools")
        entry = {"stage": len(audit["calls"]) + 1, "generation_attempted": False,
                 "request_hash": hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
        audit["calls"].append(entry)
        audit["token_count_calls"] += 1
        write_audit(audit)
        try:
            count = await adapter.client.responses.input_tokens.count(
                **{k: request[k] for k in ("model", "instructions", "input", "text")}, timeout=30)
            tokens = count.input_tokens
            if type(tokens) is not int or tokens < 0 or tokens + AI_OUTPUT_LIMIT > 1_050_000:
                raise ValueError("Invalid or oversized token count")
            # Conservative long-context / 12h cache-write input and output prices.
            reserve = (tokens * 0.50 + AI_OUTPUT_LIMIT * 0.75) / 1_000_000
            if audit["reserved_usd"] + reserve > AI_BUDGET_USD:
                raise PermissionError("Estimated maximum would exceed the authorized budget")
            audit["reserved_usd"] += reserve  # Never recycle a failed/unknown request's reserve.
            entry.update(input_tokens_counted=tokens, reserved_usd=reserve, max_output_tokens=AI_OUTPUT_LIMIT,
                         generation_attempted=True)
            write_audit(audit)
            response = await original_create(**request, max_output_tokens=AI_OUTPUT_LIMIT,
                                             service_tier="default", timeout=180)
            usage = response.usage.model_dump() if response.usage else None
            entry.update(response_id=response.id, status=response.status, model=response.model, usage=usage)
            if usage:
                i, o = usage["input_tokens"], usage["output_tokens"]
                if i > tokens or o > AI_OUTPUT_LIMIT:
                    raise RuntimeError("Reported usage exceeded its preflight limits")
                detail = usage.get("input_tokens_details") or {}
                c, w = detail.get("cached_tokens", 0), detail.get("cache_write_tokens", 0)
                if c + w > i:
                    raise ValueError("Invalid usage accounting")
                long_context = i > 272000
                ir, cr = (0.20, 0.02) if long_context else (0.10, 0.01)
                lo_wr, hi_wr = (0.25, 0.50) if long_context else (0.125, 0.25)
                out_rate = 0.75 if long_context else 0.50
                entry["cost_estimate_usd_low"] = ((i-c-w)*ir + c*cr + w*lo_wr + o*out_rate)/1_000_000
                entry["cost_estimate_usd_high"] = ((i-c-w)*ir + c*cr + w*hi_wr + o*out_rate)/1_000_000
            # Responses are private test artifacts, not request/content logs; inputs/keys are never saved here.
            artifact = Path(audit["audit_path"]).parent / f"call-{entry['stage']:02d}-response.json"
            artifact.write_text(json.dumps({"response_id": response.id, "status": response.status,
                "model": response.model, "output_text": response.output_text, "usage": usage},
                ensure_ascii=False, indent=2), encoding="utf-8")
            return response
        except Exception as exc:
            entry.update(error_type=type(exc).__name__, http_status=getattr(exc, "status_code", None))
            raise
        finally:
            write_audit(audit)
    adapter.client.responses.create = bounded_create

@app.middleware("http")
async def limit_body(request, call_next):
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > MAX_TOTAL):
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "حجم الطلب أكبر من الحد المسموح: 50 MB."}, status_code=413)
    return await call_next(request)

@app.get("/health")
def health():
    return {"status": "ok", "paid_ai_enabled": paid_enabled(), "default_mode": "MOCK", "model": os.getenv("OPENAI_MODEL", "gpt-6-luna"), "ai_readiness": ai_readiness()}

def safe_filename(name):
    basename = PureWindowsPath((name or "document.pdf").replace("/", "\\")).name
    if not basename.lower().endswith(".pdf"):
        raise HTTPException(415, "المسموح ملفات PDF فقط.")
    clean = re.sub(r"[^\w.() -]", "_", basename, flags=re.UNICODE).strip(" .")
    return (clean[:120] or "document") if clean.lower().endswith(".pdf") else clean[:115] + ".pdf"

async def save_upload(upload, folder, total):
    name = safe_filename(upload.filename)
    folder.mkdir()
    path = folder / name
    count = 0
    with path.open("xb") as stream:
        while chunk := await upload.read(64 * 1024):
            count += len(chunk)
            if count > MAX_FILE or total + count > MAX_TOTAL:
                raise HTTPException(413, "حجم الملف يتجاوز 20 MB أو إجمالي الطلب يتجاوز 50 MB.")
            stream.write(chunk)
    with path.open("rb") as stream:
        if b"%PDF-" not in stream.read(1024):
            raise HTTPException(415, "الملف ليس PDF صالحًا.")
    return path, count

async def execute(tender, companies, reference_date, mode, complete, synthetic):
    request_id = uuid.uuid4().hex
    audit = None
    if mode == "AI":
        AI_AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
        if os.getenv("TENDERPROOF_SINGLE_AI_RUN", "1") == "1":
            try:
                with AI_SINGLE_LOCK.open("x", encoding="utf-8") as lock:
                    lock.write(request_id)
            except FileExistsError:
                raise HTTPException(403, "محاولة AI المصرح بها استُخدمت؛ لا توجد إعادة تلقائية.")
        audit_dir = AI_AUDIT_ROOT / request_id
        audit_dir.mkdir(exist_ok=False)
        audit = {"request_id": request_id, "model": "gpt-6-luna", "budget_limit_usd": AI_BUDGET_USD,
            "generation_call_limit": AI_CALL_LIMIT, "output_limit_per_call": AI_OUTPUT_LIMIT, "reserved_usd": 0.0,
            "token_count_calls": 0, "calls": [], "status": "STARTED", "reference_date": str(reference_date),
            "synthetic_test": synthetic, "company_documents_complete": complete,
            "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [tender, *companies]},
            "audit_path": str(audit_dir / "audit.json")}
        write_audit(audit)
    def worker():
        async def run():
            adapter = None
            try:
                if mode == "AI":
                    from openai_adapter import OpenAIAdapter
                    adapter = OpenAIAdapter()
                    limit_openai_adapter(adapter, audit)
                report = await analyze(tender, companies, reference_date=str(reference_date), mode=mode,
                    eligibility_client=adapter, technical_client=adapter, verification_client=adapter,
                    company_documents_complete=complete, synthetic_test=synthetic)
                if audit is not None:
                    audit["status"] = "COMPLETED"
                    audit["citation_validation"] = "PASS_ORIGINAL_PIPELINE"
                    (Path(audit["audit_path"]).parent / "report.json").write_text(
                        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                return report
            except Exception as exc:
                if audit is not None:
                    audit.update(status="FAILED", error_type=type(exc).__name__)
                raise
            finally:
                if audit is not None:
                    write_audit(audit)
                if adapter is not None:
                    await adapter.aclose()
        return asyncio.run(run())
    started = time.perf_counter()
    async with analysis_lock:
        try:
            report = await run_in_threadpool(worker)
        except Exception as exc:
            # Never log exception text, document content, API payloads, or keys.
            logging.getLogger("tenderproof.web").warning("Analysis failed: %s", type(exc).__name__)
            raise HTTPException(422, "تعذر إكمال التحليل أو التحقق من المستندات. راجع ملفات PDF وإعدادات التشغيل؛ لم يُنشر تقرير نجاح.") from None
    return {"report": report, "execution": {"kind": "LIVE_AI" if mode == "AI" else "MOCK_PIPELINE",
        "is_new_analysis": True, "request_id": request_id, "synthetic_test": synthetic,
        "company_documents_complete": complete, "elapsed_seconds": round(time.perf_counter()-started, 2)}}

@app.post("/analyze")
async def analyze_uploads(
    tender: Annotated[UploadFile, File(description="Tender PDF")],
    companies: Annotated[list[UploadFile], File(description="Company PDFs")],
    reference_date: Annotated[date, Form()],
    mode: Annotated[Literal["MOCK", "AI"], Form()] = "MOCK",
    company_documents_complete: Annotated[bool, Form()] = False,
    synthetic_test: Annotated[bool, Form()] = False,
    confirm_paid_api: Annotated[bool, Form()] = False,
):
    try:
        if not 1 <= len(companies) <= 20:
            raise HTTPException(422, "ارفع من ملف واحد إلى 20 ملف شركة.")
        if mode == "AI":
            readiness = ai_readiness()
            if readiness["code"] != "READY":
                raise HTTPException(403, readiness["message"])
            if not confirm_paid_api:
                raise HTTPException(403, "يلزم تأكيد إرسال المستندات إلى OpenAI والموافقة على تكلفة هذا التشغيل.")
        with tempfile.TemporaryDirectory(prefix="tenderproof-", dir=TEMP_ROOT) as job:
            job_path = Path(job).resolve()
            assert job_path.is_relative_to(TEMP_ROOT.resolve())
            tender_path, total = await save_upload(tender, job_path / "tender", 0)
            company_paths = []
            for index, upload in enumerate(companies):
                path, size = await save_upload(upload, job_path / f"company-{index}", total)
                total += size
                company_paths.append(path)
            return await execute(tender_path, company_paths, reference_date, mode, company_documents_complete, synthetic_test)
    finally:
        await tender.close()
        for upload in companies:
            await upload.close()

def demo_manifest():
    path = DEMO_ROOT / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

def demo_case(case):
    item = demo_manifest().get(case)
    if item is None:
        raise HTTPException(404, "ملفات الديمو المحلية غير متاحة.")
    def resolve(relative):
        path = (DEMO_ROOT / relative).resolve()
        if not path.is_relative_to(DEMO_ROOT.resolve()) or not path.is_file():
            raise HTTPException(404, "ملف ديمو غير متاح.")
        return path
    return item, resolve(item["report"]), resolve(item["tender"]), [resolve(p) for p in item["company"]]

@app.get("/demo")
def list_demo():
    return [{"id": case, "label": item["label"], "company_file_count": len(item["company"])} for case, item in demo_manifest().items()]

@app.get("/demo/{case}")
def saved_demo(case: str):
    item, report_path, tender, companies = demo_case(case)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    validate_shape(report, Report)
    # Validate the saved report against the actual supplied demo PDF sources.
    paths = {p.name: p for p in [tender, *companies]}
    documents = [read_pdf(paths[m["filename"]], document_id=m["document_id"], role=m["role"]) for m in report["documents"]]
    validate_report(report, documents)
    safe_log(get_tracker(), "saved_demo_validation", "SAVED_DEMO", {}, {"validation_passed": 1, "findings": len(report["findings"])})
    return {"report": report, "execution": {"kind": "SAVED_DEMO", "is_new_analysis": False,
        "synthetic_test": True, "case": case, "label": item["label"], "elapsed_seconds": None}}

@app.post("/demo/{case}/mock")
async def mock_demo(case: str, synthetic_test: Annotated[bool, Form()] = False):
    _, _, tender, companies = demo_case(case)
    return await execute(tender, companies, date(2026, 10, 31), "MOCK", False, synthetic_test)
