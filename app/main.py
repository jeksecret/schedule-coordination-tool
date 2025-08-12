from fastapi import FastAPI, APIRouter
from app.routes import session_list
from app.routes import session_create
from app.routes import notion_fetch

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is running"}

# Health check endpoint to wake up the server
@app.get("/status")
def status_check():
    return {"status": "200"}

# Group routers /api
api_router = APIRouter(prefix="/api")
api_router.include_router(session_list.router)
api_router.include_router(session_create.router)
api_router.include_router(notion_fetch.router)
app.include_router(api_router)
