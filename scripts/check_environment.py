"""Offline setup checks only. Does not invoke agents or read .env values."""
from pathlib import Path
import importlib
import json
import sys
import typing

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("models", "llm_client", "pdf_reader", "agent1", "agent2",
           "agent3", "validation", "orchestrator")

def main() -> int:
    passed = 0
    failures = []
    def require(condition):
        if not condition:
            raise ValueError("Check failed")
    def verify(name, action):
        nonlocal passed
        try:
            action()
        except Exception as error:
            failures.append(name)
            print(f"FAIL: {name} ({type(error).__name__})")
        else:
            passed += 1
            print(f"PASS: {name}")

    verify("Python 3.12 or newer", lambda: require(sys.version_info >= (3, 12)))
    verify("Virtual environment active", lambda: require(sys.prefix != sys.base_prefix))
    sys.path.insert(0, str(ROOT))
    for name in MODULES:
        verify(f"Import {name}", lambda name=name: importlib.import_module(name))
    def contracts():
        for value in vars(importlib.import_module("models")).values():
            if typing.is_typeddict(value):
                typing.get_type_hints(value)
    verify("Contract annotations resolve", contracts)
    def workspace():
        value = json.loads((ROOT / "TenderProof-Team.code-workspace").read_text(encoding="utf-8"))
        require(len(value["folders"]) == 1 and value["folders"][0]["path"] == ".")
        interpreter = value.get("settings", {}).get("python.defaultInterpreterPath", "")
        require(interpreter.startswith("${workspaceFolder}/"))
    verify("Workspace uses clone-relative paths", workspace)
    verify("requirements.txt available", lambda: require((ROOT / "requirements.txt").is_file()))
    verify(".env.example available", lambda: require((ROOT / ".env.example").is_file()))
    count = len(list((ROOT / "tests").glob("test_*.py")))
    print(f"Behavior test files: {count} (not executed here)")
    if count == 0:
        print("NOTE: zero behavior tests does not establish a working AI pipeline.")
    print("No agents invoked, secrets read, or provider calls made.")
    print(f"Environment checks: {passed} passed, {len(failures)} failed.")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
