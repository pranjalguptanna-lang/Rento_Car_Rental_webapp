from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from backend.routers import auth, vehicles, bookings, payments, gamification

app = FastAPI(title="Rento API")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(gamification.router)

@app.get("/")
def read_root_ui():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(html_path)

@app.get("/health")
def health_check():
    return {"status": "ok"}




