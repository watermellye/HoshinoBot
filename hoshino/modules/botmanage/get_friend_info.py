from typing import List, Union
from nonebot import get_bot, on_notice, NoticeSession
from hoshino.typing import NoticeSession, MessageSegment, CommandSession
from hoshino import priv, sucmd
import hoshino
from pathlib import Path
import json
from asyncio import Lock
from datetime import datetime


FILENAME = "friend_data.json"
lck = Lock()


def get_nowtime() -> int:
    return int(datetime.timestamp(datetime.now()))


def get_local_data():
    '''
    请在使用前获取lck，直到肯定不再使用释放。
    {
        bot_qqid_int: {
            "data": [ friend_qqid_int ],
            "time": timestamp_int # 上次更新时间
        }
    }
    '''
    data_path = Path(__file__).parent / "data" / FILENAME
    if Path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as fp:
            return json.load(fp)
    return {}


def save_local_data(local_data):
    data_path = Path(__file__).parent / "data" / FILENAME
    with open(data_path, "w", encoding="utf-8") as fp:
        json.dump(local_data, fp, ensure_ascii=False, indent=4)


def update_local_data(local_data, sid: Union[int, str], data):
    local_data[str(sid)] = {"data": data, "time": get_nowtime()}
    save_local_data(local_data)


async def get_id_list_online(sid: Union[int, str]) -> List[int]:
    bot = get_bot()
    friend_list: List[dict] = await bot.get_friend_list(self_id=int(sid))
    return [x["user_id"] for x in friend_list]


async def get_id_list(sid: Union[int, str]) -> List[int]:
    '''
    获取指定bot的好友列表，其中每个元素为qq号
    :raise AssertionError: sid不在bot列表中
    '''
    sid = str(sid)
    sid_list: List[str] = hoshino.get_self_ids()
    assert sid in sid_list, f'{sid}不在bot列表中'

    async with lck:
        local_data = get_local_data()
        if (sid in local_data) and (get_nowtime() - local_data[sid]["time"]) < 3600:
            return local_data[sid]["data"]
        qqid_list = await get_id_list_online(sid)
        update_local_data(local_data, sid, qqid_list)
        return qqid_list


async def is_friend(uid: Union[int, str], sid: Union[int, str]) -> bool:
    friend_list = await get_id_list(sid)
    return int(uid) in friend_list


@on_notice("friend_add")  # 没有friend_reduce/delete
async def added_friend(session: NoticeSession):
    uid_int = int(session.event.user_id)
    sid = str(session.event.self_id)

    async with lck:
        local_data = get_local_data()
        if (sid in local_data) and (get_nowtime() - local_data[sid]["time"]) < 3600:
            local_data[sid]["data"] = list(set(local_data[sid]["data"] + [uid_int]))
            save_local_data(local_data)
            return
        qqid_list = await get_id_list_online(sid)
        update_local_data(local_data, sid, qqid_list)


# @sucmd('获取好友列表')
async def _(session: CommandSession):  # 测试用
    qqid_list = await get_id_list(session.self_id)
    print(f'共{len(qqid_list)}个好友，前10个为：{qqid_list[:10]}')
