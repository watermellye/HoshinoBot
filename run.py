import hoshino
import asyncio

bot = hoshino.init()
app = bot.asgi

if __name__ == '__main__':    
    # from hoshino.modules.priconne.pcr_secret import test_on_startup
    # asyncio.run(test_on_startup())
    bot.run(use_reloader=False, loop=asyncio.get_event_loop())