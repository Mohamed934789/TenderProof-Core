"""Offline integration checks: telemetry privacy, paid gates, original saved citations."""
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("TENDERPROOF_RUNTIME_DIR", str(ROOT / "runtime" / "test-web"))
from web import api
from orchestrator import analyze
from tracker import MLflowTracker, get_tracker

@pytest.fixture
def client():
    with patch.object(api, "DEMO_ROOT", ROOT / "demo"):
        with TestClient(api.app) as c:
            yield c

@pytest.mark.parametrize("case,counts", [
    ("case_101", [11,0,0,3]), ("case_202", [2,8,0,3]), ("case_303", [3,0,0,10])])
def test_saved_demo_validates_original_sources(client, case, counts):
    result = client.get("/demo/"+case)
    assert result.status_code == 200
    data = result.json()
    assert data["execution"]["kind"] == "SAVED_DEMO"
    assert not data["execution"]["is_new_analysis"]
    assert data["report"] == json.loads((ROOT / "demo" / case / "report.json").read_text(encoding="utf-8"))
    assert [sum(f["status"]==s for f in data["report"]["findings"]) for s in
        ("SATISFIED","CONTRADICTED","MISSING_EVIDENCE","NEEDS_REVIEW")] == counts

@pytest.mark.parametrize("allowed,key,lock,code", [
    ("0","",False,"DISABLED"), ("1","",False,"KEY_MISSING"),
    ("1","offline-test-placeholder",False,"READY"),
    ("1","offline-test-placeholder",True,"ATTEMPT_USED")])
def test_readiness_without_any_network(monkeypatch,tmp_path,allowed,key,lock,code):
    monkeypatch.setenv("TENDERPROOF_ALLOW_PAID_API",allowed)
    monkeypatch.setenv("OPENAI_API_KEY",key)
    monkeypatch.setenv("OPENAI_MODEL","gpt-6-luna")
    monkeypatch.setenv("TENDERPROOF_SINGLE_AI_RUN","1")
    monkeypatch.setattr(api,"KEY_FILE_ERROR",False)
    path=tmp_path/"attempt.lock"
    if lock: path.write_text("consumed")
    monkeypatch.setattr(api,"AI_SINGLE_LOCK",path)
    assert api.ai_readiness()["code"]==code
    if lock: assert path.read_text()=="consumed"


def test_paid_request_requires_consent_before_execution(client,monkeypatch):
    monkeypatch.setattr(api,"ai_readiness",lambda:{"code":"READY"})
    with patch.object(api,"execute",side_effect=AssertionError("No AI allowed")):
        result=client.post("/analyze",data={"reference_date":"2026-10-31","mode":"AI"},files=[
            ("tender",("test.pdf",b"%PDF-test","application/pdf")),
            ("companies",("test.pdf",b"%PDF-test","application/pdf"))])
    assert result.status_code==403


def test_mock_upload_and_safe_names(client):
    folder=ROOT/"demo/case_101"
    with (folder/"requirements_ar.pdf").open("rb") as tender, (folder/"01_company_profile.pdf").open("rb") as company:
        response=client.post("/analyze",data={"reference_date":"2026-10-31","mode":"MOCK"},files=[
            ("tender",("../../requirements_ar.pdf",tender,"application/pdf")),
            ("companies",("..\\profile.pdf",company,"application/pdf"))])
    assert response.status_code==200
    assert response.json()["report"]["mode"]=="MOCK"
    assert response.json()["report"]["findings"]==[]
    assert api.safe_filename("../../name.pdf")=="name.pdf"


def test_optional_tracker_failure_does_not_change_report(monkeypatch):
    class Broken:
        def log_agent_run(self,*args,**kwargs): raise RuntimeError("unavailable")
    folder=ROOT/"demo/case_101"
    args=(folder/"requirements_ar.pdf",[folder/"01_company_profile.pdf"])
    monkeypatch.setenv("TENDERPROOF_MLFLOW_ENABLED","0")
    baseline=asyncio.run(analyze(*args,reference_date="2026-10-31"))
    tracked=asyncio.run(analyze(*args,reference_date="2026-10-31",tracker=Broken()))
    assert tracked==baseline
    assert get_tracker() is None


