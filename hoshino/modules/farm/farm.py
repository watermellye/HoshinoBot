from pathlib import Path
import json
from traceback import print_exc
from typing import List, Tuple, Union, Optional, Dict
from collections import namedtuple, defaultdict
import asyncio
import nonebot
from peewee import fn, JOIN
from datetime import datetime
import random

import hoshino
from hoshino.typing import CQEvent, HoshinoBot

from ..utils.output import *
from ..autopcr_db.typing import *
from ..autopcr_db.autopcr_database_table import AutopcrDatabaseTable
from ..query import query
from ..query.PcrApi import PcrApi, PcrApiException

# [退出公会] 自行退出当前公会。自行退出公会后需24H才能加入新公会。
sv_help = '''
免费BCR装备农场！
指令列表：
[加入农场 <pcrid>] pcrid为(b服)个人简介内13位数字
[退出农场]
[今日捐赠]
'''.strip()
sv_help_super = '''
仅管理有效指令：
[农场人员] 离线查询所有被授权人员的id和名字
[农场人员更新] 在线查询所有被授权人员的id和名字，并更新数据库
[农场踢除 <pcrid>] 
[农场清空]
[农场号]
[农场转移 [<pcrid>] [<clanid>]]
'''.strip()

sv = hoshino.Service('farm', visible=False)

gs_currentDir = Path(__file__).resolve().parent
gs_accountPath = gs_currentDir / "data" / "account.json"


@nonebot.on_startup
async def SyncJson2DbOnStartup():
    asyncio.create_task(SyncJson2Db())
    asyncio.create_task(ForTest())


@sv.on_fullmatch(("农场帮助", "帮助农场"))
async def Help(bot: HoshinoBot, ev: CQEvent):
    if hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        await bot.finish(ev, "\n\n".join([sv_help, sv_help_super]))
    else:
        await bot.finish(ev, sv_help)


async def SyncJson2Db():
    assert Path.exists(gs_accountPath), "Skip. 无农场号配置文件，不执行同步。"
    try:
        with gs_accountPath.open("r", encoding="utf-8") as fp:
            accounts: List[dict] = json.load(fp)
    except Exception as e:
        print_exc()
        hoshino.logger.error(f'打开农场号配置文件失败：{e}。不执行同步')
        raise Exception(f'Error. 打开农场号配置文件失败：{e}。不执行同步')
    for accountDict in accounts:
        if "account" not in accountDict:
            hoshino.logger.warn(f'{accountDict}中缺少"account"字段。该账号不执行同步。')
            accountDict["activate"] = False
            continue
        if "password" not in accountDict:
            hoshino.logger.warn(f'{accountDict}中缺少"password"字段。该账号不执行同步。')
            accountDict["activate"] = False
            continue
        account = accountDict["account"]
        password = accountDict["password"]
        forceUpdate = accountDict.get("force_update", False)
        accountDict["force_update"] = False
        pcrid = accountDict.get("pcrid", None)
        try:
            if accountDict.get("activate", True) == False:
                if pcrid is None:
                    pcrid = AutopcrDatabaseTable.TryGetPcridFromAccount(account)
                    if pcrid is None:
                        continue
                farmInfo: FarmInfo = FarmInfo.get_or_none(FarmInfo.pcrid == pcrid)
                if farmInfo is not None:
                    farmInfo.activated = False
                    farmInfo.save()
                accountDict["info"] = "Succeed. 该农场号已置为不激活"
            else:
                accountDict["activate"] = True
                needInit = True
                if pcrid is not None and forceUpdate == False:
                    pcrAccount: PcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.pcrid == pcrid)
                    if pcrAccount is not None:
                        if account == pcrAccount.account and password == pcrAccount.password:
                            needInit = False

                if needInit or forceUpdate:
                    hoshino.logger.info(f'农场号{accountDict}正在同步')
                    pcrid = await AutopcrDatabaseTable.UpdatePcrAccountInfoModel(accountDict)
                    accountDict["pcrid"] = pcrid
                    pcrName = PcrAccountInfo.get(PcrAccountInfo.pcrid == pcrid).pcrname_cache
                    accountDict["pcr_name"] = pcrName
                    clanid = await AutopcrDatabaseTable.UpdateFarmInfoModel(pcrid)
                    accountDict["clanid"] = clanid
                accountDict["info"] = "Succeed. 该农场号已激活"
        except Exception as e:
            accountDict["activate"] = False
            accountDict["info"] = "该账号登录失败，已被置为不激活。请检查后重新激活。"
            accountDict["info"] += f'报错信息：{e}'
            

        with gs_accountPath.open("w", encoding="utf-8") as fp:
            json.dump(accounts, fp, ensure_ascii=False, indent=4)

    hoshino.logger.info("所有农场号同步完毕")


class NotFoundException(Exception):
    pass

def GetFarmRecords() -> ClanInfo:
    """
    获取所有会长为农场号的公会的记录
    
    Returns:
        ClanInfo join FarmInfo on pcrid
    """
    return ClanInfo.select().join(FarmInfo, on=(ClanInfo.leader_pcrid_cache == FarmInfo.pcrid)).where(FarmInfo.activated == True)

def GetFarmIds() -> List[int]:
    """
    获取所有农场公会的ID
    """
    activated_distinct_records = FarmInfo.select(FarmInfo.clanid_cache).where(FarmInfo.activated == True).distinct()
    return list({record.clanid_cache for record in activated_distinct_records if record.clanid_cache != 0})

    
