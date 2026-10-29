"""Optional MLflow metadata only. Never log source text, filenames, outputs or secrets."""
import logging
import os
from pathlib import Path
from uuid import uuid4

class MLflowTracker:
    def __init__(self, experiment_name="TenderProof_Evaluation", tracking_uri=None):
        from mlflow import MlflowClient
        runtime = Path(os.getenv("TENDERPROOF_RUNTIME_DIR", "runtime")).resolve()
        store = runtime / "mlflow"
        store.mkdir(parents=True, exist_ok=True)
        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI") or "sqlite:///" + (store / "mlflow.db").as_posix()
        self.client = MlflowClient(tracking_uri=uri)
        self.experiment_id = self.client.get_experiment_by_name(experiment_name)
        if self.experiment_id is None:
            self.experiment_id = self.client.create_experiment(experiment_name, artifact_location=(store / "artifacts").as_uri())
        else:
            self.experiment_id = self.experiment_id.experiment_id
        self.pipeline_id = uuid4().hex

    def log_agent_run(self, agent_name, document_id, mode, prompt_version, metrics,
                      output_payload=None, extra_params=None):
        # Compatibility arguments intentionally ignored: document_id, output_payload,
        # and arbitrary extra_params can contain private data.
        run = self.client.create_run(self.experiment_id, tags={
            "mlflow.runName": agent_name, "pipeline_id": self.pipeline_id,
            "evaluation_type": "Operational telemetry; no ground truth",
        })
        ident = run.info.run_id
        try:
            for key, value in {"stage": agent_name, "mode": mode, "prompt_version": prompt_version}.items():
                self.client.log_param(ident, key, str(value))
            allowed = {"elapsed_seconds", "requirements", "boq_items", "findings", "documents",
                       "validation_passed", "SATISFIED", "CONTRADICTED", "MISSING_EVIDENCE", "NEEDS_REVIEW"}
            for key, value in metrics.items():
                if key in allowed:
                    self.client.log_metric(ident, key, float(value))
            self.client.set_terminated(ident)
        except Exception:
            self.client.set_terminated(ident, status="FAILED")
            raise

    def log_validation_results(self, document_id, validation_metrics, validation_report=None):
        self.log_agent_run("validation", "", "VALIDATION", "unchanged", validation_metrics)


def get_tracker():
    if os.getenv("TENDERPROOF_MLFLOW_ENABLED", "0") != "1":
        return None
    try:
        return MLflowTracker()
    except Exception:
        logging.getLogger("tenderproof.tracking").warning("MLflow unavailable; analysis continues without tracking.")
        return None


def safe_log(tracker, stage, mode, provenance, metrics):
    if tracker is None:
        return
    try:
        tracker.log_agent_run(stage, "", mode, provenance.get("prompt_version", "unchanged"), metrics)
    except Exception:
        logging.getLogger("tenderproof.tracking").warning("MLflow write failed; analysis results are unaffected.")
