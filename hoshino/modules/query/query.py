from json import load
import asyncio
from enum import IntEnum, unique
from os.path import dirname, join, exists
from traceback import print_exc
from datetime import datetime
from typing import List, Tuple, Union

from ..autopcr_db.typing import *
from .pcr_client import PcrClientManager, PcrClient
from ..priconne import chara
from .utils import item_utils, map_utils

curpath = dirname(__file__)


async def QueryWithHeader(accountInfo: Union[dict, int, PcrAccountInfo], apiUrl: str, postData: dict = {}) -> Tuple[dict, dict]:
    """
    传入api和post的数据，返回结果

    :param accountInfo: 待登录账号。{"account":str, "password":str} | pcrid:int | pcrAccountInfo
    :param apiUrl: 访问的api
    :param postData: post的数据
    :returns: Tuple(data:dict, data_header:dict)
    :raise Exception: PcrClient.LoginAndCheck()和PcrClient.CallApi()中可能出现的异常
    :raise KeyError: 数据库中没有传入的pcrid
    :raise AssertionError: 数据库中pcrid对应记录的is_valid字段为假
    """
    
    if isinstance(accountInfo, dict):
        client = PcrClientManager.FromDict(accountInfo)
    elif isinstance(accountInfo, int):
        client = PcrClientManager.FromPcrid(accountInfo)
    elif isinstance(accountInfo, PcrAccountInfo):
        client = PcrClientManager.FromRecord(accountInfo)
    try:
        await LoginAndCheck(client)
        return await client.CallApi(apiUrl, postData, True)
    except Exception as e:
        await LoginAndCheck(client)
        return await client.CallApi(apiUrl, postData, True)
    
async def query(accountInfo: Union[dict, int, PcrAccountInfo], apiUrl: str, postData: dict = {}) -> dict:
    """
    传入api和post的数据，返回结果

    :param accountInfo: 待登录账号。{"account":str, "password":str} | pcrid:int | pcrAccountInfo
    :param apiUrl: 访问的api
    :param postData: post的数据
    :returns: dict
    :raise Exception: PcrClient.LoginAndCheck()和PcrClient.CallApi()中可能出现的异常
    """
    
    return (await QueryWithHeader(accountInfo, apiUrl, postData))[0]


async def VerifyAccount(accountInfo:dict) -> PcrClient:
    """
    强制触发一次登录。没有返回值。
    没有抛出异常就是登录成功。
    """
    client = PcrClientManager.FromDict(accountInfo)
    client._needBiliLogin = True
    client.needLoginAndCheck = True
    await LoginAndCheck(client, True)
    return client
    

async def LoginAndCheck(client: PcrClient, forceTry: bool = False):
    """
    检查当前账号对象的状态。若有需要，自动调用登录模块。
    没有抛出异常就是检验通过。

    Raises:
        Exception: 服务器维护中
        Exception: 该账号没过完教程
        Exception: 需重新过码验证，请重试
        self.BiliLogin()中可能抛出的异常
        self.CallApi()中可能抛出的异常
    
    Returns:
        bool: True=向数据库插入了新纪录，False=为数据库已有的记录
    """
    is_new = await client.LoginAndCheck(forceTry=forceTry)
    if is_new:
        try:
            pcrName = await get_username({"account":client.biliSdkClient.account, "password":client.biliSdkClient.password}) # pcrName = await client.GetUsername()
        except Exception as e:
            pass
        else:
            PcrAccountInfo.update(pcrname_cache=pcrName).where(PcrAccountInfo.pcrid == client._viewerId).execute()
    return is_new


async def get_home_index(account):
    return await query(account, "/home/index", {'message_id': 1, 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})


async def get_load_index(account):
    return await query(account, "/load/index", {'carrier': 'OPPO'})


async def get_profile(account, pcrid: int):
    return await query(account, "/profile/get_profile", {'target_viewer_id': pcrid})