def GetANotFullClan() -> ClanInfo:
    """
    根据数据库缓存判断是否有空位。（离线）

    Exceptions:
        NotFoundException: 所有公会已满员
        
    Returns:
        ClanInfo: 一个有空位的公会的记录。一个公会的农场号与活人的比例越高，被选中的概率越大。
    """
    id2co:Dict[int, float] = {}
    farms = GetFarmRecords()
    for farm in farms:
        clanid = farm.clanid
        农场号人数 = FarmInfo.select().where(FarmInfo.clanid_cache == clanid, FarmInfo.activated).count()
        被批准人数 = FarmBind.select().where(FarmBind.permitted_clanid == clanid).count()
        if (农场号人数 + 被批准人数 >= 30) or (farm.clan_member_count_cache >= 30):
            continue
        id2co[clanid] = min(3.0, 农场号人数 / (被批准人数 + 1))

    if len(id2co) == 0:
        raise NotFoundException("所有公会已满员")

    population = list(id2co.keys())
    weights = list(id2co.values())
    clanid = random.choices(population, weights=weights)[0]
    return ClanInfo.get(ClanInfo.clanid == clanid)


def GetFarmIdFromName(clanStr: str) -> int:
    """
    根据公会名查找农场会ID。若无则返回0。

    Args:
        clanStr (str): 公会名

    Returns:
        int: 公会名对应的农场会ID。若无则返回0。
    """
    farms = GetFarmRecords()
    for farm in farms:
        if farm.clan_name_cache == clanStr:
            return farm.clanid
    return 0

@sv.on_prefix(("加入农场"))
async def EnterFarmInterface(bot: HoshinoBot, ev: CQEvent):
    qqid: int = ev.user_id
    pcrid: str = ev.message.extract_plain_text().strip()

    if pcrid == "":
        query = FarmBind.select().where(FarmBind.qqid == qqid)
        if query.count() == 0:
            pcrids = [1234567890123]
        else:
            pcrids = [record.pcrid for record in query]
        outputs = [f'加入农场 {pcrid}' for pcrid in pcrids]
        bot.finish(ev, f'请传入pcrid\n示例：\n' + "\n".join(outputs))

    if pcrid[0] == "<" and pcrid[-1] == ">":
        pcrid = pcrid[1:-1]

    if (not pcrid.isdigit()) or (len(pcrid) != 13):
        bot.finish(ev, f'pcrid应为13位数字，您输入了[{pcrid}]\n示例：加入农场 1234567890123')

    try:
        await bot.send(ev, (await EnterFarm(int(pcrid), qqid)).ToStr(sep="\n"))
    except Exception as e:
        bot.finish(ev, f'邀请[{pcrid}]加入农场失败：{e}')


async def EnterFarm(pcrid: int, qqid: Union[int, None]) -> Outputs:
    """
    尝试对pcrid发起农场加入的邀请。
    如果正常返回说明成功，任何失败将抛出异常。
    
    Args:
        pcrid (int): 要加入农场的pcrid
        qqid (Union[int, None]): 绑定的qqid（可无）
    
    Exceptions:
        NotFoundException: 所有公会已满员
        KeyError: PcrAccountInfo表中没有会长对应的pcrid
        AssertionError: PcrAccountInfo表中会长pcrid对应记录的is_valid字段为假
        PcrApiException: 调用PCR的API过程中产生的异常

    Returns:
        Outputs: 操作结果
    """

    pcrid = int(pcrid)
    farmBindRecord: FarmBind = FarmBind.get_or_none(FarmBind.pcrid == pcrid)

    try:
        profileRes = await query.get_profile(GetARandomBotAccount(), pcrid)
        userInfoStr = f'[{profileRes["user_info"]["user_name"]}]({pcrid})'
        userClanName = profileRes.get("clan_name", "")  # 只返回公会名，没有ID
    except Exception as e:
        raise PcrApiException(f'获取用户信息失败：{e}') from e
            
    outputs = Outputs()
    userFarmid = GetFarmIdFromName(userClanName)
    
    if farmBindRecord is not None:
        farmBindRecord.permitted_clanid = userFarmid # 同步
        farmBindRecord.save()
        if farmBindRecord.qqid != qqid:
            if userFarmid and farmBindRecord.qqid:
                return Outputs.FromStr(OutputFlag.Error, f'[{pcrid}]已被其它QQ绑定且正在农场[{userClanName}]({userFarmid})中。请先退出农场。')
            outputs.append(OutputFlag.Info, f'该ID在数据库中有记录且绑定在其它QQ号上，已改绑至当前账号。')
        farmBindRecord.delete_instance()
    
    #FarmBind(pcrid=pcrid, qqid=qqid).save(force_insert=True) # 用create更好

    if len(userClanName):
        if userFarmid:
            FarmBind.create(pcrid=pcrid, qqid=qqid, permitted_clanid=userFarmid)
            outputs.append(OutputFlag.Succeed, f'您已成功加入[{userClanName}]')
        else:
            outputs.append(OutputFlag.Abort, f'您当前正在其它公会({userClanName})，无法向您发起邀请。')
        return outputs
    
    clanRecord = GetANotFullClan()
    FarmBind.create(pcrid=pcrid, qqid=qqid, permitted_clanid=clanRecord.clanid)
    try:
        await query.query(clanRecord.leader_pcrid_cache, '/clan/invite', {'invited_viewer_id': pcrid, "invite_message": f"欢迎加入{clanRecord.clan_name_cache}！"})
    except Exception as e:
        raise PcrApiException(f'邀请加入公会失败：{e}') from e

    asyncio.create_task(RevokeClanInviteAfterDelay(clanRecord.leader_pcrid_cache, clanRecord.clan_name_cache, pcrid, 7200))
    outputs.append(OutputFlag.Succeed, f'成功邀请{userInfoStr}进入农场[{clanRecord.clan_name_cache}]。请在2小时内接受此邀请')
    
    try:
        outputs += await AcceptClanInvite(pcrid, clanRecord.leader_pcrid_cache)    
    except Exception as e:
        pass
    
    return outputs


