from quart import render_template, request, url_for, make_response, jsonify, Blueprint, Response, send_from_directory
from pathlib import Path
from json import load, dump, dumps
import shutil
import asyncio
import nonebot
from ..pcr_secret import __do_daily, get_sec, save_sec
import datetime
import hashlib
import random
import string

gs_currentDir = Path(__file__).parent
gs_pcrSecretDir = gs_currentDir.parent / "pcr_secret"

auto_pcr_web = Blueprint('autopcr', __name__, template_folder="templates", static_folder='static', static_url_path='/static', url_prefix="/autopcr")
bot = nonebot.get_bot()
app = bot.server_app
#app.config["SEND_FILE_MAX_AGE_DEFAULT"] = datetime.timedelta(seconds=3)

def getNowtime() -> int:
    return int(datetime.datetime.timestamp(datetime.datetime.now()))

async def make_response_json(statusCode: int = 200,
                       message: str = "",
                       data: dict = {},
                       success: bool = None,
                       quick_response: list = None):
    '''
    :params quick_response: [statusCode（若为0，则自动改为200）, message]
    如果success未指定，则当statusCode==200时为True，否则False
    '''
    if type(quick_response) == list and len(quick_response) == 2:
        statusCode = quick_response[0]
        if statusCode == 0:
            statusCode = 200
        message = quick_response[1]
    if success == None:
        success = True if statusCode // 100 == 2 else False
    return await make_response(
        jsonify({
            'success': success,
            'statusCode': statusCode,
            'message': message,
            'data': data
        }))


def allow_cron() -> bool:
    f = True
    sec = gs_pcrSecretDir / "allow_cron.json"
    if sec.exists():
        with open(sec, "r", encoding="utf-8") as fp:
            f = load(fp)["allow_cron"]
    return f


# def get_sec():
#     sec = gs_pcrSecretDir / 'secret.json'
#     with open(sec, "r", encoding="utf-8") as fp:
#         dic = load(fp)
#     return dic


# def save_sec(dic):
#     sec = gs_pcrSecretDir / 'secret.json'
#     with open(sec, "w", encoding="utf-8") as fp:
#         dump(dic, fp, ensure_ascii=False, indent=4)


def auto_correct(qqid: str):
    need_correct = False
    mm = ""

    config_template = get_config_template()
    dic = get_sec()

    config_old = dic[qqid]["daily_config"]
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
        mm.append('已自动修正配置文件')
        mm.append('请阅读以上信息，随后刷新本页面以进入清日常设置')
        mm = '\n'.join(mm)
        need_correct = True

    for config in config_template:
        if config in config_old:
            dic[qqid]["daily_config"][config] = config_old[config]
    save_sec(dic)

    return need_correct, mm


# def verify_key(config):
#     comment = get_comment()
#     for item in comment:
#         if item not in config:
#             return False
#     for item in config:
#         if item not in comment:
#             return False
#     return True


def config_with_comment(config):
    comment = get_comment()
    for item in config:
        com = {
            "description": "",
            "type": "bool",
            "candidate_value": [True, False],
            "implemented": False
        }
        if item in comment:
            com = comment[item]
        config[item] = {"value": config[item], **com}
    return config

@auto_pcr_web.route('/result', methods=['GET'])
async def result_page():
    try:
        url_key = request.args["url_key"]
        assert len(url_key) > 0, "别试了"
    except:
        return await render_template("404.html", error_code=410, message="找不到该用户")
    dic = get_sec()
    for qqid in dic:
        config = dic[qqid]
        if config.get('url_key', "") == url_key:
            webPath = url_for('autopcr.static', filename='img/icon/favicon.png')
            
            srcFp = gs_pcrSecretDir / "daily_result" / f'{qqid}.png'
            if srcFp.exists():
                webPath = url_for('autopcr.static', filename=f'daily_result_pic/{MyHash(qqid)}.png')
                dstFp = gs_currentDir / "static" / "daily_result_pic" / f'{MyHash(qqid)}.png'
                shutil.copy(srcFp, dstFp)
                
            return await render_template("result_page.html", daily_result_pic=webPath)
    return await render_template("404.html", message="找不到该用户")

@auto_pcr_web.route('/config', methods=['GET'])
async def config_page():
    try:
        url_key = request.args["url_key"]
        assert len(url_key) > 0, "别试了"
    except:
        return await render_template("404.html", error_code=410, message="找不到该用户")
    dic = get_sec()
    for qqid in dic:
        config = dic[qqid]
        if config.get('url_key', "") == url_key:
            need_correct, msg = auto_correct(qqid)
            if need_correct:
                return await render_template("404.html", error_code=410, message=msg)
            return await render_template("config_page.html", qqname=config.get('name', ""), qqid=qqid, pcrname=config.get('pcrname', ""), pcrid=config.get('pcrid', ""), config=dumps(config_with_comment(config["daily_config"]), ensure_ascii=False, indent=4))
    return await render_template("404.html", message="找不到该用户")


