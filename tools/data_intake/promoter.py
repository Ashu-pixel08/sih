"""
promoter.py - Staged Data Promotion Pipeline Gatekeeper
Enforces safe promotion:
incoming -> validated (technical checks pass)
validated -> approved (human linguistic & educational review signoffs confirmed)
OR -> quarantine (if validation or licensing fails)
"""

import os
import sys
import json
import shutil
from typing import Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

INCOMING_DIR = os.path.join(WORKSPACE_ROOT, "data", "incoming")
QUARANTINE_DIR = os.path.join(WORKSPACE_ROOT, "data", "quarantine")
VALIDATED_DIR = os.path.join(WORKSPACE_ROOT, "data", "validated")
APPROVED_DIR = os.path.join(WORKSPACE_ROOT, "data", "approved")

sys.path.insert(0, SCRIPT_DIR)
from validator import DataIntakeValidator


class DataPromoter:
    def __init__(self):
        self.validator = DataIntakeValidator()

    def process_incoming_file(self, filename: str) -> Dict[str, Any]:
        src_path = os.path.join(INCOMING_DIR, filename)
        if not os.path.exists(src_path):
            return {"success": False, "error": f"File not found in incoming: {src_path}"}

        val_result = self.validator.validate_file(src_path)

        if val_result.get("quarantine_recommended") or not val_result["valid"]:
            dest_path = os.path.join(QUARANTINE_DIR, filename)
            shutil.move(src_path, dest_path)
            # Write quarantine report
            rep_path = dest_path + ".quarantine_report.json"
            with open(rep_path, "w", encoding="utf-8") as f:
                json.dump(val_result, f, indent=2)
            return {
                "success": False,
                "action": "QUARANTINED",
                "destination": dest_path,
                "errors": val_result.get("errors", [])
            }
        else:
            dest_path = os.path.join(VALIDATED_DIR, filename)
            shutil.move(src_path, dest_path)
            return {
                "success": True,
                "action": "PROMOTED_TO_VALIDATED",
                "destination": dest_path,
                "passed_records": val_result["passed_records"]
            }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python promoter.py <filename_in_incoming>")
        sys.exit(1)

    promoter = DataPromoter()
    res = promoter.process_incoming_file(sys.argv[1])
    print(json.dumps(res, indent=2))
