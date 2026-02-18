import uvicorn

from service.api import create_app
from service.config import APP_CONFIG
from service.logger.uvicorn_logging_config import LOGGING_CONFIG


def main():
    uvicorn.run(
        create_app,
        host=APP_CONFIG.app.host,
        port=APP_CONFIG.app.port,
        access_log=False,
        log_config=LOGGING_CONFIG,
    )


if __name__ == "__main__":
    main()