async def get_box_formatted(account):
    '''
    {
        1001: {...},
        1002: {
            "角色名": "优衣",
            "星级": 6,
            "等级": 170,
            "rank": 12,
            "rank_detail": "r12-1.6",
            "专武": 30,
            "好感": 12,
            "战力": 24676,
            "技能等级": {
                "all": "170/170/170/170",
                "ub": 170,
                "skill1": 170,
                "skill2": 170,
                "被动": 170
            },
            "装备": {
                "亚特兰提斯杖": "未穿",
                "神花之圣杖": "3星",
                "白祈之圣冠": "未穿",
                "纯洁的巫女服": "5星",
                "人鱼公主的灵泪": "未穿",
                "精灵王护石": "未穿"
            }
        },
        1003: {...},
        ...
    }
    '''
    load_index = await get_load_index(account)
    box = {}
    unit_list = load_index["unit_list"]
    for unit in unit_list:
        id = unit["id"] // 100

        box[id] = {
            "角色名": "unknown",
            "星级": unit["unit_rarity"],
            "等级": unit["unit_level"],
            "rank": unit["promotion_level"],
            "rank_detail": f'r{unit["promotion_level"]}',
            "专武": False,
            "好感": 1,
            "战力": 0,
            "技能等级": {
                "all": []
            },
            "装备": {}
        }
        try:
            box[id]["角色名"] = chara.fromid(id).name
        except:
            pass
        try:
            box[id]["技能等级"]["ub"] = unit["union_burst"][0]["skill_level"]
        except:
            box[id]["技能等级"]["ub"] = 0
        box[id]["技能等级"]["all"].append(f'{box[id]["技能等级"]["ub"]}')

        for cnt, dic in enumerate(unit["main_skill"]):
            box[id]["技能等级"][f"skill{cnt+1}"] = dic["skill_level"]
            box[id]["技能等级"]["all"].append(f'{dic["skill_level"]}')

        try:
            box[id]["技能等级"]["被动"] = unit["ex_skill"][0]["skill_level"]
        except:
            box[id]["技能等级"]["被动"] = 0
        box[id]["技能等级"]["all"].append(f'{box[id]["技能等级"]["被动"]}')
        box[id]["技能等级"]["all"] = '/'.join(box[id]["技能等级"]["all"])

        cnt = 0
        cnt_notfullequip = 0
        cnt_detail = ""
        cnt_fullequip = 0
        for dic in unit["equip_slot"]:
            nam = str(dic["id"])
            if nam == "999999":
                continue
            try:
                nam = item_utils.get_item_name(nam)
            except:
                pass
            if dic["is_slot"] == 0:
                box[id]["装备"][nam] = "未穿"
                cnt_detail += "x"
            else:
                star = dic["enhancement_level"]
                box[id]["装备"][nam] = f'{star}星'
                cnt_detail += f'{star}'
                if int(star) != 5:
                    cnt_notfullequip += 1
                else:
                    cnt_fullequip += 1
                cnt += star / 5
        cnt = int(cnt * 10 + 0.0001)
        if cnt % 10 == 0:
            cnt = f'{cnt // 10}'
        else:
            cnt = f'{cnt//10}.{cnt%10}'
        if cnt_notfullequip >= 2:
            box[id][
                "rank_detail"] = f'r{box[id]["rank"]}-{cnt_fullequip + cnt_notfullequip}({cnt_detail})'
        else:
            box[id]["rank_detail"] = f'r{box[id]["rank"]}-{cnt}'

        if ("unique_equip_slot" not in unit) or ("unique_equip_slot" in unit and len(unit["unique_equip_slot"]) == 0):
            box[id]["专武"] = "未实装"
        elif unit["unique_equip_slot"][0]["is_slot"] == 0:
            box[id]["专武"] = 0
        else:
            box[id]["专武"] = unit["unique_equip_slot"][0]["enhancement_level"]
        box[id]["战力"] = unit["power"]

    read_story_ids = load_index["read_story_ids"]
    for story_id in read_story_ids:
        id = story_id // 1000
        if id > 2000:
            break
        if id not in box:
            continue
        love = story_id % 1000
        box[id]["好感"] = max(box[id]["好感"], love)

    return box


