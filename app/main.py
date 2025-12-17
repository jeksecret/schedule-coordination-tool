import os
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.auth.deps import require_allowed_user
from app.routes.api.meta.enums import router as meta_router
from app.routes.api.sessions.list import router as sessions_list_router
from app.routes.api.sessions.create import router as sessions_create_router
from app.routes.api.sessions.status import router as sessions_status_router
from app.routes.api.sessions.confirmation_summary import router as confirmation_summary_router
from app.routes.api.notion.facility_info import router as notion_router
from app.routes.api.hooks.make_evaluator_email import router as evaluator_hook_router
from app.routes.api.hooks.make_facility_email import router as facility_hook_router
from app.routes.api.hooks.evaluator_response import router as evaluator_response_router
from app.routes.api.hooks.client_response import router as client_response_router
from app.routes.api.hooks.make_form_urls import router as form_urls_hook_router
from app.routes.api.hooks.auth.before_user_created import router as auth_hook_router
from app.routes.api.hooks.reminder_mail import router as reminder_mail_router

load_dotenv()

app = FastAPI()

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "https://schedule-coordination-tool.onrender.com",
)

def _parse_cors_origins(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if "*" in parsed:
        return ["*"]
    return parsed or list(DEFAULT_CORS_ORIGINS)

def _configure_cors(application: FastAPI) -> None:
    origins = _parse_cors_origins(os.getenv("CORS_ALLOW_ORIGINS"))
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials="*" not in origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_configure_cors(app)

@app.get("/")
def read_root():
    """Root endpoint for API status."""
    return {"message": "API is running"}

@app.get("/status")
def status_check():
    """Health check endpoint."""
    return {"status": "200"}

deps = [Depends(require_allowed_user)]
app.include_router(sessions_list_router, prefix="/api/sessions", dependencies=deps)
app.include_router(sessions_create_router, prefix="/api/sessions", dependencies=deps)
app.include_router(sessions_status_router, prefix="/api/sessions", dependencies=deps)
app.include_router(confirmation_summary_router, prefix="/api/sessions", dependencies=deps)
app.include_router(meta_router, prefix="/api/meta", dependencies=deps)
app.include_router(notion_router, prefix="/api/notion", dependencies=deps)
app.include_router(evaluator_hook_router, prefix="/api/hooks", dependencies=deps)
app.include_router(facility_hook_router, prefix="/api/hooks", dependencies=deps)
app.include_router(evaluator_response_router, prefix="/api/hooks")
app.include_router(client_response_router, prefix="/api/hooks")
app.include_router(form_urls_hook_router, prefix="/api/hooks")
app.include_router(auth_hook_router, prefix="/api/hooks/auth")
app.include_router(reminder_mail_router, prefix="/api/hooks")
