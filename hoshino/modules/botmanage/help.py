# built-in
import base64
from pathlib import Path
import random
from typing import Union, Optional
import time

# 3rd-party
from nonebot import MessageSegment, on_startup

# project
from hoshino import Service, priv, R
from hoshino.typing import CQEvent, HoshinoBot
from hoshino.msghandler import load_whitelist_from_db, add_group_whitelist, remove_group_whitelist, add_user_whitelist, remove_user_whitelist

gs_current_dir = Path(__file__).parent

sv = Service('_help_', manage_priv=priv.SUPERUSER, visible=False)

help_img: Path = gs_current_dir / "data" / "help.png"
help_msg: str = '''
bot最近可能收不到私聊消息，请在群聊里使用bot功能
遇到bot功能问题可以加怡宝好友询问：981082801
想要进入怡批吹水群也可以加怡宝好友进行审核
公主连结相关功能源码： https://github.com/watermellye/hoshinoBot/ 
'''.strip()

help_img_str: str = f'[CQ:image,file=base64://{base64.b64encode(help_img.read_bytes()).decode()}]'

def get_db_id(ev: CQEvent) -> int:
    return (int(ev.group_id) * 10 + 1) if ev.group_id else (int(ev.user_id) * 10 + 2)

def get_current_timestamp() -> int:
    return int(time.time())

@sv.on_fullmatch('help', '帮助')
async def send_help_async(bot: HoshinoBot, ev: CQEvent):
    #await bot.send(ev,  MessageSegment.image(f'file:///{help_img}') + MessageSegment.text(help_msg + suffix))
    await bot.send(ev, f'{help_img_str}{help_msg}')

memes = []
def reload_memes():
    global memes
    memes = []
    meme_path = Path(R.img('laopo/chosen/').path)
    if meme_path.exists() and meme_path.is_dir():
        memes = [x for x in meme_path.glob('*') if x.is_file()]

@on_startup
async def nonebot_on_startup_async():
    reload_memes()
    load_whitelist_from_db()

@sv.scheduled_job('interval', seconds=3600)
async def reload_memes_cron_async():
    reload_memes()
    
@sv.on_fullmatch('重载表情')
async def reload_memes_interface(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    reload_memes()
    await bot.send(ev, f'Done. {len(memes)} memes loaded.')

def get_random_meme() -> Union[MessageSegment, str]:
    if memes:
        file_name = random.choice(memes).name
        return R.img(f'laopo/chosen/{file_name}').cqcode
    return "我在"

@sv.on_message('group')
@sv.on_message('private')
async def send_meme_async(bot: HoshinoBot, ev: CQEvent):
    if ev.raw_message.strip() in ("怡宝", "e宝", "E宝", "恰宝", "eaq", "ebq", "ecq", "ellye"):
        await bot.send(ev, get_random_meme())

@sv.on_prefix(('添加群白名单', 'add_group_whitelist'))
async def add_whitelist_interface_async(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    raw_msg = ev.message.extract_plain_text()
    try:
        group_id = int(raw_msg)
    except:
        await bot.send(ev, f'[{raw_msg}] is not a valid group_id')
        return
    try:
        add_group_whitelist(group_id)
    except Exception as e:
        await bot.send(ev, f'Failed to add [{group_id}] to group whitelist: {e}')
        return
    await bot.send(ev, f'[{group_id}] added to group whitelist')

@sv.on_prefix(('移除群白名单', 'remove_group_whitelist'))
async def remove_whitelist_interface_async(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    raw_msg = ev.message.extract_plain_text()
    try:
        group_id = int(raw_msg)
    except:
        await bot.send(ev, f'[{raw_msg}] is not a valid group_id')
        return
    try:
        remove_group_whitelist(group_id)
    except Exception as e:
        await bot.send(ev, f'Failed to remove [{group_id}] from group whitelist: {e}')
        return
    await bot.send(ev, f'[{group_id}] removed from group whitelist')

@sv.on_prefix(('添加用户白名单', 'add_user_whitelist'))
async def add_whitelist_interface_async(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    raw_msg = ev.message.extract_plain_text()
    try:
        user_id = int(raw_msg)
    except:
        await bot.send(ev, f'[{raw_msg}] is not a valid user_id')
        return
    try:
        add_user_whitelist(user_id)
    except Exception as e:
        await bot.send(ev, f'Failed to add [{user_id}] to user whitelist: {e}')
        return
    await bot.send(ev, f'[{user_id}] added to user whitelist')

@sv.on_prefix(('移除用户白名单', 'remove_user_whitelist'))
async def remove_whitelist_interface_async(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    raw_msg = ev.message.extract_plain_text()
    try:
        user_id = int(raw_msg)
    except:
        await bot.send(ev, f'[{raw_msg}] is not a valid user_id')
        return
    try:
        remove_user_whitelist(user_id)
    except Exception as e:
        await bot.send(ev, f'Failed to remove [{user_id}] from user whitelist: {e}')
        return
    await bot.send(ev, f'[{user_id}] removed from user whitelist')

@sv.on_fullmatch(('刷新白名单', '加载白名单', 'load_whitelist'))
async def load_whitelist_interface_async(bot: HoshinoBot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        return
    try:
        load_whitelist_from_db()
    except Exception as e:
        await bot.send(ev, f'Failed to load whitelist from db: {e}')
        return
    await bot.send(ev, 'Whitelist loaded from db')