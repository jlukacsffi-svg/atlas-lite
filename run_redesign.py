"""Run the Atlas redesign against local read-only page APIs."""

from app.paths import project_path
from app.web_dashboard import run_server


if __name__ == "__main__":
    run_server(port=8771, web_dir=project_path("web_redesign"))
