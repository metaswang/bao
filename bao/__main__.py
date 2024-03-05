# start a fastapi server with uvicorn

import uvicorn

from bao.discord_client.main import run_as_daemon_service
from bao.fastapi_app import create_fastapi_app
from bao.settings.settings import settings

# 1 run discord client
run_as_daemon_service()
# 2 run fastapi and gradio ui - chatbot interface
# log_config=None: do not use the uvicorn logging configuration
# https://github.com/tiangolo/fastapi/discussions/7457#discussioncomment-5141108
app = create_fastapi_app()
uvicorn.run(app, host="0.0.0.0", port=settings().server.port, log_config=None)
