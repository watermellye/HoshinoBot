from json import load, dump
from traceback import print_exc
from hoshino import priv
from os.path import dirname, join, exists
#from ..query.safeservice import SafeService
from hoshino import Service
import time
from ..priconne.pcr_secret import getSecret, get_group_member_qqid_list
from ..priconne import chara
from . import json2excel
from ..query import query

sv_help = f'''提交账号密码后可以使用本插件自动填表！
[查box] bot会登录您的账号以获取您的详细box至数据库，随后自动调用 填box 模块。

其它指令：
[自动填表帮助]
[填box <pcrid>] 根据数据库中详细box，提取简洁box。随后自动调用 xjbbox 模块。
[xjbbox <pcrid>] 根据数据库中的简介box，提取小甲板版box。
[导出box] 仅怡宝有效
'''.strip()

sv = Service('getBox', help_=sv_help, visible=False)

curpath = dirname(__file__)

with open(join(curpath, 'equip_name.json'), "r", encoding="utf-8") as fp:
    equip2name = load(fp)

with open(join(curpath, 'equip_list.json'), encoding='utf-8') as fp:
    equip2list = load(fp)


def nowtime():
    return int(time.time())


async def _get_box_error(bot, ev, info, msg=""):
    await bot.send(ev, f'登录失败：{msg}\n请检查您的账号密码。')
    await bot.send_private_msg(
        user_id=ev.user_id,
        message=f'您登记的账号密码为：{info["account"]}\n{info["password"]}\n请发送 pcr <账号> <密码> 以更新。'
    )


async def _get_box(bot, ev, info, ret=0):
    try:
        pcr_info = await query.get_load_index(info)
        if len(str(pcr_info)) < 500:
            await _get_box_error(bot, ev, info, str(pcr_info)[:100])
            return
    except Exception as e:
        await _get_box_error(bot, ev, info, repr(e))
        return
    else:
        try:
            pcrid = pcr_info["user_info"]["viewer_id"]
        except Exception as e:
            await _get_box_error(bot, ev, info, repr(e))
            return
        else:
            save_path = join(curpath, "box", f'{pcrid}_origin.json')
            with open(save_path, "w", encoding="utf-8") as fp:
                dump(pcr_info, fp, ensure_ascii=False, indent=4)
            if ret == 0:
                await bot.send(ev, f'源数据获取成功，自动触发指令：[填box {pcrid}]')
            await _get_box_format(bot, ev, pcrid, ret)


@sv.on_fullmatch(("查box"))
async def get_box(bot, ev):
    uid = ev.user_id
    info = getSecret(uid)
    if info["status"] == False:
        await bot.send(ev, "请先登记账号密码！\n指令：pcr <账号> <密码>")
        return
    info = info["message"]
    await _get_box(bot, ev, info)


def format_box(load_index):
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
                nam = equip2name[nam]  # 注意实装前看一下编号头
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

        if ("unique_equip_slot"
                not in unit) or ("unique_equip_slot" in unit
                                 and len(unit["unique_equip_slot"]) == 0):
            box[id]["专武"] = "未实装"
        elif unit["unique_equip_slot"][0]["is_slot"] == 0:
            box[id]["专武"] = 0
        else:
            box[id]["专武"] = unit["unique_equip_slot"][0]["enhancement_level"]
        #box[id]["战力"] = unit["power"]

    read_story_ids = load_index["read_story_ids"]
    for story_id in read_story_ids:
        id = story_id // 1000
        if id > 2000:
            break
        if id not in box:
            continue
        love = story_id % 1000
        box[id]["好感"] = max(box[id]["好感"], love)

    #user_chara_info = load_index["user_chara_info"]
    # for unit in user_chara_info:
    #    id = unit["chara_id"]
    #    if id in box:
    #        box[id]["好感"] = unit["love_level"]
    return box


async def _get_box_format(bot, ev, pcrid, ret=0):
    """
    将origin转换为format。
    当ret=0时输出状态
    当ret=1时返回{"status":bool, "message":dict | None}.
    """
    save_path = join(curpath, "box", f'{pcrid}_origin.json')
    if exists(save_path):
        with open(save_path, "r", encoding="utf-8") as fp:
            box_info = load(fp)
        box_info_format = format_box(box_info)
        with open(join(curpath, "box", f'{pcrid}_format.json'), "w", encoding="utf-8") as fp:
            dump(box_info_format, fp, ensure_ascii=False, indent=4)
        if ret == 0:
            await bot.send(ev, f'box数据获取成功，自动触发指令：[xjbbox {pcrid}]')
        return await _get_box_xjb(bot, ev, pcrid, ret)
    else:
        if ret:
            return {
                "status": False,
                "message": f'FileNotFound:{pcrid}_origin.json'
            }
        await bot.send(ev, f'pcrid={pcrid}未在本bot登记box\n请发送 <查box> 以授权bot获取您的box')


