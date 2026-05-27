"""
Run with:  python -m ppe_compliance_system.api
"""
import uvicorn
from .server import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "ppe_compliance_system.api:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
