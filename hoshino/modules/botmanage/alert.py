from nonebot import on_notice, on_request, NoticeSession, RequestSession
from asyncio import sleep


@on_notice('group_decrease.kick_me')
async def kick_me_alert(session: NoticeSession):
    group_id = session.event.group_id
    operator_id = session.event.operator_id
    coffee = session.bot.config.SUPERUSERS[0]
    await session.bot.send_private_msg(self_id=session.event.self_id,
                                       user_id=coffee,
                                       message=f'被Q{operator_id}踢出群{group_id}')


@on_notice('group_ban.ban')
async def ban_me_alert(session: NoticeSession):
    group_id = session.event.group_id
    operator_id = session.event.operator_id
    coffee = session.bot.config.SUPERUSERS[0]
    self_id = session.event.self_id
    duration = session.event.get("duration", 0)
    if duration == 0:
        return
    if self_id == session.event.user_id:
        await session.bot.send_private_msg(self_id=self_id, user_id=coffee, message=f'被Q{operator_id}在群{group_id}禁言{duration}秒')
        if duration > 60:
            await session.bot.set_group_leave(group_id=group_id)
            await session.bot.send_private_msg(self_id=self_id, user_id=coffee, message='已自动退出群聊')


@on_request('friend')
async def add_friend(session: RequestSession):
    await sleep(60)
    await session.approve()


@on_request('group.invite')
async def add_group(session: RequestSession):
    await sleep(60)
    await session.approve()
