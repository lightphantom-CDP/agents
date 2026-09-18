#!/usr/bin/env python3
"""Run in CAI session after pip install — shows exactly what is missing."""

import importlib
import sys
from pathlib import Path


def _ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def main() -> int:
    print(f"Python {sys.version}")
    if sys.version_info < (3, 10):
        _fail("Need Python 3.10+ for guardrails-ai-detect-pii")
        return 1
    _ok("Python version")

    for mod in ("presidio_analyzer", "presidio_anonymizer", "guardrails", "nltk"):
        try:
            importlib.import_module(mod)
            _ok(f"import {mod}")
        except ImportError as e:
            _fail(f"import {mod}: {e}")
            print("  → run: pip install guardrails-ai guardrails-ai-detect-pii")
            return 1

    try:
        from guardrails_ai.detect_pii import DetectPII

        _ok("import guardrails_ai.detect_pii.DetectPII")
    except ImportError as e:
        _fail(f"DetectPII: {e}")
        return 1

    try:
        from guardrails import Guard, OnFailAction

        rc = Path.home() / ".guardrailsrc"
        if not rc.exists():
            rc.write_text(
                "id=local-demo\nenable_metrics=false\nuse_remote_inferencing=false\n",
                encoding="utf-8",
            )

        validator = DetectPII(
            pii_entities=["US_SSN"],
            use_local=True,
            on_fail=OnFailAction.EXCEPTION,
        )
        guard = Guard().use(validator)
        guard.validate("hello world")
        _ok("Presidio validate clean text")
        try:
            guard.validate("SSN 987-65-4321")
            _fail("SSN should have been blocked")
            return 1
        except Exception:
            _ok("Presidio blocks SSN")
    except Exception as e:
        _fail(f"Presidio runtime: {e}")
        print("  → run: python -m guardrails_ai.detect_pii.post_install")
        return 1

    for p in [Path.cwd(), Path("/home/cdsw/insuranceclaim"), Path("/home/cdsw")]:
        if (p / "guardrails_check.py").exists():
            sys.path.insert(0, str(p))
            break

    import os

    os.environ["GUARDRAILS_MODE"] = "guardrails_ai"
    from guardrails_check import check_input, mode

    print(f"guardrails_check mode={mode()}")
    r = check_input("SSN 987-65-4321")
    if r.get("engine") != "guardrails_ai":
        _fail(f"check_input used engine={r.get('engine')} (Presidio not active — import failed?)")
        return 1
    if r.get("passed"):
        _fail("SSN should be blocked")
        return 1
    _ok("guardrails_check blocks SSN with engine=guardrails_ai")
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
