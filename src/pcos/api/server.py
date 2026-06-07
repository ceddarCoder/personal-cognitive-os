import uvicorn
from pcos.api.app import create_app
from pcos.infrastructure.settings import settings

def start_api_server():
    app = create_app()
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=False,
    )