async def get_box(account):
    '''
    {
        1001: {...}
        ...,
        1137: {                         # 以下字段的value为拼凑而成，主要作说明用
        "id": 113701,                   # 六位id
        "unit_rarity": 3,               # 星级
        "battle_rarity": 0,             # 当前设定星级，0表示为默认星级
        "unit_level": 184,              # 等级
        "promotion_level": 4,           # 好感度
        "promotion_level_actual": 0,    # 实际已阅读的剧情数
        "unit_exp": 5583000,            # 角色当前经验值
        "get_time": 1665408176,         # 角色获取时间 
        "union_burst": [{"skill_id": 1137001, "skill_level": 184}], # 注意是list
        "main_skill": [{"skill_id": 117002, "skill_level": 184}, {"skill_id": 1137003, "skill_level": 4}],
        "ex_skill": [{"skill_id": 1059511, "skill_level": 172}],    # 注意是list
        "free_skill": [],
        "equip_slot": [
            {"id": 999999, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0}, # 999999表示当前未实装的装备
            {"id": 103221, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0},
            {"id": 103521, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 60},
            {"id": 103521, "is_slot": 0, "enhancement_level": 0, "enhancement_pt": 0},
            {"id": 102613, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 20},
            {"id": 102613, "is_slot": 1, "enhancement_level": 1, "enhancement_pt": 20}
        ],
        "unique_equip_slot": [{"id": 130911, "is_slot": 1, "enhancement_level": 160, "enhancement_pt": 19990, "rank": 9}], # 注意是list；为空表示游戏未实装该角色专武；不为空但"is_slot"==0表示用户未装专武
        "unlock_rarity_6_item": {"slot_1": 0, "slot_2": 1, "slot_3": 5}, # 只有5x待开花角色才有此字段。
        # slot_1==纯净记忆碎片是否安装(1/0)；slot_2==记忆碎片是否安装(1/0)；slot_3==星球杯强化([0,5])
        "power": 9181, # 战力
        "skin_data": {"icon_skin_id": 0, "sd_skin_id": 0, "still_skin_id": 0, "motion_id": 0},
        "favorite_flag": 0 # 是否置为收藏角色
        },
        ...
    }
    '''
    load_index = await get_load_index(account)
    box = {}
    for unit in load_index["unit_list"]:  # unit:dict
        unit.pop(None, None)
        for entry in ["union_burst", "main_skill", "ex_skill"]:
            for x in unit.get(entry, []):
                x.pop(None, None)
        unit_id = unit["id"] // 100
        box[unit_id] = unit
        box[unit_id]["promotion_level_actual"] = 0

    for story_id in load_index["read_story_ids"]:
        unit_id = story_id // 1000
        if unit_id > 2000:
            break
        if unit_id not in box:
            continue
        love = story_id % 1000
        box[unit_id]["promotion_level_actual"] = max(box[unit_id]["promotion_level_actual"], love)

    return box


async def get_chara(account, chara_id: Union[int, str]):
    '''
    :param chara_id: 四位
    :returns: 详见get_box()
    :raise AssertionError: 该账号没有此角色
    :raise Exception: 服务器等其它错误
    '''
    chara_id = int(str(chara_id)[:4])
    box = await get_box(account)
    assert chara_id in box, f'该账号没有角色 {chara.fromid(chara_id).name}'
    return box[chara_id]


async def get_clan_id(account):
    home_index = await get_home_index(account)
    try:
        clan_id = home_index["user_clan"]["clan_id"]
        assert clan_id != 0, "该玩家未加入行会"
        return clan_id
    except Exception as e:
        raise Exception("该玩家未加入行会")


async def get_clan_info(account, clanid: Union[int, None] = None):
    if clanid is None:
        clanid = await get_clan_id(account)
    res = await query(account, "/clan/info", {"clan_id": clanid, "get_user_equip": 0})    
    if res.get("clan", {}).get("detail", None) is not None:
        try:
            clan_detail = res["clan"]["detail"]
            ClanInfo.delete().where(ClanInfo.clanid == clanid).execute()
            ClanInfo.create(clanid = clanid, clan_name_cache = clan_detail["clan_name"], clan_member_count_cache = clan_detail["member_num"], leader_pcrid_cache = clan_detail["leader_viewer_id"])
        except Exception as e:
            print_exc()
    return res


async def get_interval_between_last_donation(account) -> int:
    '''
    获取距离上次装备请求过去的时间（秒）
    '''
    _ = await get_clan_id(account)  # 首先确定加入了行会

    ret, data_header = await QueryWithHeader(account, "/clan/info", {"clan_id": 0, "get_user_equip": 0})  # 别动，就是0
    return int(data_header["servertime"]) - int(ret.get("latest_request_time", 0))


