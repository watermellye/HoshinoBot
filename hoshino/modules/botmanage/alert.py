from nonebot import on_notice, on_request, NoticeSession, RequestSession
from asyncio import sleep
from hoshino import logger


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

# 当设置为“需要正确回答问题”后，正确回答问题后就会自动添加好友，不会触发此 API。此时显示“对方已添加你为好友”，但是单向好友。
# 当设置为“允许任何人添加我为好友”后，按理说是 QQ 自动同意，也不会触发此 API。但现在 QQ 总是风控，还是需要在客户端同意请求才加得上。此时就加不上。
@on_request('friend')
async def add_friend(session: RequestSession):
    logger.info(f'收到[{session.event.user_id}]的加好友请求，将在 50 秒后同意')
    await sleep(50)
    try:
        await session.approve()
    except Exception as e:
        logger.error(f'同意[{session.event.user_id}]的加好友请求失败: {e}')
    else:
        logger.info(f'同意[{session.event.user_id}]的加好友请求成功')


# @on_request('group.invite')
# async def add_group(session: RequestSession):
#     await sleep(50)
#     await session.approve()