async def RevokeClanInviteAfterDelay(leaderPcrid:int, leaderClanName:str, userPcrid:int, delay:int = 0) -> None:
    await asyncio.sleep(delay)

    farmBind:FarmBind = FarmBind.get_or_none(FarmBind.pcrid == userPcrid)
    if (farmBind is None) or (farmBind.permitted_clanid == 0):
        return
    
    try:
        profileRes = await query.get_profile(leaderPcrid, userPcrid)
        userClanName = profileRes.get("clan_name", "")
    except Exception as e:
        farmBind.permitted_clanid = 0
        farmBind.save()
    
    if userClanName != leaderClanName:
        farmBind.permitted_clanid = 0
        farmBind.save()
    
    try:
        inviteRes = await query.query(leaderPcrid, '/clan/invite_user_list', {"clan_id": await query.get_clan_id(leaderPcrid), "page": 0, "oldest_time": 0})
        inviteId = [x["invite_id"] for x in inviteRes["list"] if x["viewer_id"] == userPcrid and (datetime.now() - datetime.strptime(x["create_time"], "%Y-%m-%d %H:%M:%S")).total_seconds() > delay - 1]
    except Exception as e:
        print_exc()
        hoshino.logger.error(f'使用会长账号[{leaderPcrid}]查看当前邀请列表失败：{e}')
        return
    
    if len(inviteId) == 0:
        return
    inviteId:int = inviteId[0]
    
    try:
        await query.query(leaderPcrid, '/clan/cancel_invite', {"invite_id": inviteId})
    except Exception as e:
        print_exc()
        hoshino.logger.error(f'[{userPcrid}]超时未接受农场邀请，使用账号[{leaderPcrid}]撤回邀请失败：{e}')
        return

    hoshino.logger.info(f'[{userPcrid}]超时未接受农场邀请，使用账号[{leaderPcrid}]撤回邀请成功')


#@sv.on_fullmatch(("退出农场"))
async def QuitFarmConfirmInterface(bot: HoshinoBot, ev: CQEvent):
    bot.finish(ev, await QuitFarmConfirm(ev.user_id))


async def QuitFarmConfirm(qqid: int) -> str:
    """
    在线查询并展示绑定情况。同步数据库。
    """
    
    def GetIdentityCodes(values: List[int]) -> Dict[int, int]:
    
        def CommonPrefixLength(s1: str, s2:str) -> int:
            mi = min(len(s1), len(s2))
            for i in range(mi):
                if s1[i] != s2[i]:
                    return i
            return mi
        
        values = list(sorted([str(x) for x in values]))
        prep = 0
        output:Dict[int, int] = {}
        for i in range(len(values)):
            nowV:str = values[i]
            succ = CommonPrefixLength(nowV, values[i+1]) if nowV != values[-1] else 0
            output[int(nowV)] = int(nowV[:max(prep, succ) + 1])
            prep = succ
        return output
    
    records = FarmBind.select(FarmBind.pcrid).where(FarmBind.qqid == qqid)
    outputs = []
    randomBotAccount = GetARandomBotAccount()
    
    for record in records:
        pcrid = record.pcrid
        try:
            profileRes = await query.get_profile(randomBotAccount, pcrid)
            userPcrName = profileRes["user_info"]["user_name"]
            userClanName = profileRes.get("clan_name", "")
            
            userFarmid = GetFarmIdFromName(userClanName)
            record.permitted_clanid = userFarmid # 同步
            record.save()
            if userFarmid:
                outputs.append([record.pcrid, userPcrName, userClanName])
        except Exception as e:
            print_exc()
            hoshino.logger.error(f'向QQ[{qqid}]展示农场绑定情况时，获取用户PCRID[{pcrid}]信息失败：{e}')
            continue
        
    if len(outputs) == 0:
        return f'{qqid}当前没有绑定任何在农场中的PCR账号'
    
    identityCodes:Dict[int, int] = GetIdentityCodes([x[0] for x in outputs])
    for output in outputs:
        output[0] = identityCodes[output[0]]
    outputs = [["识别码", "昵称", "所在公会"]] + outputs + [["请发送[退出农场 <识别码>]（不含尖括号）以选定对应账号"]]
    return "\n".join([" ".join([str(y) for y in x]) for x in outputs])


@sv.on_prefix(("退出农场"))
async def QuitFarmInterface(bot: HoshinoBot, ev: CQEvent):
    qqid: int = ev.user_id
    identityCodes: List[str] = ev.message.extract_plain_text().strip().split()
    if len(identityCodes) == 0:
        return await QuitFarmConfirmInterface(bot, ev)
    
    outputs, pcrids = GetPcridsFromIdentityCodes(qqid, identityCodes)
    await bot.send(ev, str(outputs))
    for pcrid in pcrids:
        try:
            await bot.send(ev, str(await QuitFarm(pcrid)))
        except Exception as e:
            await bot.send(ev, f'将[{pcrid}]移出农场失败：{e}')


