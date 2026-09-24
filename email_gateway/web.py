"""Public project landing page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

WEB_ROOT = Path(__file__).parent / "web"
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=FileResponse)
def landing_page() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")