@auto_pcr_web.route('/login', methods=['GET'])
async def login_page():
    return await render_template("login.html")


@auto_pcr_web.route('/api/login', methods=['POST'])
async def login():
    try:
        data = await request.form
        qqid:str = str(data.get('field_qq_id'))
        if len(qqid) == 0:
            return await make_response_json(400, "QQ不可为空")
        pcr_password:str = str(data.get('field_pcr_password'))
        if len(pcr_password) == 0:
            return await make_response_json(400, "PCR密码不可为空")
    except:
        return await make_response_json(400, "请求格式错误")
    
    dic = get_sec()
    
    if dic.get(qqid, {}).get("password", "") != pcr_password:
        return await make_response_json(406, "账号或密码错误")
    if "pcrid" not in dic[qqid]:
        return await make_response_json(406, "没有账号基础信息")
    if "url_key" not in dic[qqid]:
        dic[qqid]["url_key"] = MyHash(f'{qqid}{dic[qqid]["pcrid"]}')
        save_sec(dic)

    return await make_response_json(200, f'/autopcr/config?url_key={dic[qqid]["url_key"]}')
    


@auto_pcr_web.route('/api/trigger_daily', methods=['POST'])
async def trigger_daily():
    try:
        data = await request.form
        qqid = data.get('qqid')
        url_key = data.get('url_key')
        assert len(url_key) > 0, "别试了"
    except:
        return await make_response_json(400, "请求格式错误")
    dic = get_sec()
    if qqid not in dic:
        return await make_response_json(404, "用户不存在")
    if dic[qqid]["url_key"] != url_key:
        return await make_response_json(406, "校验失败")
    
    # return await make_response_json(501, "即将实装")
    
    task = asyncio.create_task(__do_daily(qqid))
    await asyncio.sleep(3)
    if task.done():
        try:
            result = task.result()
            return await make_response_json(403, f'清日常模块立即返回：{result}')
        except Exception as e:
            return await make_response_json(403, f'清日常模块异常终止：{e}')
    else:
        return await make_response_json(201, "已成功触发清日常。请过几分钟查询结果。")
    

@auto_pcr_web.route('/api/config', methods=['PUT'])
async def update_config():
    config = await request.get_json()
    try:
        qqid = str(config["qqid"])
        url_key = str(config["url_key"])
        assert len(url_key) > 0, "别试了"
    except:
        return await make_response_json(400, "请求格式错误")
    dic = get_sec()
    if qqid not in dic:
        return await make_response_json(404, "用户不存在")
    if dic[qqid]["url_key"] != url_key:
        return await make_response_json(406, "校验失败")
    del config["qqid"]
    del config["url_key"]
    comment = get_comment()
    retmsg = []

    for item, value in config.items():
        if comment[item]["type"] == "enum":
            try:
                value = int(value)
            except:
                pass
        if value not in comment[item]["candidate_value"]:
            return await make_response_json(
                400,
                f'保存失败：{item}项允许的候选值为{comment[item]["candidate_value"]}，您传入了{int(value)}'
            )
        if dic[qqid]["daily_config"][item] != value:
            print(f'{qqid} {item} {dic[qqid]["daily_config"][item]} -> {value}')
            retmsg.append(f'{item} {dic[qqid]["daily_config"][item]} -> {value}')
        dic[qqid]["daily_config"][item] = value

    save_sec(dic)
    return await make_response_json(200, f'修改成功：\n' + '\n'.join(retmsg))


def get_comment() -> dict: 
    with (gs_pcrSecretDir / "function_list.json").open("r", encoding="utf-8") as fp:
        return load(fp)


def get_config_template() -> dict:
    config_template = {}
    function_list = get_comment()
    for k, v in function_list.items():
        config_template[k] = v["default"]
    return config_template


def MyHash(inputStr: str) -> str:
    hash_object = hashlib.sha256()
    hash_object.update((gs_secretKey + inputStr).encode('utf-8'))
    return hash_object.hexdigest()[17:43]


gs_secretKeyPath = gs_currentDir / "secret.key"
if gs_secretKeyPath.exists():
    with gs_secretKeyPath.open("r", encoding="utf-8") as fp:
        gs_secretKey = fp.read()
else:
    gs_secretKey = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    with gs_secretKeyPath.open("w", encoding="utf-8") as fp:
        fp.write(gs_secretKey)
        

if __name__ == "__main__":
    from gevent import pywsgi
    server = pywsgi.WSGIServer(('127.0.0.1', 3859), app)
    server.serve_forever()
    #app.run(host='127.0.0.1', port=3859, debug=True)
