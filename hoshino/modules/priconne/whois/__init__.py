from hoshino import Service
from hoshino.typing import HoshinoBot, CQEvent
from hoshino.util import FreqLimiter, filt_message

from .. import chara

sv_help = '''
[谁是霸瞳] 角色别称查询
'''.strip()

sv = Service('whois', help_=sv_help, bundle='pcr查询')

lmt = FreqLimiter(3)

async def get_chara_pic(c: chara.Chara):
    # 如果本地有存立绘的话可以考虑改成立绘
    return await c.get_icon_cqcode()


@sv.on_suffix('是谁')
@sv.on_prefix('谁是')
async def whois(bot: HoshinoBot, ev: CQEvent):
    name = ev.message.extract_plain_text().strip()
    if not name or len(name) > 20:
        return
    
    uid: int = ev.user_id
    if not lmt.check(uid):
        return
        # await bot.finish(ev, f'兰德索尔花名册冷却中(剩余 {int(lmt.left_time(uid)) + 1}秒)', at_sender=True)
    lmt.start_cd(uid)
    
    id_ = chara.name2id(name)
    if id_ != chara.UNKNOWN:
        c = chara.fromid(id_)
        bot.finish(ev, f'{await get_chara_pic(c)}{" ".join(c.names)}'.strip())

    ids = chara.guess_ids(name)
    if len(ids) == 0:
        return
    
    
    msg = [f'兰德索尔似乎没有叫"{filt_message(name)}"的人...', "角色别称补全计划: github.com/Ice9Coffee/LandosolRoster", "您要找的可能是："]
    for id, name, score in ids:
        c = chara.fromid(id)
        msg.append(f'{await c.get_icon_cqcode()}{" ".join(c.names)}'.strip()) # 近似匹配可能有多个，就不走get_chara_pic了，只发头像
    
    bot.finish(ev, '\n'.join(msg))
