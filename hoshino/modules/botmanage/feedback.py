import hoshino
from hoshino import Service, priv
from hoshino.typing import CQEvent, HoshinoBot
from hoshino.util import DailyNumberLimiter

sv = Service('_feedback_', manage_priv=priv.SUPERUSER, help_='[#来杯咖啡] 后接反馈内容 联系维护组')

_group_id = 779766811
_max = 3
lmt = DailyNumberLimiter(_max)
EXCEED_NOTICE = f'您今天已经喝过{_max}杯了，请明早5点后再来！'

@sv.on_prefix('来杯咖啡')
async def feedback_help_interface(bot: HoshinoBot, ev: CQEvent):
    await bot.send(ev, "为避免误触，请使用 #来杯咖啡+您要反馈的内容~", at_sender=True)

@sv.on_prefix('#来杯咖啡')
async def feedback(bot: HoshinoBot, ev: CQEvent):
    text = str(ev.message).strip()
    if not text:
        await bot.send(ev, "请发送#来杯咖啡+您要反馈的内容~", at_sender=True)
        return

    uid = ev.user_id
    if not lmt.check(uid):
        await bot.finish(ev, EXCEED_NOTICE, at_sender=True)
        return

    try:
        await bot.send_group_msg(self_id=ev.self_id, group_id=_group_id, message=f'Q{uid}@群{ev.group_id}\n{text}')
    except Exception as e:
        await bot.send(ev, f'反馈发送失败：{e}', at_sender=True)
    else:
        await bot.send(ev, f'您的反馈已发送至怡宝！\n======\n{text}', at_sender=True)
        lmt.increase(uid)
    
