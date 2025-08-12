from fastapi import FastAPI
from app.routes import session_list

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API is running"}

# Health check endpoint to wake up the server
@app.get("/status")
def status_check():
    return {"status": "200"}

app.include_router(session_list.router, prefix="/api")
