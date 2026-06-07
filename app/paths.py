"""Central code and writable-data paths for local and cloud Atlas runtimes."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.getenv("ATLAS_DATA_ROOT", str(PROJECT_ROOT))).resolve()


def data_path(*parts):
    return DATA_ROOT.joinpath(*parts)


def project_path(*parts):
    return PROJECT_ROOT.joinpath(*parts)