# GetPcridsFromIdentityCodesReturn = namedtuple('GetPcridsFromIdentityCodesReturn', ['outputs', 'pcrids'])
# GetPcridsFromIdentityCodesReturn.__annotations__ = {
#     'outputs': Outputs,
#     'pcrids': List[int],
# }

def GetPcridsFromIdentityCodes(qqid: int, identityCodes: List[str]) -> Tuple[Outputs, List[int]]:
    """
    查找绑定在qqid上且识别码足以唯一确定pcrid的记录。
    
    Returns:
        Tuple[Outputs, List[int]]: outputs, pcrids
    """
    outputs = Outputs()
    pcrids:List[int] = []
    farmBindRecords:List[FarmBind] = FarmBind.select(FarmBind.pcrid).where((FarmBind.qqid == qqid) & (FarmBind.permitted_clanid != 0))
    farmBindRecordpcrids:List[str] = [str(farmBindRecord.pcrid) for farmBindRecord in farmBindRecords]
    for identityCode in identityCodes:
        l = len(identityCode)
        res:List[str] = [pcrid for pcrid in farmBindRecordpcrids if pcrid[:l] == identityCode]
        if len(res) == 0:
            outputs.append(OutputFlag.Abort, f'未找到识别码[{identityCode}]对应的绑定记录')
        elif len(res) > 1:
            outputs.append(OutputFlag.Abort, f'识别码[{identityCode}]对应多条绑定记录')
        else:
            pcrid = res[0]
            outputs.append(OutputFlag.Info, f'识别码[{identityCode}]找到记录[{pcrid}]')
            pcrids.append(int(pcrid))
            
    if outputs.Result == OutputFlag.Abort:
        outputs.append(OutputFlag.Info, "请发送[退出农场]以查看详情")
    return outputs, pcrids


async def QuitFarm(pcrid: int) -> Output:
    """
    将pcrid移出农场（若在）。
    将pcrid移出邀请（若在）。

    Args:
        pcrid (int): pcrid

    Returns:
        Output: 移除结果
    """
    
    farmBindRecords:FarmBind = FarmBind.select(FarmBind.permitted_clanid).where((FarmBind.pcrid == pcrid) & (FarmBind.permitted_clanid != 0))
    if not farmBindRecords.exists():
        return Output(OutputFlag.Abort, f'未找到[{pcrid}]对应的绑定记录')
    farmBindRecord = farmBindRecords[0]
    clanid:int = farmBindRecord.permitted_clanid
    
    clanInfoRecords:ClanInfo = ClanInfo.select().where(ClanInfo.clanid == clanid)
    if not clanInfoRecords.exists():
        return Output(OutputFlag.Abort, f'[{pcrid}]记录的公会[{clanid}]未被收录')
    clanInfoRecord:ClanInfo = clanInfoRecords[0]
    leaderPcrid:int = clanInfoRecord.leader_pcrid_cache
    
    try:
        inviteRes = await query.query(leaderPcrid, '/clan/invite_user_list', {"clan_id": clanInfoRecord.clanid, "page": 0, "oldest_time": 0})
        inviteId = [x["invite_id"] for x in inviteRes["list"] if x["viewer_id"] == pcrid]
    except Exception as e:
        print_exc()
        hoshino.logger.error(f'使用会长账号[{leaderPcrid}]查看当前邀请列表失败：{e}')
        return Output(OutputFlag.Error, f'使用会长账号[{leaderPcrid}]查看当前邀请列表失败：{e}')
    if len(inviteId):
        inviteId:int = inviteId[0]
        try:
            await query.query(leaderPcrid, '/clan/cancel_invite', {"invite_id": inviteId})
        except Exception as e:
            print_exc()
            hoshino.logger.error(f'使用会长账号撤回对[{pcrid}]的邀请失败：{e}')
            return Output(OutputFlag.Error, f'使用会长账号撤回对[{pcrid}]的邀请失败：{e}')
        else:
            FarmBind.update(permitted_clanid=0).where(FarmBind.pcrid == pcrid).execute()
            return Output(OutputFlag.Succeed, f'使用会长账号撤回对[{pcrid}]的邀请成功')
    
    try:
        clanInfoRes = await query.get_clan_info(leaderPcrid, clanid)
        members:List[dict] = clanInfoRes["clan"]["members"]
        isInFarm:List[bool] = [True for x in members if x["viewer_id"] == pcrid]
    except Exception as e:
        print_exc()
        hoshino.logger.error(f'使用会长账号查看当前公会详情失败：{e}')
        return Output(OutputFlag.Error, f'使用会长账号查看当前公会详情失败：{e}')
    if len(isInFarm):
        try:
            await query.query(leaderPcrid, '/clan/remove', {'clan_id': clanid, "remove_viewer_id": pcrid})
        except Exception as e:
            print_exc()
            hoshino.logger.error(f'使用会长账号将[{pcrid}]移出农场失败：{e}')
            return Output(OutputFlag.Error, f'使用会长账号将[{pcrid}]移出农场失败：{e}')
        else:
            FarmBind.update(permitted_clanid=0).where(FarmBind.pcrid == pcrid).execute()
            return Output(OutputFlag.Succeed, f'使用会长账号将[{pcrid}]移出农场成功')
    
    FarmBind.update(permitted_clanid=0).where(FarmBind.pcrid == pcrid).execute()
    return Output(OutputFlag.Skip, f'[{pcrid}]既不在公会中也不在邀请列表中')