async def get_server_time(account):
    ret, data_header = await QueryWithHeader(account, "/gacha/index", {})
    return int(data_header["servertime"])


async def get_pcrid(account):
    load_index = await get_load_index(account)
    return load_index["user_info"]["viewer_id"]


async def get_buy_mana_times(account):
    load_index = await get_load_index(account)
    return load_index["shop"]["alchemy"]["exec_count"]


async def get_jewel(account, typ=0) -> int:
    '''
    0全部 1付费 2免费
    '''
    load_index = await get_load_index(account)
    free = load_index["user_jewel"]["free_jewel"]
    paid = load_index["user_jewel"]["paid_jewel"]
    if typ in [2, "free"]:
        return free
    if typ in [1, "paid"]:
        return paid
    return free + paid


async def get_mana(account, typ=0) -> int:
    '''
    0全部 1付费 2免费
    '''
    load_index = await get_load_index(account)
    free = load_index["user_gold"]["gold_id_free"]
    paid = load_index["user_gold"]["gold_id_pay"]
    if typ in [2, "free"]:
        return free
    if typ in [1, "paid"]:
        return paid
    return free + paid


async def get_stamina(account):
    load_index = await get_load_index(account)
    return load_index["user_info"]["user_stamina"]


async def get_username(account):
    load_index = await get_load_index(account)
    return load_index["user_info"]["user_name"]


async def get_item_dict(account) -> dict:
    """
    :returns: {id(int): stock(int)}
    """
    load_index = await get_load_index(account)
    item_list = load_index["item_list"]
    item_dic = {}
    for item in item_list:
        item_dic[item["id"]] = item["stock"]
    return item_dic


async def get_item_stock(account, id: int) -> int:
    """
    :param id: 五位数
    :returns: {id(int): stock(int)}
    """
    dic = await get_item_dict(account)
    return dic.get(int(id), 0)


async def get_user_equip_dict(account) -> dict:
    """
    :returns: {id(int): stock(int)}
    """
    load_index = await get_load_index(account)
    user_equip_list = load_index["user_equip"]
    user_equip_dict = {}
    for equip in user_equip_list:
        user_equip_dict[equip["id"]] = equip["stock"]
    return user_equip_dict


async def get_user_equip_stock(account, id: int) -> int:
    """
    :param id: 六位数，1打头
    :returns: {id(int): stock(int)}
    """
    dic = await get_user_equip_dict(account)
    return dic.get(int(id), 0)


async def get_item_or_equip_stock(account, id: int) -> int:
    return max(await get_item_stock(account, id), await get_user_equip_stock(account, id))


async def get_clan_battle_info(account: dict):
    """
    返回该账号的公会战状态dict。常用的有：
    {
        "using_unit" : [105201, 102701, etc]  # 补偿角色
        "used_unit": list[int] # 已用角色
        "point": int 今日已刷取体力点
        "remaining_count": 今日剩余刀
        "carry_over_time": 当前刀补时
    }
    """
    clan_id = await get_clan_id(account)
    current_clan_battle_coin = await get_item_stock(account, 90006)
    return await query(account, "/clan_battle/top", {"clan_id": clan_id, "is_first": 0, "current_clan_battle_coin": current_clan_battle_coin})


async def get_support_unit_setting(account):
    _ = await get_clan_id(account)
    res = await query(account, "/support_unit/get_setting")
    assert "friend_support_units" in res, "无好友关卡支援字段"
    assert "clan_support_available_status" in res, "无公会/地下城/露娜塔支援字段"
    return res


async def get_units_info(account):
    load_index = await get_load_index(account)
    return load_index["unit_list"]
    

async def get_unit_info(account, unit_id):
    unit_id = int(f'{str(unit_id)[:4]}01')
    unit = [unit for unit in await get_units_info(account) if unit["id"] == unit_id]
    if len(unit) == 0:
        raise Exception(f'该账号无角色{unit_id}')
    return unit[0]


