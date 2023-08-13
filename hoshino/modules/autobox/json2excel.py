import json
from os.path import dirname, join

with open(join(dirname(__file__), "CHARA_NAME.json"), "r",
          encoding="utf-8") as fp:
    names = json.load(fp)

names_special = {"欧尼酱": "圣千", "高达佩可": "高达", "六星优衣": "优衣", "油腻仙贝": "优妮"}

from difflib import SequenceMatcher


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()  # 引用ratio方法，返回序列相似性的度量


def get_id(nam, simi=True):
    nam = nam.strip().replace('（', '(').replace('）', ')').lower()
    if nam in names_special:
        nam = names_special[nam]
    global names
    for i in names:
        if nam in names[i]:
            return i
    if '(' in nam:
        nam = nam.replace(')', '').split('(')
        # print(nam)
        for i in nam:
            na = get_id(i, False)
            if na != False:
                # print(na)
                return na

    if simi:
        simi_max = 0
        simi_name = "UNKNOWN"
        simi_id = 1000
        for i in names:
            for j in names[i]:
                si = similarity(nam, j)
                if si > simi_max:
                    simi_max = si
                    simi_name = j
                    simi_id = i
        if simi_max >= 0.8:
            names_special[nam] = simi_name
            print(
                f"Automatic identification: {nam}->{simi_name}({simi_id}) ({simi_max*100:.2f}%)"
            )
            return simi_id
    return False


def xjb_excel(inp: str, box: dict, strict: bool = 0):
    #print(inp, len(box), strict)
    dic = {
        "星级": '["星级"]',
        "rank": '["rank_detail"]',
        "品级": '["rank_detail"]',
        "ex": '["技能等级"]["被动"]',
        "ex技能": '["技能等级"]["被动"]',
        "ex等级": '["技能等级"]["被动"]',
        "被动": '["技能等级"]["被动"]',
        "被动等级": '["技能等级"]["被动"]',
        "被动技能": '["技能等级"]["被动"]',
        "ub": '["技能等级"]["ub"]',
        "等级": '["等级"]',
        "专武": '["专武"]',
        "技能": '["技能等级"]["all"]',
        "1技能": '["技能等级"]["skill1"]',
        "一技能": '["技能等级"]["skill1"]',
        "2技能": '["技能等级"]["skill2"]',
        "二技能": '["技能等级"]["skill2"]',
        "好感": '["好感"]',
        "战力": '["战力"]'
    }
    dic_special = {
        "普通女仆好感": 'box["1025"]["好感"] if "1025" in box else "无"',
        "有没有圣克": '("有，好感度"+str(box["1115"]["好感"])) if "1115" in box else "无"',
        "有无春环": '"有" if "1702" in box else "无"',
        "姐姐本体好感": 'box["1049"]["好感"] if "1049" in box else "无"'
    }
    inp = inp.strip().split()
    unit = []
    tot = 0
    for cnt, nam in enumerate(inp):
        if nam == "星级":
            tot = cnt
            break
        else:
            unit.append(nam)
    cnt = -1
    output = []
    id = "UNKNOWN"
    for i in range(tot, len(inp)):
        tag = inp[i].lower()
        tag = tag.replace("技能等级", "技能")
        if tag == "星级":
            cnt += 1
            id = get_id(unit[cnt])
            #print(id, unit[cnt])
            if id == False:
                print(f"Unprocessed name: {unit[cnt]}")
            elif str(id) not in box:
                # print(f"box中无{id}({unit[cnt]})")
                pass
        if id == False:
            if strict:
                return {
                    "status": False,
                    "message": f"Unprocessed name: {unit[cnt]}"
                }
            output.append("Error")
            continue
        id = str(id)
        if str(id) not in box:
            output.append("无")
            continue

        if tag in dic:
            # print(f'box[{unit[cnt]}]{dic[tag]}')
            try:
                output.append(str(eval(f'box["{id}"]{dic[tag]}')))
            except:
                if tag == "2技能":
                    output.append("0")
                else:
                    output.append("无")
        elif tag in dic_special:
            try:
                #print(f'special tag: {tag} - {dic_special[tag]} - {str(eval(dic_special[tag]))}')
                output.append(str(eval(dic_special[tag])))
            except:
                print(
                    f"special tag Error: {tag} - {dic_special[tag]}\t\tname={unit[cnt]} id={id}"
                )
                output.append("Error")
        else:
            if strict:
                return {"status": False, "message": f"Unprocessed tag: {tag}"}
            print(f"Unprocessed tag: {tag}")
    if strict:
        return {"status": True, "message": output}
    return output
