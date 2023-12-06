import asyncio
import threading
from typing import Dict, List, Optional, Tuple, Union, Set
import math
from os.path import dirname, join, exists
from pathlib import Path
from json import load, dump, dumps
from io import BytesIO
import base64
import re
import datetime
import time
from enum import IntEnum, unique
from traceback import print_exc, format_exc
from collections import defaultdict

from nonebot import get_bot, on_command, on_startup
from nonebot import on_notice, NoticeSession
import pandas as pd
import PIL as pil
import dataframe_image as dfi

from hoshino import R, Service, priv, util
from hoshino.typing import CQEvent, HoshinoBot

from ...query import query
from ...query.PcrApi import PcrApi, PcrApiException
from ...query.utils import item_utils, map_utils, star6_utils
from .. import chara
from .utils.file_io import gs_fileIo
from ...utils.output import *


sv_help_all = '''
[#pcr 账号 密码] 上传或更新自己的账号和密码
[清日常设置]
[清日常]
[#清日常@somebody]
[#刷图推荐]
[删除账号]

[查box] bot会登录您的账号以获取您的详细box至数据库
[查角色] 发这条指令试试就知道怎么用了
[#上[地下城|公会|关卡]支援@<somebody> 角色]
'''.strip()

sv_help_group_manager = '''
[发号<@号><@代刀人>]
[更新状态<@号><状态>]  状态: 1/正常 2/错误 3/未交号
[更新密码<qq号> <密码>]  私聊edq使用哟
[导出账号]
'''.strip()

sv_help_bot_superuser = '''
[账号校验 @号]
[账号批量校验] 检测在密码本中且在本群中的成员的账号，设置状态并保存box。若不可登录，提示号主。
[导出box]
[催交号] 向状态记录为2和3的账号号主发送更改密码消息
[加入密码本 <@号>+]
'''.strip()

sv = Service('AutoPcr', visible=False)

friendnum = []
g_doDailyQueue: Set[str] = set()
admin_qqid_int = 981082801
uri = "https://bot.ellye.cn"
if uri.endswith(r'/'):
    uri = uri[:-1]

group_manager = [
]

curpath = dirname(__file__)

# dic = {}
# dic[str(qq)] = {name, account, password, status}
# 账号/密码缺失则为空
sec = join(curpath, 'secret.json')
IOLock = threading.Lock()
   

@sv.on_fullmatch(("pcr帮助", "PCR帮助"))
async def send_help(bot: HoshinoBot, ev: CQEvent):
    sv_help = [sv_help_all]
    if ev.user_id in group_manager:
        sv_help.append(sv_help_group_manager)
    if priv.check_priv(ev, priv.SUPERUSER):
        sv_help.append(sv_help_bot_superuser)
    await bot.finish(ev, "\n\n".join(sv_help))


def getNowtime() -> int:
    return int(datetime.datetime.timestamp(datetime.datetime.now()))


async def get_friends():
    global friendnum
    if len(friendnum) < 10:
        bot = get_bot()
        friendnum.clear()
        flist = await bot.get_friend_list()
        for i in flist:
            friendnum.append(int(i['user_id']))
    return friendnum


@on_notice("friend_add")
async def added_friend(session: NoticeSession):
    global friendnum
    if len(friendnum) < 10:
        await get_friends()
    friendnum.append(int(session.event.user_id))
    friendnum = list(set(friendnum))


def save_sec_backup(dic):
    with open(join(curpath, 'secret_backup.json'), 'w', encoding="utf-8") as fp:
        dump(dic, fp, indent=4, ensure_ascii=False)


def save_sec(dic):
    with IOLock:
        with open(sec, 'w', encoding="utf-8") as fp:
            dump(dic, fp, indent=4, ensure_ascii=False)


def get_sec() -> dict:
    with IOLock:
        dic = {}
        if not exists(sec) and exists(join(curpath, 'secret.txt')):
            with open(join(curpath, 'secret.txt'), encoding="utf-8") as fp:
                for line in fp:
                    # QQ号 名称 账号 密码 状态
                    line = line.strip()
                    a = line.split('\t')
                    if len(a) == 1 and len(line.split(' ') > 1):
                        a = line.split(' ')
                    if len(a) == 5:
                        dic[a[0]] = {
                            "name": a[1],
                            "account": a[2],
                            "password": a[3],
                            "status": a[4]
                        }
                    if len(a) == 3:
                        dic[a[0]] = {
                            "name": a[1],
                            "account": "",
                            "password": "",
                            "status": "3"
                        }
            save_sec(dic)

        if exists(sec):
            try:
                with open(sec, "r", encoding="utf-8") as fp:
                    dic = load(fp)
            except:
                with open(sec, "r", encoding="gb2312") as fp:
                    dic = load(fp)
        return dic


def getSecret(qqid: Union[str, int, None] = None) -> Dict[str, str]:
    """
    传入qqid，返回pcr账号信息；若不传，返回全部信息
    若存在，``return {"status": True, "message": {name:pcr内昵称（登记时）, account:pcrid, password, status:状态}``
    若不存在，``return {"status": False}``
    """
    dic = get_sec()
    if qqid == None:
        return {"status": True, "message": dic}
    try:
        qqid = str(qqid)
        return {"status": True, "message": dic[qqid]}
    except:
        return {"status": False}


async def sendHao(bot, ev, xx, yy):
    # 把xx的号发给yy
    result = [xx, yy]
    dic = get_sec()
    if str(result[0]) not in dic:
        await bot.finish(ev, f"[CQ:at,qq={result[0]}]的账号状态为 无记录")
    else:
        info = dic[str(result[0])]
        # 状态 1/正常 2/错误 3/未交号
        if info["status"] in [
                3, '3', "未交号"
        ] or info["account"] == "" or info["password"] == "":
            await bot.finish(ev, f"[CQ:at,qq={result[0]}]的账号状态为 未交号！")
        if info["status"] in [2, '2', "错误"]:
            await bot.finish(ev, f"[CQ:at,qq={result[0]}]的账号状态为 错误！")
        if info["status"] in [1, '1', "正常"]:
            msg = info.get("name", str(xx)) + '\n' + info["account"] + '\n' + info["password"]
            if "pcrid" in info:
                appendmsg = ""
                try:
                    if "last_get_account_member" in info:
                        qid = info["last_get_account_member"]
                        tim = info["last_get_account_time"]
                        appendmsg += f'\n该号最后记录于 {tim} 发给 {dic.get(str(qid),{}).get("name", qid)}'
                    info["last_get_account_member"] = str(yy)
                    info["last_get_account_time"] = datetime.datetime.now().strftime("%m-%d %H:%M")
                    save_sec(dic)
                except:
                    pass
                try:
                    res = await query.query({"account": "zcm36857", "password": "013460"}, '/profile/get_profile', {'target_viewer_id': int(info["pcrid"])})
                    timestamp = res["user_info"]["last_login_time"]
                    timestr = time.strftime("%m-%d %H:%M", time.localtime(timestamp))
                    appendmsg += f'\n该号最后登录于 {timestr}'
                except:
                    pass
                try:
                    from ...daidao import daidao
                    dat = await daidao.get_yobot_data(ev.group_id)
                    chudao = dat["challenges"]
                    for record in reversed(chudao):
                        if record["qqid"] == int(xx):
                            timestr = time.strftime("%m-%d %H:%M", time.localtime(record["challenge_time"]))
                            appendmsg += f'\n该号最后出刀于 {timestr} 向 boss{record["cycle"]}-{record["boss_num"]} ({record["damage"]//10000}w{" 补偿刀" if record["is_continue"] else ""}{" 尾刀" if record["health_ramain"] == 0 else ""})'
                            break
                    # print(dat)
                except:
                    pass
                await bot.send(ev, f'{info.get("name", str(xx))}' + appendmsg)
            friendnum = await get_friends()
            if int(result[1]) not in friendnum:
                await bot.send(ev, f"Warning: [CQ:at,qq={result[1]}]非edq好友，账号信息发送可能不成功。")
            if int(result[0]) not in friendnum:
                await bot.send(ev, f"Warning: [CQ:at,qq={result[0]}]非edq好友，代刀提醒发送可能不成功。")

            try:
                await bot.send_private_msg(
                    user_id=result[0],
                    message=f'您好~代刀手{result[1]}正在为您代刀，请勿登录！')
            except:
                pass
            try:
                await bot.send_private_msg(user_id=result[1], message=msg + appendmsg)
            except:
                pass
            if str(result[1]) != str(ev.user_id):
                msg = "发号抄送：\n" + msg
                await bot.send_private_msg(user_id=ev.user_id, message=msg + appendmsg)


lingHao = True


@sv.on_prefix(("允许领号"))
async def 允许领号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    global lingHao
    lingHao = True
    await bot.finish(ev, f"Succeed")


@sv.on_prefix(("禁止领号"))
async def 禁止领号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    global lingHao
    lingHao = False
    await bot.finish(ev, f"Succeed")


@sv.on_prefix(("领号"))
# 领号<@号>
async def 领号(bot, ev):
    global lingHao
    print(lingHao)
    dic = get_sec()
    if lingHao == False:
        return
    if str(ev.user_id) not in dic:
        return
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    print(result)
    if len(result) == 2:
        if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id not in group_manager):
            await bot.finish(ev, f"领号仅可将号发给自己！\n例：领号@某人")
        else:
            await 发号(bot, ev)
    if len(result) == 1:
        await sendHao(bot, ev, str(result[0]), str(ev.user_id))


@sv.on_prefix(("发号"))
# 发号<@号><@代刀人>
async def 发号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id not in group_manager):
        return
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    print(result)
    if len(result) == 2:
        await sendHao(bot, ev, str(result[0]), str(result[1]))


@sv.on_prefix(("更新状态"))
# 更新状态<@号><状态>
async def 更新状态(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id not in group_manager):
        return
    dic = get_sec()
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    msg = ev.message.extract_plain_text().strip()
    friendnum = await get_friends()
    if len(result) == 1 and msg != "":
        if str(result[0]) not in dic or "account" not in dic[str(result[0])]:
            dic[str(result[0])] = {}
            dic[str(result[0])]["status"] = "3"
            await bot.send(ev, f"[CQ:at,qq={result[0]}]的账号状态为 无记录")
            if int(result[0]) not in friendnum:
                await bot.send(
                    ev, f"Warning: [CQ:at,qq={result[0]}]非edq好友，账号信息发送可能不成功。")
            else:
                await bot.send_private_msg(
                    user_id=result[0],
                    message="请直接在此聊天框交号。指令：\npcr 账号 密码")
        elif msg in ['3', "未交号"]:
            dic[str(result[0])]["status"] = "3"
            await bot.send(ev, f"[CQ:at,qq={result[0]}]的账号状态已置为 未交号")
        elif msg in ['2', "错误", "密码错误", "密码错", "登不上"]:
            dic[str(result[0])]["status"] = "2"
            await bot.send(ev, f"[CQ:at,qq={result[0]}]的账号状态已置为 错误")
            await bot.send_private_msg(
                user_id=result[0],
                message="您的pcr账号状态被置为 错误\n请修改密码后将新密码通过以下指令更新：\n更新密码<密码>")
            if int(result[0]) not in friendnum:
                await bot.send(
                    ev, f"Warning: [CQ:at,qq={result[0]}]非edq好友，账号信息发送可能不成功。")
        elif msg in ['1', "正常", "正确", "密码正确"]:
            dic[str(result[0])]["status"] = "1"
            await bot.send(ev, f"[CQ:at,qq={result[0]}]的账号状态已置为 正常")
        save_sec(dic)


@sv.on_fullmatch(("删除账号"))
async def 删除账号确认(bot, ev):
    if ev.group_id:
        await bot.finish(ev, "请私聊使用本功能")
    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, "无记录")
    config = dic[qqid]
    await bot.finish(ev, f'您的pcr信息为：pcrname={config.get("pcrname", "Unknown")}\npcrid={config.get("pcrid", "Unknown")}\naccount={config.get("account", "Unknown")}\npassword={config.get("password", "Unknown")}\n删除账号将同时清除清日常设置\n若确认，请发送"#删除账号"')


@sv.on_fullmatch(("#删除账号"))
async def 删除账号(bot, ev):
    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, "无记录")
    dic.pop(qqid)
    save_sec(dic)
    await bot.finish(ev, "删除成功")


@sv.on_prefix(("更新密码"))
# 更新密码<qq号> <密码>
async def 更新密码(bot, ev):
    if ev.group_id:
        await bot.finish(ev, "请私聊使用本功能")
    msg = ev.message.extract_plain_text().strip().split(' ')
    dic = get_sec()
    if len(msg) == 1:
        msg = [str(ev.user_id), msg[0]]
        msg[1] = msg[1].replace('"', '')
        if msg[0] not in dic:
            await bot.finish(ev, f"{msg[0]}的账号状态为 无记录")
        dic[msg[0]]["password"] = msg[1]
        if dic[msg[0]]["account"] == "":
            await bot.send(ev, f"Warning: {msg[0]}的账号名无记录")
        else:
            dic[msg[0]]["status"] = "1"
        dic[msg[0]]["updatetime"] = str(datetime.datetime.now())
        save_sec(dic)
        await bot.finish(ev, f"{msg[0]}的密码已更新")
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id not in group_manager):
        return
    if len(msg) == 2:
        msg[1] = msg[1].replace('"', '')
        if msg[0] not in dic:
            await bot.finish(ev, f"{msg[0]}的账号状态为 无记录")
        dic[msg[0]]["password"] = msg[1]
        if dic[msg[0]]["account"] == "":
            await bot.send(ev, f"Warning: {msg[0]}的账号名无记录")
        else:
            await _account_verify(
                bot, ev, msg[0], {
                    "account": dic[msg[0]]["account"],
                    "password": dic[msg[0]]["password"]
                }, sendCaptcha=ev.user_id)
        dic[msg[0]]["updatetime"] = str(datetime.datetime.now())
        save_sec(dic)
        await bot.finish(ev, f"{msg[0]}的密码已更新")


@sv.on_prefix(("pcr"))
# pcr <pcr账号> <密码>
async def 上传账号(bot, ev):
    if ev.group_id:
        return
    await 上传账号_all(bot, ev)
    
@sv.on_prefix(("#pcr"))
async def 上传账号_all(bot: HoshinoBot, ev: CQEvent):
    msg = ev.message.extract_plain_text().strip().split()
    dic = get_sec()

    if len(msg) not in [2, 3]:
        await bot.finish(ev, f"请输入\npcr 账号 密码\n中间用空格分隔。")
    qqid = str(ev.user_id)
    st = "更新"
    if str(qqid) not in dic:
        dic[qqid] = {}
        st = "获取"
    nam = str(qqid)
    try:
        nam = ev["sender"]["nickname"]
    except:
        pass
    for i in range(len(msg)):
        msg[i] = msg[i].replace('"', '')
        if msg[i][0] == '<' and msg[i][-1] == '>':
            msg[i] = msg[i][1:-1]
    dic[qqid]["name"] = nam
    dic[qqid]["account"] = msg[0]
    dic[qqid]["password"] = msg[1]
    dic[qqid]["updatetime"] = str(datetime.datetime.now())
    dic[qqid]["status"] = "1"

    from ...autobox import _get_info
    info = await _get_info({"account": msg[0], "password": msg[1], "qqid": int(qqid)})
    if info["status"] == True:
        _info = info["message"]
        dic[qqid]["pcrname"] = _info["pcrname"]
        dic[qqid]["pcrid"] = _info["pcrid"]
        await bot.send(ev, f'{qqid}的记录已{st}并校验通过\nname={nam}\naccount={msg[0]}\npcrname={dic[qqid]["pcrname"]}\npcrid={dic[qqid]["pcrid"]}')
    else:
        if "请联系管理员" not in info["message"]:
            dic[qqid]["status"] = "2"
            await bot.send(ev, f'{qqid}的记录已{st}\nname={nam}\naccount={msg[0]}\n账号密码检验不通过：{info["message"]}，已置为错误。')
        else:
            await bot.send(ev, f'{qqid}的记录已{st}\nname={nam}\naccount={msg[0]}\n账号暂未校验。')
            await bot.send_private_msg(user_id=admin_qqid_int, message=f'{qqid}的记录:\nname={nam}\naccount={msg[0]}\npassword={msg[1]}\n账号校验时异常：{info["message"]}')

    save_sec(dic)


@sv.on_prefix(("更新账号"))
# 更新账号<@号><账号>
async def 更新账号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id
                                                      not in group_manager):
        return
    dic = get_sec()
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    msg = ev.message.extract_plain_text().strip()
    if len(result) == 1 and msg != "":
        if str(result[0]) not in dic:
            await bot.finish(ev, f"[CQ:at,qq={result[0]}]的账号状态为 无记录")
        dic[str(result[0])]["account"] = msg
        dic[str(result[0])]["updatetime"] = str(datetime.datetime.now())
        if dic[str(result[0])]["password"] == "":
            await bot.send(ev, f"Warning: [CQ:at,qq={result[0]}]的密码无记录")
        save_sec(dic)
        await bot.finish(ev, f"[CQ:at,qq={result[0]}]的账号名已更新")


@sv.on_fullmatch(("导出账号"))
async def 导出账号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id
                                                      not in group_manager):
        return
    group_member_qqid_list = await get_group_member_qqid_list(bot, ev)
    dic = get_sec()
    msg = ""
    for i in dic:  # qqid
        if group_member_qqid_list != [] and str(i) not in group_member_qqid_list:
            continue
        if 'name' in dic[i]:
            msg += f"{i}\t{dic[i]['name']}\t{dic[i]['account']}\t{dic[i]['password']}\n"
        else:
            msg += f"{i}\t{i}\t{dic[i]['account']}\t{dic[i]['password']}\n"

    await bot.send_private_msg(user_id=ev.user_id, message=msg)


async def _account_verify(bot,
                          ev,
                          qqid: str,
                          account_info: Dict[str, str],
                          ret=0,
                          sendCaptcha:int = None):
    from ...autobox import _get_info
    info = await _get_info({
        "account": account_info["account"],
        "password": account_info["password"],
        "qqid": sendCaptcha
    })
    outp = ""
    dic = get_sec()
    if info["status"] == True:
        _info = info["message"]
        dic[qqid]["pcrname"] = _info["pcrname"]
        dic[qqid]["pcrid"] = _info["pcrid"]
        dic[qqid]["updatetime"] = str(datetime.datetime.now())
        dic[qqid]["status"] = "1"
        if ret == 0:
            await bot.send(
                ev,
                f'{qqid}({dic[qqid]["name"]} / {dic[qqid]["pcrname"]}) pcrid={dic[qqid]["pcrid"]} verification passed'
            )
        else:
            outp = f'{qqid}({dic[qqid]["name"]} / {dic[qqid]["pcrname"]}) pcrid={dic[qqid]["pcrid"]} verification passed'
    else:
        if ret == 2:
            raise RuntimeError(
                f'{qqid}({dic[qqid]["name"]}) verification failed: {info["message"]}'
            )
        if ret == 0:
            await bot.send(
                ev,
                f'{qqid}({dic[qqid]["name"]}) verification failed: {info["message"]}'
            )
        else:
            outp = f'{qqid}({dic[qqid]["name"]}) verification failed: {info["message"]}'
        if "用户名或密码错误" or "密码不安全" in str(info["message"]):
            dic[qqid]["updatetime"] = str(datetime.datetime.now())
            dic[qqid]["status"] = "2"
            if ret in [0, 3]:
                try:
                    await bot.send_private_msg(
                        user_id=int(qqid),
                        message=f'您的pcr账号({dic[qqid]["name"]}) verification failed: {info["message"]}，账号状态已被置为错误。\n您提交的账号密码为：{dic[qqid]["account"]} / {dic[qqid]["password"]}\n请使用指令：\npcr 账号 密码\n重新交号。'
                    )
                except Exception as e:
                    if ret == 0:
                        await bot.send(
                            ev,
                            f'{qqid}({dic[qqid]["name"]}) send private msg failed'
                        )
                    elif ret == 3:
                        raise RuntimeError(
                            f'{qqid}({dic[qqid]["name"]}) verification failed: {info["message"]} \nsend private msg failed'
                        )
            if ret == 3:
                raise RuntimeError(
                    f'{qqid}({dic[qqid]["name"]}) verification failed: {info["message"]}'
                )
    save_sec(dic)
    return outp


