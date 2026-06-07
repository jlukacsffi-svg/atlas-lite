import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class RuntimePathTests(unittest.TestCase):
    def test_private_runtime_paths_follow_atlas_data_root(self):
        project_root = Path(__file__).resolve().parent.parent
        script = """
import json
from app.analyst_actions import DEFAULT_ANALYST_CACHE_DIR
from app.earnings_calendar import DEFAULT_EARNINGS_CACHE_DIR
from app.growth import DEFAULT_SEC_CACHE_DIR
from app.insider_transactions import DEFAULT_INSIDER_CACHE_DIR
from app.paper_trading import DEFAULT_ACCOUNT_FILE
from app.portfolio import DEFAULT_PORTFOLIO_PATH
from app.research_memory import DEFAULT_ARCHIVE_DIR
from app.research_tasks import DEFAULT_TASK_FILE
from app.weekly_summary import DEFAULT_REPORTS_DIR
print(json.dumps({
    "analysts": str(DEFAULT_ANALYST_CACHE_DIR),
    "earnings": str(DEFAULT_EARNINGS_CACHE_DIR),
    "sec": str(DEFAULT_SEC_CACHE_DIR),
    "insiders": str(DEFAULT_INSIDER_CACHE_DIR),
    "paper": str(DEFAULT_ACCOUNT_FILE),
    "portfolio": str(DEFAULT_PORTFOLIO_PATH),
    "archive": str(DEFAULT_ARCHIVE_DIR),
    "tasks": str(DEFAULT_TASK_FILE),
    "reports": str(DEFAULT_REPORTS_DIR),
}))
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            env = os.environ.copy()
            env["ATLAS_DATA_ROOT"] = temp_dir
            completed = subprocess.run(
                [os.sys.executable, "-c", script],
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            paths = json.loads(completed.stdout)

        root = Path(temp_dir)
        for value in paths.values():
            self.assertTrue(Path(value).is_relative_to(root), value)


if __name__ == "__main__":
    unittest.main()