def test_real_mlflow_records_metrics_without_sensitive_artifacts(tmp_path,monkeypatch):
    pytest.importorskip("mlflow")
    monkeypatch.setenv("TENDERPROOF_RUNTIME_DIR",str(tmp_path))
    tracker=MLflowTracker(tracking_uri="sqlite:///"+(tmp_path/"tracking.db").as_posix())
    tracker.log_agent_run("agent1","private-filename", "MOCK","v4",{"requirements":2},
        output_payload={"secret":"must-never-be-saved"},extra_params={"key":"must-never-be-saved"})
    runs=tracker.client.search_runs([tracker.experiment_id])
    assert len(runs)==1 and runs[0].data.metrics["requirements"]==2
    assert tracker.client.list_artifacts(runs[0].info.run_id)==[]
    assert "key" not in runs[0].data.params and "document_id" not in runs[0].data.params


def test_mlflow_pipeline_records_all_stages(tmp_path,monkeypatch):
    pytest.importorskip("mlflow")
    monkeypatch.setenv("TENDERPROOF_RUNTIME_DIR",str(tmp_path))
    tracker=MLflowTracker(tracking_uri="sqlite:///"+(tmp_path/"pipeline.db").as_posix())
    folder=ROOT/"demo/case_101"
    asyncio.run(analyze(folder/"requirements_ar.pdf",[folder/"01_company_profile.pdf"],
        reference_date="2026-10-31",tracker=tracker))
    runs=tracker.client.search_runs([tracker.experiment_id])
    assert {r.data.params["stage"] for r in runs}=={"agent1","agent2","agent3","validation"}
    assert all(r.info.status=="FINISHED" for r in runs)
    validation=next(r for r in runs if r.data.params["stage"]=="validation")
    assert validation.data.metrics["validation_passed"]==1


def test_mlflow_initialization_failure_is_nonfatal(monkeypatch):
    monkeypatch.setenv("TENDERPROOF_MLFLOW_ENABLED","1")
    with patch("tracker.MLflowTracker",side_effect=RuntimeError("tracking down")):
        assert get_tracker() is None


@pytest.mark.asyncio
async def test_cost_gate_refuses_oversized_input_before_generation(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    generation=AsyncMock()
    responses=SimpleNamespace(create=generation,input_tokens=SimpleNamespace(count=AsyncMock(
        return_value=SimpleNamespace(input_tokens=1_000_000))))
    adapter=SimpleNamespace(model="gpt-6-luna",client=SimpleNamespace(
        base_url="https://api.openai.com/v1",max_retries=0,responses=responses))
    audit={"audit_path":str(tmp_path/"audit.json"),"calls":[],"token_count_calls":0,"reserved_usd":0.0}
    api.limit_openai_adapter(adapter,audit)
    with pytest.raises(PermissionError,match="budget"):
        await responses.create(model="gpt-6-luna",instructions="test",input="test",text={})
    generation.assert_not_awaited()
    assert audit["calls"][0]["generation_attempted"] is False


@pytest.mark.asyncio
async def test_call_limit_prevents_fourth_request(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    generation=AsyncMock()
    counter=AsyncMock()
    responses=SimpleNamespace(create=generation,input_tokens=SimpleNamespace(count=counter))
    adapter=SimpleNamespace(model="gpt-6-luna",client=SimpleNamespace(
        base_url="https://api.openai.com/v1",max_retries=0,responses=responses))
    audit={"audit_path":str(tmp_path/"audit.json"),"calls":[{}, {}, {}],"token_count_calls":0,"reserved_usd":0.0}
    api.limit_openai_adapter(adapter,audit)
    with pytest.raises(PermissionError,match="call limit"):
        await responses.create(model="gpt-6-luna")
    generation.assert_not_awaited()
    counter.assert_not_awaited()