@sv.on_prefix(("填box"))
async def get_box_format(bot, ev):
    pcrid = ev.message.extract_plain_text().strip()
    if pcrid == "":
        uid = ev.user_id
        info = getSecret(uid)
        if info["status"] == True and "pcrid" in info["message"]:
            pcrid = info["message"]["pcrid"]
            await bot.send(ev, f'已将该指令重定向为：[填box {pcrid}]')
            await _get_box_format(bot, ev, pcrid)
        else:
            await bot.send(ev, sv_help)
    else:
        await _get_box_format(bot, ev, pcrid)


xjb_inp = '''
春黑			羽衣		水流夏		春妈			油腻仙贝			蝶妈			优花梨（黄骑）			春猫				圣诞熊锤				猫剑				初音			驴			魔驴		露娜		千歌				欧尼酱					水电			雪哥			生菜		魔栞		mcw		圣诞克		圣诞伊利亚		露		水老师			大江户空花			可可萝（妈）			深月			栞（tp弓）			姬塔（吉他）			日和莉（猫拳）			美里（圣母）		凯露（普黑）				万圣美咲（瓜眼）		似似花			水壶			安			龙姬			露			矛依未（511）			真琴（狼）			水狼			凛		卯月				克莉丝提娜（克总）				环奈			惠理子（病娇）			情病			情姐				香织（狗）				亚里莎（yls）			智			忍			怜（剑圣）			忍扇			春剑		水暴弓			咲恋（充电宝）			咕噜灵波				高达佩可		水妈（水白）			纯（黑骑）			流夏				水猫剑		水黑				杏奈（中二）			伊里（姐法）			伊莉亚（yly）			新年优衣（春田）				六星优衣					春女仆				茜里（妹法）			依里(姐法)			七七香			镜华（xcw）			松鼠			圣母			TP弓			水吃			水猫剑			水子龙			水女仆		万圣兔		水狗			吉塔			毛二力			水中二
星级	rank	等级	星级	rank	星级	rank	星级	rank	等级	星级	rank	ex等级	星级	rank	等级	星级	rank	专武	星级	rank	等级	专武	星级	rank	1技能等级	专武	星级	rank	二技能等级	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	星级	rank	等级	专武	星级	rank	专武	等级	UB	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	星级	rank	星级	rank	星级	rank	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	专武	等级	星级	rank	星级	rank	等级	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	2技能	ex	星级	rank	专武	有没有圣克	星级	rank	有无春环	星级	rank	专武	星级	rank	专武	星级	rank	专武	姐姐本体好感	星级	rank	专武	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	专武	星级	rank	专武	星级	rank	专武	等级	星级	rank	星级	rank	专武	星级	rank	专武	星级	rank	ex	专武	星级	rank	星级	rank	专武	等级	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	1技能	星级	rank	专武	1技能	ub	星级	rank	等级	普通女仆好感	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank	星级	rank	星级	rank	专武	星级	rank	专武	星级	rank	专武	星级	rank
'''


def xjb_box(box_info):
    return json2excel.xjb_excel(xjb_inp, box_info)


async def _get_box_xjb(bot, ev, pcrid, ret=0):
    save_path = join(curpath, "box", f'{pcrid}_format.json')
    if exists(save_path):
        with open(save_path, "r", encoding="utf-8") as fp:
            box_info = load(fp)
        box_info_xjb = "\t".join(xjb_box(box_info))
        with open(join(curpath, "box", f'{pcrid}_xjb.txt'),
                  "w",
                  encoding="utf-8") as fp:
            print(box_info_xjb, file=fp)
        if ret == 0:
            await bot.send(ev, f'xjb版数据获取成功。您的任务已完成，请等待管理员导出。')
        return {"status": True, "message": box_info_xjb}
    else:
        if ret:
            return {
                "status": False,
                "message": f'FileNotFound:{pcrid}_format.json'
            }
        await bot.send(ev,
                       f'pcrid={pcrid}未在本bot登记box\n请发送 <查box> 以授权bot获取您的box')


@sv.on_prefix(("xjbbox"))
async def get_box_xjb(bot, ev):
    pcrid = ev.message.extract_plain_text().strip()
    if pcrid == "":
        uid = ev.user_id
        info = getSecret(uid)
        if info["status"] == True and "pcrid" in info["message"]:
            pcrid = info["message"]["pcrid"]
            await bot.send(ev, f'已将该指令重定向为：[xjbbox {pcrid}]')
            await _get_box_xjb(bot, ev, pcrid)
        else:
            await bot.send(ev, sv_help)
    else:
        await _get_box_xjb(bot, ev, pcrid)


