
# built-in
from pathlib import Path
from typing import Optional

# 3rd-party
from peewee import SqliteDatabase, Model, IntegerField, TextField

# project
from hoshino import Service, util, priv
from hoshino.typing import NoticeSession, CQHttpError, CQEvent, HoshinoBot

sv1 = Service('group-leave-notice', help_='退群通知')

@sv1.on_notice('group_decrease.leave')
async def leave_notice(session: NoticeSession):
    ev = session.event
    name = ev.user_id
    if ev.user_id == ev.self_id:
        return
    try:
        info = await session.bot.get_stranger_info(self_id=ev.self_id, user_id=ev.user_id)
        name = info['nickname'] or name
        name = util.filt_message(name)
    except CQHttpError as e:
        sv1.logger.exception(e)
    await session.send(f"{name}({ev.user_id})退群了。")


sv2 = Service('group-welcome', help_='入群欢迎')

gk_default_welcome_msg = "欢迎新群员！"
gk_current_dir = Path(__file__).resolve().parent
gk_data_dir = gk_current_dir / "data"
db = SqliteDatabase(str(gk_data_dir / "welcome_msg.sqlite"))

class BaseModel(Model):
    class Meta:
        database = db
        
class Group2Msg(BaseModel):
    group_id = IntegerField(primary_key=True)
    welcome_msg = TextField()

db.connect()
db.create_tables([Group2Msg])

@sv2.on_notice('group_increase')
async def increace_welcome_interface(session: NoticeSession):
    if session.event.user_id == session.event.self_id:
        return  # ignore myself

    welcome_msg = get_welcome_msg(session.event.group_id)
    if welcome_msg is None:
        welcome_msg = f'{gk_default_welcome_msg}\n\n*可通过[设置入群欢迎词]指令自定义欢迎词'
    await session.send(welcome_msg, at_sender=True)

@sv2.on_prefix("设置入群欢迎词")
async def set_welcome_msg_interface(bot: HoshinoBot, ev: CQEvent):
    group_id = ev.group_id
    if not group_id:
        return
    
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev, "只有管理员及以上权限可以设置欢迎词")
        return

    old_msg = get_welcome_msg(group_id)
    new_msg = ev.message.extract_plain_text().strip()
    
    output = []
    if new_msg == "":
        output.append("入群欢迎词不可为空，将恢复为默认欢迎词")
        output.append("*可通过[#disable group-welcome]关闭入群欢迎功能")
        output.append("")
        delete_welcome_msg(group_id)
    else:
        set_welcome_msg(group_id, new_msg)
    
    if old_msg is None:
        output.append(f'已设置入群欢迎词：{new_msg or gk_default_welcome_msg}')
    else:
        output.append(f'已更新入群欢迎词\n旧欢迎词：{old_msg}\n新欢迎词：{new_msg or gk_default_welcome_msg}')
    await bot.send(ev, "\n".join(output))

def get_welcome_msg(group_id: int) -> Optional[str]:
    record: Optional[Group2Msg] = Group2Msg.get_or_none(Group2Msg.group_id == group_id)
    return record.welcome_msg if record else None

def set_welcome_msg(group_id: int, msg: str) -> None:
    Group2Msg.replace(group_id=group_id, welcome_msg=msg).execute()

def delete_welcome_msg(group_id: int) -> None:
    Group2Msg.delete().where(Group2Msg.group_id == group_id).execute()