@sv.on_fullmatch(("今日捐赠", "查询捐赠"))
async def QueryDonateInterface(bot: HoshinoBot, ev: CQEvent):
    await bot.send(ev, QueryDonate())


def QueryDonate() -> str:
    """
    返回bot今日捐赠情况的字符串描述
    """
    farmRecords = GetFarmRecords()
    outp = []
    for farmRecord in farmRecords:
        outp.append(f'{farmRecord.clan_name_cache}')
        records = FarmInfo.select(FarmInfo.today_donate_cache, PcrAccountInfo.pcrname_cache).join(PcrAccountInfo, on=(FarmInfo.pcrid == PcrAccountInfo.pcrid)).where((FarmInfo.clanid_cache == farmRecord.clanid) & (FarmInfo.activated == True)).order_by(FarmInfo.today_donate_cache.desc())
        if records.exists():
            clusters = defaultdict(list)
            for record in records:
                clusters[record.today_donate_cache].append(record.pcr_account_info.pcrname_cache)
            for value, keys in clusters.items():
                outp.append(f'{value}: {", ".join(sorted(keys))}')
        else:
            outp.append("-")
    
    return "\n".join(outp) if len(outp) else "当前没有正在工作的农场"


@sv.on_fullmatch(("农场成员", "农场人员", "查询农场", "查询农场人员", "查询农场成员", "查询农场信息", "农场名单"))
async def QueryBindOfflineInterface(bot: HoshinoBot, ev: CQEvent):
    if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        return
    bot.finish(ev, "\n".join([QueryBindOffline(), "此为数据库离线查询结果。若需更新数据库，请使用[农场人员更新]指令。"]))


def QueryBindOffline() -> str:
    query = (
        FarmBind
        .select(FarmBind, PcrAccountInfo.pcrname_cache, QqAccountInfo.nickname_cache, ClanInfo.clan_name_cache)
        .join(PcrAccountInfo, JOIN.LEFT_OUTER, on=(FarmBind.pcrid == PcrAccountInfo.pcrid))
        .switch(FarmBind)
        .join(QqAccountInfo, JOIN.LEFT_OUTER, on=(FarmBind.qqid == QqAccountInfo.qqid))
        .switch(FarmBind)
        .join(ClanInfo, JOIN.LEFT_OUTER, on=(FarmBind.permitted_clanid == ClanInfo.clanid))
        .where(FarmBind.permitted_clanid != 0)
        .order_by(FarmBind.permitted_clanid.desc())
    )
    if not query.exists():
        return "尚未准许任何人员进入农场"
    outputs = [['pcrid', 'pcr_name', 'qqid', 'qq_name', 'clanid', 'clan_name']]
    for row in query:
        outputs.append([
            row.pcrid,
            row.pcr_account_info.pcrname_cache if hasattr(row, 'pcr_account_info') else None,
            row.qqid,
            row.qq_account_info.nickname_cache if hasattr(row, 'qq_account_info') else None,
            row.permitted_clanid,
            row.clan_info.clan_name_cache if hasattr(row, 'clan_info') else None
        ])
    return "\n".join([" ".join([str(y) for y in x]) for x in outputs])


@sv.on_fullmatch(("农场人员更新", "农场成员更新", "农场名单更新", "农场信息更新", "更新农场人员", "更新农场成员", "更新农场名单", "更新农场信息"))
async def QueryBindOnlineInterface(bot: HoshinoBot, ev: CQEvent):
    if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        return
    outputs = await UpdateBind()
    await bot.send(ev, str(outputs))
    if outputs:
        await bot.send(ev, QueryBindOffline())


async def UpdateBind() -> Outputs:
    outputs = Outputs()
    farmRecords = GetFarmRecords()
    farmPcrids = set([record.pcrid for record in FarmInfo.select().where(FarmInfo.activated == 1)])

    for farmRecord in farmRecords:
        pcrid = farmRecord.leader_pcrid_cache
        try:
            clanid = await query.get_clan_id(pcrid)
        except Exception as e:
            print_exc()
            outputs.append(OutputFlag.Error, f'获取会长账号[{pcrid}]的公会id失败：{e}')
            continue
        
        userPcrids:List[int] = []
        try:
            inviteRes = await query.query(pcrid, '/clan/invite_user_list', {"clan_id": clanid, "page": 0, "oldest_time": 0})
            userPcrids += [x["viewer_id"] for x in inviteRes["list"]]
        except Exception as e:
            print_exc()
            outputs.append(OutputFlag.Error, f'使用会长账号[{pcrid}]查看当前邀请列表失败：{e}')
            continue
        try:
            clanInfoRes = await query.get_clan_info(pcrid, clanid)
            userPcrids += [x["viewer_id"] for x in clanInfoRes["clan"]["members"]]
        except Exception as e:
            print_exc()
            outputs.append(OutputFlag.Error, f'使用会长账号[{pcrid}]查看公会详情失败：{e}')
            continue

        userPcrids = list(set(userPcrids) - farmPcrids)
        modifyCount = 0
        createCount = 0
        for userPcrid in userPcrids:
            record = FarmBind.get_or_none(pcrid=userPcrid)
            if record is not None:
                if record.permitted_clanid != clanid:
                    modifyCount += 1
                    record.permitted_clanid = clanid
                    record.save()
            else:
                createCount += 1
                FarmBind.create(pcrid=userPcrid, permitted_clanid=clanid)
        outputs.append(OutputFlag.Succeed, f'更新农场[{clanid}]记录成功：修改={modifyCount} 新增={createCount}')
        
        try:
            await query.get_clan_info(pcrid, clanid) # 更新公会信息
        except Exception as e:
            print_exc()
            outputs.append(OutputFlag.Error, f'使用会长账号[{pcrid}]获取并更新公会信息失败：{e}')
    
    return outputs


