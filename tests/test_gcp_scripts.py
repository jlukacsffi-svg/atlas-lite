import subprocess
import unittest
from pathlib import Path


class GoogleCloudScriptTests(unittest.TestCase):
    def test_bootstrap_and_deploy_scripts_parse(self):
        root = Path(__file__).resolve().parent.parent
        scripts = [
            root / "scripts" / "gcp_bootstrap_staging.ps1",
            root / "scripts" / "gcp_configure_oauth_secrets.ps1",
            root / "scripts" / "gcp_deploy_staging.ps1",
            root / "scripts" / "gcp_deploy_jobs_staging.ps1",
            root / "scripts" / "gcp_configure_monitoring_staging.ps1",
            root / "scripts" / "gcp_configure_artifact_cleanup.ps1",
            root / "scripts" / "gcp_set_schedules_staging.ps1",
            root / "scripts" / "gcp_staging_readiness.ps1",
            root / "scripts" / "gcp_staging_status.ps1",
            root / "scripts" / "gcp_disable_billing.ps1",
            root / "scripts" / "gcp_zero_cost_audit.ps1",
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
            "gcp_configure_monitoring_staging.ps1",
            "gcp_configure_artifact_cleanup.ps1",
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
            "gcp_configure_monitoring_staging.ps1",
            "gcp_configure_artifact_cleanup.ps1",
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
        self.assertIn("$previousErrorAction = $ErrorActionPreference", content)
        self.assertIn(
            "$ErrorActionPreference = 'SilentlyContinue'",
            content,
        )

    def test_dashboard_build_uses_purpose_built_cloud_build_role(self):
        root = Path(__file__).resolve().parent.parent
        deploy_content = (
            root / "scripts" / "gcp_deploy_staging.ps1"
        ).read_text(encoding="utf-8")
        bootstrap_content = (
            root / "scripts" / "gcp_bootstrap_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertNotIn("--service-account=projects/", deploy_content)
        self.assertIn(
            "'--role=roles/cloudbuild.builds.builder'",
            bootstrap_content,
        )

    def test_dashboard_deploy_uses_owner_oauth_and_secret_manager(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_deploy_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("ATLAS_AUTH_MODE=google_oauth", content)
        self.assertIn("'--allow-unauthenticated'", content)
        self.assertIn("'--no-iap'", content)
        self.assertNotIn("'--iap'", content)
        self.assertIn("--set-secrets=", content)
        self.assertIn("roles/secretmanager.secretAccessor", content)
        self.assertIn("atlas-google-oauth-client-id", content)
        self.assertIn("atlas-google-oauth-client-secret", content)
        self.assertIn("atlas-session-secret", content)

    def test_monitoring_uses_low_frequency_checks_and_owner_alerts(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_configure_monitoring_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("'--period=10'", content)
        self.assertIn("$UptimeTimeoutSeconds = 30", content)
        self.assertIn("'monitoring', 'uptime', 'update'", content)
        self.assertIn("'--regions=usa-oregon,usa-iowa,usa-virginia'", content)
        self.assertIn("Atlas dashboard unavailable", content)
        self.assertIn("Atlas cloud job failed", content)
        self.assertIn("notificationChannels", content)
        self.assertIn("email_address = $OwnerEmail", content)
        self.assertIn("$0-$0.10 per month", content)

    def test_staging_status_includes_jobs_schedules_and_monitoring(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_staging_status.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("'scheduler', 'jobs', 'describe'", content)
        self.assertIn("'run', 'jobs', 'executions', 'list'", content)
        self.assertIn("'monitoring', 'uptime', 'list-configs'", content)
        self.assertIn("'monitoring', 'policies', 'list'", content)
        self.assertIn("'artifacts', 'docker', 'images', 'list'", content)
        self.assertIn("Artifact image count:", content)
        self.assertIn("'--format=value(cleanupPolicyDryRun)'", content)

    def test_schedule_resume_requires_explicit_recurring_approval(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_set_schedules_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[switch]$ApproveRecurringExecution", content)
        self.assertIn(
            "-Apply -ConfirmCosts -ApproveRecurringExecution",
            content,
        )
        self.assertIn("Latest execution for $job", content)
        self.assertIn("Required staging monitoring", content)

    def test_artifact_cleanup_defaults_to_dry_run_and_keeps_rollbacks(self):
        root = Path(__file__).resolve().parent.parent
        script = (
            root / "scripts" / "gcp_configure_artifact_cleanup.ps1"
        ).read_text(encoding="utf-8")
        policy = (
            root / "cloud" / "artifact_cleanup_policy.json"
        ).read_text(encoding="utf-8")
        self.assertIn("[switch]$ActivateDeletion", script)
        self.assertIn("$arguments += '--dry-run'", script)
        self.assertIn('"olderThan": "14d"', policy)
        self.assertIn('"keepCount": 3', policy)
        self.assertIn(
            "Cleanup policy is configured in dry-run mode",
            script,
        )

    def test_staging_readiness_is_read_only_and_preserves_manual_gates(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_staging_readiness.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("Mode: READ ONLY", content)
        self.assertIn("No project Editor role", content)
        self.assertIn("Artifact cleanup is non-destructive", content)
        self.assertIn("Cold-start monitoring tolerance", content)
        self.assertIn("Cross-device owner login", content)
        self.assertIn("Non-owner Google account denial", content)
        self.assertIn("Separate owner approval before schedule resume", content)
        for mutation in (
            "'deploy'",
            "'update'",
            "'resume'",
            "'create'",
            "'delete'",
            "'set-iam-policy'",
        ):
            self.assertNotIn(mutation, content)

    def test_oauth_secret_setup_never_prints_secret_values(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_configure_oauth_secrets.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[switch]$Apply", content)
        self.assertIn("[switch]$ConfirmCosts", content)
        self.assertIn("RandomNumberGenerator]::Create()", content)
        self.assertIn("GetBytes($sessionBytes)", content)
        self.assertIn("redacted secret version", content)
        self.assertNotIn("Write-Host $clientId", content)
        self.assertNotIn("Write-Host $clientSecret", content)
        self.assertNotIn("Write-Host $sessionValue", content)

    def test_cloud_cost_policy_preserves_controlled_cost_gate(self):
        root = Path(__file__).resolve().parent.parent
        content = (root / "CLOUD_COST_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("Billing is linked only", content)
        self.assertIn("`$10` monthly alert budget", content)
        self.assertIn("budgets are alerts, not hard spending caps", content)
        self.assertIn("explicit approval", content)

    def test_zero_cost_audit_checks_billing_resources_and_deployment_apis(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_zero_cost_audit.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("billing projects describe", content)
        self.assertIn("storage buckets list", content)
        self.assertIn("BigQuery datasets", content)
        self.assertIn("run.googleapis.com", content)
        self.assertIn("zero-cost audit failed", content)

    def test_bootstrap_defaults_to_small_budget_and_no_paid_scanning(self):
        root = Path(__file__).resolve().parent.parent
        content = (
            root / "scripts" / "gcp_bootstrap_staging.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("[int]$MonthlyBudgetUsd = 10", content)
        self.assertIn(
            "'--credit-types-treatment=exclude-all-credits'",
            content,
        )
        self.assertIn("$_" + ".displayName -eq 'atlas-staging-monthly'", content)
        self.assertNotIn("'--filter=displayName=atlas-staging-monthly'", content)
        self.assertIn("$ErrorActionPreference = 'SilentlyContinue'", content)
        self.assertIn("'--threshold-rule=percent=0.25'", content)
        self.assertNotIn("--allow-vulnerability-scanning", content)
        self.assertLess(
            content.index("'billing', 'budgets', 'create'"),
            content.index("'artifactregistry.googleapis.com'"),
        )
        self.assertIn("[switch]$BillingAndBudgetOnly", content)
        self.assertLess(
            content.index("if ($BillingAndBudgetOnly)"),
            content.index("$services = @("),
        )
        self.assertIn("roles/storage.legacyBucketReader", content)
        self.assertIn("roles/storage.legacyObjectReader", content)
        self.assertIn("Invoke-Gcloud -AllowFailure", content)
        self.assertIn("$ProjectNumber-compute@developer.gserviceaccount.com", content)
        self.assertIn("'--role=roles/editor'", content)
        self.assertIn('"--member=user:$OwnerEmail"', content)
        self.assertIn("'--role=roles/storage.admin'", content)
        self.assertIn("'cloudresourcemanager.googleapis.com'", content)
        self.assertLess(
            content.index('"--member=user:$OwnerEmail"'),
            content.index("foreach ($legacyBinding"),
        )


if __name__ == "__main__":
    unittest.main()