async def buy_stamina(account, buy_stamina_passive_max, stamina_expect, stamina_now=None) -> Tuple[str, int]:
    '''
    :returns: tuple(执行函数过程中产生的输出，执行完函数后当前体力)。将返回的字符串加入结果，继续执行后续逻辑。
    :raise Exception: 将抛出的字符串(str(e))加入结果，中断后续逻辑执行
    '''
    if stamina_now is None:
        try:
            stamina_now = await get_stamina(account)
        except Exception as e:
            raise Exception(f'Fail. 获取当前体力失败：{e}')

    if stamina_now >= stamina_expect:
        return f'Skip. 当前体力{stamina_now}>=目标体力({stamina_expect})', stamina_now

    outp = []
    # cost_jewel_tot = 0
    buy_stamina_tot = 0
    while stamina_now < stamina_expect:
        try:
            load_index = await get_load_index(account)
            buy_stamina_already = load_index["shop"]["recover_stamina"]["exec_count"]
            cost = load_index["shop"]["recover_stamina"]["cost"]
            jewel = load_index["user_jewel"]["free_jewel"] + load_index["user_jewel"]["paid_jewel"]
        except Exception as e:
            raise Exception(f'Fail. 获取用户信息失败：{e}')
        if buy_stamina_already >= buy_stamina_passive_max:
            # outp.append(f'Abort. 今日购买体力管数达设置上限({buy_stamina_already}/{buy_stamina_passive_max})')
            break
        if stamina_now + 120 > 999:
            # outp.append('Abort. 体力已达上限')
            break
        if jewel < cost:
            outp.append(f'Warn. 钻石不足。当前拥有{jewel}，购买体力需{cost}')
            break
        try:
            await query(account, '/shop/recover_stamina', {"current_currency_num": jewel})
        except Exception as e:
            outp.append(f'Fail. 购买体力失败：{e}')
            break
        else:
            # cost_jewel_tot += cost
            buy_stamina_tot += 1
            stamina_now += 120

    msg = f'共购买{buy_stamina_tot}管体力({buy_stamina_already}/{buy_stamina_passive_max})。当前体力{stamina_now}'
    if stamina_now < stamina_expect:
        outp.append(f'Warn. {msg}，小于期望体力{stamina_expect}')
    else:
        outp.append(f'Succeed. {msg}')
    return " ".join(outp), stamina_now


async def sweep(account: dict, map_id: int, count: Union[int, None], buy_stamina_passive_max: int = 0) -> str:
    '''
    :param count: 刷取次数。若传入None则清空体力。本函数会不校验地图当前剩余可刷取次数。
    :returns: 1. 将返回的字符串加入结果；2. stamina_short = account.get("stamina_short", False)；3. 继续执行后续逻辑。
    :raise Exception: 将抛出的字符串(str(e))加入结果，中断后续逻辑执行。

    注意：实际扫荡次数可能少于count，因此重置前需重新请求今日实际刷图次数。
    '''
    assert (count is None) or (count > 0), f'参数"count"的值非法：{count}'

    map_name = map_utils.from_id(map_id).name
    stamina_take = map_utils.from_id(map_id).stamina
    msg = []

    try:
        star = await get_quest_star(account, map_id)
    except Exception as e:
        raise Exception(f'Fail. 获取关卡{map_name}通关情况失败：{e}')
    assert star >= 3, f'Abort. 关卡{map_name}为{star}星通关，无法扫荡。'

    try:
        stamina = await get_stamina(account)
    except Exception as e:
        raise Exception(f'Fail. 获取体力失败：{e}')
    if count is None:
        count = stamina // stamina_take
        if count == 0:
            return 'Skip. 体力已清空'
    count_expect = count

    try:
        ticket = await get_ticket_num(account)
    except Exception as e:
        raise Exception(f'Fail. 获取扫荡券数量失败：{e}')
    if ticket == 0:
        return 'Warn. 扫荡券数量为0，不执行刷图'
    elif ticket < count:
        msg.append(f"Warn. 扫荡券数量{ticket} 少于设定刷图次数({count})")
        count = ticket

    stamina_expect = stamina_take * count
    if stamina < stamina_expect:
        try:
            ret, stamina = await buy_stamina(account, buy_stamina_passive_max, stamina_expect, stamina)
        except Exception as e:
            msg.append(str(e))
            return " ".join(msg)
        else:
            msg.append(ret)
        if stamina < stamina_expect:
            account["stamina_short"] = True
            msg.append(f"Warn. 当前体力{stamina}少于刷图所需({stamina_expect})。体力耗尽，不执行后续刷图。")
            count = stamina // stamina_take

    if count > 0:
        try:
            ret = await query(account, "/quest/quest_skip", {"quest_id": map_id, "random_count": count, "current_ticket_num": ticket})
        except Exception as e:
            msg.append(f'Fail. 扫荡{map_name}失败：{e}')
            raise Exception(" ".join(msg))

    if count == count_expect:
        msg.append(f'Succeed. 扫荡{map_name}成功({count}次)')
    else:
        msg.append(f'Warn. 扫荡{map_name} {count}次(期望{count_expect}次)')
    return " ".join(msg)