@sv.on_prefix(("农场踢除", "踢除人员", "踢除成员", "移除成员", "移除人员", "农场移除"))
async def KickInterface(bot: HoshinoBot, ev: CQEvent):
    if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        return
    pcrid: str = ev.message.extract_plain_text().strip()
    try:
        pcrid: int = int(pcrid)
    except Exception as e:
        bot.finish(ev, f'无法识别[{pcrid}]')
    else:
        bot.finish(ev, str(await Kick(pcrid)))
    
    
async def Kick(pcrid: int) -> Outputs:
    farmBindRecord: FarmBind = FarmBind.get_or_none(FarmBind.pcrid == pcrid)
    
    if farmBindRecord is None:
        return Outputs([
            Output(OutputFlag.Warn, f'数据库中不存在记录[{pcrid}]'),
            Output(OutputFlag.Info, f'若您确信该账号位于农场，请先发送[加入农场{pcrid}]'),
            Output(OutputFlag.Info, f'若需立即更新数据库，请发送[农场人员更新]'),
        ])

    if farmBindRecord.permitted_clanid == 0:
        return Outputs([
            Output(OutputFlag.Warn, f'数据库中存在记录[{pcrid}]，但未被授权至任何农场。'),
            Output(OutputFlag.Info, f'若您确信该账号位于农场，请先发送[加入农场{pcrid}]'),
            Output(OutputFlag.Info, f'若需立即更新数据库，请发送[农场人员更新]'),
        ])
    
    return Outputs([await QuitFarm(pcrid)])


@sv.on_fullmatch(("清空农场", "农场清空"))
async def RemoveAllConfirmInterface(bot: HoshinoBot, ev: CQEvent):
    if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        return
    bot.finish(ev, "请使用指令[#农场清空]")
    

@sv.on_fullmatch(("#清空农场", "#农场清空"))
async def RemoveAllInterface(bot: HoshinoBot, ev: CQEvent):
    if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
        return
    bot.finish(ev, str(await RemoveAll()))


async def RemoveAll() -> Outputs:
    outputs = await UpdateBind()
    if not outputs:
        return outputs
    farmBindRecords:List[FarmBind] = FarmBind.select(FarmBind.pcrid).where(FarmBind.permitted_clanid != 0)
    return outputs + Outputs([await QuitFarm(farmBindRecord.pcrid) for farmBindRecord in farmBindRecords])


@sv.scheduled_job('cron', hour='2')
async def RevokeAllOverdueClanInviteCron():
    await RevokeAllOverdueClanInvite()
    await UpdateBind()


async def RevokeAllOverdueClanInvite(threshold: int = 7200) -> None:
    """
    挨个登录会长农场号，撤回超时的公会邀请
    """
    farmRecords = GetFarmRecords()
    for farmRecord in farmRecords:
        pcrid = farmRecord.leader_pcrid_cache
        try:
            clanid = await query.get_clan_id(pcrid)
        except Exception as e:
            print_exc()
            hoshino.logger.error(f'获取会长账号[{pcrid}]的公会id失败：{e}')
            continue
        try:
            inviteRes = await query.query(pcrid, '/clan/invite_user_list', {"clan_id": clanid, "page": 0, "oldest_time": 0})
            inviteIds = [x["invite_id"] for x in inviteRes["list"] if (datetime.now() - datetime.strptime(x["create_time"], "%Y-%m-%d %H:%M:%S")).total_seconds() > threshold]
            userPcrids = [x["viewer_id"] for x in inviteRes["list"] if (datetime.now() - datetime.strptime(x["create_time"], "%Y-%m-%d %H:%M:%S")).total_seconds() > threshold]
        except Exception as e:
            print_exc()
            hoshino.logger.error(f'使用会长账号[{pcrid}]查看当前邀请列表失败：{e}')
            continue
        
        for userPcrid in userPcrids:
            FarmBind.update(permitted_clanid=0).where(FarmBind.pcrid == userPcrid).execute()
        
        for inviteId in inviteIds:
            try:
                await query.query(pcrid, '/clan/cancel_invite', {"invite_id": inviteId})
            except Exception as e:
                print_exc()
                hoshino.logger.error(f'[{inviteId}]超时未接受农场邀请，使用账号[{pcrid}]撤回邀请失败：{e}')
                break
            else:
                hoshino.logger.info(f'[{inviteId}]超时未接受农场邀请，使用账号[{pcrid}]撤回邀请成功')


@sv.scheduled_job('cron', hour='0')
async def DonateResetCron():
    DonateReset()


def DonateReset() -> None:
    """
    农场号的数据库记录中的今日捐赠缓存置0
    """
    FarmInfo.update(today_donate_cache=0).execute()


