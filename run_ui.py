"""Run the Family Network UI."""

import subprocess
import sys


# Set path and run
sys.path.insert(0, ".")

from src.ui.main_app import run_app

if __name__ == "__main__":
    run_app()
