import asyncio
from typing import Dict, Optional, Union
from nonebot import get_bot, on_command
from nonebot import on_notice, NoticeSession
from hoshino import R, Service, priv, util
from os.path import dirname, join, exists
from json import load, dump, dumps
from io import BytesIO
import base64
import re
import datetime
import time
import copy
from hoshino import aiorequests
curpath = dirname(__file__)


async def update_timeaxis() -> bool:
    clanbattle_work = {str(i): {} for i in range(1, 5 + 1)}
    try:
        all_work = (await (await aiorequests.get("https://www.caimogu.cc/gzlj/data?date=", headers={'x-requested-with': 'XMLHttpRequest', })).json())["data"]
        for work in all_work:
            nowwork = {"1": [], "2": [], "3": []}
            if len(work["homework"]):
                for homework in work["homework"]:
                    worktype = "3" if homework["remain"] else ("1" if homework["auto"] == 2 else "2")  # 1手动 2自动 3尾刀 # 绝大部分自动刀的"auto"字段为1，但是还看到一个0的
                    nowwork[worktype].append({"sn": homework["sn"], "units": homework["unit"], "damage": homework["damage"], "videos": homework["video"]})
                clanbattle_work[work["homework"][0]["sn"][-3]][str(work["stage"])] = copy.deepcopy(nowwork)
        with open(join(curpath, "axis.json"), "w", encoding='utf-8') as f:
            dump(clanbattle_work, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(e)
        return False
    return True


async def get_timeaxis(boss=[1, 2, 3, 4, 5], stage=[1, 2, 3, 4], axistype=[1, 2]) -> list:
    '''
    boss: int(1~5) | list[int]
    stage: int(1~4) | list[int]
    axistype: int(1~3) | list[int|str] 1->手动 2->auto 3->尾刀
    '''
    if type(boss) == int:
        boss = [boss]
    if type(stage) == int:
        stage = [stage]
    if type(axistype) == int:
        axistype = [axistype]
    outp = []
    if not exists(join(curpath, "axis.json")):
        if not (await update_timeaxis()):
            raise RuntimeError('Get timelines from Web Failed.')
    with open(join(curpath, "axis.json"), 'r', encoding='utf-8') as f:
        timeline = load(f)
    for i in boss:
        for j in stage:
            for k in axistype:
                outp += timeline[str(i)][str(j)][str(k)]
    return outp