def GetARandomBotAccount() -> PcrAccountInfo:
    """
    随机获取一个农场号的账密记录。可用于查询他人档案

    Raises:
        NotFoundException: 未找到激活的农场号

    Returns:
        PcrAccountInfo: 一个农场号的账密记录
    """
    
    farmInfoRecord: FarmInfo = FarmInfo.select().where(FarmInfo.activated == 1).order_by(fn.Random()).limit(1)
    if farmInfoRecord.exists():    
        # TODO 尝试登录函数（bool）。不安全则函数内修改记录的activate为false；is_valid为false。
        return PcrAccountInfo.get(PcrAccountInfo.pcrid == farmInfoRecord[0].pcrid)
    raise NotFoundException("未找到激活的农场号")


@sv.scheduled_job('interval', seconds=14400)
async def FindDonationRequestCron():
    if 3 <= datetime.now().hour <= 6:
        return  # 休息，留给清日常模块
    await FindDonationRequest()
    
    
@sv.on_fullmatch(('请求捐赠', '申请捐赠', '发起捐赠'))
async def FindDonationRequestInterface(bot: HoshinoBot, ev: CQEvent):
    await FindDonationRequest()
    

async def FindDonationRequest() -> None:
    for farmId in GetFarmIds():
        invalid_requests:List[int] = []
        farmInfoRecords:List[FarmInfo] = FarmInfo.select().where((FarmInfo.activated == 1) & (FarmInfo.clanid_cache == farmId) & (FarmInfo.today_donate_cache < 10)).order_by(FarmInfo.today_donate_cache.asc())
        if not farmInfoRecords.exists():
            continue
        for farmInfoRecord in farmInfoRecords:
            # TODO 更新today_donate_cache
            pcrid = farmInfoRecord.pcrid 
            try:
                clanInfoList = await query.query(pcrid, '/clan/chat_info_list', {
                    "clan_id": farmId,
                    "start_message_id": 0,
                    "search_date": "2099-12-31",
                    "direction": 1,
                    "count": 10,
                    "wait_interval": 3,
                    "update_message_ids": [],
                })
            except Exception as e:
                print_exc()
                hoshino.logger.error(f'使用账号[{pcrid}]查看公会消息失败：{e}')
                continue
            
            try:
                serverTime = await query.get_server_time(pcrid)
            except Exception as e:
                print_exc()
                hoshino.logger.error(f'获取服务器时间失败：{e}')
                continue
            
            # 过滤出8h内的请求
            DonateMessageIds:List[int] = [x["message_id"] for x in clanInfoList.get("clan_chat_message", []) if ("message_id" in x) and (x.get("message_type", -1) == 2) and (serverTime - x.get("create_time", -1) < 8 * 3600 - 60 * 30) and (x["message_id"] not in invalid_requests)]
            # 进一步过滤出未捐赠完毕的请求 
            equipRequests:List[dict] = [x for x in clanInfoList.get("equip_requests", []) if x.get("message_id", -1) in DonateMessageIds and x.get("donation_num", -1) < x.get("request_num", -1)]
            if len(equipRequests) == 0:
                break
            # id -> count
            userEquipData:Dict[int, int] = {x["equip_id"]: x["equip_count"] for x in clanInfoList.get("user_equip_data", [])} 

            for equipRequest in equipRequests:
                if "history" in equipRequest:
                    continue # 不响应自己的请求
                canDonateNum = min(2 - equipRequest["user_donation_num"], equipRequest["request_num"] - equipRequest["donation_num"], userEquipData.get(equipRequest["equip_id"], 0), 10 - int(farmInfoRecord.today_donate_cache))
                if canDonateNum <= 0:
                    continue
                try:
                    donateRes = await query.query(pcrid, '/equipment/donate', {
                        "clan_id": farmId,
                        "message_id": equipRequest["message_id"],
                        "donation_num": canDonateNum,
                        "current_equip_num": userEquipData[equipRequest["equip_id"]]
                    })
                except Exception as e:
                    print_exc()
                    hoshino.logger.error(f'在农场[{farmId}]使用账号[{pcrid}]向捐赠请求[{equipRequest["message_id"]}]捐赠[{canDonateNum}]个装备失败：{e}')
                    invalid_requests.append(equipRequest["message_id"])
                    continue
                
                farmInfoRecord.today_donate_cache = int(donateRes.get("donation_num", farmInfoRecord.today_donate_cache + canDonateNum))
                farmInfoRecord.save()


# @sv.on_prefix(("农场转移"))
# async def FarmTransferInterface(bot: HoshinoBot, ev: CQEvent):
#     if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
#         return
#     msg: List[str] = ev.message.extract_plain_text().strip().split()
#     try:
#         pcrid = int(msg[0])
#         clanid = int(msg[1])
#     except Exception as e:
#         await bot.send(ev, f'{msg}无法被转换为[pcrid:int, clanid:int]')
#     else:    
#         await bot.send(ev, str(await FarmTransferInterface(pcrid, clanid)))
    
    
# async def FarmTransfer(pcrid: int, clanid: int) -> Outputs:
#     if clanid 无记录:
#         return Outputs.FromStr(OutputFlag.Abort, f'[{clanid}]未被收录')
#     if clanid的会长无账号记录:
#         return Outputs.FromStr(OutputFlag.Abort, f'[{clanid}]的会长无账号记录')
#     if clanid的会长账号记录不合法:
#         return Outputs.FromStr(OutputFlag.Abort, f'[{clanid}]的会长账号记录不合法')
    