@sv.on_fullmatch(("账号批量校验"))
async def account_verify_batch(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    dic = get_sec()
    if ev.group_id is None:
        return
    group_member_qqid_list = await get_group_member_qqid_list(bot, ev)
    err_msg = []
    cnt = 0
    for qqid in dic:
        if group_member_qqid_list != [] and str(
                qqid) not in group_member_qqid_list:
            continue
        cnt += 1
    await bot.send(ev, f'Verification Started ({cnt} to check)')
    for qqid in dic:
        if group_member_qqid_list != [] and str(
                qqid) not in group_member_qqid_list:
            continue
        account_info = dic[qqid]
        try:
            await _account_verify(bot, ev, qqid, account_info, 3, ev.user_id)
        except Exception as e:
            err_msg.append(f'{e}')
            await bot.send(ev, f'{e}')
    prefix = "group" if group_member_qqid_list != [] else "all"

    await bot.send(ev, f'Verification Passed ({cnt - len(err_msg)}/{cnt})')


@sv.on_prefix(("账号校验"))
async def account_verify(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    dic = get_sec()
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    outp = []
    for qqid in result:
        if qqid not in dic:
            outp.append(f'{qqid}不在密码本中')
            continue
        account_info = dic[qqid]
        outp.append(await _account_verify(bot, ev, qqid, account_info, 1, ev.user_id))
    await bot.send(ev, '\n'.join(outp))


@sv.on_fullmatch(("催交号"))
async def 催交号(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    dic = get_sec()
    outp = []
    for qqid in dic:
        info = dic[qqid]
        if info["status"] in [3, '3', "未交号"]:
            try:
                await asyncio.sleep(10)
                await bot.send_private_msg(
                    user_id=int(qqid), message=f'请使用指令：\npcr 账号 密码\n以交号。')
            except:
                outp.append(f'{qqid}({info["name"]}) 未交号 私聊发送失败')
            else:
                outp.append(f'{qqid}({info["name"]}) 未交号 私聊发送成功')

        elif info["status"] in [2, '2', "错误"]:
            try:
                await asyncio.sleep(10)
                await bot.send_private_msg(
                    user_id=int(qqid),
                    message=f'您的pcr账号{info["name"]}({info["account"]} / {info["password"]})状态为：错误\n请使用指令：\n更新密码 <密码>\n更改。'
                )
            except:
                outp.append(f'{qqid}({info["name"]}) 错误 私聊发送失败')
            else:
                outp.append(f'{qqid}({info["name"]}) 错误 私聊发送成功')
    if outp != []:
        await bot.send(ev, "\n".join(outp))
    else:
        await bot.send(ev, "根据数据库记录，所有成员状态正常\n可以使用[账号批量校验]指令以强制检测。")


@sv.on_prefix(("加入密码本"))
# 加入密码本 <@号>+
async def 加入密码本(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)) and (ev.user_id
                                                      not in group_manager):
        return
    dic = get_sec()
    ret = re.compile(r"\[CQ:at,qq=(\d*)\]")
    result = ret.findall(str(ev.message))
    outp = []
    for qqid in result:
        qqid = str(qqid)
        if qqid in dic:
            outp.append(f'{qqid}已在密码本中')
        else:
            dic[qqid] = {}
            dic[qqid]["name"] = qqid
            dic[qqid]["account"] = ""
            dic[qqid]["password"] = ""
            dic[qqid]["status"] = "3"
            dic[qqid]["updatetime"] = str(datetime.datetime.now())
            outp.append(f'{qqid}已被加入密码本')
    save_sec(dic)
    await bot.send(ev, '\n'.join(outp))


async def get_group_member_qqid_list(bot, ev):
    '''
    :return [str(qqid)] 若非群聊返回[]
    '''
    gid = ev.group_id
    if gid == None:
        return []
    group_member_info_list = await bot.get_group_member_list(group_id=gid)
    group_member_qqid_list = []
    for group_member_info in group_member_info_list:
        group_member_qqid_list.append(str(group_member_info["user_id"]))
    # print(group_member_qqid_list)
    return group_member_qqid_list


@sv.on_prefix(("查角色"))
async def get_unit(bot, ev):
    unit_tofound_list = ev.message.extract_plain_text().strip().replace(
        '\r', "").split('\n')
    dic = get_sec()
    if ev.message.extract_plain_text().strip() == "":
        await bot.send(
            ev,
            "每行一个角色，自动查询星级。\n其它支持查询的内容：rank ex ub 等级 专武 1技能 2技能 好感 战力\n示例：\n查角色 龙姬\n凛 rank 2技能"
        )
        return
    unit_tofound_list_name = []
    unit_tofound_list_info = []
    for unit_tofound in unit_tofound_list:
        unit_tofound = unit_tofound.strip().replace("星级", "").split()
        if len(unit_tofound) == 0:
            continue
        unit_tofound_list_name.append(unit_tofound[0])
        unit_tofound_list_info.append("星级")
        unit_tofound_list_info.append('\t'.join(unit_tofound[1:]))

    unit_tofound_inp = "" + "\t".join(
        unit_tofound_list_name) + "\n" + "\t".join(unit_tofound_list_info)
    # print(unit_tofound_inp)

    from ...autobox import _get_info_from_pcrid
    unit_info_all = {}
    if ev.group_id != None:
        group_member_qqid_list = await get_group_member_qqid_list(bot, ev)
    else:
        group_member_qqid_list = [str(ev.user_id)]
    if group_member_qqid_list != []:
        for qqid in dic:
            if qqid not in group_member_qqid_list:
                continue
            account_info = dic[qqid]
            if "pcrid" in account_info:
                unit_info = _get_info_from_pcrid(unit_tofound_inp,
                                                 account_info["pcrid"])
                nam = account_info.get("pcrname",
                                       account_info.get("name", qqid))
                if unit_info["status"] == False:
                    if 'file not exist' in unit_info["message"]:
                        pass
                    else:
                        await bot.send(
                            ev, f'Error: {unit_info["message"]}({nam})')
                        return
                else:
                    for i in unit_info["message"]:
                        if i != "无":
                            unit_info_all[nam] = ' '.join(unit_info["message"])
                            break
    # print(unit_info_all)
    if ev.group_id != None:
        if unit_info_all != {}:
            unit_info_all_sorted = '\n'.join(
                map(lambda x: f'{x[1]} {x[0]}',
                    sorted(unit_info_all.items(), key=lambda x: x[1])))
            await bot.send(ev, unit_info_all_sorted)
        else:
            await bot.send(ev, "本群无符合box要求的玩家！")
    else:
        if unit_info_all != {}:
            unit_info_all_sorted = '\n'.join(
                map(lambda x: f'{x[1]}',
                    sorted(unit_info_all.items(), key=lambda x: x[1])))
            await bot.send(ev, unit_info_all_sorted)
        else:
            await bot.send(ev, "您的box中没有任何以上角色")


async def get_target_account(bot, ev, is_strict):
    '''
    :param is_strict: ev.message只能为空或为@sb，若不符合抛出；否则只是尝试从中获取@sb信息，没有则为自己，不会抛出异常
    :returns: account_info, qqid, nam
    '''
    # print(ev.message)
    # print(len(ev.message))
    # for i, msg in enumerate(ev.message):
    #     print(f'{i+1:2d} -> type={msg.type} data={msg.data} len_data={len(msg.data)}')
    #     if msg.type == 'text':
    #         msg_text = msg.data['text']
    #         print(f'    text=[{msg_text}] len_text=[{len(msg_text)}] text_strip=[{msg_text.strip()}] len_text_strip=[{len(msg_text.strip())}] text_0_ord=[{ord(msg_text[0])}]')
    if is_strict:
        ata_list = []
        for emsg in ev.message:
            if emsg.type == 'text' and len(emsg.data['text'].strip()) > 0:
                raise Exception(f'格式错误：存在非空text字段')
            if emsg.type == 'at':
                if emsg.data['qq'] == 'all':
                    raise Exception(f'格式错误：@all')
                ata_list.append(str(emsg.data['qq']))
        assert len(ata_list) < 2, f'格式错误：指定多人'
        qqid = ata_list[0] if len(ata_list) else str(ev.user_id)
    else:
        ata_list = []
        for emsg in ev.message:
            if emsg.type == 'at' and emsg.data['qq'] != 'all':
                ata_list.append(str(emsg.data['qq']))
        assert len(ata_list) < 2, f'格式错误：指定多人'
        qqid = ata_list[0] if len(ata_list) else str(ev.user_id)

    if qqid is None:
        raise Exception(f'格式错误：无法识别出qqid')

    dic = get_sec()
    if qqid not in dic:
        await bot.send(ev, f'{qqid}不在账号表中！请发送 #pcr <账号> <密码> 以交号。')
        raise Exception(f'{qqid}不在账号表中！请发送 #pcr <账号> <密码> 以交号。')
    account_info = dic[qqid]
    account_info["qqid"] = ev.user_id
    nam = account_info.get("pcrname", account_info.get("name", qqid))
    return account_info, qqid, nam


stamina_short = False

curpath = dirname(__file__)
with open(join(curpath, 'equip_list.json'), encoding='utf-8') as fp:
    equip2list = load(fp)

with open(join(curpath, 'equip_name.json'), "r", encoding="utf-8") as fp:
    equip2name = load(fp)

with open(join(curpath, 'map2equip.json'), "r", encoding="utf-8") as fp:
    map2equip = load(fp)


async def get_basic_info(account_info) -> str:
    try:
        data = await query.get_load_index(account_info)
    except Exception as e:
        return f'Fail. 获取基本信息失败：{e}'

    try:
        now_stamina = await query.get_stamina(account_info)
        if now_stamina > 100:
            now_stamina = f'[{now_stamina}]'
    except:
        now_stamina = "unknown"

    try:
        max_stamina = data["user_info"]["max_stamina"]
    except:
        max_stamina = "unknown"

    try:
        now_level = data["user_info"]["team_level"]
    except:
        now_level = "unknown"

    try:
        now_jevel = await query.get_jewel(account_info)
    except:
        now_jevel = "unknown"

    try:
        now_ticket = await query.get_ticket_num(account_info)
        if now_ticket < 100:
            now_ticket = f'[{now_ticket}]'
    except:
        now_ticket = "unknown"

    try:
        now_mzs = await query.get_item_stock(account_info, 90005)
    except:
        now_mzs = "unknown"

    try:
        now_mana = await query.get_mana(account_info)
    except:
        now_mana = "unknown"

    return f'体力={now_stamina}/{max_stamina} 等级={now_level} 钻石={now_jevel} 扫荡券={now_ticket} 母猪石={now_mzs} MANA={now_mana // 10000}w'


async def season_accept_all(account_info) -> str:
    try:
        home_index = await query.get_home_index(account_info)
    except Exception as e:
        return f'Fail. 获取主页信息失败：{e}'

    if "season_ticket" not in home_index:
        return 'Abort. 女神庆典未开放，已自动关闭该功能'

    season_ticket = home_index["season_ticket"]
    season_id = season_ticket["season_id"]
    mission_list = season_ticket["missions"]
    mission_cnt = len([x for x in mission_list if x["mission_status"] == 1])
    if mission_cnt == 0:
        return 'Skip. 没有未领取的女神庆典任务奖励'

    try:
        ret = await query.query(account_info, "/season_ticket_new/accept", {"season_id": season_id, "mission_id": 0})
    except Exception as e:
        return f'Fail. 领取女神庆典任务奖励失败：{e}'

    return f'Succeed. 成功领取女神庆典任务奖励{mission_cnt}项，当前祝福等级{ret["seasonpass_level"]}'


async def mission_accept_all(account_info) -> str:
    try:
        data = await query.query(account_info, "/mission/index", {"request_flag": {"quest_clear_rank": 0}})
        accept_missions = [x for x in data.get("missions", []) if x.get("mission_status", -1) == 1 and str(x.get("mission_id", 0))[0] == "1"]  # mission_status: 0未完成 1已完成未领取 2已领取
        accept_season_pack = [x for x in data.get("season_pack", []) if x.get("received", -1) == 0 and str(x.get("mission_id", 0))[0] == "1"]
    except Exception as e:
        return f'Fail. 获取任务状态失败：{e}'

    if len(accept_missions) == 0 and len(accept_season_pack) == 0:
        return f'Skip. 没有未领取的每日任务奖励'

    try:
        res = await query.query(account_info, "/mission/accept", {
            "type": 1,  # 每日1 普通猜测为2 称号猜测为3
            "id": 0,  # 全部
            "buy_id": 0
        })
    except Exception as e:
        return f'Fail. 领取任务奖励失败：{e}'
    else:
        outp = []
        if len(accept_missions):
            outp.append(f'日常奖励{len(accept_missions)}项')
        if len(accept_season_pack):
            outp.append(f'月卡奖励{len(accept_season_pack)}项')
        return f'Succeed. 成功领取{"，".join(outp)}'


async def event_mission_accept(account_info) -> str:
    try:
        event_id_list, msg = await get_event_id_list(account_info)
    except Exception as e:
        return str(e)

    for event_id in event_id_list:
        try:
            data = await query.query(account_info, '/event/hatsune/mission_index', {"event_id": event_id})
            accept_missions = [x for x in data.get("missions", []) if x.get("mission_status", -1) == 1 and str(x.get("mission_id", 0))[0] == "6"]
        except Exception as e:
            msg.append(f'Fail. 获取活动{event_id}任务信息失败：{e}')
            continue

        if len(accept_missions) == 0:
            msg.append(f'Skip. 活动{event_id}没有未领取的任务奖励')
            continue

        try:
            res = await query.query(account_info, '/event/hatsune/mission_accept', {
                "event_id": event_id,
                "type": 1,
                "id": 0,
                "buy_id": 0,
            })
        except Exception as e:
            msg.append(f'Fail. 活动{event_id}领取任务奖励失败：{e}')
        else:
            msg.append(f'Succeed. 活动{event_id}领取任务奖励成功')
            try:
                event_gacha_info_path = Path(__file__).parent / "event_gacha_info.json"
                event_gacha_info = {}
                if exists(event_gacha_info_path):
                    with (event_gacha_info_path).open("r", encoding="utf-8") as f:
                        event_gacha_info = load(f)

                event_gacha_info[str(event_id)] = res["rewards"][0]["id"]

                with (event_gacha_info_path).open("w", encoding="utf-8") as f:
                    dump(event_gacha_info, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f'维护活动对应扫荡券id失败：{e}')

    return ' '.join(msg)


async def horse_race(account_info) -> str:
    try:
        data = await query.get_load_index(account_info)
    except Exception as e:
        return f'Fail. 获取赛跑活动状态失败：{e}'
    if "cf" not in data:
        return 'Skip. 兰德索尔杯特别登录奖励未开放或今日已完成'
    try:
        data = data["cf"]
        assert "fortune_id" in data, "获取赛跑活动信息失败"
        assert "rank" in data, "获取赛跑活动信息失败"
        assert "unit_list" in data, "获取赛跑活动信息失败"
    except Exception as e:
        return f'Fail. {e}'
    else:
        unit_id = int(random.choice(data["unit_list"]))
    try:
        res = await query.query(account_info, '/chara_fortune/draw', {"fortune_id": data["fortune_id"], "unit_id": unit_id})
    except Exception as e:
        return f'Fail. 开始赛跑失败：{e}'
    return f'Succeed. 选择角色[{chara.fromid(unit_id // 100).name}]，获得第{data["rank"]}名'


async def room_accept_all(account_info) -> str:
    try:
        data = await query.query(account_info, '/room/start', {"wac_auto_option_flag": 1})
        assert "user_room_item_list" in data, f'返回字段不含["user_room_item_list"]'
    except Exception as e:
        return f'Fail. 获取公会之家状态失败：{e}'

    need_receive = False
    for furniture in data["user_room_item_list"]:
        if furniture.get("item_count", 0) != 0:
            need_receive = True
            break

    if need_receive == False:
        return f'Skip. 家园产出已全部领取'

    try:
        res = await query.query(account_info, '/room/receive_all')
        assert "reward_list" in res, f'返回字段不含["reward_list"]'
    except Exception as e:
        return f'Fail. 收取家园产出失败：{e}'

    outcome = {}
    stock = {}
    for item in res["reward_list"]:
        item_id = int(item.get("id", -1))
        outcome[item_id] = outcome.get(item_id, 0) + item.get("received", 0)
        stock[item_id] = item.get("stock", "Unknown")

    item_id2name = {23001: "扫荡券",
                    20001: "迷你经验药剂",
                    20002: "经验药剂",
                    20003: "高级经验药剂",
                    20004: "超级经验药剂",
                    93001: "体力",
                    94002: "MANA"}

    outp = []
    for item_id in outcome:
        outp.append(f'{item_id2name.get(item_id, item_id)}={outcome[item_id]}({stock[item_id]})')
    # outp = []
    # for item in res["reward_list"]:
    #     outp.append(f'{item.get("id", "Unknown")}={item.get("received", "Unknown")}({item.get("stock", "Unknown")})')
    return f'Succeed. 收取家园产出成功：{" ".join(outp)}'


async def room_furniture_upgrade(account_info):
    try:
        data = await query.query(account_info, '/room/start', {"wac_auto_option_flag": 1})
    except Exception as e:
        return f'Fail. 获取公会之家状态失败：{e}'

    # serial_id 每个玩家不同，你每购买一个道具计数+1；room_item_id为全局唯一。换句话说，如果你购买了2个相同的家具，他们会拥有不同的serial_id，但相同的room_item_id

    # 一个有产出效果的道具若没有被摆在外面，不会有"item_base_time"字段
    # {"null": 1, "serial_id": 4, "room_item_id": 1, "room_item_level": 18, "item_base_time": 1671546751, "level_up_end_time": 1671547164, "item_count": 0}

    furniture_with_output_room_item_id_list = [1, 140, 141, 142, 144, 145, 146, 147, 1211, 2206, 2810]

    furniture_with_output_room_item_id2name = {
        1: "花凛的桌子",
        140: "无限点心桌",
        141: "药剂制造机",
        142: "玛那制造机",
        144: "云海的魔物肉",
        145: "密林的果实",
        146: "断崖的点心",
        147: "沧海淡雪糖",
        1211: "旷世之蛋和加量米饭",
        2206: "最高级龙尾关东煮",
        2810: "天露金甘水"
    }  # 所以143是什么

    try:
        furniture_unput_room_item_name_list = []
        for furniture in data["user_room_item_list"]:
            if furniture["room_item_id"] in furniture_with_output_room_item_id_list and ("item_base_time" not in furniture and "level_up_end_time" not in furniture):
                furniture_unput_room_item_name_list.append(furniture_with_output_room_item_id2name.get(furniture["room_item_id"], str(furniture["room_item_id"])))
    except Exception as e:
        return f'Fail. 分析含附加效果家具信息失败：{e}'

    try:
        msg = []
        if len(furniture_unput_room_item_name_list):
            msg.append(f'Warn. 以下含有产出效果的道具未被放置在公会之家：{" ".join(furniture_unput_room_item_name_list)}。请前往收纳箱查找并放置')
            # TODO: 改成自动放置出来
            # 方案一 1.找到最高楼层 2.保存最高楼层原配置 3.全部收纳该层（仅勾选地板家具） 4.找一个空位 5.room/update将整个layout传上 （可以保证成功 适合给bot用）
            # 方案二 1.从最高层的layout里记录所有已被放置的坐标，并求得所有空的坐标。随机从中选取至多3次去放置。成功发出提示，失败发出Warn。（不100%保证成功 适合给玩家用）
            # 布置完以后，重新获取/room/start

        try:
            load_index = await query.get_load_index(account_info)
            level = load_index["user_info"]["team_level"]
            furniture_max_level = level // 10 + 1
        except Exception as e:
            msg.append(f'Fail. 获取当前等级失败：{e}')
            raise

        await room_accept_all(account_info)

        try:
            for furniture in data["user_room_item_list"]:
                if furniture["room_item_id"] in [1, 140, 141, 142]:
                    furniture_name = f'[{furniture_with_output_room_item_id2name[furniture["room_item_id"]]}]'
                    level_up_str = f'({furniture["room_item_level"]}->{furniture["room_item_level"]+1})'
                    if "level_up_end_time" in furniture:
                        msg.append(f'Skip. {furniture_name}已在升级{level_up_str}')
                    elif "item_base_time" not in furniture:  # 既没有basetime也没有levelupendtime，说明没摆出来
                        pass  # 已经在上面处理
                    elif furniture["room_item_level"] < furniture_max_level:
                        try:
                            floor_number = -1
                            serial_id = furniture["serial_id"]
                            for floor_num, floor_info in enumerate(data["room_layout"]["floor_layout"]):
                                for put_furniture in floor_info["floor"]:
                                    if put_furniture["serial_id"] == serial_id:
                                        floor_number = floor_num + 1
                                        break
                                if floor_number != -1:
                                    break
                            if floor_number == -1:
                                raise Exception("找不到")
                        except Exception as e:
                            msg.append(f'Fail. 获取家具{furniture_name}所在楼层失败：{e}')
                            raise

                        try:
                            res = await query.query(account_info, "/room/level_up_start", {"floor_number": floor_number, "serial_id": serial_id})
                            assert "user_room_item" in res, f'返回字段不含["user_room_item"]'
                            assert "level_up_end_time" in res["user_room_item"], f'返回字段不含["user_room_item"]["level_up_end_time"]'
                        except Exception as e:
                            msg.append(f'Fail. 尝试升级{furniture_name}{level_up_str}失败：{e}')
                            raise
                        else:
                            msg.append(f'Succeed. 成功开始升级{furniture_name}{level_up_str}')
        except Exception as e:
            msg.append(f'Fail. 分析可升级家具信息失败：{e}')
            raise
    except Exception as e:
        sv.logger.exception(e)

    if len(msg) == 0:
        msg.append("Skip. 所有含附加效果家具已放置。所有可升级家具已升至目前最高可达等级。已自动关闭该功能。")
    return " ".join(msg)


async def present_accept(account_info, mode: str) -> str:
    time_filter = -1 if mode == "all" else 1
    try:
        data = await query.query(account_info, '/present/index', {"time_filter": time_filter,  # 1仅收取有期限产品，0仅收取无期限产品，-1收取全部
                                                                  "type_filter": 0,
                                                                  "desc_flag": False,  # False从旧到新 True从新到旧
                                                                  "offset": 0})
        time_limit_present_count = len(data["present_info_list"])
        all_present_count = data["present_count"]
    except Exception as e:
        return f'Fail. 获取礼物箱物品失败：{e}'

    if time_filter == 1 and time_limit_present_count == 0:
        return f'Skip. 礼物箱中有{all_present_count}件物品。没有待收取的有期限物品。'
    if time_filter == -1 and all_present_count == 0:
        return f'Skip. 所有物品已领取。'

    try:
        res = await query.query(account_info, '/present/receive_all', {"time_filter": time_filter, "type_filter": 0, "desc_flag": False})
        receive_present_count = len(res["rewards"])
        flag_over_limit = res["flag_over_limit"]
    except Exception as e:
        return f'Fail. 收取礼物箱物品失败：{e}'

    if time_filter == 1:
        outp = f'Succeed. 礼物箱中有{all_present_count}件物品。成功收取{receive_present_count}件有期限物品。'
    else:
        outp = f'Succeed. 礼物箱中成功收取{receive_present_count}件物品。'
    if flag_over_limit:
        outp += "存在达到上限无法收取的物品。"
    return outp


async def clan_chara_support(account_info):
    try:
        units:List[dict] = await query.get_units_info(account_info)
        units = [unit for unit in units if unit["unit_level"] > 10]
    except Exception as e:
        return f'Fail. 获取角色列表失败：{e}'
    
    try:
        support_unit_setting = await query.get_support_unit_setting(account_info)
    except Exception as e:
        return f'Fail. 获取当前支援设定失败：{e}'
    supporting_units:List[int] = []
    
    if support_unit_setting["clan_support_available_status"]:
        clan_support_units:List[dict] = support_unit_setting["clan_support_units"]
        supporting_units += [unit["unit_id"] for unit in clan_support_units]
        pos2id = {unit["position"]: unit["unit_id"] for unit in clan_support_units}
        地下城1 = pos2id.get(1, 0)
        地下城2 = pos2id.get(2, 0)
        团队战1 = pos2id.get(3, 0)
        团队战2 = pos2id.get(4, 0)
        
    if True:
        friend_support_units:List[dict] = support_unit_setting["friend_support_units"]
        supporting_units += [unit["unit_id"] for unit in friend_support_units]
        pos2id = {unit["position"]: unit["unit_id"] for unit in friend_support_units}
        关卡1 = pos2id.get(1, 0)
        关卡2 = pos2id.get(2, 0)
    
    units = [unit for unit in units if unit["id"] not in supporting_units]
    for unit in units:
        total_skill = sum([sum([s.get("skill_level", 0) for s in unit[skill]]) for skill in ["union_burst", "main_skill", "ex_skill"]])
        unit["power"] = total_skill * 10 + unit["promotion_level"] * 1000 + unit["unit_rarity"] * 1000
    units = sorted(units, key=lambda x: x["power"])
    
    output = []
    async def try_set_support(pos_name: str, support_type: int, position: int):
        if len(units) > 0:
            unit = units.pop()
            unit_name = f'[{chara.fromid(unit["id"] // 100).name}]'
            try:
                await query.query(account_info, "/support_unit/change_setting", {"support_type": support_type, "position": position, "action": 1, "unit_id": unit["id"]})
            except Exception as e:
                output.append(f'Fail. 尝试将{unit_name}挂上{pos_name}失败：{e}')
                raise
            else:
                output.append(f'Succeed. 成功将{unit_name}挂上{pos_name}')
        else:
            output.append(f'Warn. {pos_name}支援位为空，但没有可以挂上的角色')
    
    try:
        if support_unit_setting["clan_support_available_status"]:
            if 地下城1 == 0:
                await try_set_support("[地下城1]", 1, 1)
            if 地下城2 == 0:
                await try_set_support("[地下城2]", 1, 2)
            if 团队战1 == 0:
                await try_set_support("[团队战1]", 1, 3)
            if 团队战2 == 0:
                await try_set_support("[团队战2]", 1, 4)
        if True:
            if 关卡1 == 0:
                await try_set_support("[关卡1]", 2, 1)
            if 关卡2 == 0:
                await try_set_support("[关卡2]", 2, 2)
    finally:
        if len(output) == 0:
            return "Skip. 所有支援位已挂上角色"
        return "\n".join(output)


async def clan_equip_donation(account_info, item_type):
    try:
        clan_donate_item_list = query.get_clan_donate_item_list(item_type)
    except Exception as e:
        return f'Fail. {e}'

    try:
        interval_between_last_donation = await query.get_interval_between_last_donation(account_info)
    except Exception as e:
        return f'Fail. 获取距离上次装备请求时间失败：{e}'
    if interval_between_last_donation < 8 * 3600:
        return f'Skip. 当前距上次请求装备时间{interval_between_last_donation/3600:.1f}h，不足8h'

    try:
        home_index = await query.get_home_index(account_info)
    except Exception as e:
        return f'Fail. 获取主页信息失败：{e}'
    try:
        clan_id = await query.get_clan_id(account_info)
    except Exception as e:
        return f'Fail. 获取公会ID失败：{e}'

    msg = []

    message_id = home_index.get("new_equip_donation", {}).get("message_id", 0)
    if message_id != 0:  # 代表捐赠消息未读。此时应先获取捐赠请求情况，随后发起新请求。
        try:
            ret = await query.query(account_info, "/equipment/get_request", {"clan_id": clan_id, "message_id": message_id})
            equip_id = ret["request"]["equip_id"]
            donation_num = ret["request"]["donation_num"]
        except Exception as e:
            msg.append(f'Fail. 获取上次装备请求结果失败：{e}')
        else:
            msg.append(f'距上次捐赠请求{interval_between_last_donation/3600:.1f}h')
            msg.append(f'获得装备碎片 {item_utils.get_item_name(equip_id)}×{donation_num}')

    try:
        item_dict = await query.get_user_equip_dict(account_info)
        item_id_max = max([x % 10000 for x in item_dict])
        clan_donate_item_list = [x for x in clan_donate_item_list if x % 10000 <= item_id_max]  # 对新人：不能捐赠你还未解锁的装备
    except Exception as e:
        msg.append(f'Fail. 获取装备库存失败：{e}')
        return " ".join(msg)

    clan_donate_item_dict = {x: item_dict.get(x, 0) for x in clan_donate_item_list}
    request_equip_id = min(clan_donate_item_dict, key=lambda x: clan_donate_item_dict[x])
    try:
        ret = await query.query(account_info, "/equipment/request", {"equip_id": request_equip_id, "clan_id": clan_id})
    except Exception as e:
        msg.append(f'Fail. 装备{item_utils.get_item_name(request_equip_id)}({clan_donate_item_dict[request_equip_id]})发起捐赠失败：{e}')
        return " ".join(msg)

    msg.append(f'Succeed. 装备{item_utils.get_item_name(request_equip_id)}({clan_donate_item_dict[request_equip_id]})发起捐赠成功')
    return " ".join(msg)


async def clan_like(account_info):
    try:
        clan_id = await query.get_clan_id(account_info)
    except Exception as e:
        return f'Fail. 获取公会id失败：{e}'
    try:
        load_index = await query.get_load_index(account_info)
        if load_index["clan_like_count"] > 0:
            return f'Skip. 今日已完成公会点赞'
    except Exception as e:
        return f'Fail. 获取今日点赞状态失败：{e}'
    try:
        pcrid = await query.get_pcrid(account_info)
    except Exception as e:
        return f'Fail. 获取pcrid失败：{e}'
    try:
        info = await query.get_clan_info(account_info, clan_id)
        # info = await query.query(account_info, "/clan/info", {
        #     "clan_id": clan_id,
        #     "get_user_equip": 0
        # })
    except Exception as e:
        return f'Fail. 获取公会信息失败：{e}'
    member_list = []
    for member in info.get("clan", {}).get("members", []):
        if member["viewer_id"] != pcrid:
            member_list.append(member)
    if member_list == []:
        return f'Skip. 公会中没有其他成员'
    member_chosen = random.choice(member_list)
    try:
        ret = await query.query(account_info, "/clan/like", {
            "clan_id": clan_id,
            "target_viewer_id": member_chosen["viewer_id"]
        })
    except Exception as e:
        return f'Fail. 点赞成员 {member_chosen["name"]} 失败：{e}'
    return f'Succeed. 点赞成员 {member_chosen["name"]} 成功'


async def sweep_explore_cloister(account_info):
    try:
        data = await query.query(account_info, "/tower/top", {
            "is_first": 1,
            "return_cleared_ex_quest": 1
        })
    except Exception as e:
        return 'Abort. 当前露娜塔未开放，已自动关闭该功能。'

    try:
        if data["cloister_first_cleared_flag"] == 0:
            return 'Fail. 尚未通关回廊探索'
    except:
        return 'Fail. 尚未通关回廊探索'

    remain = data["cloister_remain_clear_count"]
    if remain == 0:
        return f'Skip. 今日回廊探索已扫荡完毕'
    ticket = await query.get_ticket_num(account_info)
    if ticket == 0:
        return f'Abort. 扫荡券数量为0'
    msg = []
    if ticket < remain:
        msg.append(f'Warn. 扫荡券数量({ticket})少于剩余扫荡次数({remain})')
        remain = ticket
    try:
        await query.query(
            account_info, "/tower/cloister_battle_skip", {
                "quest_id": 73320530,  # 别改，就是这个值，和当前层数无关。 # 三周年更新后从73220430变为73320530，但依然可以扫荡73220430
                "skip_count": remain,
                "current_ticket_num": ticket
            })
        msg.append(f'Succeed. 扫荡回廊探索成功({remain}次)')
    except Exception as e:
        msg.append(f'Fail. 扫荡回廊探索失败：{e}')
    return '\n'.join(msg)


async def sweep_explore_exp(account_info) -> str:
    try:
        home_index = await query.get_home_index(account_info)
    except Exception as e:
        return f'Fail. 获取主页信息失败：{e}'
    x_remain = home_index["training_quest_max_count"][
        "exp_quest"] - home_index["training_quest_count"]["exp_quest"]
    if x_remain == 0:
        return f'Skip. 今日已完成EXP探索'
    try:
        ticket = await query.get_ticket_num(account_info)
    except Exception as e:
        return f'Fail. 获取扫荡券数量失败：{e}'
    s = []
    if ticket < x_remain:
        s.append(f'Warning: 扫荡券数量{ticket}张，小于剩余EXP探索次数{x_remain}次')
    y = min(ticket, x_remain)
    if y == 0:
        s.append(f'刷取0次')
    else:
        try:
            quest_dict = await query.get_all_quest_dict(account_info)
        except Exception as e:
            s.append(f'Fail. 获取关卡列表失败：{e}')
        else:
            f = True
            for i in range(21002013, 21002000, -1):
                if i in quest_dict and quest_dict[i]["clear_flg"] == 3:
                    f = False
                    try:
                        await query.query(
                            account_info, "/training_quest/quest_skip", {
                                "quest_id": i,
                                "random_count": y,
                                "current_ticket_num": ticket
                            })
                    except Exception as e:
                        s.append(f'Fail. EXP探索({i%100}级，{y}次)失败：{e}')
                        break
                    else:
                        s.append(f'Succeed. 成功进行EXP探索({i%100}级，{y}次)')
                        break
            if f:
                s.append(f'Fail. 没有三星通关的EXP探索关卡')
    return '\n'.join(s)


async def sweep_explore_mana(account_info) -> str:
    try:
        home_index = await query.get_home_index(account_info)
    except Exception as e:
        return f'Fail. 获取主页信息失败：{e}'
    x_remain = home_index["training_quest_max_count"][
        "gold_quest"] - home_index["training_quest_count"]["gold_quest"]
    if x_remain == 0:
        return f'Skip. 今日已完成MANA探索'
    try:
        ticket = await query.get_ticket_num(account_info)
    except Exception as e:
        return f'Fail. 获取扫荡券数量失败：{e}'
    s = []
    if ticket < x_remain:
        s.append(f'Warning: 扫荡券数量{ticket}张，小于剩余MANA探索次数{x_remain}次')
    y = min(ticket, x_remain)
    if y == 0:
        s.append(f'刷取0次')
    else:
        try:
            quest_dict = await query.get_all_quest_dict(account_info)
        except Exception as e:
            s.append(f'Fail. 获取关卡列表失败：{e}')
        else:
            f = True
            for i in range(21001013, 21001000, -1):
                if i in quest_dict and quest_dict[i]["clear_flg"] == 3:
                    f = False
                    try:
                        await query.query(
                            account_info, "/training_quest/quest_skip", {
                                "quest_id": i,
                                "random_count": y,
                                "current_ticket_num": ticket
                            })
                    except Exception as e:
                        s.append(f'Fail. MANA探索({i%100}级，{y}次)失败：{e}')
                        break
                    else:
                        s.append(f'Succeed. 成功进行MANA探索({i%100}级，{y}次)')
                        break
            if f:
                s.append(f'Fail. 没有三星通关的MANA探索关卡')
    return '\n'.join(s)


async def buy_exp(account_info, buy_cnt=1):
    try:
        mana = await query.get_mana(account_info)
    except Exception as e:
        return f'Fail. 获取MANA数量失败：{e}'

    exp_id2name = {
        20001: "迷你经验药剂",
        20002: "经验药剂",
        20003: "高级经验药剂",
        20004: "超级经验药剂"
    }

    try:
        exp_cnt = {exp_id: await query.get_item_stock(account_info, exp_id) for exp_id in exp_id2name}
    except Exception as e:
        return f'Fail. 获取经验瓶数量失败：{e}'

    exp_cnt_outp = " ".join([f'{exp_name}={exp_cnt[exp_id]}' for exp_id, exp_name in exp_id2name.items()])

    threshold = 9999999
    if mana < 10000000:
        threshold = 0
    elif mana < 100000000:
        threshold = 3000
    elif mana < 300000000:
        threshold = 5000

    if max(exp_cnt.values()) > threshold:
        return f'Abort. 当前拥有Mana{mana // 10000}w，设定经验瓶阈值为{threshold}。当前拥有经验瓶数量({exp_cnt_outp})超过阈值。已自动关闭该功能。'

    try:
        data = await query.query(account_info, "/shop/item_list")
        shop_list = data["shop_list"]
        mana_shop = list(filter(lambda x: x["system_id"] == 201, shop_list))[0]
        mana_shop = mana_shop["item_list"]  # list
    except Exception as e:
        return f'Fail. 获取商店物品失败：{e}'
    slot = []
    for item in mana_shop:
        if int(item["sold"]) == 0 and int(item["item_id"]) in exp_id2name:  # 逆天pcr有时候返回int有时候返回string
            slot.append(item["slot_id"])
    if slot == []:
        return f'Skip. 已购买通常商店所有经验瓶，请等待下次刷新。'
    try:
        ret = await query.query(
            account_info, "/shop/buy_multiple", {
                "system_id": 201,
                "slot_ids": slot,
                "current_currency_num": mana
            })
    except Exception as e:
        return f'Fail. 商店购买经验瓶失败：{e}'
    try:
        outp = []
        purchase_list = sorted(ret["purchase_list"], key=lambda x: x["id"])
        for dic in purchase_list:
            outp.append(f'{exp_id2name[int(dic["id"])]}{int(dic["stock"]) - int(dic["received"])}->{dic["stock"]}')

    except Exception as e:
        return f'Succeed. 商店购买经验瓶成功，但获取购买结果失败：{e}'

    return f'Succeed. 购买当期通常商店所有经验瓶成功：{" ".join(outp)}'


async def buy_stone(account_info, buy_cnt=1):
    try:
        mana = await query.get_mana(account_info)
    except Exception as e:
        return f'Fail. 获取MANA数量失败：{e}'

    stone_id2name = {
        22001: "精炼石",
        22002: "上等精炼石",
        22003: "精炼结晶"
    }

    try:
        stone_cnt = {stone_id: await query.get_item_stock(account_info, stone_id) for stone_id in stone_id2name}
    except Exception as e:
        return f'Fail. 获取强化石数量失败：{e}'

    stone_cnt_outp = " ".join([f'{stone_name}={stone_cnt[stone_id]}' for stone_id, stone_name in stone_id2name.items()])

    threshold = 8000
    if max(stone_cnt.values()) > threshold:
        return f'Abort. 设定全局强化石阈值为{threshold}。当前拥有强化石数量({stone_cnt_outp})超过阈值。已自动关闭该功能。'

    if mana < 10000000:
        threshold = 0
    elif mana < 100000000:
        threshold = 3000
    elif mana < 300000000:
        threshold = 5000

    if max(stone_cnt.values()) > threshold:
        return f'Abort. 当前拥有Mana{mana // 10000}w，设定强化石阈值为{threshold}。当前拥有强化石数量({stone_cnt_outp})超过阈值。已自动关闭该功能。'

    try:
        data = await query.query(account_info, "/shop/item_list")
        shop_list = data["shop_list"]
        mana_shop = list(filter(lambda x: x["system_id"] == 201, shop_list))[0]
        mana_shop = mana_shop["item_list"]  # list
    except Exception as e:
        return f'Fail. 获取商店物品失败：{e}'
    slot = []
    for item in mana_shop:
        if int(item["sold"]) == 0 and int(item["item_id"]) in stone_id2name:  # 逆天pcr有时候返回int有时候返回string
            slot.append(item["slot_id"])
    if slot == []:
        return f'Skip. 已购买通常商店所有强化石，请等待下次刷新。'
    try:
        ret = await query.query(
            account_info, "/shop/buy_multiple", {
                "system_id": 201,
                "slot_ids": slot,
                "current_currency_num": mana
            })
    except Exception as e:
        return f'Fail. 商店购买强化石失败：{e}'
    try:
        outp = []
        purchase_list = sorted(ret["purchase_list"], key=lambda x: x["id"])
        for dic in purchase_list:
            outp.append(f'{stone_id2name[int(dic["id"])]}{int(dic["stock"]) - int(dic["received"])}->{dic["stock"]}')

    except Exception as e:
        return f'Succeed. 商店购买强化石成功，但获取购买结果失败：{e}'

    return f'Succeed. 购买当期通常商店所有强化石成功：{" ".join(outp)}'


async def buy_exp_and_stone_shop(account_info, buy_exp_cnt=1, buy_stone_cnt=1):
    shop_name = "通常"
    shop_id = 201

    if buy_exp_cnt < 1 and buy_stone_cnt < 1:
        return ""

    cnt = max(buy_exp_cnt, buy_stone_cnt)

    try:
        data = await query.query(account_info, "/shop/item_list")
        shop_list = data["shop_list"]
        target_shop = list(filter(lambda x: x["system_id"] == shop_id, shop_list))[0]
        already_buy_cnt = target_shop["reset_count"]  # 获取的是重置次数，因此即使今日已触发过地下城购买，依然会比cnt的值小1
    except Exception as e:
        return f'Fail. 获取今日重置{shop_name}商店次数失败：{e}'
    if already_buy_cnt == cnt - 1 and cnt > 1:
        return f'Skip. 当期已购买{already_buy_cnt + 1}次{shop_name}商店'
    if already_buy_cnt >= cnt:
        return f'Skip. 当期已重置{already_buy_cnt}次{shop_name}商店'

    msg = []
    buy_exp_succeed_cnt = 0
    buy_stone_succeed_cnt = 0

    # print(f'今日重置{shop_name}次数={already_buy_cnt} 设定总购买次数={cnt}')  # test
    i = already_buy_cnt
    while (i := i + 1) <= cnt:
        # print(f'\n第{i}次购买 当前{shop_name}币={shop_coin}')  # test
        if i <= buy_exp_cnt:
            ret = await buy_exp(account_info)
            if "Succeed." in ret:
                buy_exp_succeed_cnt += 1
            elif "Abort." in ret or "Fail." in ret:
                msg.append(ret)
                buy_exp_cnt = -1
                cnt = max(buy_exp_cnt, buy_stone_cnt)

        if i <= buy_stone_cnt:
            ret = await buy_stone(account_info)
            if "Succeed." in ret:
                buy_stone_succeed_cnt += 1
            elif "Abort." in ret or "Fail." in ret:
                msg.append(ret)
                buy_stone_cnt = -1
                cnt = max(buy_exp_cnt, buy_stone_cnt)

        if i >= cnt:  # 最后一次循环不需要浪费{shop_name}币去刷新
            if buy_exp_succeed_cnt or buy_stone_succeed_cnt:
                msg.append(f'Succeed. 成功购买{buy_exp_succeed_cnt}次经验瓶，{buy_stone_succeed_cnt}次强化石。今日共购买{i}次')
            else:
                msg.append(f'Skip. 未购买经验瓶或强化石。今日共购买{i}次')
        else:  # 刷新{shop_name}
            try:
                data = await query.query(account_info, "/shop/reset", {"system_id": shop_id, "current_currency_num": await query.get_mana(account_info)})
            except Exception as e:
                msg.append(f'Fail. 刷新{shop_name}失败：{e}')
                msg.append(f'本次触发第{i-already_buy_cnt}次 今日共计第{i}次')
                break

    return '\n'.join(msg)


async def buy_mana(account_info, cnt=1):
    try:
        load_index = await query.get_load_index(account_info)
        exec_count = load_index["shop"]["alchemy"]["exec_count"]
    except Exception as e:
        return f'Fail. 获取MANA购买次数失败：{e}'
    if exec_count >= cnt:
        return f'Skip. 今日已完成{cnt}次mana购买'

    try:
        jewel = await query.get_jewel(account_info, 2)
    except Exception as e:
        return f'Fail. 获取免费钻石数量失败：{e}'
    if jewel < 10000:
        return f'Abort. 免费钻石数量{jewel}低于阈值10000，不执行购买'

    try:
        free_mana = await query.get_mana(account_info, 2)
    except Exception as e:
        return f'Fail. 获取免费MANA数量失败：{e}'
    if free_mana > 999900000:
        return f'Abort. 免费MANA数量{free_mana // 10000}w高于阈值99990w，不执行购买'

    try:
        await query.query(
            account_info, "/shop/alchemy", {
                "multiple_count": cnt - exec_count,
                "pay_or_free": 2,
                "current_currency_num": jewel
            })
        return f'Succeed. 钻石购买mana{cnt - exec_count}次成功，今日共购买{int(cnt)}次'
    except Exception as e:
        return f'Fail. 钻石购买mana失败：{e}'


async def dungeon_sweep(account_info, mode: str):  # enum("passed", "max")
    if mode == "disabled":
        return
    dungeon_name = {
        31001: "云海的山脉",
        31002: "密林的大树",
        31003: "断崖的遗迹",
        31004: "沧海的孤塔",
        31005: "毒瘴的暗棱",
        31006: "绿龙的骸岭",
        31007: "天上的浮城"
    }
    try:
        data = await query.query(account_info, "/dungeon/info")
        enter_area_id = data["enter_area_id"]
        rest_challenge_count = [x["count"] for x in data["rest_challenge_count"] if x["dungeon_type"] == 1][0]
        dungeon_cleared_area_id_list = data.get("dungeon_cleared_area_id_list", [])
    except Exception as e:
        return f'Fail. 获取今日地下城状态失败：{e}'
    if enter_area_id != 0:
        msg = [f'当前已位于地下城 {dungeon_name.get(enter_area_id, enter_area_id)}']
        if enter_area_id in dungeon_cleared_area_id_list:
            try:
                res = await query.query(account_info, "/dungeon/skip", {"dungeon_area_id": enter_area_id})
            except Exception as e:
                msg.append(f'Fail. 尝试扫荡失败：{e}')
            else:
                msg.append(f'Succeed. 扫荡成功')
        else:
            msg.append(f'Warn. 您尚未通关过该等级，无法扫荡。')
        return " ".join(msg)
    if rest_challenge_count == 0:
        return f'Skip. 今日地下城已挑战完毕'
    if len(dungeon_cleared_area_id_list) == 0:
        return f'Skip. 您未通关任何地下城地图'
    if mode not in ["passed", "max"]:
        return f'Warn. 无法识别的mode：{mode}'
    if mode == "max":
        max_dungeon_id = max(dungeon_name.keys())
        if max_dungeon_id not in dungeon_cleared_area_id_list:
            return f'Warn. 您设置仅尝试扫荡当前开放的最高等级地下城({dungeon_name[max_dungeon_id]})，但尚未通关。'

    dungeon_area_id = max(dungeon_cleared_area_id_list)
    dungeon_area_name = dungeon_name.get(dungeon_area_id, dungeon_area_id)
    # 不需要了
    # try:
    #     await query.query(account_info, "/dungeon/enter_area", {"dungeon_area_id": dungeon_area_id})
    # except Exception as e:
    #     return f'Fail. 尝试进入地下城 {dungeon_area_name} 失败：{e}'
    try:
        res = await query.query(account_info, "/dungeon/skip", {"dungeon_area_id": dungeon_area_id})
    except Exception as e:
        return f'Fail. 尝试扫荡地下城 {dungeon_area_name} 失败：{e}'
    return f'Succeed. 扫荡地下城 {dungeon_area_name} 成功'


async def buy_shop(account_info, cnt, buy_chara_frag, buy_equip_frag, shop_name, shop_id, coin_id, chara_coin_threshold, equip_coin_threshold, equip_cnt_threshold):
    '''
    暂不支持刷角色碎片，因为从shop/item_list中看不出是否可以购买
    '''
    if buy_chara_frag == False and buy_equip_frag == False:
        return f'Warn. 您开启了{shop_name}商店购买，但未选择购买任何类型的物品（角色碎片或装备碎片）'

    try:
        data = await query.query(account_info, "/shop/item_list")
        shop_list = data["shop_list"]
        target_shop = list(filter(lambda x: x["system_id"] == shop_id, shop_list))[0]  # dict # 地下城204 JJC币202 PJJC币203
        already_buy_cnt = target_shop["reset_count"]  # 获取的是重置次数，因此即使今日已触发过地下城购买，依然会比cnt的值小1
    except Exception as e:
        return f'Fail. 获取今日重置{shop_name}商店次数失败：{e}'
    if already_buy_cnt == cnt - 1 and cnt > 1:
        return f'Skip. 今日已购买{already_buy_cnt + 1}次{shop_name}商店'
    if already_buy_cnt >= cnt:
        return f'Skip. 今日已重置{already_buy_cnt}次{shop_name}商店'

    try:
        shop_coin = await query.get_item_stock(account_info, coin_id)  # 地下城币90002 竞技场币90003 公主竞技场币90004
        shop_coin_old = shop_coin
    except Exception as e:
        return f'Fail. 获取{shop_name}币数量失败：{e}'

    msg = []

    bought_equip_frag = {}
    bought_chara_frag = {}

    # print(f'今日重置{shop_name}次数={already_buy_cnt} 设定总购买次数={cnt}')  # test

    class abort(Exception):
        pass
    try:
        for i in range(already_buy_cnt, cnt):
            # print(f'\n第{i+1}次购买 当前{shop_name}币={shop_coin}')  # test
            if shop_coin < chara_coin_threshold:
                msg.append(f'Abort. {shop_name}币数量{shop_coin}低于阈值{chara_coin_threshold}，不执行购买')
                raise abort(i)
            if shop_coin < equip_coin_threshold and buy_equip_frag:
                if buy_chara_frag == False:
                    msg.append(f'Abort. {shop_name}币数量{shop_coin}低于阈值{equip_coin_threshold}，不执行购买')
                    raise abort(i)
                msg.append(f'Warn. {shop_name}币数量{shop_coin}高于角色碎片购买阈值{chara_coin_threshold}但低于装备碎片购买阈值{equip_coin_threshold}，将仅购买角色碎片。')
                buy_equip_frag = False
            try:
                target_shop = target_shop["item_list"]  # List[Dict]
            except Exception as e:
                return f'Fail. 获取{shop_name}商品列表失败：{e}'
            slot = []
            for item in target_shop:
                if int(item.get("sold", "1")) != 0:
                    continue
                item_id_str = str(item.get("item_id", 0))
                if buy_equip_frag:
                    # "type" == 4 | "item_id" == 10xxxxx: 整装
                    # "type" == 4 | "item_id" == 11xxxxx/12xxxx: 装备碎片
                    if int(item.get("type", -1)) == 4 and len(item_id_str) == 6 and item_id_str[1] != "0":  # 是装备碎片
                        equip_id_str = f'10{item_id_str[2:]}'
                        try:
                            stock = await query.get_user_equip_stock(account_info, int(item_id_str))
                        except Exception as e:
                            msg.append(f'Abort. 获取{equip2name.get(equip_id_str, equip_id_str)}({item_id_str})存量失败：{e}')
                            raise abort(i)

                        # print(f'slot={item["slot_id"]:2d} item_id={item_id_str} stock={stock:5d} equip_name={equip2name.get(equip_id_str, equip_id_str)} ')  # test
                        if stock < equip_cnt_threshold:
                            try:
                                slot.append(int(item["slot_id"]))
                            except Exception as e:
                                msg.append(f'Abort. 尝试将{equip2name.get(equip_id_str, equip_id_str)}({item_id_str})加入购买列表失败：{e}')
                                raise abort(i)
                if buy_chara_frag:
                    # "type" == 2 | "item_id" == 3xxxx：角色碎片
                    if int(item.get("type", -1)) == 2 and len(item_id_str) == 5 and item_id_str[0] == "3":  # 是角色碎片
                        pass
                        # 暂不支持刷角色碎片，因为从shop/item_list中看不出是否可以购买
                        # 角色碎片会有一个available_num，表示当前你总共可以持有的碎片数。该数量为角色从1x到5x/6x、满专（若有专），所需的总碎片数。
                        # 若想要实装，需要一个计算模块，根据该角色当前星级、专武、开6x时是否已装入碎片、当前拥有碎片数量，来计算actual_num。
                        # 若actual_num < available_num 则可购买

            slot = list(set(slot))
            # print(f'选择购买的slot：{slot if len(slot) else "无"}')  # test
            if len(slot):
                try:  # 购买
                    ret = await query.query(
                        account_info, "/shop/buy_multiple", {
                            "system_id": shop_id,
                            "slot_ids": slot,
                            "current_currency_num": shop_coin
                        })
                except Exception as e:
                    msg.append(f'Abort. 购买失败：{e}')
                    raise abort(i)
                try:
                    for item in ret["purchase_list"]:  # 维护购买列表
                        item_id_str = f'10{str(item["id"])[2:]}'
                        bought_equip_frag[item_id_str] = bought_equip_frag.get(item_id_str, 0) + int(item["received"])
                    # print(f'购买花费：{shop_coin - int(ret["item_data"][0]["stock"])}')  # test
                    shop_coin = int(ret["item_data"][0]["stock"])
                except Exception as e:
                    msg.append(f'Abort. 获取购买结果失败：{e}')
                    raise abort(i)

            if i == cnt - 1:  # 最后一次循环不需要浪费{shop_name}币去刷新
                if len(bought_equip_frag) == 0 and cnt == 1 and already_buy_cnt == 0:
                    return f'Skip. 未购买任何商品'
                msg.append(f'Succeed. 实际购买{cnt-already_buy_cnt}次 今日共购买{cnt}次')
            else:  # 刷新{shop_name}
                try:
                    data = await query.query(account_info, "/shop/reset", {"system_id": shop_id, "current_currency_num": shop_coin})
                    # print(f'重置花费：{data["shop"]["reset_cost"]}')  # test
                    shop_coin = int(data["item_data"][0]["stock"])
                    target_shop = data["shop"]
                    # shop_coin -= target_shop["reset_cost"]
                except Exception as e:
                    msg.append(f'Abort. 刷新{shop_name}失败：{e}')
                    raise abort(i)
    except abort as e:
        e = int(str(e))
        msg.append(f'本次触发第{e-already_buy_cnt+1}次 今日共计第{e+1}次')

    bought_equip_frag_outp = []
    if len(bought_equip_frag):
        bought_equip_frag_outp.append(f'共花费{shop_coin_old - shop_coin}{shop_name}币 购得物品：')
        bought_equip_frag = list(sorted(bought_equip_frag.items(), key=lambda x: x[0], reverse=True))
        for item in bought_equip_frag:
            bought_equip_frag_outp.append(f'{equip2name.get(item[0], item[0])}*{item[1]}')

    return '\n'.join(msg) + '\n' + '\n'.join(bought_equip_frag_outp)


async def buy_jjc_shop(account_info, cnt=1, buy_chara_frag=False, buy_equip_frag=True):
    return await buy_shop(account_info, cnt, buy_chara_frag, buy_equip_frag, "竞技场", 202, 90003, 20000, 50000, 100)


async def buy_pjjc_shop(account_info, cnt=1, buy_chara_frag=False, buy_equip_frag=True):
    return await buy_shop(account_info, cnt, buy_chara_frag, buy_equip_frag, "公主", 203, 90004, 20000, 50000, 100)


async def buy_dungeon_shop(account_info, cnt=1, buy_chara_frag=False, buy_equip_frag=True):
    return await buy_shop(account_info, cnt, buy_chara_frag, buy_equip_frag, "地下城", 204, 90002, 50000, 100000, 300)


async def buy_flash_shop(account_info, buy_exp_frag=False):
    buy_equip_frag = True
    shop_name = "限时"
    shop_id = 212
    exp_coin_threshold = 100000000
    equip_coin_threshold = 10000000
    equip_cnt_threshold = 300

    try:
        data = await query.query(account_info, "/shop/item_list")
        shop_list = data["shop_list"]
        target_shop: dict = list(filter(lambda x: x["system_id"] == shop_id, shop_list))[0]
    except Exception as e:
        return f'Fail. 获取限时商店状态失败：{e}'

    try:
        shop_coin = await query.get_mana(account_info)
    except Exception as e:
        return f'Fail. 获取MANA数量失败：{e}'
    if shop_coin < equip_coin_threshold:
        return f'Skip. MANA数量{shop_coin}低于阈值{equip_coin_threshold // 10000}w，不执行购买'

    try:
        target_shop: List[dict] = target_shop["item_list"]
    except Exception as e:
        return f'Fail. 获取{shop_name}商品列表失败：{e}'
    slot = []
    for item in target_shop:
        if int(item.get("sold", "1")) != 0:
            continue
        item_id_str = str(item.get("item_id", 0))
        if buy_equip_frag:
            # "type" == 4 | "item_id" == 10xxxxx: 整装
            # "type" == 4 | "item_id" == 11xxxxx/12xxxx: 装备碎片
            if int(item.get("type", -1)) == 4 and len(item_id_str) == 6 and item_id_str[1] != "0":  # 是装备碎片
                equip_id_str = f'10{item_id_str[2:]}'
                try:
                    stock = await query.get_user_equip_stock(account_info, int(item_id_str))
                except Exception as e:
                    return f'Fail. 获取{equip2name.get(equip_id_str, equip_id_str)}({item_id_str})存量失败：{e}'

                if stock < equip_cnt_threshold:
                    slot.append(int(item["slot_id"]))

        if buy_exp_frag and shop_coin >= exp_coin_threshold:
            if int(item.get("item_id", -1)) == 20004:
                slot.append(int(item["slot_id"]))

    slot = list(set(slot))
    if len(slot) == 0:
        return f'Skip. 未购买任何商品'

    try:  # 购买
        ret = await query.query(
            account_info, "/shop/buy_multiple", {
                "system_id": shop_id,
                "slot_ids": slot,
                "current_currency_num": shop_coin
            })
    except Exception as e:
        return f'Fail. 购买失败：{e}'

    bought_equip_frag: Dict[str, int] = {}  # item_id_str: cnt
    bought_exp_cnt = 0
    try:
        for item in ret["purchase_list"]:  # 维护购买列表
            item_id_str = str(item["id"])
            received_cnt = int(item["received"])
            if item_id_str == "20004":
                bought_exp_cnt += received_cnt
            else:
                item_id_str = f'10{str(item["id"])[2:]}'
                bought_equip_frag[item_id_str] = bought_equip_frag.get(item_id_str, 0) + received_cnt
        shop_coin_new = ret["user_gold"]["gold_id_free"] + ret["user_gold"]["gold_id_pay"]
    except Exception as e:
        return f'Fail. 获取购买结果失败：{e}'

    bought_equip_frag_outp = []
    bought_equip_frag_outp.append(f'Succeed. 共花费{(shop_coin - shop_coin_new) // 10000}w MANA。购得物品：')
    if bought_exp_cnt > 0:
        bought_equip_frag_outp.append(f'超级经验瓶*{bought_exp_cnt}')
    if len(bought_equip_frag):
        bought_equip_frag: List[Tuple[str, int]] = list(sorted(bought_equip_frag.items(), key=lambda x: x[0], reverse=True))
        for item in bought_equip_frag:
            bought_equip_frag_outp.append(f'{equip2name.get(item[0], item[0])}*{item[1]}')

    return '\n'.join(bought_equip_frag_outp)


async def accept_jjc_reward(account_info):
    try:
        arena_info = await query.query(account_info, '/arena/info')
        if arena_info["reward_info"]["count"] == 0:
            return 'Skip. 没有未收取的jjc币'
    except Exception as e:
        return f'Fail. 获取竞技场信息失败：{e}'
    try:
        data = await query.query(account_info, '/arena/time_reward_accept')
        return f'Succeed. 成功收取jjc币{data["reward_info"]["count"]}个'
    except Exception as e:
        return f'Fail. 获取jjc币失败：{e}'


async def accept_pjjc_reward(account_info):
    try:
        arena_info = await query.query(account_info, '/grand_arena/info')
        if arena_info["reward_info"]["count"] == 0:
            return 'Skip. 没有未收取的pjjc币'
    except Exception as e:
        return f'Fail. 获取公主竞技场信息失败：{e}'
    try:
        data = await query.query(account_info,
                                 '/grand_arena/time_reward_accept')
        return f'Succeed. 成功收取pjjc币{data["reward_info"]["count"]}个'
    except Exception as e:
        return f'Fail. 获取pjjc币失败：{e}'


@unique
class GachaType(IntEnum):
    普通 = 1
    白金 = 2
    精选 = 3  # 新池
    附奖 = 31  # 复刻池
    星3确定 = 7
    公主 = -2  # 不知道
    unknown = -1


# 处理复刻池需要选择碎片的情况：gacha.get("selected_item_id", -1) == 0 -> /gacha/select_prize {"prizegacha_id": 100011, "item_id": 31092}
# 免费装备和角色碎片十连的特征："type"==3  可以抽的特征："free_exec_times": 0
# 星3确定的特征："id":70030 "cost_num_single": 1500 被抽取以后是找不到的，所以找不到就是被抽了
# 当期池子的特征：存在bonus_item_list字段，且其中的target_unit_id在recommend_unit中有出现
# 可以抽活动免费十连的特征：data.get("campaign_info", {}).get("fg10_exec_cnt", -1) == 1
# 可以抽活动免费单抽的特征：data.get("campaign_info", {}).get("fg1_exec_cnt", -1) == 1


def getGachaType(gacha: dict) -> GachaType:
    if gacha.get("type") == 3:
        return GachaType.普通
    if "selected_item_id" in gacha:
        return GachaType.附奖
    if gacha.get("cost_num_single", -1) == 1500 and str(gacha.get("id", 0))[0] == '7':
        return GachaType.星3确定
    recommend_unit_id_list = [x.get("unit_id", 100001) for x in gacha.get("recommend_unit", [])]
    if set(recommend_unit_id_list) == set([105701, 105702, 101201, 101202, 101101, 101102]):
        return GachaType.白金
    bonus_unit_id_list = [x.get("target_unit_id", 100001) for x in gacha.get("bonus_item_list", [])]
    if len(set(bonus_unit_id_list) - set(recommend_unit_id_list)) == 0:
        return GachaType.精选
    return GachaType.unknown


async def get_gacha_free(account_info):
    try:
        data = await query.query(account_info, '/gacha/index')
        gacha_info = data["gacha_info"]
    except Exception as e:
        return f'Fail. 获取扭蛋信息失败：{e}'
    for gacha in gacha_info:
        if gacha["type"] == 3:
            if gacha["free_exec_times"] != 0:
                return f'Skip. 已抽取'
            try:
                res = await query.query(account_info, "/gacha/exec", {
                    "gacha_id": gacha["id"],
                    "gacha_times": 10,
                    "exchange_id": 0,
                    "draw_type": 1,
                    "current_cost_num": -1,
                    "campaign_id": 0
                })
            except Exception as e:
                return f'Fail. 抽取免费十连扭蛋失败：{e}'
            else:
                return f'Succeed.'


async def free_gacha_special_event(account_info):
    try:
        data = await query.query(account_info, '/gacha/index')
        assert "gacha_info" in data, f'返回字段不含["gacha_info"]'
    except Exception as e:
        return f'Fail. 获取扭蛋信息失败：{e}'

    if ("campaign_info" not in data) or ("fg10_exec_cnt" not in data["campaign_info"]):
        return 'Abort. 当前没有免费十连活动，已自动关闭该功能。'
    if data["campaign_info"]["fg10_last_exec_time"] == data["campaign_info"]["fg10_exec_cnt"] == 0:
        return 'Abort. 当前没有免费十连活动，已自动关闭该功能。'

    # 当前有免费十连活动
    remain_cnt = data["campaign_info"]["fg10_exec_cnt"]
    if remain_cnt > 0:
        gacha_types = set([getGachaType(gacha) for gacha in data["gacha_info"]])
        if GachaType.公主 in gacha_types:
            selected_gacha_type = GachaType.公主
        elif GachaType.精选 in gacha_types:
            selected_gacha_type = GachaType.精选
        elif GachaType.附奖 in gacha_types:
            selected_gacha_type = GachaType.附奖
        elif GachaType.白金 in gacha_types:
            selected_gacha_type = GachaType.白金
        else:
            return f'Warn. 检测到免费十连，但池子类别不受支持，目前无法抽取。'
        for gacha in data["gacha_info"]:
            if getGachaType(gacha) == selected_gacha_type:
                msg = []
                if getGachaType(gacha) == GachaType.附奖 and gacha["selected_item_id"] == 0:
                    try:
                        res = await query.query(account_info, "/gacha/select_prize", {"prizegacha_id": 100044, "item_id": 31155}) # temp TODO modifiy
                    except Exception as e:
                        return f'Fail. 设置附奖扭蛋奖品角色失败：{e}'
                    else:
                        msg.append(f'检测到当前为复刻池，自动设置附奖扭蛋奖品角色成功')
                
                get_already_have_3x_name = []
                get_new_name = []
                
                for i in range(remain_cnt, 0, -1): # 还未抽取
                    try:
                        res = await query.query(account_info, "/gacha/exec", {
                            "gacha_id": gacha["id"],
                            "gacha_times": 10,
                            "exchange_id": gacha["exchange_id"],
                            "draw_type": 6,  # 普通免费碎片扭蛋=1 150钻单抽/1500钻抽十连=2 单抽券/十连券单抽=3 免费十连=6 付费50钻=4 付费1500钻抽星3=?
                            "current_cost_num": i,  # 当前抽取所用的物品的数量（普通免费碎片扭蛋=-1 普通钻石抽=钻石数量 单抽券单抽=单抽券数量 免费十连活动抽=剩余免费十连次数 付费钻抽=付费钻数量
                            "campaign_id": data["campaign_info"]["campaign_id"],
                        })
                    except Exception as e:
                        return f'Fail. 抽取免费十连失败：{e}'
                    try:                        
                        for reward_info in res["reward_info_list"]:
                            if "exchange_data" in reward_info:
                                exchange_data = reward_info["exchange_data"]
                                if int(exchange_data["rarity"]) == 3:
                                    get_already_have_3x_name.append(chara.fromid(int(exchange_data["unit_id"]) // 100).name)
                            elif int(reward_info["id"]) != 90005 and len(str(reward_info["id"])) == 6:
                                get_new_name.append(chara.fromid(int(reward_info["id"]) // 100).name)
                    except Exception as e:
                        return f'Warn. 抽取免费十连成功，但获取结果失败：{e}'
                msg.append("Succeed.")
                msg.append(f'恭喜抽出新角色：{" ".join(get_new_name)}' if len(get_new_name) else "没有抽出新角色")
                msg.append(f'抽出已有三星角色：{" ".join(get_already_have_3x_name)}' if len(get_already_have_3x_name) else "没有抽出已有三星角色")
                msg.append(f'当前进度{res["gacha_point_info"]["current_point"]}/{res["gacha_point_info"]["max_point"]}')
                return " ".join(msg)
    else:
        return f'Skip. 今日免费十连已抽取。'


async def event_gacha(account_info, event_id_list=None):
    event_gacha_info_path = Path(__file__).parent / "event_gacha_info.json"
    event_gacha_info = {}
    if exists(event_gacha_info_path):
        with (event_gacha_info_path).open("r", encoding="utf-8") as f:
            event_gacha_info = load(f)

    if event_id_list is None:
        try:
            event_id_list, msg = await get_event_id_list(account_info)
        except Exception as e:
            return str(e)
    else:
        msg = []

    for event_id in event_id_list:
        if str(event_id) not in event_gacha_info:
            msg.append(f'Abort. 未记录活动{event_id}对应的扫荡券id，暂无法提供服务')
            continue
        event_gacha_item_id = event_gacha_info[str(event_id)]
        try:
            gacha_cnt = await query.get_item_stock(account_info, event_gacha_item_id)
        except Exception as e:
            msg.append(f'Fail. 活动{event_id}获取讨伐证数量失败：{e}')
            continue
        if gacha_cnt == 0:
            msg.append(f'Skip. 活动{event_id}讨伐证数量为0')
            continue
        try:
            data = await query.query(account_info, "/event/hatsune/gacha_index", {"event_id": event_id, "gacha_id": event_id})
            gacha_step = data["event_gacha_info"]["gacha_step"]
        except Exception as e:
            msg.append(f'Fail. 活动{event_id}获取当前讨伐列表失败：{e}')
            continue
        if gacha_step < 6:
            msg.append(f'Abort. 目前仅支持自动交换第{6}轮及以后的列表')
            continue
        try:
            res = await query.query(account_info, "/event/hatsune/gacha_exec", {"event_id": event_id, "gacha_id": event_id, "gacha_times": gacha_cnt, "current_cost_num": gacha_cnt, "loop_box_multi_gacha_flag": 1})
        except Exception as e:
            msg.append(f'Fail. 活动{event_id}交换讨伐证失败：{e}')
            continue
        msg.append(f'Succeed. 活动{event_id}交换讨伐证({gacha_cnt}张)成功')
    return " ".join(msg)

import random


async def _read_story(account_info, story_ids, story_name):
    try:
        load_index = await query.get_load_index(account_info)
        read_story_ids = load_index["read_story_ids"]
    except Exception as e:
        return f'Fail. 获取剧情阅读信息失败：{e}'

    succ = 0
    msg = []
    f = True
    for story_id in story_ids:
        if story_id not in read_story_ids:
            f = False
            try:
                data = await query.query(account_info, "/story/check",
                                         {"story_id": story_id})
                data = await query.query(account_info, "/story/start",
                                         {"story_id": story_id})
                succ += 1
            except Exception as e:
                msg.append(
                    f'Warn. 阅读{story_name}剧情{story_id}失败，可能为未通关对应关卡。中断后续阅读。'
                )
                break
    if succ > 0:
        msg.append(f'Succeed. 阅读{story_name}剧情成功({succ}个)')
    if f:
        msg.append(f'Skip. 没有未读的{story_name}剧情')
    return '\n'.join(msg)


async def update_story_id(account_info):
    try:
        load_index = await query.get_load_index(account_info)
        read_story_ids = load_index["read_story_ids"]
    except Exception as e:
        return f'Fail. 获取剧情阅读信息失败：{e}'

    try:
        with open(join(curpath, 'main_story_id.json'), "r", encoding="utf-8") as fp:
            main_story_id = load(fp)
    except:
        return f'Fail. 获取主线剧情列表失败。请联系bot主人。'
    account_main_story_id = [x for x in read_story_ids if x // 1000000 == 2]
    merged_main_story_id = list(sorted(set(main_story_id) | set(account_main_story_id)))
    if merged_main_story_id != main_story_id:
        with open(join(curpath, 'main_story_id.json'), "w", encoding="utf-8") as fp:
            dump(merged_main_story_id, fp, ensure_ascii=False)

    try:
        with open(join(curpath, 'tower_story_id.json'), "r", encoding="utf-8") as fp:
            tower_story_id = load(fp)
    except:
        return f'Fail. 获取露娜塔剧情列表失败。请联系bot主人。'
    account_tower_story_id = [x for x in read_story_ids if x // 1000000 == 7]
    merged_tower_story_id = list(sorted(set(tower_story_id) | set(account_tower_story_id)))
    if merged_tower_story_id != tower_story_id:
        with open(join(curpath, 'tower_story_id.json'), "w", encoding="utf-8") as fp:
            dump(merged_tower_story_id, fp, ensure_ascii=False)

    try:
        account_chara_story_list = [x for x in read_story_ids if x // 1000000 == 1]
        cache_chara_story_list = gs_fileIo.CharaStoryList
        if account_chara_story_list != cache_chara_story_list:
            gs_fileIo.CharaStoryList = list(sorted(set(account_chara_story_list) | set(cache_chara_story_list)))
    except:
        return f'Fail. 获取角色剧情列表失败。请联系bot主人。'
    
    return f'Succeed. 维护剧情列表成功'


def stock2usage(stock: Dict[int, int], v: int) -> Dict[int, int]:
    """
    PCR同款的蛋糕或强化石使用策略。
    优先从价值小的物品开始使用，并非DP。
    
    Args:
        stock: 物品价值: 物品数量
        v: 所需价值
    Raises:
        ValueError: v<=0
        ValueError: 存在价值<=0或数量<0的物品
        ValueError: 所有物品价值之和小于所需价值。
    Returns:
        Dict[int, int]: 物品价值: 使用数量。保证总价值不小于v。使用数量为0的物品不会出现在此dict中。
    """
    if v <= 0:
        raise ValueError(f'所需价值应为正整数。传入了[{v}]')
    if any(key <= 0 for key in stock):
        raise ValueError(f'物品价值应为正整数')
    if any(value < 0 for value in stock.values()):
        raise ValueError(f'物品数量应为非负整数')
    s = sum(sv * st for sv, st in stock.items())
    if s < v:
        raise ValueError(f'所有物品价值之和小于所需价值')
    usage = {}
    for sv, st in sorted(stock.items(), reverse=True):
        if s - sv * st < v:
            ut = math.ceil(st - (s - v) / sv)
            usage[sv] = ut
            v -= sv * ut
        s -= sv * st
    return dict(sorted(usage.items()))


async def give_gift(pcrClient: PcrApi) -> Outputs:
    try:
        id42rarity = {id // 100: unit_info.unit_rarity for id, unit_info in (await pcrClient.GetUnitInfoDict()).items()}
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取各角色当前星级失败：{e}')
    # 计算各角色满好感经验值
    id42love_max_exp = {id: 700 if rarity <= 2 else 4200 if rarity <= 5 else 16800 for id, rarity in id42rarity.items()}
    try:
        id42love_now_exp = {id: love_info.chara_love for id, love_info in (await pcrClient.GetCharaLoveInfoDict()).items()}
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取各角色当前好感经验值失败：{e}')
    # 计算各角色还需要的好感经验值
    id42love_needed_exp = {id: max_exp - id42love_now_exp.get(id, 0) for id, max_exp in id42love_max_exp.items()}
    id42love_needed_exp = {k: v for k, v in id42love_needed_exp.items() if v > 0}
    if (id42love_needed_exp == {}):
        return Outputs.FromStr(OutputFlag.Skip, "所有角色好感已满")
    
    try:
        stock = {10: await pcrClient.GetItemStock(50001), 20: await pcrClient.GetItemStock(50002), 30: await pcrClient.GetItemStock(50003)}
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取蛋糕库存数量失败：{e.__cause__}')

    outputs = Outputs()
    succeeded: List[str] = []
    skipped: List[str] = []
    for id, needed_exp in sorted(id42love_needed_exp.items(), key=lambda item: item[1]):
        #print(f"{PcrApi.CharaOutputName(id)}需要{needed_exp}好感经验值")
        if stock[10] * 10 + stock[20] * 20 + stock[30] * 30 < needed_exp:
            skipped.append(PcrApi.CharaOutputName(id))
            continue
        usage = stock2usage(stock, needed_exp)
        #print(f'库存={stock} 用量={usage}')
        request: List[PcrApi.ItemInfoRequest] = []
        for v, t in usage.items():
            request.append(PcrApi.ItemInfoRequest(item_id=50000 + v // 10, item_num=t, current_item_num=stock[v]))
            stock[v] -= t
        try:
            await pcrClient.MultiGiveGift(PcrApi.MultiGiveGiftRequest(unit_id=id * 100 + 1, item_info=request))
        except PcrApiException as e:
            outputs.append(OutputFlag.Error, f"提升角色{PcrApi.CharaOutputName(id)}好感失败：{e.__cause__}")
            break
        else:
            succeeded.append(PcrApi.CharaOutputName(id))
    if succeeded:
        outputs.append(OutputFlag.Succeed, f"以下角色提升好感成功：{' '.join(succeeded)}")
    if skipped:
        outputs.append(OutputFlag.Warn, f"由于蛋糕不足，以下角色好感未满：{' '.join(skipped)}")
    return outputs            
    
async def read_chara_story(pcrClient: PcrApi) -> Outputs:
    try:
        load_index = await pcrClient.GetLoadIndexRaw()
        read_story_ids = load_index["read_story_ids"]
    except PcrApiException as e:
        return f'Fail. 获取剧情阅读信息失败：{e}'
    account_chara_story_list = [x for x in read_story_ids if x // 1000000 == 1]
    
    id42read = {}
    for id7 in account_chara_story_list:
        id42read[id7 // 1000] = max(id42read.get(id7 // 1000, 0), id7 % 1000)

    outputs = Outputs()
    succeeded: List[str] = []
    try:
        chara_loveinfo = await pcrClient.GetCharaLoveInfoDict()
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取各角色好感信息失败：{e}')
    
    cache_chara_story_list = gs_fileIo.CharaStoryList
    for id4, love_info in chara_loveinfo.items():
        already_read_id = id42read.get(id4, 0)
        love_level = love_info.love_level
        chara_name = PcrApi.CharaOutputName(id4)
        
        full_story = True
        if '(' in chara.fromid(id4).name: # 非原皮角色剧情不满
            full_story = False
        if id4 in [1061, 1068, 1070, 1071, 1092, 1093, 1094, 1097, 1098, 1099, 1701, 1702]: # 七冠，联动角色，环奈剧情不满
            full_story = False
        if (id4 * 1000 + 8) not in cache_chara_story_list: # 上面的列表可能更新不及时，添加此判断：该角色缓存中无8话剧情则视为不满
            full_story = False
            
        if full_story:
            max_read_id = love_level
        else:
            if love_level < 4:
                max_read_id = 1
            elif love_level == 4:
                max_read_id = 2
            elif love_level < 8:
                max_read_id = 3
            else:
                max_read_id = love_level - 4

        if max_read_id <= already_read_id:
            continue
        for read_id in range(already_read_id + 1, max_read_id + 1):
            story_id = id4 * 1000 + read_id
            try:
                await pcrClient.ReadStory(story_id)
            except Exception as e:
                outputs.append(OutputFlag.Error, f'阅读角色{chara_name}剧情{story_id}失败。若此角色为活动角色，请先阅读活动剧情。')
                break
        if outputs:
            succeeded.append(f'{chara_name}({already_read_id}→{max_read_id})')

    if succeeded:
        outputs.append(OutputFlag.Succeed, f"以下角色阅读好感剧情成功：{' '.join(succeeded)}")
    if outputs.Result == OutputFlag.Empty:
        return Outputs.FromStr(OutputFlag.Skip, "没有未读的角色好感剧情")
    return outputs    


async def read_main_story(account_info):
    try:
        with open(join(curpath, 'main_story_id.json'), "r", encoding="utf-8") as fp:
            main_story_id = load(fp)
    except:
        return f'Fail. 获取主线剧情列表失败。请联系bot主人。'

    return await _read_story(account_info, main_story_id, "主线")


async def read_tower_story(account_info):
    try:
        with open(join(curpath, 'tower_story_id.json'), "r", encoding="utf-8") as fp:
            tower_story_id = load(fp)
    except:
        return f'Fail. 获取露娜塔剧情列表失败。请联系bot主人。'

    return await _read_story(account_info, tower_story_id, "露娜塔")


async def read_past_story(account_info):
    try:
        load_index = await query.get_load_index(account_info)
        read_story_ids = load_index["read_story_ids"]
        unlock_story_ids = load_index["unlock_story_ids"]
        to_read_story_ids = []
        for unlock_story in unlock_story_ids:
            if unlock_story not in read_story_ids:
                if int(str(unlock_story)[0]) in [5]:
                    to_read_story_ids.append(unlock_story)
    except Exception as e:
        return f'Fail. 获取剧情阅读信息失败：{e}'

    if to_read_story_ids == []:
        return "Skip. 没有未读的往期剧情。"

    succ = 0
    msg = []
    for story_id in to_read_story_ids:
        try:
            data = await query.query(account_info, "/story/check",
                                     {"story_id": story_id})
            data = await query.query(account_info, "/story/start",
                                     {"story_id": story_id})
            succ += 1
        except Exception as e:
            msg.append(f'Warn. 阅读往期活动剧情{story_id}失败：{e}。中断后续阅读。')
            break
    if succ > 0:
        msg.append(f'Succeed. 阅读往期活动剧情成功({succ}个)')
    return '\n'.join(msg)


async def read_event_story(account_info):
    event_id_list = []
    try:
        load_index = await query.get_load_index(account_info)
        for event in load_index["event_statuses"]:
            if event["event_type"] == 1 and event["period"] in [2, 3]:
                event_id_list.append(event["event_id"])
    except Exception as e:
        return f'Fail. 获取当前活动列表失败：{e}'
    if event_id_list == []:
        return f"Skip. 当前无开放的活动"
    msg = []
    for event_id in event_id_list:
        try:
            data = await query.query(account_info, "/event/hatsune/top",
                                     {"event_id": event_id})
        except Exception as e:
            msg.append(f'Fail. 获取活动{event_id}信息失败：{e}')
            continue
        story_list = [data.get("opening", {})]
        story_list += data.get("stories", [])
        story_list += [data.get("ending"), {}]

        story_id_list = []
        for story in story_list:
            if story.get("is_unlocked", -1) == 1 and story.get(
                    "is_readed", -1) == 0:
                story_id_list.append(story["story_id"])

        if story_id_list == []:
            msg.append(f'Skip. 活动{event_id}所有剧情已阅读完毕')
            continue

        succ = 0
        for story_id in story_id_list:
            try:
                data = await query.query(account_info, "/story/check",
                                         {"story_id": story_id})
                data = await query.query(account_info, "/story/start",
                                         {"story_id": story_id})
                succ += 1
            except Exception as e:
                msg.append(
                    f'Warn. 阅读活动{event_id}剧情{story_id}失败：{e}。中断后续阅读。')
                break
        if succ > 0:
            msg.append(f'Succeed. 阅读活动{event_id}剧情成功({succ}个)')
    return '\n'.join(msg)


async def read_trust_chapter(account_info):
    event_id_list = []
    try:
        load_index = await query.get_load_index(account_info)
        for event in load_index["event_statuses"]:
            if event["event_type"] == 1 and event["period"] in [2, 3]:
                event_id_list.append(event["event_id"])
    except Exception as e:
        return f'Fail. 获取当前活动列表失败：{e}'
    if event_id_list == []:
        return "Skip. 当前无开放的活动"
    msg = []
    for event_id in event_id_list:
        try:
            data = await query.query(account_info, "/event/hatsune/top",
                                     {"event_id": event_id})
        except Exception as e:
            msg.append(f'Fail. 获取活动{event_id}信息失败：{e}')
            continue
        if "unchoiced_dear_story_id_list" not in data:
            msg.append(f'Skip. 活动{event_id}尚未解锁羁绊系统')
            continue
        story_id_list = data["unchoiced_dear_story_id_list"]
        if story_id_list == []:
            msg.append(f'Skip. 活动{event_id}所有羁绊剧情已阅读完毕')
            continue
        succ = 0
        for story_id in story_id_list:
            try:
                data = await query.query(account_info, "/story/check",
                                         {"story_id": story_id})
                data = await query.query(
                    account_info, "/event/hatsune/dear_finish", {
                        "event_id": event_id,
                        "story_id": story_id,
                        "choice": random.randint(1, 3)
                    })
                succ += 1
            except Exception as e:
                msg.append(
                    f'Warn. 阅读活动{event_id}羁绊剧情{story_id}失败：{e}。中断后续阅读。')
                break
        if succ > 0:
            msg.append(f'Succeed. 阅读活动{event_id}羁绊剧情成功({succ}个)')
    return '\n'.join(msg)


async def eat_pudding(pcrClient: PcrApi) -> Outputs:    
    pudding_event_id = 10080
    
    try:
        events = await pcrClient.GetEvents()
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取当前活动列表失败：{e}')
    
    is_open = False
    for event in events:
        if event.event_type == 1 and event.period == 2 and event.event_id == pudding_event_id:
            is_open = True
            break
    if not is_open:
        return Outputs.FromStr(OutputFlag.Skip, "吃布丁活动已结束")
    
    try:
        event_info = await pcrClient.GetEventInfo(pudding_event_id)
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取活动{pudding_event_id}信息失败：{e}')
    
    is_found = False
    for boss_battle_info in event_info.boss_battle_info:
        if boss_battle_info.boss_id == 1008001:
            is_found = True
            if not boss_battle_info.is_unlocked:
                return Outputs.FromStr(OutputFlag.Abort, f'活动{pudding_event_id}的普通Boss尚未解锁，无法开启吃布丁小游戏')
            if boss_battle_info.kill_num < 1:
                return Outputs.FromStr(OutputFlag.Abort, f'活动{pudding_event_id}的普通Boss尚未通关，无法开启吃布丁小游戏')
    if not is_found:
        return Outputs.FromStr(OutputFlag.Abort, f'活动{pudding_event_id}的普通Boss尚未解锁，无法开启吃布丁小游戏')
    
    try:
        pudding_info = await pcrClient.GetEatPuddingGameInfo()
        material_item_id = pudding_info.psy_setting["material_item_id"]
        get_pudding_frame_id_list = [x.frame_id for x in pudding_info.cooking_status] 
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取吃布丁小游戏信息失败：{e}')
        
    for drama in pudding_info.drama_list:
        if not drama.read_status:
            try:
                await pcrClient.EatPuddingGameReadDrama(drama.drama_id)
            except PcrApiException as e:
                return Outputs.FromStr(OutputFlag.Error, f'阅读吃布丁小游戏剧情[{drama.drama_id}]失败：{e}')
    
    try:
        stock = await pcrClient.GetItemStock(material_item_id)
    except PcrApiException as e:
        return Outputs.FromStr(OutputFlag.Error, f'获取布丁材料库存信息失败：{e}')
    if stock <= 0:
        return Outputs.FromStr(OutputFlag.Skip, f'布丁材料已用尽')
    
    outputs = Outputs()
    total_use_pudding_num = 0
    while stock > 0 or len(get_pudding_frame_id_list) > 0:
        use_pudding_num = min(stock, 24)
        start_cooking_frame_id_list = [x for x in range(1, use_pudding_num + 1)]
        try:
            await pcrClient.EatPuddingGameStartCook(start_cooking_frame_id_list, get_pudding_frame_id_list)
        except PcrApiException as e:
            outputs.append(OutputFlag.Error, f'制作布丁失败：{e}')
            break
        get_pudding_frame_id_list = start_cooking_frame_id_list
        stock -= use_pudding_num
        total_use_pudding_num += use_pudding_num
    
    if total_use_pudding_num > 0:
        outputs.append(OutputFlag.Succeed, f'成功制作{total_use_pudding_num}个布丁')
    return outputs
    

async def __star6_sweep(account_info, map_id, sweep_cnt, item_id, buy_stamina_passive_max) -> str:
    '''
    :returns: 将返回的字符串加入结果，继续执行后续逻辑
    :raise Exception: 将抛出的字符串(str(e))加入结果，中断后续逻辑执行
    '''
    chara_id = int(f'1{str(item_id)[-3:]}')
    chara_name = chara.fromid(chara_id).name

    global stamina_short

    outp = []
    try:
        ret = await query.sweep(account_info, map_id, sweep_cnt, buy_stamina_passive_max)
    except Exception as e:
        outp.append(str(e))
        raise Exception(" ".join(outp))
    else:
        outp.append(ret)
        stamina_short = account_info.get("stamina_short", False)

    try:
        chara_pure_frag_stock = await query.get_item_stock(account_info, item_id)
    except Exception as e:
        outp.append(f'Fail. 获取 {chara_name} 纯净记忆碎片数量失败：{e}')
        raise Exception(" ".join(outp))
    if chara_pure_frag_stock >= 50:
        outp.append(f'Abort. {chara_name} 的纯净记忆碎片已刷满')
        raise Exception(" ".join(outp))
    else:
        outp.append(f'(共{chara_pure_frag_stock}片)')

    return " ".join(outp)


async def _star6_sweep(account_info, allow_recovery: bool, buy_stamina_passive_max):
    try:
        box = await query.get_box(account_info)
    except Exception as e:
        return f'Fail. 获取box失败：{e}'

    try:
        all_quest = await query.get_all_quest_dict(account_info)
    except Exception as e:
        return f'Fail. 获取地图通关信息失败：{e}'

    try:
        item_dict = await query.get_item_dict(account_info)
    except Exception as e:
        return f'Fail. 获取装备信息失败：{e}'

    global stamina_short
    outp = []
    已刷满但未开花角色: List[str] = []
    已开放但未3星通关地图: List[str] = []
    今日已完成扫荡地图: List[str] = []
    for map_id, item_id in star6_utils.get_map_2_item_dict().items():  # 13018001: 32058
        if stamina_short:
            break

        if map_id not in all_quest:
            continue

        map_name = map_utils.from_id(map_id).name
        chara_id = int(f'1{str(item_id)[-3:]}')
        chara_name = chara.fromid(chara_id).name

        # 没有的角色不触发刷取
        if chara_id not in box:
            continue

        # 已6x角色不刷取
        chara_detail = box[chara_id]
        if chara_detail["unit_rarity"] == 6:
            continue

        if chara_detail.get("unlock_rarity_6_item", {}).get("slot_1", -1) == 1:
            已刷满但未开花角色.append(chara_name)
            #outp.append(f'Warn. {chara_name} 的纯净记忆碎片已配置，但尚未开花')
            continue

        chara_pure_frag_stock = item_dict.get(item_id, 0)

        if chara_pure_frag_stock >= 50:
            已刷满但未开花角色.append(chara_name)
            #outp.append(f'Abort. {chara_name} 的纯净记忆碎片已刷满')
            continue

        map_info = all_quest[map_id]

        # 判断地图通关星数
        map_star = map_info["clear_flg"]
        if map_star < 3:
            已开放但未3星通关地图.append(map_name)
            #outp.append(f'Abort. {map_name}为{map_star}星通关，无法扫荡')
            continue

        daily_clear_count = map_info["daily_clear_count"]
        if daily_clear_count == 6:
            今日已完成扫荡地图.append(map_name)
            #outp.append(f'Skip. {map_name}今日已扫荡并重置')
            continue
        if daily_clear_count == 3 and allow_recovery == False:
            今日已完成扫荡地图.append(map_name)
            #outp.append(f'Skip. {map_name}今日已扫荡')
            continue

        daily_recovery_count = map_info["daily_recovery_count"]
        max_clear_cnt = 3 * (1 + daily_recovery_count)
        if daily_clear_count < max_clear_cnt:
            try:
                ret = await __star6_sweep(account_info, map_id, max_clear_cnt - daily_clear_count, item_id, buy_stamina_passive_max)
            except Exception as e:
                outp.append(str(e))
                continue
            else:
                outp.append(ret)

        # 不需要回复或已执行过回复
        if daily_recovery_count == 1 or allow_recovery == False:
            continue

        try:
            map_info = await query.get_quest_dict(account_info, map_id)
            assert "daily_clear_count" in map_info, "扫荡次数获取失败"
        except Exception as e:
            outp.append(f'Fail. 获取扫荡结果失败：{e}')
            continue
        else:
            if map_info["daily_clear_count"] != 3:
                continue

        try:
            ret = await query.recover_quest(account_info, map_id)
        except Exception as e:
            outp.append(str(e))
            continue
        else:
            outp.append(ret)

        try:
            ret = await __star6_sweep(account_info, map_id, 3, item_id, buy_stamina_passive_max)
        except Exception as e:
            outp.append(str(e))
            continue
        else:
            outp.append(ret)

    if len(已刷满但未开花角色):
        outp.append(f'Skip. 以下角色碎片已刷满但未开花：' + ' '.join(已刷满但未开花角色))
    if len(已开放但未3星通关地图):
        outp.append(f'Skip. 以下地图已开放但未3星通关：' + ' '.join(已开放但未3星通关地图))
    if len(今日已完成扫荡地图):
        outp.append(f'Skip. 以下地图今日已扫荡：' + ' '.join(今日已完成扫荡地图))
    if len(outp) == 0:
        return f'Skip. 所有当前6x已开放角色已开花完毕'

    return " ".join(outp)


async def star6_sweep(account_info, sweep_cnt, buy_stamina_passive_max):
    return await _star6_sweep(account_info, True if sweep_cnt == 6 else False, buy_stamina_passive_max)


async def _event_sweep(account_info, quest_id, x_remain, buy_stamina_passive_max):
    global stamina_short
    if stamina_short:
        return ""
    try:
        ticket = await query.get_ticket_num(account_info)
    except Exception as e:
        return f'Fail. 获取扫荡券数量失败：{e}'
    try:
        stamina = await query.get_stamina(account_info)
    except Exception as e:
        return f'Fail. 获取当前体力失败：{e}'
    #s = [f'当前体力{stamina}']
    s = []

    identify_code = quest_id % 1000
    if identify_code in [101, 102, 103, 104, 105]:
        stamina_take = 8
    elif identify_code in [106, 107, 108, 109, 110]:
        stamina_take = 9
    elif identify_code in [111, 112, 113, 114, 115]:
        stamina_take = 10
    elif identify_code in [201, 202]:
        stamina_take = 16
    elif identify_code in [203, 204]:
        stamina_take = 18
    elif identify_code in [205]:
        stamina_take = 20
    else:
        return f'Fail. 不可识别的关卡：{identify_code}'

    if x_remain == -1:
        x_remain = stamina // stamina_take

    if stamina < stamina_take * x_remain:
        stamina_old = stamina
        message, stamina = await buy_stamina(account_info,
                                             buy_stamina_passive_max,
                                             stamina_take * x_remain, stamina)
        s.append(f'尝试购买体力({stamina_old}->{stamina_take * x_remain})：{message}')
        if stamina < stamina_take * x_remain:
            stamina_short = True
    y = min(ticket, x_remain, stamina // stamina_take)
    if y == ticket:
        s.append(f'Warn. 扫荡券仅剩{ticket}张')
    if y == 0:
        s.append('Skip. 实际刷取0次')
    else:
        try:
            info = await query.query(
                account_info, "/event/hatsune/quest_skip", {
                    "event_id": quest_id // 1000,
                    "quest_id": quest_id,
                    "use_ticket_num": y,
                    "current_ticket_num": ticket
                })
        except Exception as e:
            s.append(f'Fail. 扫荡{quest_id}失败：{e}')
        else:
            s.append(f'Succeed. 扫荡{quest_id}成功({y}次)')
    if stamina_short:
        s.append('体力耗尽，不执行后续刷图')
    return '\n'.join(s)


async def get_new_event_id_list(account_info, event_id_list: List[int]) -> List[int]:
    '''
    返回的活动列表中将过滤掉复刻活动，且新活动按从新到旧排序
    '''
    cache_path = join(curpath, "new_event_list.json")
    if exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as fp:
            cache = load(fp)
            if getNowtime() - cache.get("time", 0) < 3600:
                if len(cache.get("new_event_id_list", [])):
                    return cache["new_event_id_list"]

    story_id_list = [-1] * len(event_id_list)
    for i, event_id in enumerate(event_id_list):
        try:
            data = await query.query(account_info, "/event/hatsune/top", {"event_id": event_id})
            if data.get("opening", {}).get("story_id", 0):
                story_id_list[i] = int(data["opening"]["story_id"]) // 1000 % 100
            elif len(data.get("stories", [])):
                story_id_list[i] = int(data["stories"][0].get("story_id", 0)) // 1000 % 100
        except Exception as e:
            raise Exception(f'Fail. 获取活动{event_id}信息失败：{e}')

    ew_list = sorted(zip(event_id_list, story_id_list), key=lambda x: x[1], reverse=True)
    new_event_id_list = [ew[0] for ew in ew_list if ew_list[0][1] - ew[1] < 5]

    with open(cache_path, "w", encoding="utf-8") as fp:
        dump({"new_event_id_list": new_event_id_list, "time": getNowtime()}, fp, ensure_ascii=False, indent=4)

    return new_event_id_list


async def get_event_id_list(account_info, sweep_type: str = "all", only_open: bool = True, return_close_msg: bool = False):
    '''
    sweep_type: enum("old", "new", "all")
    return event_id_list:List[int], msg:List[str]
    '''

    event_id_list = []
    msg = []

    try:
        load_index = await query.get_load_index(account_info)
        for event in load_index["event_statuses"]:
            if event["event_type"] == 1:
                if only_open:
                    if event["period"] == 2:
                        event_id_list.append(event["event_id"])
                    else:
                        msg.append(f'活动{event["event_id"]}未开放')
                else:
                    event_id_list.append(event["event_id"])

    except Exception as e:
        raise Exception(f'Fail. 获取当前活动列表失败：{e}')

    if event_id_list == []:
        raise Exception("Abort. 当前无开放的活动")

    if sweep_type != "all":
        new_event_id_list = await get_new_event_id_list(account_info, event_id_list)
        old_event_id_list = list(set(event_id_list) - set(new_event_id_list))
        if len(new_event_id_list) and len(old_event_id_list):
            if sweep_type == "new":
                event_id_list = new_event_id_list
            elif sweep_type == "old":
                event_id_list = old_event_id_list

    return event_id_list, msg if return_close_msg else []


async def event_hard_boss_sweep(account_info, cnt: Union[int, str], event_id_list=None):
    '''
    cnt: int | enum("max", "max-1", "max-2")
    '''

    if cnt == 0:
        return ""

    if event_id_list is None:
        try:
            event_id_list, msg = await get_event_id_list(account_info)
        except Exception as e:
            return str(e)
    else:
        msg = []
    event_id_list.reverse()
    for event_id in event_id_list:
        try:
            data = await query.query(account_info, "/event/hatsune/top", {"event_id": event_id})
            boss_ticket_num = data["boss_ticket_info"]["stock"]
            oneblow_kill_count = [x["oneblow_kill_count"] for x in data["boss_battle_info"] if x["boss_id"] == int(f'{event_id}02')][0]
        except Exception as e:
            msg.append(f'Fail. 获取活动{event_id}信息失败：{e}')
            continue
        if boss_ticket_num < 30:
            msg.append(f'Skip. 活动{event_id}的首领挑战券数量为{boss_ticket_num}，无法扫荡')
            continue
        if oneblow_kill_count == 0:
            msg.append(f'Abort. 活动{event_id}的Hard Boss未解锁扫荡')
            continue
        # if oneblow_kill_count < 3:
        #     msg.append(f'Abort. 活动{event_id}的Hard Boss未解锁扫荡。解锁扫荡需完成[一场战斗内获胜]{3}次，您目前完成了[{oneblow_kill_count}]次')
        #     continue
        try:
            skip_ticket_num = await query.get_ticket_num(account_info)
        except Exception as e:
            msg.append(f'Fail. 获取扫荡券数量失败：{e}')
            continue

        msg.append(f'活动{event_id}Boss挑战券{boss_ticket_num}张，扫荡券{skip_ticket_num}张')
        if cnt == "max":
            sweep_cnt = min(boss_ticket_num // 30, skip_ticket_num)
        elif cnt == "max-1":
            sweep_cnt = min((boss_ticket_num // 30) - 1, skip_ticket_num)
        elif cnt == "max-2":
            sweep_cnt = min((boss_ticket_num // 30) - 2, skip_ticket_num)
        else:
            sweep_cnt = min(boss_ticket_num // 30, skip_ticket_num, cnt)
            if sweep_cnt < cnt:
                msg.append(f'Warn. 无法达到设定的扫荡次数')
        if skip_ticket_num == sweep_cnt:
            msg.append(f'Warn. 扫荡券数量过少，请注意刷取')

        if sweep_cnt <= 0:
            msg.append(f'Skip. 实际扫荡0次')
            continue

        try:
            res = await query.query(account_info, "/event/hatsune/boss_battle_skip", {"event_id": event_id,
                                                                                      "boss_id": int(f'{event_id}02'),
                                                                                      "exec_skip_num": sweep_cnt,
                                                                                      "current_skip_ticket_num": skip_ticket_num,
                                                                                      "current_boss_ticket_num": boss_ticket_num})
        except Exception as e:
            msg.append(f'Fail. 扫荡困难Boss失败：{e}')
            continue

        msg.append(f'Succeed. 扫荡困难Boss成功({sweep_cnt}次)')
    return " ".join(msg)


async def event_normal_sweep(account_info, sweep_type: str, buy_stamina_passive_max, map_id_int: int):
    '''
    sweep_type: enum("old", "new")
    map_id_int: enum(1, 15)
    '''
    global stamina_short
    if stamina_short:
        return ""

    try:
        event_id_list, _ = await get_event_id_list(account_info, sweep_type)
    except Exception as e:
        return str(e)

    event_id = event_id_list[0]

    try:
        event_quest = await query.query(account_info, "/event/hatsune/quest_top", {"event_id": event_id})
        quest_list = event_quest["quest_list"]
    except Exception as e:
        return f'Fail. 获取活动{event_id}通关信息失败：{e}'

    quest_id = int(f'{event_id}1{map_id_int:02d}')
    try:
        clear_flag = [x["clear_flag"] for x in quest_list if x["quest_id"] == quest_id][0]
    except Exception as e:
        return f'Fail. 获取活动{event_id} N1-{map_id_int}通关信息失败：{e}'

    if clear_flag != 3:
        return f'Abort. N1-{map_id_int}为{clear_flag}星通关，无法扫荡'

    return await _event_sweep(account_info, quest_id, -1, buy_stamina_passive_max)


async def event_hard_sweep(account_info, sweep_type: str, buy_stamina_passive_max, map_list=[1, 2, 3, 4, 5]):
    '''
    sweep_type: enum("old", "new", "all")
    '''
    global stamina_short
    if stamina_short:
        return ""

    try:
        event_id_list, msg = await get_event_id_list(account_info, sweep_type)
    except Exception as e:
        return str(e)

    for event_id in event_id_list:
        msg.append(f'活动{event_id}')
        try:
            event_quest = await query.query(account_info, "/event/hatsune/quest_top", {"event_id": event_id})
            quest_list = event_quest["quest_list"]
        except Exception as e:
            msg.append(f'Fail. 获取活动{event_id}通关信息失败：{e}')
            break
        for i in map_list:
            # msg.append(f'H1-{i}: ')
            f = False
            quest_id = int(f'{event_id}2{i:02d}')
            for quest in quest_list:
                if quest["quest_id"] == quest_id:
                    f = True
                    if quest["clear_flag"] != 3:
                        msg.append(f'Abort. H1-{i}为{quest["clear_flag"]}星通关，无法扫荡')
                        break
                    if quest["daily_clear_count"] == 3:
                        msg.append(f'Skip. H1-{i}已扫荡')
                        break
                    msg.append(await _event_sweep(account_info, quest_id, 3 - quest["daily_clear_count"], buy_stamina_passive_max))
                    if stamina_short:
                        break
            if stamina_short:
                break
            if f == False:
                msg.append(f'Abort. H1-{i} Unlock')
                break
    return ' '.join(msg)


async def buy_stamina_active(account_info, buy_stamina_active_daycount):
    try:
        stamina_now = await query.get_stamina(account_info)
        stamina_old = stamina_now
    except Exception as e:
        return f'Fail. 获取当前体力失败：{e}'
    cost_jewel_tot = 0
    buy_stamina_tot = 0
    msg = []
    while True:
        try:
            load_index = await query.get_load_index(account_info)
            buy_stamina_already = load_index["shop"]["recover_stamina"][
                "exec_count"]
            cost = load_index["shop"]["recover_stamina"]["cost"]
            jewel = load_index["user_jewel"]["free_jewel"] + load_index[
                "user_jewel"]["paid_jewel"]
        except Exception as e:
            return f'Fail. 获取钻石或体力信息失败：{e}'
        if buy_stamina_already >= buy_stamina_active_daycount:
            break
        if stamina_now + 120 > 999:
            msg.append(f'Abort. 购买体力后超过999限制，终止购买。')
            break
        if jewel < 10000:
            msg.append(f'Abort. 当前钻石数量({jewel})低于阈值({10000})，终止购买')
            break
        try:
            await query.query(account_info, '/shop/recover_stamina',
                              {"current_currency_num": jewel})
        except Exception as e:
            msg.append(f'Fail. 购买体力失败：{e}')
            break
        else:
            cost_jewel_tot += cost
            buy_stamina_tot += 1
            stamina_now += 120
    if buy_stamina_tot:
        msg.append(f'Succeed. 共花费{cost_jewel_tot}钻石购买{buy_stamina_tot}管体力')
        msg.append(
            f'当前体力{stamina_now}，今日已购{buy_stamina_already}管，设置每日购买{buy_stamina_active_daycount}管'
        )
    else:
        msg.append(
            f'Skip. 设置每日购买{buy_stamina_active_daycount}管，今日已购{buy_stamina_already}管'
        )
    if stamina_now > stamina_old:
        global stamina_short
        stamina_short = False
    return '\n'.join(msg)


async def buy_stamina(account_info,
                      buy_stamina_passive_max,
                      stamina_expect,
                      stamina_now=None):
    '''返回(提示语句str, 执行操作后当前体力int)'''
    try:
        if stamina_now == None:
            stamina_now = await query.get_stamina(account_info)
    except Exception as e:
        return f'Fail. 获取当前体力失败：{e}', 0
    cost_jewel_tot = 0
    buy_stamina_tot = 0
    while stamina_now < stamina_expect:
        try:
            load_index = await query.get_load_index(account_info)
            buy_stamina_already = load_index["shop"]["recover_stamina"]["exec_count"]
            cost = load_index["shop"]["recover_stamina"]["cost"]
            jewel = load_index["user_jewel"]["free_jewel"] + load_index["user_jewel"]["paid_jewel"]
        except Exception as e:
            return f'Fail. 获取用户信息失败：{e}', stamina_now
        if buy_stamina_already >= buy_stamina_passive_max:
            return f'Skip. 今日购买体力管数达设置上限({buy_stamina_already}/{buy_stamina_passive_max})', stamina_now
        if stamina_now + 120 > 999:
            return 'Skip. 无法购买体力，因为购买后将超出999上限', stamina_now
        if jewel < cost:
            return f'Fail. 钻石不足。当前拥有{jewel}，购买体力需{cost}', stamina_now
        try:
            await query.query(account_info, '/shop/recover_stamina',
                              {"current_currency_num": jewel})
        except Exception as e:
            return f'Fail. 购买体力失败：{e}', stamina_now
        else:
            cost_jewel_tot += cost
            buy_stamina_tot += 1
            stamina_now += 120
    return f'Succeed. 共花费{cost_jewel_tot}钻石购买{buy_stamina_tot}管体力，当前体力{stamina_now}', stamina_now


async def investigate(account_info, qid: int, max_sweep_cnt: int, buy_stamina_passive_max):
    global stamina_short
    outp = []

    try:
        info = await query.get_quest_dict(account_info, qid)
    except Exception as e:
        return f'Fail. 获取关卡信息失败：{e}'
    if info["clear_flg"] != 3:
        return f'Abort. 关卡为{info["clear_flg"]}星通关，无法扫荡'
    if info["daily_clear_count"] >= max_sweep_cnt:
        return f'Skip. 今日已刷取{info["daily_clear_count"]}次心碎'

    while True:
        try:
            info = await query.get_quest_dict(account_info, qid)
        except Exception as e:
            return f'Fail. 获取关卡信息失败：{e}'
        x_remain = min((info["daily_recovery_count"] + 1) * 5, max_sweep_cnt) - info["daily_clear_count"]
        if x_remain > 0:  # 当设定值从5改为10时可能存在x_remain==0
            try:
                outp.append(await query.sweep(account_info, qid, x_remain, buy_stamina_passive_max))
            except Exception as e:
                outp.append(str(e))
                break
            else:
                stamina_short = account_info.get("stamina_short", False)
                if stamina_short:
                    outp.append('体力耗尽，不执行后续刷图。')
                    break

            try:
                info = await query.get_quest_dict(account_info, qid)
            except Exception as e:
                return f'Fail. 获取关卡信息失败：{e}'
            if info["daily_clear_count"] >= max_sweep_cnt:
                break
            if info["daily_clear_count"] < (info["daily_recovery_count"] + 1) * 5:  # 可能因为扫荡券不够没刷满
                break

        try:
            outp.append(await query.recover_quest(account_info, qid))
        except Exception as e:
            outp.append(str(e))
            break

    outp.append(f'今日共刷取{info["daily_clear_count"]}次')
    return '\n'.join(outp)


async def sweep_normal(account_info, map_id, count):  # 11035012
    map_name = f'N{int(str(map_id)[2:5])}-{int(str(map_id)[5:8])}'
    msg = []
    try:
        star = await query.get_quest_star(account_info, map_id)
        if star < 3:
            return f'Abort. 关卡{map_name}为{star}星通关，无法扫荡。'
    except Exception as e:
        return f'Fail. 获取关卡{map_name}通关情况失败：{e}'
    try:
        ticket = await query.get_ticket_num(account_info)
    except Exception as e:
        return f'Fail. 获取扫荡券数量失败：{e}'
    if ticket == 0:
        return f'Fail. 扫荡券数量为0'
    if ticket < count:
        msg.append(f"Warn. 扫荡券数量({ticket})少于设定刷图次数({count})")
        count = ticket
    try:
        info = await query.query(
            account_info, "/quest/quest_skip", {
                "quest_id": map_id,
                "random_count": count,
                "current_ticket_num": ticket
            })
    except Exception as e:
        msg.append(f'Fail. 扫荡{map_name}失败：{e}')
        return " ".join(msg)

    msg.append(f'Succeed. 扫荡{map_name}成功({count}次)')
    return " ".join(msg)


async def allin_N2(account_info, d: dict):
    try:
        stamina = await query.get_stamina(account_info)
    except Exception as e:
        return f'Fail. 获取当前体力失败：{e}'
    msg = [f'当前体力{stamina}']
    stamina //= 10
    if stamina < 1:
        return f'Skip. 体力已用尽'

    triggered = False
    vall = sum(d.values())
    for k, v in d.items():
        n = int(stamina / vall * v)
        if n:
            triggered = True
            msg.append(await sweep_normal(account_info, k, n))
    if triggered == False:
        return f'Skip. 体力已用尽'

    return '\n'.join(msg)


async def sweep_normal_smart(account_info):
    try:
        stamina = await query.get_stamina(account_info)
    except Exception as e:
        return f'Fail. 获取当前体力失败：{e}'
    if stamina < 10:
        return f'Skip. 体力已用尽'
    try:
        ticket = await query.get_ticket_num(account_info)
    except Exception as e:
        return f'Fail. 获取扫荡券数量失败：{e}'
    try:
        quest_dict = await query.get_all_quest_dict(account_info)  # id(int): dict
    except Exception as e:
        return f'Fail. 获取关卡列表失败：{e}'
    try:
        user_equip = await query.get_user_equip_dict(account_info)  # id(int):stock(int)
    except Exception as e:
        return f'Fail. 获取装备列表失败：{e}'
    s = [f'当前体力{stamina}']
    y = min(ticket, stamina // 10)
    if y == ticket:
        s.append(f'Warn. 扫荡券仅剩{ticket}张')
    map_value_dict = {}  # map_id(int): value(int)
    for map_id, equip_drop_list in map2equip.items():
        major, minor = map_id.split('-')  # "33", "6"
        quest_id = int(f'11{int(major):03d}{int(minor):03d}')
        if quest_id not in quest_dict or quest_dict[quest_id]["clear_flg"] != 3:
            continue
        map_value = 0
        max_value = 0
        for equip_no in equip_drop_list:  # "125076"
            max_value = max(max_value, user_equip.get(int(equip_no), 0))
            map_value += user_equip.get(int(equip_no), 0)
        map_value -= max_value
        map_value_dict[quest_id] = map_value
    if map_value_dict == {}:
        s.append("Fail. 该账号没有三星通关的normal关卡")
    else:
        map_id, map_value = min(map_value_dict.items(), key=(lambda x: x[1]))
        major = map_id // 1000 % 1000
        minor = map_id % 1000
        s.append(f'已自动选取地图{major}-{minor}，包含装备为：')
        s4 = ""
        for equip_id in map2equip[f'{major}-{minor}']:  # "125046"
            s4 += f'{equip2name.get(f"10{equip_id[2:]}", equip_id)}({user_equip.get(int(equip_id), 0)}个) '
        s.append(s4)

        try:
            info = await query.query(
                account_info, "/quest/quest_skip", {
                    "quest_id": map_id,
                    "random_count": y,
                    "current_ticket_num": ticket
                })
        except Exception as e:
            s.append(f'Fail. 扫荡{major}-{minor}失败：{e}')
        else:
            s.append(f'Succeed. 成功刷取{major}-{minor}({y}次)')

    return '\n'.join(s)


async def advice_normal_smart(account_info):
    def weight(x: float) -> float:
        return 32 - 20 * math.atan(x / 24 - 4)

    try:
        quest_dict = await query.get_all_quest_dict(account_info)  # id(int): dict
    except Exception as e:
        return f'Fail. 获取关卡列表失败：{e}'
    try:
        user_equip = await query.get_user_equip_dict(account_info)  # id(int):stock(int)
    except Exception as e:
        return f'Fail. 获取装备列表失败：{e}'

    max_major = 0
    map_value_dict = {}  # map_id(int): value(int)
    for map_id, equip_drop_list in map2equip.items():  # "33-6": ["125076", "115556", "125376"],
        major, minor = map_id.split('-')  # "33", "6"
        quest_id = int(f'11{int(major):03d}{int(minor):03d}')
        if quest_id not in quest_dict or quest_dict[quest_id]["clear_flg"] != 3:
            continue
        if int(major) < 24 and len(map_value_dict):
            break
        max_major = max(max_major, int(major))

        map_value_list = [0, 0, 0]
        for index, equip_no in enumerate(equip_drop_list):
            if index > 2:
                break
            x = weight(user_equip.get(int(equip_no), 0))
            if index == 2:
                x *= 0.7
            map_value_list[index] = x
        map_value_list.sort(reverse=True)
        map_value_dict[quest_id] = 2 * (int(major) - max_major) + map_value_list[0] * 1.5 + map_value_list[1] * 1 + map_value_list[2] * 0.5
        # print(f'{map_id} [{user_equip.get(int(equip_drop_list[0]), 0)}, {user_equip.get(int(equip_drop_list[1]), 0)}, {user_equip.get(int(equip_drop_list[0]), 2)}] {map_value_list} {int(major) * 4 + map_value_list[0] * 3 + map_value_list[1] * 2 + map_value_list[2]}')

    if map_value_dict == {}:
        return "Abort. 该账号没有三星通关的normal关卡"

    map_sorted = sorted(map_value_dict.items(), key=(lambda x: x[1]), reverse=True)
    outp = ["从3星通关的n图中智能推荐以下关卡进行刷取："]
    cnt = 0
    for map_id, map_value in map_sorted:
        cnt += 1
        if cnt >= 8:
            break
        major = map_id // 1000 % 1000
        minor = map_id % 1000
        line = [f'[{major:02d}-{minor:02d}]({int(map_value):<3d}):']
        for equip_id in map2equip[f'{major}-{minor}']:  # "125046"
            line.append(f'{equip2name.get(f"10{equip_id[2:]}", equip_id)}({user_equip.get(int(equip_id), 0)})')
        outp.append(" ".join(line))
    return "\n".join(outp)


@sv.on_fullmatch(("#刷图推荐"))
async def advice_normal_smart_interface(bot, ev):
    try:
        account_info, qqid, nam = await get_target_account(bot, ev, True)
    except:
        return
    try:
        await query.VerifyAccount(account_info)
    except Exception as e:
        await bot.finish(f'尝试登录[{nam}]失败：{e}')
    else:
        await bot.send(ev, f'{nam}\n{await advice_normal_smart(account_info)}')


@sv.on_fullmatch(("刷图推荐"))
async def advice_normal_smart_interface_private(bot, ev):
    if ev.group_id == None:
        await advice_normal_smart_interface(bot, ev)
    else:
        await bot.send(ev, '在群聊模式下，请使用 #刷图推荐 进行操作。')


import hashlib


def get_url_key(qqid):
    dic = get_sec()
    from ..myweb.run import MyHash
    dic[qqid]['url_key'] = MyHash(f'{qqid}{dic[qqid]["pcrid"]}')
    save_sec(dic)


def get_comment() -> dict:
    function_list_path = Path(__file__).parent / "function_list.json"
    with (function_list_path).open("r", encoding="utf-8") as f:
        return load(f)


def get_config_template() -> dict:
    config_template = {}
    function_list = get_comment()
    for k, v in function_list.items():
        config_template[k] = v["default"]
    return config_template


def get_config_str(config):
    msg = []
    for key, value in config.items():
        if value and value not in ["disabled"] and key not in ["cron_no_response_1", "cron_no_response_2", "buy_stamina_passive", "buy_exp&stone_mode", "allow_ata_trigger"]:
            if type(value) == bool:
                msg.append(key)
            else:
                msg.append(f'{key}={value}')
    return '\n'.join(msg)


@sv.on_fullmatch(("清日常结果", "#清日常结果", "＃清日常结果"))
async def get_daily_result(bot, ev):
    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, f'{qqid}不在账号表中！')
    config = dic[qqid]
    if 'pcrid' not in config:
        await bot.finish(ev, '没有账号基础信息，请先发送“查box”')
    if 'daily_config' not in config:
        await bot.finish(ev, '不存在清日常配置文件，请先发送“清日常设置”')
    if exists(join(curpath, f'daily_result/{qqid}.png')):
        img = pil.Image.open(join(curpath, f'daily_result/{qqid}.png'))

        def outp_b64(outp_img) -> str:
            buf = BytesIO()
            outp_img.save(buf, format='PNG')
            base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
            return f'[CQ:image,file={base64_str}]'
        await bot.send(ev, f'[CQ:reply,id={ev.message_id}]{outp_b64(img)}')
    else:
        await bot.send(ev, "没有清日常记录")


@sv.on_prefix(("定时清日常", "#定时清日常"))
async def do_daily_set_cron(bot, ev):
    cron_hour = ev.message.extract_plain_text().strip().replace(',', " ").replace('，', " ").split()
    try:
        if len(cron_hour) == 0:
            raise
        cron_hour_set = set()
        for x in cron_hour:
            x = int(x)
            if x == 24:
                x = 0
            if not -1 <= x <= 23:
                raise
            if 0 <= x <= 23:
                cron_hour_set.add(x)
        cron_hour = list(sorted(cron_hour_set))

        h1 = -1
        if len(cron_hour) > 0:
            h1 = cron_hour[0]
        h2 = -1
        if len(cron_hour) > 1:
            h2 = cron_hour[1]
    except:
        await bot.finish(ev, "请输入1~2个[-1,24]中的整数。其中-1表示关闭定时清日常")

    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, f'{qqid}不在账号表中！')
    config = dic[qqid]
    if 'pcrid' not in config:
        await bot.finish(ev, '没有账号基础信息，请先发送“查box”')
    if 'daily_config' not in config:
        await bot.finish(ev, '不存在清日常配置文件，请先发送“清日常设置”')
    config["daily_config"]["cron_no_response_1"] = h1
    config["daily_config"]["cron_no_response_2"] = h2
    save_sec(dic)
    if h1 == h2 == -1:
        await bot.send(ev, f'设置成功。已关闭定时清日常')
    elif h1 != -1 and h2 != -1:
        await bot.send(ev, f'设置成功。将在每日{h1}时和{h2}时自动清日常\n由于风控严重，不会返回清日常结果')
    else:
        await bot.send(ev, f'设置成功。将在每日{h1}时自动清日常\n由于风控严重，不会返回清日常结果')


@sv.on_fullmatch(("允许本群清日常"))
async def ata_trigger_whitelist_add(bot, ev):
    if ev.group_id is None:
        await bot.finish(ev, "该指令只可群聊触发！")

    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, f'{qqid}不在账号表中！请发送 #pcr <账号> <密码> 以交号')
    if 'daily_config' not in dic[qqid]:
        await bot.finish(ev, f'{qqid}无pcr清日常配置文件，请先发送“清日常设置”')

    outp = []

    whitelist = dic[qqid].get("allow_daily_trigger_group", [])
    group_id = int(ev.group_id)
    if group_id in whitelist:
        outp.append(f'Skip. {group_id}已在白名单中')
    else:
        whitelist.append(group_id)
        dic[qqid]["allow_daily_trigger_group"] = whitelist
        save_sec(dic)
        outp.append(f'Succeed. {group_id}加入白名单成功。本群成员可代您触发清日常')

    if dic[qqid]["daily_config"].get("allow_ata_trigger", False) == True:
        outp.append(f'Warn. 您当前全局允许他人清日常，白名单将被忽略')

    await bot.send(ev, "\n".join(outp))


@sv.on_fullmatch(("禁止本群清日常"))
async def ata_trigger_whitelist_remove(bot, ev):
    if ev.group_id is None:
        await bot.finish(ev, "该指令只可群聊触发！")

    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, f'{qqid}不在账号表中！请发送 #pcr <账号> <密码> 以交号')
    if 'daily_config' not in dic[qqid]:
        await bot.finish(ev, f'{qqid}无pcr清日常配置文件，请先发送“清日常设置”')

    outp = []

    whitelist = dic[qqid].get("allow_daily_trigger_group", [])
    group_id = int(ev.group_id)
    if group_id not in whitelist:
        outp.append(f'Skip. {group_id}不在白名单中')
    else:
        whitelist.remove(group_id)
        dic[qqid]["allow_daily_trigger_group"] = whitelist
        save_sec(dic)
        outp.append(f'Succeed. {group_id}移出白名单成功')

    if dic[qqid]["daily_config"].get("allow_ata_trigger", False) == True:
        outp.append(f'Warn. 您当前全局允许他人清日常，白名单将被忽略')

    await bot.send(ev, "\n".join(outp))


@sv.on_fullmatch(("清日常设置", "#清日常设置", "＃清日常设置", "清日常配置", "#清日常配置", "＃清日常配置"))
async def do_daily_config(bot: HoshinoBot, ev: CQEvent):
    dic = get_sec()
    qqid = str(ev.user_id)
    if qqid not in dic:
        await bot.finish(ev, f'{qqid}不在账号表中！请发送 #pcr <账号> <密码> 以交号')
    config = dic[qqid]
    if 'pcrid' not in config:
        await bot.finish(ev, '没有账号基础信息。请先发送“查box”')
    if 'daily_config' not in config:
        await _do_daily(bot, ev)
    if 'url_key' not in config:
        get_url_key(qqid)
        dic = get_sec()

    config_old = dic[qqid]["daily_config"]
    config_template = get_config_template()
    dic[qqid]["daily_config"] = config_template

    new_feature = []
    for config_key in config_template:
        if config_key not in config_old:
            new_feature.append(config_key)
    old_feature = []
    for config_key in config_old:
        if config_key not in config_template:
            old_feature.append(config_key)
    if new_feature or old_feature:
        function_list = get_comment()
        mm = ['清日常功能变化！']
        if old_feature:
            mm.append(f'被移除的功能：{" ".join(old_feature)}')
        if new_feature:
            mm.append(f'新增的功能：{" ".join([function_list.get(x, {}).get("cn", x) for x in new_feature])}')
            # mm.append('如有需要，请私发“清日常设置”开启。')
        mm.append('已自动修正配置文件')
        mm = '\n'.join(mm)
        await bot.send(ev, mm)

    for config in config_template:
        if config in config_old:
            dic[qqid]["daily_config"][config] = config_old[config]
    save_sec(dic)
    
    
        
    # if ev.group_id is not None:
    #     from ...botmanage.get_friend_info import is_friend
    #     if not await is_friend(ev.user_id, ev.self_id):
    #         await bot.finish(ev, "请先添加ebq（本bot）为好友，等待一分钟后重新发送此指令。")
    
    if ev.group_id is not None:
        await bot.send(ev, f'请私聊发送此指令')
        # try:
        #     await bot.send_private_msg(user_id=ev.user_id, message=f'{uri}/autopcr/config?url_key={dic[qqid]["url_key"]}\n请勿泄露该密钥！')
        #     #await bot.send_private_msg(user_id=ev.user_id, group_id=ev.group_id, message=f'{uri}/autopcr/config?url_key={dic[qqid]["url_key"]}\n请勿泄露该密钥！')
        # except Exception as e:
        #     await bot.send(ev, f'私发秘钥失败。请私聊发送此指令。\n原始报错：{e}')
        # else:
        #     await bot.send(ev, f'已私聊发送清日常设置秘钥，请查收')
    else:
        await bot.send(ev, f'{uri}/autopcr/config?url_key={dic[qqid]["url_key"]}\n请勿泄露该密钥！')
        

def close_event_config(qqid):
    dic = get_sec()
    dic[qqid]["daily_config"]["event_hard_135"] = "disabled"
    dic[qqid]["daily_config"]["event_hard_24"] = "disabled"
    dic[qqid]["daily_config"]["event_hard_boss_sweep"] = False
    dic[qqid]["daily_config"]["event_normal_5"] = "disabled"
    dic[qqid]["daily_config"]["event_normal_15"] = "disabled"
    save_sec(dic)
    return dic[qqid]["daily_config"]


def is_bot(qqid: str) -> bool:
    qqid = str(qqid)
    return 1 <= len(qqid) <= 3 or not qqid.isdigit()


def DoDailyEnqueueWrapper(do_daily_func):
    async def wrapper(*args, **kwargs):
        qqid: str = args[0]
        if qqid in g_doDailyQueue:
            raise RuntimeError(f'{qqid}已有一个正在运行或排队的清日常实例')

        g_doDailyQueue.add(qqid)
        print(f'将{qqid}加入队列。当前队列：{g_doDailyQueue}')

        try:
            print(f'为{qqid}执行清日常')
            res = await do_daily_func(*args, **kwargs)
        except Exception as e:
            print(f'为{qqid}执行清日常失败：{e}')
            raise
        else:
            print(f'为{qqid}执行清日常成功')
            return res
        finally:
            g_doDailyQueue.discard(qqid)
            print(f'将{qqid}挪出队列。当前队列：{g_doDailyQueue}')
    return wrapper


@DoDailyEnqueueWrapper
async def __do_daily(qqid: str, nam=None, bot=None, ev=None):
    dic = get_sec()
    account_info = dic[qqid]
    pcrClient = PcrApi(account_info)
    if nam is None:
        nam = account_info.get("pcrname", account_info.get("name", qqid))
    if bot is None:
        bot = get_bot()
    config_old = dic[qqid]["daily_config"]
    config_template = get_config_template()
    dic[qqid]["daily_config"] = config_template
    new_feature = []
    for config_key in config_template:
        if config_key not in config_old:
            new_feature.append(config_key)
    old_feature = []
    for config_key in config_old:
        if config_key not in config_template:
            old_feature.append(config_key)
    if new_feature or old_feature:
        function_list = get_comment()
        mm = ['清日常功能变化！']
        if old_feature:
            mm.append(f'被移除的功能：{" ".join(old_feature)}')
        if new_feature:
            mm.append(f'新增的功能：{" ".join([function_list.get(x, {}).get("cn", x) for x in new_feature])}')
            mm.append('如有需要，请私发“清日常设置”开启。')
        mm.append('已自动修正配置文件。')
        mm = '\n'.join(mm)
        if ev is not None:
            await bot.send(ev, f'[CQ:reply,id={ev.message_id}]{mm}')
        else:
            pass  # await bot.send_private_msg(user_id=int(qqid), message=mm)
    for config_key in config_template:
        if config_key in config_old:
            dic[qqid]["daily_config"][config_key] = config_old[config_key]
    save_sec(dic)
    # config = dic[qqid]["daily_config"]
    import copy
    config = copy.deepcopy(dic[qqid]["daily_config"])  # 不这样写的话，在清日常过程中若有人发送“清日常设置”，则该函数中的config也会被修改。
    msg = get_config_str(config)
    if msg == "":
        if ev != None:
            await bot.send(ev, f'[CQ:reply,id={ev.message_id}]该账号没有激活任何功能！')
        else:
            pass  # await bot.send_private_msg(user_id=int(qqid), message=f'该账号没有激活任何功能！')
        return "该账号没有激活任何功能"
    if ev != None:
        await bot.send(ev, f'[CQ:reply,id={ev.message_id}]Doing daily routine for {nam}.')
    else:
        pass  # await bot.send_private_msg(user_id=int(qqid), message=f'Doing daily routine for {nam}.')
    progress = []
    try:
        await pcrClient.Login()
        #await _account_verify(bot, ev, qqid, account_info, 2, None if ev is None else ev.user_id)
    except Exception as e:
        print_exc()
        if ev != None:
            await bot.send(ev, f'[CQ:reply,id={ev.message_id}]Fail. Password verification failed: {e}')
        else:
            pass  # await bot.send_private_msg(user_id=int(qqid), message=f'Fail. Password verification failed: {e}')
        return f'Password Verification Failed: {e}'
    await update_story_id(account_info)
    if config["horse_race"] or is_bot(qqid):
        progress.append(["horse_race", f'{await horse_race(account_info)}'])
    if config["mission_accept_all"]:
        progress.append(["mission_accept_all", f'{await mission_accept_all(account_info)}'])
    if config["clan_like"]:
        progress.append(["clan_like", f'{await clan_like(account_info)}'])
    if config["room_accept_all"]:
        progress.append(["room_accept_all", f'{await room_accept_all(account_info)}'])
    if config["explore"]:
        progress.append(["explore", f'{await sweep_explore_exp(account_info)}'])
        progress.append(["explore", f'{await sweep_explore_mana(account_info)}'])
    if config["explore_cloister"]:
        ret = await sweep_explore_cloister(account_info)
        if "已自动关闭该功能" in ret:
            dic = get_sec()
            dic[qqid]["daily_config"]["explore_cloister"] = False
            save_sec(dic)
        progress.append(["explore_cloister", f'{ret}'])
    if config["free_gacha"]:
        progress.append(["free_gacha", f'{await get_gacha_free(account_info)}'])
    if config["free_gacha_special_event"] or is_bot(qqid):
        ret = await free_gacha_special_event(account_info)
        if "已自动关闭该功能" in ret:
            dic = get_sec()
            dic[qqid]["daily_config"]["free_gacha_special_event"] = False
            save_sec(dic)
        progress.append(["free_gacha_special_event", f'{ret}'])
    if (config["buy_exp&stone_mode"] == "all" and get_allow_cron() == False and config["clan_battle_allow_cron"] == False) or config["buy_exp&stone_mode"] == "follow":
        if config["buy_exp_count"] or config["buy_stone_count"]:
            progress.append(["通常商店", f'{await buy_exp_and_stone_shop(account_info, config["buy_exp_count"], config["buy_stone_count"])}'])
    if config["buy_mana"]:
        progress.append(["buy_mana", f'{await buy_mana(account_info, config["buy_mana"])}'])
    if config["buy_dungeon_shop"]:
        progress.append(["buy_dungeon_shop", f'{await buy_dungeon_shop(account_info, config["buy_dungeon_shop"])}'])
    if config["buy_jjc_shop"]:
        progress.append(["buy_jjc_shop", f'{await buy_jjc_shop(account_info, config["buy_jjc_shop"])}'])
    if config["buy_pjjc_shop"]:
        progress.append(["buy_pjjc_shop", f'{await buy_pjjc_shop(account_info, config["buy_pjjc_shop"])}'])
    if is_bot(qqid):
        config["dungeon_sweep"] = "max"
    if config["dungeon_sweep"] not in ["disabled"]:
        progress.append(["dungeon_sweep", f'{await dungeon_sweep(account_info, config["dungeon_sweep"])}'])
    if config["jjc_reward"]:
        progress.append(["jjc_reward", f'{await accept_jjc_reward(account_info)}'])
        progress.append(["jjc_reward", f'{await accept_pjjc_reward(account_info)}'])
    global stamina_short
    stamina_short = False
    if config["6x_sweep"] and not stamina_short:
        progress.append(["6x_sweep", f'{await star6_sweep(account_info, config["6x_sweep"], config["buy_stamina_passive"])}'])
    if config["event_hard_135"] != "disabled" and not stamina_short:
        ret = await event_hard_sweep(account_info, config["event_hard_135"], config["buy_stamina_passive"], [1, 3, 5])
        if '当前无开放的活动' in ret:
            config = close_event_config(qqid)
        progress.append(["event_hard_135", f'{ret}'])
    if config["event_hard_24"] != "disabled" and not stamina_short:
        ret = await event_hard_sweep(account_info, config["event_hard_24"], config["buy_stamina_passive"], [2, 4])
        if '当前无开放的活动' in ret:
            config = close_event_config(qqid)
        progress.append(["event_hard_24", f'{ret}'])
    if config["xinsui_4"] and not stamina_short:
        progress.append(["xinsui_4", f'{await investigate(account_info, 18001004, config["xinsui_4"], config["buy_stamina_passive"])}'])
    if config["xinsui_3"] and not stamina_short:
        progress.append(["xinsui_3", f'{await investigate(account_info, 18001003, config["xinsui_3"], config["buy_stamina_passive"])}'])
    if config["xinsui_2"] and not stamina_short:
        progress.append(["xinsui_2", f'{await investigate(account_info, 18001002, config["xinsui_2"], config["buy_stamina_passive"])}'])
    if config["xinsui_1"] and not stamina_short:
        progress.append(["xinsui_1", f'{await investigate(account_info, 18001001, config["xinsui_1"], config["buy_stamina_passive"])}'])
    if config["xingqiubei_2"] and not stamina_short:
        progress.append(["xingqiubei_2", f'{await investigate(account_info, 19001002, config["xingqiubei_2"], config["buy_stamina_passive"])}'])
    if config["xingqiubei_1"] and not stamina_short:
        progress.append(["xingqiubei_1", f'{await investigate(account_info, 19001001, config["xingqiubei_1"], config["buy_stamina_passive"])}'])
    
    # allin
    for i in range(10):
        if config["allin_normal_temp"] or config["event_normal_5"] or config["event_normal_15"] or config["auto_sweep_normal"]:
            if i == 0:
                if config["buy_stamina_active"]:
                    progress.append(["buy_stamina_active", f'{await buy_stamina_active(account_info, config["buy_stamina_active"])}'])
                
            try:
                stamina_begin = await query.get_stamina(account_info)
            except Exception as e:
                break
            
            if config["allin_normal_temp"]:
                progress.append(["allin_normal_temp", f'{await allin_N2(account_info, {11052009:3, 11052010:2, 11052011:5, 11052012:10, 11052013:10, 11052014:5})}'])
            if config["event_normal_5"] != "disabled":
                ret = await event_normal_sweep(account_info, config["event_normal_5"], config["buy_stamina_passive"], 5)
                if '当前无开放的活动' in ret:
                    config = close_event_config(qqid)
                progress.append(["event_normal_5", f'{ret}'])
            if config["event_normal_15"] != "disabled":
                ret = await event_normal_sweep(account_info, config["event_normal_15"], config["buy_stamina_passive"], 15)
                if '当前无开放的活动' in ret:
                    config = close_event_config(qqid)
                progress.append(["event_normal_15", f'{ret}'])
            if config["auto_sweep_normal"]:
                progress.append(["auto_sweep_normal", f'{await sweep_normal_smart(account_info)}'])
                
            try:
                stamina_after_allin = await query.get_stamina(account_info)
            except Exception as e:
                break
            if stamina_begin == stamina_after_allin:
                break
            
            if is_bot(qqid):
                config["present_receive"] = "all"
            if config["present_receive"] in ["dated", "all"]:
                progress.append(["present_receive", f'{await present_accept(account_info, config["present_receive"])}'])
            if config["mission_accept_all"]:
                progress.append(["mission_accept_all", f'{await mission_accept_all(account_info)}'])
            if config["buy_stamina_active"]:
                progress.append(["buy_stamina_active", f'{await buy_stamina_active(account_info, config["buy_stamina_active"])}'])
            
            try:
                stamina_end = await query.get_stamina(account_info)
            except Exception as e:
                break
            if stamina_end <= 20:
                break
    # allin
    
    if config["event_hard_boss_sweep"]:
        ret = await event_hard_boss_sweep(account_info, config["event_hard_boss_sweep"])
        if '当前无开放的活动' in ret:
            config = close_event_config(qqid)
        progress.append(["event_hard_boss_sweep", f'{ret}'])
    if config["event_mission_accept"]:
        progress.append(["event_mission_accept", f'{await event_mission_accept(account_info)}'])
    if config["event_gacha"]:
        progress.append(["event_gacha", f'{await event_gacha(account_info)}'])
    if config["flash_shop"]:
        progress.append(["flash_shop", f'{await buy_flash_shop(account_info, (config["buy_exp_count"] > 0))}'])
    if is_bot(qqid):
        config["present_receive"] = "all"
    if config["present_receive"] in ["dated", "all"]:
        progress.append(["present_receive", f'{await present_accept(account_info, config["present_receive"])}'])
    if config["mission_accept_all"]:
        progress.append(["mission_accept_all", f'{await mission_accept_all(account_info)}'])
    if config["season_accept_all"]:
        ret = await season_accept_all(account_info)
        if "已自动关闭该功能" in ret:
            dic = get_sec()
            dic[qqid]["daily_config"]["season_accept_all"] = False
            save_sec(dic)
        progress.append(["season_accept_all", f'{ret}'])
    if config["clan_equip_donation"] != "disabled":
        progress.append(["clan_equip_donation", f'{await clan_equip_donation(account_info, config["clan_equip_donation"])}'])
    if config["clan_chara_support"] or is_bot(qqid):
        progress.append(["clan_chara_support", f'{await clan_chara_support(account_info)}'])
    if config["room_furniture_upgrade"] or is_bot(qqid):
        ret = await room_furniture_upgrade(account_info)
        if "已自动关闭该功能" in ret:
            dic = get_sec()
            dic[qqid]["daily_config"]["room_furniture_upgrade"] = False
            save_sec(dic)
        progress.append(["room_furniture_upgrade", f'{ret}'])
    if config["give_gift"]:
        progress.append(["give_gift", f'{await give_gift(pcrClient)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["give_gift"] = False
        save_sec(dic)
    if config["read_chara_story"]:
        progress.append(["read_chara_story", f'{await read_chara_story(pcrClient)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["read_chara_story"] = False
        save_sec(dic)
    if config["read_main_story"]:
        progress.append(["read_main_story", f'{await read_main_story(account_info)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["read_main_story"] = False
        save_sec(dic)
    if config["read_tower_story"]:
        progress.append(["read_tower_story", f'{await read_tower_story(account_info)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["read_tower_story"] = False
        save_sec(dic)
    if config["read_event_story"]:
        progress.append(["read_event_story", f'{await read_event_story(account_info)}'])
        progress.append(["read_event_story", f'{await read_past_story(account_info)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["read_event_story"] = False
        save_sec(dic)
    if config["read_trust_chapter"]:
        progress.append(["read_trust_chapter", f'{await read_trust_chapter(account_info)}'])
        dic = get_sec()
        dic[qqid]["daily_config"]["read_trust_chapter"] = False
        save_sec(dic)
    if config["eat_pudding"]:
        progress.append(["eat_pudding", f'{await eat_pudding(pcrClient)}'])
    progress.append([f'{nam}', f'{await get_basic_info(account_info)}'])
    progress.append([f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', "发送[清日常结果]可重新调取本记录"])

    try:
        function_list = get_comment()

        def GetKV(key: str) -> Tuple[str, str]:
            if key not in function_list:
                return key, ""
            brief = function_list[key].get("brief", None) or key
            value = "" if function_list[key].get("type", "bool") == "bool" else config[key]
            return brief, value

        def GetRM(msg: str) -> Tuple[str, str]:
            msg = msg.strip()
            match_list = ['Fail.', 'Abort.', 'Warn.', 'Succeed.', 'Skip.', 'Error:', 'Abort:', 'Warn:', 'Succeed:', 'Skip:']
            result = [item for item in match_list if item in msg]
            if len(result) == 0:
                return "", msg
            return result[0][:-1], (msg if len(result) > 1 else msg.replace(result[0], ""))

        outp_pd = {"key": [], "value": [], "result": [], "message": []}
        for i in progress:
            key, value = GetKV(i[0])
            result, message = GetRM(i[1])
            outp_pd["key"].append(key)
            outp_pd["value"].append(value)
            outp_pd["result"].append(result)
            outp_pd["message"].append(message)

        # if int(qqid) == 981082801:
        #     print(outp)
        outp_pd = pd.DataFrame(outp_pd)

        async def outp_draw_img(outp_pd: pd.DataFrame):
            def draw_result(val):
                if 'Skip' in val:
                    return 'background-color: #0FBEC0; color: White'  # 天蓝
                if 'Succeed' in val:
                    return 'background-color: #A1B75D; color: White'  # 草绿
                if 'Abort' in val:
                    return 'background-color: #D0B777; color: White; font-weight: bold'  # 土黄
                if 'Warn' in val:
                    return 'background-color: #B270A2; color: White; font-weight: bold'  # 浅紫
                if 'Fail' in val or 'Error' in val:
                    return 'background-color: #B45A3C; color: White; font-weight: bold'  # 砖红

            outp_pd_styled = outp_pd.style.applymap(draw_result, subset=['result'])
            outp_pd_styled = outp_pd_styled.set_properties(**{'text-align': 'left'})
            save_path = join(curpath, f'daily_result/{qqid}.png')

            def pd2img(outp_pd_styled, save_path, table_conversion) -> bool:
                try:
                    dfi.export(outp_pd_styled, save_path, table_conversion=table_conversion)
                except Exception as e:
                    print(f'\n\n\n----{table_conversion} failed----')
                    print(f'{e}')
                    return False
                return True

            async def pd2img_async(outp_pd_styled, save_path: str, table_conversion: str) -> bool:
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, pd2img, outp_pd_styled, save_path, table_conversion)

            if (await asyncio.create_task(pd2img_async(outp_pd_styled, save_path, 'selenium'))) == False:
                if (await asyncio.create_task(pd2img_async(outp_pd_styled, save_path, 'chrome'))) == False:
                    if (await asyncio.create_task(pd2img_async(outp_pd_styled, save_path, 'matplotlib'))) == False:
                        raise Exception("所有图片导出媒介均遇异常")

            img = pil.Image.open(save_path)
            return img

        outp_img = await outp_draw_img(outp_pd)

        def outp_b64(outp_img) -> str:
            buf = BytesIO()
            outp_img.save(buf, format='PNG')
            base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
            return f'[CQ:image,file={base64_str}]'

        if ev is not None:
            await bot.send(ev, f'[CQ:reply,id={ev.message_id}]{outp_b64(outp_img)}')

    except Exception as e:
        print_exc()
        if ev is not None:
            await bot.send(ev, f'[CQ:reply,id={ev.message_id}]清日常完毕，但渲染结果图片失败：{e}')


async def _do_daily(bot: HoshinoBot, ev: CQEvent):
    dic = get_sec()
    try:
        account_info, qqid, nam = await get_target_account(bot, ev, True)
    except Exception as e:
        return

    if "daily_config" not in dic[qqid]:
        dic[qqid]["daily_config"] = get_config_template()
        save_sec(dic)
        await bot.finish(ev, f'{nam}不存在清日常配置文件，已生成默认配置。\n请添加bot为好友后发送“清日常设置”。设置选项完毕后再次发送 #清日常。')

    if (int(qqid) != int(ev.user_id)) and (dic[qqid]["daily_config"].get("allow_ata_trigger", False) == False) and (int(ev.group_id) not in dic[qqid].get("allow_daily_trigger_group", [])):
        if (not priv.check_priv(ev, priv.SUPERUSER)):
            await bot.finish(ev, f'{nam}禁止他人触发清日常，且您和该群均不在白名单中。程序中止。')

    try:
        await __do_daily(qqid, nam, bot, ev)
    except Exception as e:
        print_exc()
        await bot.finish(ev, f'清日常模块异常终止：{e}')


@sv.on_prefix(("#清日常", "＃清日常"))
async def do_daily(bot, ev):
    await _do_daily(bot, ev)


@sv.on_prefix(("清日常"))
# 清日常<@人> 不ata默认自己
async def do_daily_2(bot, ev):
    if ev.group_id == None:
        await _do_daily(bot, ev)
    else:
        try:
            ata_list = []
            for emsg in ev.message:
                if emsg.type == 'text' and len(emsg.data['text'].strip()) > 0:
                    raise Exception(f'格式错误：存在非空text字段')
                if emsg.type == 'at':
                    if emsg.data['qq'] == 'all':
                        raise Exception(f'格式错误：@all')
                    ata_list.append(str(emsg.data['qq']))
            assert len(ata_list) < 2, f'格式错误：指定多人'
        except Exception as e:
            return
        await bot.send(ev, '在群聊模式下，请使用 #清日常 进行操作。')


# @sv.on_prefix(("清日常广播"))
async def broadcast_do_daily(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    broadcast_msg = ev.message.extract_plain_text().strip()
    dic = get_sec()
    friendnum = await get_friends()
    for qqid in dic:
        if int(qqid) not in friendnum:
            await bot.send(ev, f'{qqid}非好友，广播失败')
            continue
        try:
            await bot.send_private_msg(user_id=int(qqid), message=broadcast_msg)
        except Exception as e:
            await bot.send(ev, f'{qqid}广播失败：{e}')
        await asyncio.sleep(10)


def body_count():
    have_config = 0
    have_effect = 0

    dic = get_sec()
    for qqid in dic:
        if "daily_config" in dic[qqid]:
            have_config += 1
            if len(qqid) > 3:
                have_effect += 1
    return f'{len(dic)}/{have_config}/{have_effect}'


@sv.on_fullmatch(("开启定时清日常", "允许定时清日常"))
async def open_cron(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    with open(join(curpath, 'allow_cron.json'), "w", encoding="utf-8") as fp:
        dump({"allow_cron": True}, fp, ensure_ascii=False, indent=4)  # allow_cron==True表示当前不处于公会战期间
    await bot.send(ev, f'{body_count()}/opened')


@sv.on_fullmatch(("关闭定时清日常", "禁止定时清日常"))
async def close_cron(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    with open(join(curpath, 'allow_cron.json'), "w", encoding="utf-8") as fp:
        dump({"allow_cron": False}, fp, ensure_ascii=False, indent=4)  # allow_cron==False表示当前处于公会战期间
    await bot.send(ev, f'{body_count()}/closed')


async def __clear_event_ticket(semaphore: asyncio.Semaphore, qqid: str) -> str:
    async with semaphore:
        try:
            dic = get_sec()
            account_info = dic[qqid]
            await asyncio.sleep(1)
            await _account_verify(None, None, qqid, account_info, 2)
            await asyncio.sleep(1)
            progress = []
            progress.append(f'{await event_hard_boss_sweep(account_info, "max-2")}')
            # progress.append(f'{await event_mission_accept(account_info)}')
            progress.append(f'{await event_gacha(account_info)}')
            ret = "\n".join(progress)
        except Exception as e:
            print(f'为{qqid}清活动扫荡券失败：{e}')
        else:
            print(f'为{qqid}清活动扫荡券成功：{ret}')
            return ret


is_cleaning_event_ticket = False


@sv.on_fullmatch(("清活动扫荡券", "清空活动扫荡券"))
async def clear_event_ticket(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    global is_cleaning_event_ticket
    if is_cleaning_event_ticket:
        await bot.finish(ev, "指令触发中")
    await bot.send(ev, "triggered")
    is_cleaning_event_ticket = True

    tasks = []
    semaphore = asyncio.Semaphore(5)

    try:
        dic = get_sec()
        total_cnt = len(dic)
        keys = list(dic.keys())
        keys.reverse()
        for cnt, qqid in enumerate(keys):
            if is_bot(qqid):
                continue
            if "daily_config" not in dic[qqid]:
                continue
            if dic[qqid]["daily_config"].get("event_ticket_allow_trigger", False):
                tasks.append(__clear_event_ticket(semaphore, qqid))
        await asyncio.gather(*tasks)
    except Exception as e:
        raise
    finally:
        is_cleaning_event_ticket = False


def get_allow_cron() -> bool:
    if exists(join(curpath, 'allow_cron.json')):
        with open(join(curpath, 'allow_cron.json'), "r", encoding="utf-8") as fp:
            return load(fp)["allow_cron"]
    return True


async def __buy_exp_and_stone_cron(qqid: str) -> str:
    dic = get_sec()
    account_info = dic[qqid]
    config = dic[qqid]["daily_config"]  

    try:
        ret = await buy_exp_and_stone_shop(account_info, config["buy_exp_count"], config["buy_stone_count"])
        if "经验瓶阈值" in ret and "强化石阈值" in ret:
            dic = get_sec()
            dic[qqid]["daily_config"]["buy_exp&stone_mode"] = "follow"
            save_sec(dic)
    except Exception as e:
        dic = get_sec()
        dic[qqid]["daily_config"]["buy_exp&stone_mode"] = "follow"
        save_sec(dic)
        raise    
    return f'{ret}'


async def _buy_exp_and_stone_cron(semaphore: asyncio.Semaphore, qqid: str) -> None:
    async with semaphore:
        try:
            ret = await __buy_exp_and_stone_cron(qqid)
        except Exception as e:
            print(f'为{qqid}购买一天四次商店失败：{e}')
        else:
            print(f'为{qqid}购买一天四次商店成功：{ret}')


@sv.on_fullmatch(('触发定时买药'))
async def trigger_buy_exp_and_stone_cron(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    await bot.send(ev, 'triggered')
    await buy_exp_and_stone_cron()


@sv.scheduled_job('cron', hour='1,7,13,19', minute="20")
async def buy_exp_and_stone_cron():
    allow_cron = get_allow_cron()
    dic = get_sec()

    tasks = []
    semaphore = asyncio.Semaphore(5)

    for qqid in dic:
        if "daily_config" in dic[qqid]:
            config = dic[qqid]["daily_config"]
            if allow_cron or config.get("clan_battle_allow_cron", False) or is_bot(qqid):
                if config.get("buy_exp&stone_mode", "disabled") == "all":
                    if config.get("buy_exp_count", 0) or config.get("buy_stone_count", 0):
                        tasks.append(_buy_exp_and_stone_cron(semaphore, qqid))

    await asyncio.gather(*tasks)


@sv.on_fullmatch(('触发定时清日常'))
async def trigger_daily_cron(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    await bot.send(ev, 'triggered')
    await do_daily_cron()


async def _do_daily_cron(semaphore: asyncio.Semaphore, qqid: str) -> None:
    async with semaphore:
        try:
            print(f'为{qqid}定时清日常')
            await __do_daily(qqid)
        except Exception as e:
            print(f'为{qqid}定时清日常失败：{e}')


@sv.scheduled_job('cron', hour='*', minute="1")
async def do_daily_cron():
    allow_cron = get_allow_cron()

    curr_time = datetime.datetime.now()
    curr_hour = curr_time.hour
    print(f'触发{curr_hour}点自动清日常')

    dic = get_sec()

    if len(dic):
        save_sec_backup(dic)

    tasks = []
    semaphore = asyncio.Semaphore(5)

    for qqid in dic:
        if "daily_config" in dic[qqid]:
            config = dic[qqid]["daily_config"]
            if allow_cron or config.get("clan_battle_allow_cron", False) or is_bot(qqid):
                if config.get("cron_no_response_1", -1) == curr_hour or config.get("cron_no_response_2", -1) == curr_hour:
                    tasks.append(_do_daily_cron(semaphore, qqid))

    await asyncio.gather(*tasks)


# @sv.on_fullmatch(('触发bot清日常'))
async def trigger_bot_cron(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    await bot.send(ev, 'triggered')
    dic = get_sec()
    
    if len(dic):
        save_sec_backup(dic)

    tasks = []
    semaphore = asyncio.Semaphore(5)

    for qqid in dic:
        if "daily_config" in dic[qqid]:
            if is_bot(qqid):
                # if len(qqid) == 2 and 68 <= int(qqid) <= 90: # temp
                    tasks.append(_do_daily_cron(semaphore, qqid))

    await asyncio.gather(*tasks)


async def _change_bot_name(semaphore: asyncio.Semaphore, qqid: str, account_info: dict, new_name: str) -> None:
    async with semaphore:
        print(f'尝试将[{qqid}]更名为[{new_name}]')
        try:
            old_name = await query.get_username(account_info)
        except Exception as e:
            print(f'Fail. 尝试获取[{qqid}]当前pcr昵称失败：{e}')
            return
        if old_name == new_name:
            print(f'Skip. [{qqid}]的当前pcr昵称已为[{new_name}]')
            return
        try:
            await query.query(account_info, '/profile/rename', {"user_name": new_name})
        except Exception as e:
            print(f'Fail. 尝试将[{qqid}]更名为[{new_name}]失败：{e}')
            return
        print(f'Succeed. 将[{qqid}]更名为[{new_name}]成功，尝试更新本地缓存')
        dic = get_sec()
        dic[qqid]["pcrname"] = new_name
        save_sec(dic)
        print(f'Succeed. 将[{qqid}]更名为[{new_name}]成功，更新本地缓存成功')
            
            
# @sv.on_fullmatch(("ebq改名")) # temp
async def change_bot_name(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    await bot.send(ev, 'triggered')
    dic = get_sec()
    
    if len(dic):
        save_sec_backup(dic)

    tasks = []
    semaphore = asyncio.Semaphore(5)

    for qqid in dic:
        if "daily_config" in dic[qqid]:
            if is_bot(qqid):
                if len(qqid) <= 2:
                    tasks.append(_change_bot_name(semaphore, qqid, dic[qqid], f'ebq{qqid}'))                    

    await asyncio.gather(*tasks)


async def get_proper_team(knife: int, box: set = None, boss=[1, 2, 3, 4, 5], stage=4, axistype=[1, 2]) -> str:
    '''
    剩余刀数 
    可用box set(int)
    筛选：boss(int|list[int]) 周目(int|list[int]) 轴类型（手动/auto/尾刀）(int|list[int])
    '''

    # 简要流程（不考虑补偿刀尾刀）
    if box == None:
        box = set([i for i in range(1000, 2000)])
    box = set(box)

    from .clanbattle_timeaxis import get_timeaxis
    battle_array = await get_timeaxis(boss, stage, axistype)
    # [
    #     {
    #         "sn": "A107",
    #         "units": [int],
    #         "damage": int,
    #         "videos": [
    #             {"text":str, "url":str, "note":str},
    #             {...}
    #         ]
    #     },
    #     {
    #         ...
    #     }
    # ]

    def same_chara(x, y):
        return 10 - len(x | y)

    def have_chara(x):
        return len(x & box)

    def have_84(x, y):
        return have_chara(x) >= 8 and have_chara(y) >= 4

    proper_team = []

    battle_array_set = []
    for homework in battle_array:
        battle_array_set.append(set(homework["units"]))

    cnt = len(battle_array)

    if knife == 1:  # 剩1刀没出
        for i in range(cnt):
            x = battle_array_set[i]
            if have_chara(x) >= 4:  # 五个角色里有4个可用即可
                proper_team.append([i])
    elif knife == 2:  # 剩2刀没出
        for i in range(cnt - 1):
            x = battle_array_set[i]
            for j in range(i + 1, cnt):
                y = battle_array_set[j]
                if same_chara(x, y) == 0:  # 如果没有重复
                    if have_chara(x) >= 4 and have_chara(y) >= 4:  # 这两队中每队的5个角色要有4个
                        proper_team.append([i, j])
                elif same_chara(x, y) <= 2:  # 有1~2个重复
                    if have_chara(x | y) >= 8:  # 这两队中出现的角色要有8个
                        proper_team.append([i, j])

    elif knife == 3:  # 剩3刀没出
        for i in range(cnt - 2):
            x = battle_array_set[i]
            for j in range(i + 1, cnt - 1):
                y = battle_array_set[j]
                for k in range(j + 1, cnt):
                    z = battle_array_set[k]

                    jxy, jyz, jxz = same_chara(x, y), same_chara(y, z), same_chara(x, z)  # 获取两两之间重复角色
                    if jxy < 3 and jyz < 3 and jxz < 3 and jxy + jxz + jyz <= 3:
                        # print("无冲，接下来判断当前账号是否可用")
                        if jxy + jxz + jyz == 3:  # 210/111
                            if set(x | y | z).issubset(box):  # 三队中出现的所有角色都要有
                                proper_team.append([i, j, k])
                        elif (jxy == 0) + (jxz == 0) + (jyz == 0) == 2:  # 200/100
                            if jxy and have_84(x | y, z) or jxz and have_84(x | z, y) or jyz and have_84(y | z, x):  # 重复的两队有8个角色 另一队有4个
                                proper_team.append([i, j, k])
                        elif jxy + jxz + jyz == 0:  # 000
                            if have_chara(x) >= 4 and have_chara(y) >= 4 and have_chara(z) >= 4:  # 每队有4个
                                proper_team.append([i, j, k])
                        else:  # 110:
                            if have_chara(x | y | z) >= 12:  # 三队中出现的所有角色（13个）要有任意12个
                                proper_team.append([i, j, k])

    import heapq
    proper_team = heapq.nlargest(6, proper_team, lambda x: sum([battle_array[y]["damage"] for y in x]))
    # proper_team = sorted(proper_team, key=lambda x: sum([battle_array[y]["damage"] for y in x]), reverse=True)

    proper_team_str = []
    sn2videostr = {}
    for team_indexs in proper_team:  # [i,j]
        team_str = []
        for team_index in team_indexs:  # i
            team_info = battle_array[team_index]  # {}
            team_str.append(f'{team_info["sn"]:<5s} {team_info["damage"]:5d}w {" ".join([chara.fromid(unit).name for unit in team_info["units"]])}')
            # for video in team_info["videos"]:
            #     team_str.append(f'{video["text"]} {video["url"]} {video["note"]}')
            # if team_info["sn"] not in sn2videostr:
            #     videostr = []
            #     for video in team_info["videos"]:
            #         videostr.append(f'{video["text"]} {video["url"]} {video["note"]}')
            #     sn2videostr[team_info["sn"]] = '\n'.join(videostr)
        proper_team_str.append('\n'.join(team_str))

    # proper_team_videostr = []
    # for sn, videostr in sn2videostr.items():
    #     if '\n' in videostr:
    #         proper_team_videostr.append(f'{sn:<5s}\n{videostr}')
    #     else:
    #         proper_team_videostr.append(f'{sn:<5s} {videostr}')
    #
    # team_outp = '\n\n'.join(proper_team_str)
    # video_outp = '\n'.join(proper_team_videostr)
    # with open(join(curpath, "timeline_status_temp.txt"), "w", encoding='utf-8') as fp:
    #     print(f'自动配刀：\n{team_outp}\n\n阵容信息：\n{video_outp}', file=fp)
    # return team_outp, video_outp

    team_outp = ('\n\n' if (knife > 1) else "\n").join(proper_team_str)

    # with open(join(curpath, "timeline_status_temp.txt"), "w", encoding='utf-8') as fp:
    #    print(f'自动配刀：\n{team_outp}', file=fp)

    if len(team_outp):
        return f'自动配刀：\n{team_outp}\n\n发送“查轴[轴号]”以获取链接等详细信息。例：查轴{battle_array[proper_team[0][0]]["sn"]}'
    else:
        return '无推荐配刀'


@sv.on_prefix("查轴")
async def get_timeline_detail_info(bot, ev):
    from .clanbattle_timeaxis import get_timeaxis
    battle_array = await get_timeaxis()
    sn = ev.message.extract_plain_text().strip()
    battle_array = list(filter(lambda x: x["sn"] == sn, battle_array))

    if len(battle_array):
        battle_array = battle_array[0]
        await bot.send(ev, f'{battle_array["sn"]:<5s} {battle_array["damage"]:5d}w {" ".join([chara.fromid(unit).name for unit in battle_array["units"]])}' + '\n'.join([f'{video["text"]} {video["url"]}{(chr(10) + video["note"] + chr(10)) if len(video["note"]) else ""}' for video in battle_array["videos"]]))
    else:
        await bot.send(ev, f'未找到轴{sn}')


async def _get_clan_battle_info(account_info, boss, stage, worktype) -> str:
    try:
        info = await query.get_clan_battle_info(account_info)
    except Exception as e:
        return f'Fail. {e}'
    else:
        s = []
        s.append(f'今日体力点：{info.get("point", "unknown")}/900')
        s.append(
            f'未出整刀数：{info.get("remaining_count", "unknown")}刀/共{info.get("point", 900)//300}刀'
        )

        knife_left = info.get("remaining_count", 0) + 3 - info.get("point", 900) // 300
        used_unit_id = info.get("used_unit", [])

        used_unit_str = " ".join([chara.fromid(int(unit) // 100).name for unit in used_unit_id])
        s.append(f'已用角色：{used_unit_str if used_unit_str != "" else "无"}')

        using_unit_id = info.get("using_unit", [])
        using_unit_str = " ".join([chara.fromid(int(unit) // 100).name for unit in using_unit_id])
        if using_unit_str == "":
            s.append(f'补偿刀：无')
        else:
            s.append(f'补偿刀：{info.get("carry_over_time", "unknown")}秒')
            s.append(f'补偿角色：{using_unit_str}')

        s = '\n'.join(s)
        if knife_left:
            from ...autobox import _get_box_id_list_from_pcrid
            user_box = set(_get_box_id_list_from_pcrid(account_info["pcrid"]))
            # print(f'该账号拥有的角色\n{user_box}')
            used_box = set(int(uid) // 100 for uid in used_unit_id)
            # print(f'今日出刀已用角色 {used_unit_str}\n{used_box}')
            avail_box = user_box - used_box
            # print(f'该账号当前实际可用角色\n{avail_box}')
            if len(avail_box):
                team_str = await get_proper_team(knife_left, avail_box, boss, stage, worktype)
                return f'{s}\n{team_str}\n发送“自动配刀帮助”获取详细筛选方式'

        return s

team_match_auto_help_str = '''
自动获取该账号今日当前可用角色（会上号）。
随后给出可选配刀组合，按伤害降序排序，输出前6套。
可以按boss号、周目、刀型筛选。

指令：
# 自动配刀
# 自动配刀@somebody
# 自动配刀@somebody [boss号] [周目] [刀型]

boss号：默认为12345
周目：默认为4（D面）
刀型：默认为12（1为手动刀，2为auto刀，3为尾刀）

例：查询ellye当前可出的，目标boss为D2D3的尾刀轴：
# 自动配刀@ellye 23 4 3
'''.strip()


@sv.on_prefix(("自动配刀帮助"))
async def team_match_auto_help(bot, ev):
    await bot.send(ev, team_match_auto_help_str)


async def get_team_match_params(bot, ev):
    msg = ev.message.extract_plain_text().strip().split()

    def preprocess(st: str, mi: int, ma: int):
        lis = list(sorted(list(set([int(i) if i.isdigit() and int(i) >= mi and int(i) <= ma else 0 for i in st]) - set([0]))))
        return lis if len(lis) else [i for i in range(mi, ma + 1)]
    boss = [1, 2, 3, 4, 5]
    stage = [4]
    worktype = [1, 2]
    stagename = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
    worktypename = {1: "手动", 2: "auto", 3: "尾"}
    if len(msg) >= 3:
        boss = preprocess(msg[-3], 1, 5)
        stage = preprocess(msg[-2], 1, 4)
        worktype = preprocess(msg[-1], 1, 3)
    # elif len(msg) == 2:
    #     await bot.send(ev, f"参数数量错误！\n\n{team_match_auto_help_str}")
    #     raise RuntimeError("Number of Params Error")
    ss = f'筛选{"".join([stagename[k] for k in stage])}面{"".join([str(l) for l in boss])}号boss的{"/".join([worktypename[j] for j in worktype])}刀'
    return boss, stage, worktype, ss

team_match_help_str = '''
根据指定给出可选配刀组合，按伤害降序排序，输出前6套。

指令：
配刀 [刀数] [boss号] [周目] [刀型]
boss号：1~5 周目：1~4
刀型：1为手动刀，2为auto刀，3为尾刀

例：查询C面三刀组合阵容：
配刀 3 12345 3 12
'''.strip()


@sv.on_prefix(("配刀帮助"))
async def team_match_help(bot, ev):
    await bot.send(ev, team_match_help_str)


@sv.on_prefix(("配刀"))
async def get_team_match(bot, ev):
    try:
        knife = max(1, min(3, int(ev.message.extract_plain_text().strip().split()[0])))
    except:
        await bot.send(ev, f'参数错误！\n\n{team_match_help_str}')
    boss, stage, worktype, ss = await get_team_match_params(bot, ev)
    ss = ss.strip() + f' {knife}刀组合'
    ret = await get_proper_team(knife, None, boss, stage, worktype)
    await bot.send(ev, f'{ss}\n{ret}\n发送“配刀帮助”获取详细筛选方式')


@sv.on_prefix(("#自动配刀"))
# 自动配刀<@人> 不ata默认自己
async def get_team_match_auto(bot, ev):
    try:
        account_info, qqid, nam = await get_target_account(bot, ev, True)
    except:
        return

    boss, stage, worktype, ss = await get_team_match_params(bot, ev)
    clan_battle_info = await _get_clan_battle_info(account_info, boss, stage, worktype)
    await bot.send(ev, f'{nam}\n{ss}\n{clan_battle_info}')


def PraseUnitInfo(unit_info: dict) -> str:
    unit_id:int = int(f'{str(unit_info["id"])[:4]}01')
    unit_level = unit_info["unit_level"]
    unit_rarity = unit_info["unit_rarity"]
    battle_rarity = unit_info["battle_rarity"] or unit_rarity
    ub_level = "/".join([str(x["skill_level"]) for x in unit_info.get("union_burst", [])]) or "unknown"
    skill_level = "/".join([str(x["skill_level"]) for x in unit_info.get("main_skill", [])]) or "unknown"
    ex_level = "/".join([str(x["skill_level"]) for x in unit_info.get("ex_skill", [])]) or "unknown"
    equip_slot = "".join(["-" if x["is_slot"] == 0 else str(x["enhancement_level"]) for x in unit_info.get("equip_slot", [])])
    unique_slot = "".join(["-" if x["is_slot"] == 0 else str(x["enhancement_level"]) for x in unit_info.get("unique_equip_slot", [])])
    equip_num = len([1 for x in unit_info.get("equip_slot", []) if x["is_slot"] == 1])
    rank = f'R{unit_info["promotion_level"]}-{equip_num}({equip_slot})'
    return f'角色当前状态：\n{battle_rarity}({unit_rarity})x {unit_level}级\n{rank} {unique_slot}专\nub={ub_level} 技能={skill_level} ex={ex_level}'
    


async def _change_support_unit(account, support_unit_id: int, mode: int):  # 1=地下城 2=团队战/露娜塔 3=关卡
    support_unit_id:int = int(f'{str(support_unit_id)[:4]}01')
    support_unit_name:str = f'[{chara.fromid(support_unit_id // 100).name}]'
    try:
        unit_info = await query.get_unit_info(account, support_unit_id)
    except Exception as e:
        return f'Fail. 获取{support_unit_name}数据失败：{e}'
    if unit_info["unit_level"] <= 10:
        return f'Abort. {support_unit_name}的等级({unit_info["unit_level"]})过低(<=10级)，不可设置支援。'
    try:
        ret = await query.get_support_unit_setting(account)
    except Exception as e:
        return f'Fail. 获取当前支援设定失败：{e}'
    try:
        server_time = await query.get_server_time(account)
    except Exception as e:
        return f'Fail. 获取当前服务器时间失败：{e}'

    # 地下城：clan_support_units support_type=1 position=1/2 mode=1 
    # 团队战/露娜塔：clan_support_units support_type=1 position=3/4 mode=2 
    # 关卡：friend_support_units support_type=2 position=1/2 mode=3 
    # "action": 1=上 2=下
    # "unit_id": xxxx01
    
    当前支援状态 = {
        1: [x for x in ret["clan_support_units"] if x["position"] in [1, 2]],
        2: [x for x in ret["clan_support_units"] if x["position"] in [3, 4]],
        3: ret["friend_support_units"]
    }
    目标支援组:list = 当前支援状态[mode]
    mode2str = {
        1: "地下城",
        2: "团队战/露娜塔",
        3: "关卡"
    }
    目标支援字符串:str = f'{mode2str[mode]}支援'

    if len([x for x in 目标支援组 if x["unit_id"] == support_unit_id]): # 查询是否在目标支援中。
        return f'Skip. {support_unit_name}当前已位于{目标支援字符串}'
    
    坑位 = [1, 2] if mode != 2 else [3, 4] # 查询目标支援是否有坑位。
    if len(目标支援组) == 0: # 若有坑位，记录坑位。
        坑位 = 坑位[0]
    elif len(目标支援组) == 1:
        坑位 = list(set(坑位) - set([目标支援组[0]["position"]]))[0]
    else: # 若无坑位，查询是否可终止原支援
        坑位 = 0
        可终止目标 = [x for x in 目标支援组 if server_time - x["support_start_time"] > 1800]
        if len(可终止目标) == 0: # 若无法终止原支援，程序终止
            return f'Abort. {目标支援字符串}当前已挂满且均不足30分钟，无法结束支援'
        可终止目标 = min(可终止目标, key=lambda x: x["support_start_time"]) # 若两个都可终止，终止挂的时间较早的那个

    outp = []
    for m, 支援组 in 当前支援状态.items():
        if m != mode:
            过滤支援状态组 = [x for x in 支援组 if x["unit_id"] == support_unit_id] # 查询是否在其它类型的支援中。
            if len(过滤支援状态组): # 若在，尝试结束支援。
                目标角色支援状态 = 过滤支援状态组[0]
                当前支援字符串:str = f'{support_unit_name}当前正在{mode2str[m]}支援'
                if server_time - 目标角色支援状态["support_start_time"] < 1800: # 若无法结束，终止程序
                    return f'Abort. {当前支援字符串}，且挂上不足30分钟，无法结束支援'
                try:
                    await query.query(account, "/support_unit/change_setting", {
                        "support_type": 2 if m == 3 else 1,
                        "position": 目标角色支援状态["position"],
                        "action": 2,
                        "unit_id": support_unit_id
                    })
                except Exception as e:
                    return f'Fail. {当前支援字符串}，尝试结束支援失败：{e}'
                else:
                    outp.append(f'Info. {当前支援字符串}，已成功结束支援')

    if 坑位 == 0: # 若上面记录无坑位，则终止之前选定的坑位
        可终止角色id:int = 可终止目标["unit_id"]
        可终止角色名:str = f'[{chara.fromid(可终止角色id // 100).name}]'
        可终止位置:int = 可终止目标["position"]
        try:
            await query.query(account, "/support_unit/change_setting", {
                "support_type": 2 if mode == 3 else 1,
                "position": 可终止位置,
                "action": 2,
                "unit_id": 可终止角色id
            })
        except Exception as e:
            outp.append(f'Fail. {目标支援字符串}当前已挂满。尝试终止其中{可终止角色名}支援失败：{e}')
            return "\n".join(outp)
        else:
            坑位 = 可终止位置
            outp.append(f'Info. {目标支援字符串}当前已挂满。成功终止其中{可终止角色名}支援。')
    
    try: # 上公会支援
        await query.query(account, "/support_unit/change_setting", {
            "support_type": 2 if mode == 3 else 1,
            "position": 坑位,
            "action": 1,
            "unit_id": support_unit_id
        })
    except Exception as e:
        outp.append(f'Fail. 尝试将{support_unit_name}挂上{目标支援字符串}失败：{e}')
        return "\n".join(outp)
    else:
        outp.append(f'Succeed. 成功将{support_unit_name}挂上{目标支援字符串}')
    
    outp.append(PraseUnitInfo(unit_info))
    return "\n".join(outp)
    
    

async def change_support_unit(bot: HoshinoBot, ev: CQEvent):
    account_info, qqid, nam = await get_target_account(bot, ev, False)
    support_unit = ev.message.extract_plain_text().strip()
    if support_unit == "":
        await bot.send(ev, "#上公会支援@somebody 角色名\n不@则为自己号")
        raise Exception("参数错误")
    support_unit_id = chara.roster.get_id(support_unit)
    if support_unit_id == 1000:
        _, name, score = chara.guess_id(support_unit)
        await bot.send(ev, f'无法识别"{support_unit}"' + (f'您说的有{score}%可能是{name}' if score > 70 else ""))
        raise Exception("参数错误")
    return account_info, support_unit_id


@sv.on_prefix(("上地下城支援", "挂地下城支援"))
async def change_dungeon_support_unit_private(bot, ev):
    if ev.group_id is None:
        await change_dungeon_support_unit(bot, ev)
    else:
        await bot.send(ev, '在群聊模式下，请使用 #上地下城支援 进行操作。')


@sv.on_prefix(("#上地下城支援", "#挂地下城支援"))
async def change_dungeon_support_unit(bot, ev):
    account_info, support_unit_id = await change_support_unit(bot, ev)
    await bot.send(ev, await _change_support_unit(account_info, support_unit_id, 1))


@sv.on_prefix(("上公会支援", "挂公会支援", "上公会站支援", "挂公会站支援", "上会战支援", "挂会战支援", "上露娜支援", "挂露娜支援", "上露娜塔支援", "挂露娜塔支援"))
async def change_clan_support_unit_private(bot, ev):
    if ev.group_id is None:
        await change_clan_support_unit(bot, ev)
    else:
        await bot.send(ev, '在群聊模式下，请使用 #上公会支援 进行操作。')


@sv.on_prefix(("#上公会支援", "#挂公会支援", "#上公会站支援", "#挂公会站支援", "#上会战支援", "#挂会战支援", "#上露娜支援", "#挂露娜支援", "#上露娜塔支援", "#挂露娜塔支援"))
async def change_clan_support_unit(bot, ev):
    account_info, support_unit_id = await change_support_unit(bot, ev)
    await bot.send(ev, await _change_support_unit(account_info, support_unit_id, 2))


@sv.on_prefix(("上关卡支援", "挂关卡支援"))
async def change_quest_support_unit_private(bot, ev):
    if ev.group_id is None:
        await change_quest_support_unit(bot, ev)
    else:
        await bot.send(ev, '在群聊模式下，请使用 #上关卡支援 进行操作。')


@sv.on_prefix(("#上关卡支援", "#挂关卡支援"))
async def change_quest_support_unit(bot, ev):
    account_info, support_unit_id = await change_support_unit(bot, ev)
    await bot.send(ev, await _change_support_unit(account_info, support_unit_id, 3))


@sv.scheduled_job('interval', hours=12)
@sv.on_fullmatch('更新花舞组轴表')
async def update_axis(*args):
    from .clanbattle_timeaxis import update_timeaxis
    await update_timeaxis()

    # from .clanbattle_timeaxis import get_timeaxis  # test
    # print(await get_timeaxis([2, 3], 4))  # test


@sv.on_fullmatch('axistest')
async def axistest(*args):
    bbox = [
        1025, 1026, 1027, 1028, 1029, 1030, 1031, 1032, 1033,
        1036, 1037, 1038, 1040, 1042, 1043, 1044, 1045, 1046,
        1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1055,
        1056, 1057, 1058, 1059, 1060, 1061, 1063, 1065, 1066,
        1070, 1075, 1076, 1078, 1079, 1080, 1081, 1082, 1083,
        1084, 1085, 1086, 1087, 1088, 1089, 1090, 1091, 1092,
        1093, 1094, 1095, 1096, 1097, 1098, 1100, 1101, 1104,
        1105, 1106, 1107, 1110, 1111, 1112, 1113, 1114, 1115,
        1116, 1117, 1119, 1120, 1121, 1122, 1123, 1124, 1125,
        1126, 1127, 1128, 1129, 1130, 1131, 1132, 1134, 1135,
        1136, 1701, 1702, 1802, 1804, 1001, 1004, 1005, 1006,
        1007, 1008, 1009, 1010, 1011, 1012, 1013, 1014, 1015,
        1016, 1017, 1018, 1020, 1021, 1022, 1023
    ]
    await get_proper_team(2, set(bbox))
# 优衣 怜 优花梨 克莉丝提娜 咲恋(夏日) 可可萝(公主)

@on_startup
async def test_on_startup_interface():
    asyncio.create_task(test_on_startup())
    
async def test_on_startup():
    ...    
    # dic = get_sec()
    # account_info = dic['491673070']
    # pcrClient = PcrApi(account_info)
    # await pcrClient.Login()
    # print(await eat_pudding(pcrClient))