async def recover_quest(account, map_id: int) -> str:
    '''
    :returns: 将返回的字符串加入结果，继续执行后续逻辑
    :raise Exception: 将抛出的字符串(str(e))加入结果，中断后续逻辑执行
    '''
    map_name = map_utils.from_id(map_id).name
    try:
        jewel = await get_jewel(account)
    except Exception as e:
        raise Exception(f'Fail. 获取钻石数量失败：{e}')
    assert jewel >= 50, f'Abort. 当前钻石数量{jewel}<50，无法重置'
    try:
        ret = await query(account, "/quest/recover_challenge", {"quest_id": int(map_id), "current_currency_num": jewel})
    except Exception as e:
        raise Exception(f'Fail. 重置{map_name}失败：{e}')
    return f'Succeed. 重置{map_name}成功'


async def get_all_quest_dict(account) -> dict:
    """
    返回该账号的所有通关图dict。
    dict[quest_id:int] = {
        "clear_flg": 3,
        "result_type": 2,
        "daily_clear_count": 0,
        "daily_recovery_count": 0
    }
    """
    home_index = await get_home_index(account)
    quest_list = home_index.get("quest_list", [])
    quest_dict = {}
    for quest in quest_list:
        quest_dict[quest["quest_id"]] = {}
        for key in quest:
            if key not in ["null", "quest_id"]:
                quest_dict[quest["quest_id"]][key] = quest[key]
    return quest_dict


async def get_quest_dict(account, map_id: int) -> dict:
    '''
    {
        "clear_flg": 3,
        "result_type": 2,
        "daily_clear_count": 0,
        "daily_recovery_count": 0
    }
    若该账号不存在该地图记录，以上字段的值均为0。
    '''
    return (await get_all_quest_dict(account)).get(int(map_id), {"clear_flg": 0, "result_type": 0, "daily_clear_count": 0, "daily_recovery_count": 0})


async def get_quest_star(account, map_id: int) -> int:
    '''
    返回该账号该图的通过星数。未通关或未解锁为0。
    '''
    return (await get_quest_dict(account, int(map_id))).get("clear_flg", 0)


async def get_ticket_num(account):
    return await get_item_stock(account, 23001)


def get_clan_donate_item_dict() -> dict:
    '''
    {
        "blue": [101011, 101071, ...],
        ...,
        "purple": [115011, 125012, ...]
    }
    '''
    clan_donate_item_id_path = join(curpath, 'data/clan_donate_item_dict.json')
    if exists(clan_donate_item_id_path):
        with open(clan_donate_item_id_path, 'r', encoding='utf-8') as fp:
            return load(fp)
    else:
        raise Exception(f'File Not Exist: "data/clan_donate_item_dict.json"')


@unique
class ItemType(IntEnum):
    unlimited = -1
    blue = 0
    bronze = 1
    silver = 2
    gold = 3
    purple = 4
    red = 5
    green = 6
    orange = 7


def get_clan_donate_item_list(item_type: Union[str, ItemType]) -> List[int]:
    '''
    :param item_type: enum("unlimited", "blue", "bronze", "silver", "gold", "purple", "red", "green", "orange")
    '''
    if type(item_type) == str:
        assert item_type in ItemType.__members__, f'无法识别的物品类型：{item_type}'
        item_type = ItemType[item_type]

    clan_donate_item_dict = get_clan_donate_item_dict()
    for k in clan_donate_item_dict:
        assert k in ItemType.__members__, f'内部错误：无法识别数据库中的项目类型：{k}'

    return [item_id for k, v in clan_donate_item_dict.items() for item_id in v if ItemType[k] >= item_type]
