import threading
from pathlib import Path
import time

from nonebot.command import SwitchException
from peewee import SqliteDatabase, Model, IntegerField

from hoshino import CanceledException, message_preprocessor, trigger
from hoshino.typing import CQEvent
import hoshino

g_group_whitelist: set = set()
g_user_whitelist: set = set()

gs_current_dir = Path(__file__).parent
db = SqliteDatabase(str(gs_current_dir / "modules" / "botmanage" / "data" / "whitelist.sqlite"))

class BaseModel(Model):
    class Meta:
        database = db

class group_whitelist(BaseModel):
    group_id = IntegerField(primary_key=True)

class user_whitelist(BaseModel):
    user_id = IntegerField(primary_key=True)

db.connect()
db.create_tables([group_whitelist, user_whitelist])

def load_whitelist_from_db() -> None:
    global g_group_whitelist, g_user_whitelist
    g_group_whitelist = { g.group_id for g in group_whitelist.select() }
    g_user_whitelist = { u.user_id for u in user_whitelist.select() }

def add_group_whitelist(group_id: int) -> None:
    global g_group_whitelist
    g_group_whitelist.add(group_id)
    _ = group_whitelist.get_or_create(group_id=group_id)

def remove_group_whitelist(group_id: int) -> None:
    global g_group_whitelist
    g_group_whitelist.discard(group_id)
    group_whitelist.delete().where(group_whitelist.group_id == group_id).execute()

def add_user_whitelist(user_id: int) -> None:
    global g_user_whitelist
    g_user_whitelist.add(user_id)
    _ = user_whitelist.get_or_create(user_id=user_id)

def remove_user_whitelist(user_id: int) -> None:
    global g_user_whitelist
    g_user_whitelist.discard(user_id)
    user_whitelist.delete().where(user_whitelist.user_id == user_id).execute()

def refresh_whitelist():
    while True:
        load_whitelist_from_db()
        time.sleep(3600)

task_thread = threading.Thread(target=refresh_whitelist, daemon=True)
task_thread.start()

def is_group_in_whitelist(group_id: int) -> bool:
    global g_group_whitelist
    return group_id in g_group_whitelist

def _should_respond(event: CQEvent) -> bool:
    global g_group_whitelist, g_user_whitelist
    return_true_on_warning = True
    if event.message_type == 'private': # 私聊消息
        if event.sub_type == 'friend': ## 好友私聊消息
            return True
        elif event.sub_type == 'group': ## 通过群发起的临时私聊会话
            return False # raise CanceledException('忽略群临时会话')
        elif event.sub_type == 'group_self': ## bot 自己向外发起的群临时会话消息
            return True
        elif event.sub_type == 'other':
            hoshino.logger.warning(f'Unexpected private message: sub_type is other, message_id is {event.message_id}')
            return return_true_on_warning
        else:
            hoshino.logger.warning(f'Unexpected private message: sub_type is {event.sub_type}, message_id is {event.message_id}')
            return return_true_on_warning
    elif event.message_type == 'group': # 群消息
        if event.sub_type == 'normal': 
            if event.group_id in g_group_whitelist or event.user_id in g_user_whitelist:
                return True
            else:
                return False # raise CanceledException('group or user not in whitelist')
        elif event.sub_type == 'anonymous':
            return False # raise CanceledException('忽略群匿名消息')
        elif event.sub_type == 'notice': ## 放通系统提示消息
            return True
        else:
            hoshino.logger.warning(f'Unexpected group message: sub_type is {event.sub_type}, message_id is {event.message_id}')
            return return_true_on_warning
    else:
        hoshino.logger.warning(f'Unexpected message type: {event.message_type}, message_id is {event.message_id}')
        return return_true_on_warning

@message_preprocessor
async def handle_message(bot, event: CQEvent, _):
    if len(event.message.extract_plain_text()) > 512:
        raise CanceledException('ignore too long messages')

    if not _should_respond(event):
        raise CanceledException('ignore message')

    for t in trigger.chain:
        for service_func in t.find_handler(event):
            if service_func.only_to_me and not event['to_me']:
                continue  # not to me, ignore.

            if not service_func.sv._check_all(event):
                continue  # permission denied.

            service_func.sv.logger.info(f'Message {event.message_id} triggered {service_func.__name__}.')
            try:
                await service_func.func(bot, event)
            except SwitchException:     # the func says: continue to trigger another function.
                continue
            except CanceledException:   # the func says: stop triggering.
                raise
            except Exception as e:      # other general errors.
                service_func.sv.logger.error(f'{type(e)} occured when {service_func.__name__} handling message {event.message_id}.')
                service_func.sv.logger.exception(e)
            # the func completed successfully, stop triggering. (1 message for 1 function at most.)
            raise CanceledException('Handled by Hoshino')
            # exception raised, no need for break