async def _get_info(info: dict) -> dict:
    """
    :param info: {"account": str, "password": str, "qqid": int = None}
    :returns: {"status": bool, "message": str | dict}
    """
    try:
        await query.VerifyAccount(info)
        pcr_info = await query.get_load_index(info)
        if len(str(pcr_info)) < 500:
            return {"status": False, "message": str(pcr_info)}
    except Exception as e:
        print_exc()
        return {"status": False, "message": str(e)}
    else:
        try:
            info = {}
            info["pcrid"] = pcr_info["user_info"]["viewer_id"]
            info["pcrname"] = pcr_info["user_info"]["user_name"]
        except Exception as e:
            return {"status": False, "message": e}
        else:
            save_path = join(curpath, "box", f'{info["pcrid"]}_origin.json')
            with open(save_path, "w", encoding="utf-8") as fp:
                dump(pcr_info, fp, ensure_ascii=False, indent=4)
            return {"status": True, "message": info}


@sv.on_fullmatch(("导出box"))
async def box_export(bot, ev):
    if (not priv.check_priv(ev, priv.SUPERUSER)):
        return
    outp_excel = []
    accounts_info = getSecret()["message"]
    group_member_qqid_list = await get_group_member_qqid_list(bot, ev)
    for qqid in accounts_info:
        if group_member_qqid_list != [] and str(
                qqid) not in group_member_qqid_list:
            continue
        info = accounts_info[qqid]
        nam = info.get("pcrname", info.get("name", qqid))
        outp_line = [
            nam,
            str(qqid),
            info.get("updatetime", "unknown").split('.')[0], "", "", "",
            info.get("contact", ""), ""
        ]
        if "pcrid" in info:
            pcrid = info["pcrid"]
            save_path = join(curpath, "box", f'{pcrid}_origin.json')
            # if not exists(save_path):
            #    await _get_box(bot, ev, {"account": info["account"], "password": info["password"]}, 1, 1)
            if exists(save_path):
                with open(save_path, "r", encoding="utf-8") as fp:
                    box_info = load(fp)
                item_list = box_info["item_list"]
                mzs = list(filter(lambda x: x["id"] == 90005, item_list))
                try:
                    outp_line[3] = f'{mzs[0]["stock"]}'
                except:
                    outp_line[3] = "0"
                outp_line[
                    4] = f'{box_info["user_jewel"].get("free_jewel",0)+box_info["user_jewel"].get("paid_jewel",0)}'
                outp_line[
                    5] = f'{box_info["user_gold"].get("gold_id_free",0)+box_info["user_gold"].get("gold_id_pay",0)}'

            ret = await _get_box_format(bot, ev, pcrid, 1)
            outp_line.append(ret["message"])
        else:
            outp_line.append("pcrid未知")
        outp_excel.append('\t'.join(outp_line))
    xjb_outp = xjb_inp.strip().split('\n')
    xjb_outp_formatted = f" \t \t \t \t \t \t \t \t{xjb_outp[0]}\n"
    xjb_outp_formatted += f"游戏昵称\tqqid\t更新时间\t母猪石\t钻石\tMANA\t联系方式\t备注栏\t{xjb_outp[1]}\n"

    nowtimestamp = nowtime()
    with open(join(curpath, "box", f'0_box_all.txt'), "w",
              encoding="utf-8") as fp:
        print(xjb_outp_formatted + '\n'.join(outp_excel), file=fp)
    await bot.send(ev, f'导出成功\n请前往插件根目录./box/查看')


def _get_box_format_from_pcrid(pcrid):
    '''
    return {"status": True, "message": <format.json>}
    {"status": False, "message": "file not exist"}
    '''
    save_path = join(curpath, "box", f'{pcrid}_format.json')
    if exists(save_path):
        with open(save_path, "r", encoding="utf-8") as fp:
            return {"status": True, "message": load(fp)}
    return {"status": False, "message": "file not exist"}


def _get_info_from_pcrid(inp, pcrid):
    box_info = _get_box_format_from_pcrid(pcrid)
    return box_info if box_info["status"] == False else json2excel.xjb_excel(
        inp, box_info["message"], 1)


def _get_box_id_list_from_pcrid(pcrid, exception=False):
    '''
    return [int]
    exception || return []
    '''
    box_info = _get_box_format_from_pcrid(pcrid)
    if box_info["status"] == False:
        if exception:
            raise RuntimeError(box_info["message"])
        else:
            return []
    box_id_list = []
    for key in box_info["message"]:
        box_id_list.append(int(key))
    return box_id_list
