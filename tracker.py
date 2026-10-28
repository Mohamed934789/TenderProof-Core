from typing import Any, Dict, Optional
import mlflow

class MLflowTracker:
    def __init__(self, experiment_name: str = "TenderProof_Evaluation", tracking_uri: Optional[str] = None):
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        self.experiment_name = experiment_name
        mlflow.set_experiment(self.experiment_name)

    def log_agent_run(
        self,
        agent_name: str,
        document_id: str,
        mode: str,
        prompt_version: str,
        metrics: Dict[str, float],
        output_payload: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ):
        """Log agent execution data and artifacts automatically."""
        run_name = f"{agent_name}_{document_id}"
        with mlflow.start_run(run_name=run_name, nested=True):
            
            mlflow.log_param("agent_name", agent_name)
            mlflow.log_param("document_id", document_id)
            mlflow.log_param("mode", mode)
            mlflow.log_param("prompt_version", prompt_version)

            if extra_params:
                for key, val in extra_params.items():
                    mlflow.log_param(key, val)

            for metric_name, val in metrics.items():
                mlflow.log_metric(metric_name, val)

            if output_payload:
                mlflow.log_dict(output_payload, f"{agent_name}_output.json")

    def log_validation_results(
        self,
        document_id: str,
        validation_metrics: Dict[str, float],
        validation_report: Optional[Dict[str, Any]] = None,
    ):
        """Log validation layer metrics and report."""
        with mlflow.start_run(run_name=f"validation_{document_id}", nested=True):
            mlflow.log_param("stage", "validation")
            mlflow.log_param("document_id", document_id)

            for metric_name, val in validation_metrics.items():
                mlflow.log_metric(metric_name, val)

            if validation_report:
                mlflow.log_dict(validation_report, "validation_report.json")
