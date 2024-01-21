import numpy as np
from hoshino import Service
from hoshino.typing import CQEvent

aa = np.zeros(15001, dtype=int)
aa[1:11] = 50
aa[11:101] = 10
aa[101:201] = 5
aa[201:501] = 3
aa[501:1001] = 2
aa[1001:2001] = 2
aa[2001:4000] = 1
aa[4000:8000:100] = 50
aa[8100:15001:100] = 15

bb = np.zeros(15001, dtype=int)
bb[1:11] = 500
bb[11:101] = 50
bb[101:201] = 30
bb[201:501] = 10
bb[501:1001] = 5
bb[1001:2001] = 3
bb[2001:4001] = 2
bb[4001:7999] = 1
bb[8100:15001:100] = 30

sv = Service('mining')

@sv.on_prefix('挖矿', 'jjc钻石', '竞技场钻石', 'jjc钻石查询', '竞技场钻石查询')
async def arena_miner(bot, ev: CQEvent):
    try:
        n = int(ev.message.extract_plain_text())
        if n < 1:
            return
        n = min(n, 15001)
    except:
        return
    m = n
    msg = str(n)
    cnt = 0
    while n > 1:
        n = max((int(0.85 * n) if (70 < n <= 15001) else n - 10), 1)    
        cnt += 1
        if cnt <= 10:
            msg += " → " + str(n)
    if cnt > 10:
        msg += f' ...\n至少需{cnt}次登顶'
    if m < 11:
        msg = ''
    s_b = bb[1:m].sum()
    s_a = aa[1:m].sum()
    msg += f"\n当季排名奖励还剩{s_a}钻\n生涯排名奖励还剩{s_b}钻"
    await bot.send(ev, msg)