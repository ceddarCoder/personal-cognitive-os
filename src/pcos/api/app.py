from contextlib import asynccontextmanager
from fastapi import FastAPI
from pcos.infrastructure.database import Database
from pcos.infrastructure.settings import settings
from pcos.api.routers import capture, notes, state, divergence, convergence, chat, tasks, schedule, graph, files
from pcos.workers.embedding_worker import start_worker as start_embedding_worker
from pcos.workers.entity_extractor import start_entity_extractor
from pcos.core.bootstrap_service import BootstrapService
from pcos.workers.divergence_generator import start_generator
from pcos.workers.divergence_pusher import start_pusher
from pcos.workers.file_watcher import start_watchdog  # <-- ADD THIS
import logging
import threading
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


logger = logging.getLogger("pcos.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PCOS API starting...")
    db = Database()
    db.initialize()
    
    # Run bootstrap (idempotent)
    bootstrap = BootstrapService()
    bootstrap.run()
    
    # Start embedding worker backfill
    start_embedding_worker()
    
    # Start entity extractor (safe, non-blocking)
    start_entity_extractor()
    
    # Start background divergence workers
    threading.Thread(target=start_generator, daemon=True, name="DivergenceGenerator").start()
    threading.Thread(target=start_pusher, daemon=True, name="DivergencePusher").start()
    
    # Start file watcher for automatic indexing
    watch_dir = settings.PCOS_DATA_DIR / "watch"
    watch_dir.mkdir(parents=True, exist_ok=True)
    watch_observer = start_watchdog(watch_dir)  # <-- ADD THIS
    logger.info(f"File watcher started on {watch_dir}")
    
    logger.info("Divergence generator and pusher workers started")
    
    yield
    
    # Cleanup: stop watchdog
    if watch_observer:
        watch_observer.stop()
        watch_observer.join()
    
    logger.info("PCOS API shutting down.")

def create_app() -> FastAPI:
    app = FastAPI(title="PCOS API", version="0.3.0", lifespan=lifespan)

    # After creating the app, mount static directory
    app.mount("/static", StaticFiles(directory="src/pcos/web/static"), name="static")

    @app.get("/app")
    async def web_app():
        return FileResponse("src/pcos/web/static/index.html")
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "port": settings.API_PORT}
    
    # Routers
    app.include_router(capture.router, prefix="/capture", tags=["capture"])
    app.include_router(notes.router, prefix="/notes", tags=["notes"])
    app.include_router(state.router, prefix="/state", tags=["state"])
    app.include_router(divergence.router, prefix="/diverge", tags=["intelligence"])
    app.include_router(convergence.router, prefix="/converge", tags=["intelligence"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    app.include_router(schedule.router, prefix="/schedule", tags=["schedule"])
    app.include_router(graph.router, prefix="/graph", tags=["graph"])
    app.include_router(files.router, prefix="/files", tags=["files"])
    
    return app