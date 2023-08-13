import nonebot
from .run import auto_pcr_web

app = nonebot.get_bot().server_app
app.register_blueprint(auto_pcr_web)