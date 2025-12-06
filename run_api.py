"""Run FastAPI server."""
import sys
sys.path.insert(0, ".")

import uvicorn
from src.api.main import app

if __name__ == "__main__":
    print("Starting FastAPI on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
