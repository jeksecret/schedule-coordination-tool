from fastapi import FastAPI, APIRouter
from app.routes.api.meta import enums
from app.routes.api.sessions import list
from app.routes.api.notion import facility_info

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is running"}

# Health check endpoint to wake up the server
@app.get("/status")
def status_check():
    return {"status": "200"}

# Group routers /api/sessions
api_router = APIRouter(prefix="/api/sessions")
api_router.include_router(list.router)
app.include_router(api_router)

# Group routers /api/meta
api_router = APIRouter(prefix="/api/meta")
api_router.include_router(enums.router)
app.include_router(api_router)

# Group routers /api/notion
api_router = APIRouter(prefix="/api/notion")
api_router.include_router(facility_info.router)
app.include_router(api_router)