#     if pcrid is 农场号:
#         now_clanid = pcrid 当前所在的 clanid
#         if now_clanid == clanid:
#             return Outputs.FromStr(OutputFlag.Skip, f'[{pcrid}]当前已位于[{clanid}]')
        
#         outputs = Outputs()
#         if now_clanid != 0: # 当前正在其它农场，尝试离开
#             outputs += await StaffQuitFarm(pcrid)
#             if not outputs:
#                 return outputs
        
#         outputs += await StaffEnterFarm(pcrid)
#         return outputs
        
#     elif pcrid is 农场人员:
#         now_clanid = pcrid 当前所在的 clanid
#         qqid = pcrid 当前所绑的qqid
#         if now_clanid == clanid:
#             return Outputs.FromStr(OutputFlag.Skip, f'[{pcrid}]当前已位于[{clanid}]')
        
#         outputs = Outputs()
#         if now_clanid != 0: # 当前正在其它农场，尝试离开
#             outputs += await QuitFarm(pcrid)
#             if not outputs:
#                 return outputs
        
#         outputs += await EnterFarm(pcrid, qqid)
#         return outputs
        
#     else:
#         return Outputs.FromStr(OutputFlag.Abort, f'[{pcrid}]非农场号且非农场人员')


# @sv.on_prefix(("农场号"))
# async def QueryStaffOfflineInterface(bot: HoshinoBot, ev: CQEvent):
#     if not hoshino.priv.check_priv(ev, hoshino.priv.SUPERUSER):
#         return
#     bot.finish(ev, "\n".join([QueryStaffOffline(), "此为数据库离线查询结果。"]))


# def QueryStaffOffline() -> str:
#     ...
#     # TODO


# TODO 测试用户拒绝邀请后的表现

async def CreateClan(pcrid: int, clan_name: str, description: str = "") -> Outputs:
    """
    使用pcrid账号创建一个公会。
    
    Args:
        clan_name (str): 公会名
        description (str, optional): 公会描述
    """
    try:
        res = await PcrApi(pcrid).CreateClan(PcrApi.CreateClanRequest(clan_name=clan_name, description=description))
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'[{pcrid}]创建公会[{clan_name}]失败：{e}')
    return Outputs.FromStr(OutputFlag.Succeed, f'[{pcrid}]创建公会[{clan_name}]({res.clan_id})成功')


async def InviteToClan(leader_pcrid: int, invited_pcrid: int) -> Outputs:
    """
    尝试使用leader_pcrid账号对member_pcrid账号发起加入公会的邀请。
    如果正常返回说明成功，任何失败将抛出异常。
    """
    
    leaderPcrClient = PcrApi(leader_pcrid)
    try:
        invitedProfile = await leaderPcrClient.GetProfile(invited_pcrid)
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'使用会长账号[{leader_pcrid}]查看账号[{invited_pcrid}]信息失败：{e}')
    
    if invitedProfile.get("clan_name", "") != "":
        return Outputs.FromStr(OutputFlag.Abort, f'账号[{invited_pcrid}]已在公会[{invitedProfile["clan_name"]}]，无法邀请')
    
    try:
        await leaderPcrClient.ClanInvite(PcrApi.ClanInviteRequest(invited_pcrid, "欢迎加入怡宝的装备农场！"))
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'使用会长账号[{leader_pcrid}]邀请账号[{invited_pcrid}]加入公会失败：{e}')

    return Outputs.FromStr(OutputFlag.Succeed, f'使用会长账号[{leader_pcrid}]邀请账号[{invited_pcrid}]加入公会成功')


async def AcceptClanInvite(pcrid: int, inviter_pcrid: int) -> Outputs:
    pcrClient = PcrApi(pcrid)
    try:
        invitedClans = await pcrClient.GetInvitedClans()
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'查看账号[{pcrid}]被公会邀请信息失败：{e}')
    
    if invitedClans == []:
        return Outputs.FromStr(OutputFlag.Skip, f'账号[{pcrid}]未被任何公会邀请')
    
    targetClan = [x.clan_id for x in invitedClans if x.leader_viewer_id == inviter_pcrid]
    if targetClan == []:
        return Outputs.FromStr(OutputFlag.Skip, f'账号[{pcrid}]未被会长账号[{inviter_pcrid}]邀请')
    targetClanId = targetClan[0]
    try:
        await pcrClient.AcceptClanInvite(targetClanId)
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'账号[{pcrid}]收到公会[{targetClanId}]邀请，但同意请求失败：{e}')
    
    return Outputs.FromStr(OutputFlag.Succeed, f'账号{pcrClient.OutputName}接受公会[{targetClanId}]邀请成功')


@sv.on_fullmatch(("退出公会"))
async def QuitClanSelfConfirmInterface(bot: HoshinoBot, ev: CQEvent):
    ...
    # TODO
    # 如果在农场，则转移至退出农场
    # 否则提示退出公会有1天冷却期

async def QuitClanSelfConfirm():
    ...
    # TODO
    

@sv.on_fullmatch(("#退出公会"))
async def QuitClanSelfInterface(bot: HoshinoBot, ev: CQEvent):
    ...
    # TODO


async def QuitClanSelf():
    ...
    # TODO
    # 判断自己是否是会长
    
    
async def ForTest():
    ...

    # members = [1393560518763]
    # leader = 1370335173164
    # for member in members:
    #     print(await InviteToClan(leader, member))
    #     print(await AcceptClanInvite(member, leader))