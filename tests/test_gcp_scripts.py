import subprocess
import unittest
from pathlib import Path


class GoogleCloudScriptTests(unittest.TestCase):
    def test_bootstrap_and_deploy_scripts_parse(self):
        root = Path(__file__).resolve().parent.parent
        scripts = [
            root / "scripts" / "gcp_bootstrap_staging.ps1",
            root / "scripts" / "gcp_deploy_staging.ps1",
            root / "scripts" / "gcp_deploy_jobs_staging.ps1",
            root / "scripts" / "gcp_staging_status.ps1",
            root / "scripts" / "gcp_disable_billing.ps1",
        ]
        for script in scripts:
            command = (
                "$errors=$null; "
                f"[System.Management.Automation.Language.Parser]::ParseFile("
                f"'{script}',[ref]$null,[ref]$errors) > $null; "
                "if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}"
            )
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                completed.returncode,
                0,
                f"{script.name}: {completed.stdout}{completed.stderr}",
            )

    def test_scripts_default_to_plan_only(self):
        root = Path(__file__).resolve().parent.parent
        for name in (
            "gcp_bootstrap_staging.ps1",
            "gcp_deploy_staging.ps1",
            "gcp_deploy_jobs_staging.ps1",
        ):
            content = (root / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("[switch]$Apply", content)
            self.assertIn("PLAN ONLY", content)

    def test_paid_deployments_require_explicit_cost_confirmation(self):
        root = Path(__file__).resolve().parent.parent
        for name in (
            "gcp_bootstrap_staging.ps1",
            "gcp_deploy_staging.ps1",
            "gcp_deploy_jobs_staging.ps1",
        ):
            content = (root / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("[switch]$ConfirmCosts", content)
            self.assertIn("$Apply -and -not $ConfirmCosts", content)

    def test_scheduled_jobs_are_paused_after_deployment(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_deploy_jobs_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("'scheduler', 'jobs', 'pause'", content)
        self.assertIn("separate owner approval", content)

    def test_cloud_cost_policy_preserves_zero_cost_gate(self):
        root = Path(__file__).resolve().parent.parent
        content = (root / "CLOUD_COST_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("Billing must remain disabled", content)
        self.assertIn("budgets are alerts, not hard spending caps", content)
        self.assertIn("explicit approval", content)


if __name__ == "__main__":
    unittest.main()
