# built-in
from pathlib import Path
from json import load, dumps
import asyncio
import datetime
import hashlib
import random
import string
from multidict import MultiDict
from typing import Optional, Dict

# 3rd-party
from quart import render_template, request, make_response, jsonify, Blueprint, send_file, redirect, url_for
import nonebot

# project
from ..pcr_secret import __do_daily, get_sec, save_sec

gs_currentDir = Path(__file__).parent # myweb
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


def auto_correct(qqid: str):
    config_template = get_config_template()
    dic = get_sec()

    if "daily_config" not in dic[qqid]:
        dic[qqid]["daily_config"] = config_template
        save_sec(dic)
        return False, ""
    
    need_correct = False
    mm = ""
    
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
        #mm.append('请阅读以上信息，随后刷新本页面以进入清日常设置')
        mm = '\n'.join(mm)
        need_correct = True

    for config in config_template:
        if config in config_old:
            dic[qqid]["daily_config"][config] = config_old[config]
    save_sec(dic)

    return need_correct, mm


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


def get_url_key_from_request(data: MultiDict) -> Optional[str]:
    url_key = data.get("url_key", None)
    return url_key if url_key else None

# may raise AssertionError
def get_qqid_from_url_key(url_key: str) -> Optional[int]:
    if not url_key:
        return None
    qqids = [qqid for qqid, config in get_sec().items() if config.get("url_key", None) == url_key]
    if not qqids:
        return None
    assert len(qqids) == 1, "Internal Error: duplicate url_key"
    return qqids[0]


def generate_url_key_if_not_exist(dic: Dict[int, dict], qqid: int) -> None:
    config = dic.get(qqid, None)
    if not config:
        return
    if "url_key" not in config:
        dic[qqid]["url_key"] = MyHash(f'{qqid}{dic[qqid]["pcrid"]}')
        save_sec(dic)


def get_config_from_qqid(qqid: int) -> Optional[dict]:
    return get_sec().get(qqid, None)


def get_config_from_qqid_with_validation(qqid: int, url_key: str) -> Optional[dict]:
    dic = get_sec()
    config = dic.get(qqid, None)
    if not config:
        return None
    generate_url_key_if_not_exist(dic, qqid)
    if config["url_key"] != url_key:
        return None
    return config


@auto_pcr_web.route('/result', methods=['GET'])
async def result_page():
    return await render_template("result_page.html")


@auto_pcr_web.route('/api/result', methods=['POST'])
async def get_result_pic():
    url_key = get_url_key_from_request(await request.form)
    if not url_key:
        return 'Invalid param(s): url_key', 404

    try:
        qqid = get_qqid_from_url_key(url_key)
    except AssertionError as e:
        return str(e), 500
    if not qqid:
        return 'User not found', 404
    
    image_path = gs_pcrSecretDir / "daily_result" / f'{qqid}.png'
    if not image_path.exists():
        return 'Image not found', 404
    return await send_file(image_path.as_posix(), mimetype='image/png')


@auto_pcr_web.route('/update_pwd', methods=['GET'])
async def update_pwd_page():
    url_key = get_url_key_from_request(request.args)
    if not url_key:
        return await render_template("404.html", error_code=410, message="找不到该用户")
    
    qqid = get_qqid_from_url_key(url_key)
    if qqid:
        return await render_template("update_pwd_page.html")
    else:
        return await render_template("404.html", message="找不到该用户")


@auto_pcr_web.route('/api/update_pwd', methods=['POST'])
async def update_pwd():
    url_key = get_url_key_from_request(await request.form)
    if not url_key:
        return 'User not found', 404

    qqid = get_qqid_from_url_key(url_key)
    if not qqid:
        return 'User not found', 404

    return await make_response_json(200, f'即将实装') # TODO


@auto_pcr_web.route('/config', methods=['GET'])
async def config_page():
    url_key = get_url_key_from_request(request.args)
    if not url_key:
        return await render_template("404.html", error_code=410, message="找不到该用户")

    qqid = get_qqid_from_url_key(url_key)
    if qqid:
        return await render_template("config_page.html")
    else:
        return await render_template("404.html", message="找不到该用户")


@auto_pcr_web.route('/el', methods=['GET'])
async def login_page():
    return await render_template("login.html")

@auto_pcr_web.route('/ell', methods=['GET'])
async def login_page_ell():
    return await render_template("login.html")    

@auto_pcr_web.route('/api/el', methods=['POST'])
async def login():
    data = await request.form
    
    qqid: str = data.get('field_qq_id', None)
    if not qqid:
        return await make_response_json(400, "请求格式错误")
    qqid = str(qqid)
    
    pcr_password: str = data.get('field_pcr_password', None)
    if not pcr_password:
        return await make_response_json(400, "请求格式错误")
    pcr_password = str(pcr_password)

    dic = get_sec()
    if dic.get(qqid, {}).get("password", "") != pcr_password:
        return await make_response_json(406, "账号或密码错误")
    generate_url_key_if_not_exist(dic, qqid)
    return await make_response_json(200, f'/autopcr/config?url_key={dic[qqid]["url_key"]}')


@auto_pcr_web.route('/api/trigger_daily', methods=['POST'])
async def trigger_daily():
    data = await request.form
    qqid = data.get('qqid', None)
    url_key = data.get('url_key', None)
    if not qqid or not url_key:
        return await make_response_json(400, "请求格式错误")
    
    dic = get_sec()
    if qqid not in dic:
        return await make_response_json(404, "用户不存在")
    generate_url_key_if_not_exist(dic, qqid)
    if dic[qqid]["url_key"] != url_key:
        return await make_response_json(406, "校验失败")

    task = asyncio.create_task(__do_daily(qqid))
    await asyncio.sleep(2)
    if task.done():
        try:
            result = task.result()
            return await make_response_json(403, f'清日常模块立即返回：{result}')
        except Exception as e:
            return await make_response_json(403, f'清日常模块异常终止：{e}')
    else:
        return await make_response_json(201, "已成功触发清日常。请过几分钟查询结果。")


@auto_pcr_web.route('/api/config', methods=['POST'])
async def get_config():
    try:
        data = await request.form
        qqid = data.get('qqid')
        url_key = data.get('url_key')
        assert(url_key and len(url_key) > 0), "别试了"
    except:
        return await make_response_json(400, "请求格式错误")
    dic = get_sec()
    if qqid not in dic:
        return await make_response_json(404, "用户不存在")
    if dic[qqid]["url_key"] != url_key:
        return await make_response_json(406, "校验失败")
    
    need_correct, msg = auto_correct(qqid)
    if need_correct:
        return await make_response_json(410, msg) # 此为临时方案，应改为使用list    
    #return await make_response_json(data=config_with_comment(dic[qqid]["daily_config"])) # dict不转成str的话在js会被自动排序
    return await make_response_json(data=dumps(config_with_comment(dic[qqid]["daily_config"]), ensure_ascii=False)) # 此为临时方案，应改为使用list
    
    
@auto_pcr_web.route('/api/userdata', methods=['POST'])
async def get_userdata():
    try:
        data = await request.form
        url_key = data.get('url_key')
        assert(url_key and len(url_key) > 0), "别试了"
    except:
        return await make_response_json(400, "请求格式错误")
    dic = get_sec()
    qqids = [qqid for qqid in dic if "url_key" in dic[qqid] and dic[qqid]["url_key"] == url_key]
    if not qqids:
        return await make_response_json(406, "校验失败")
    if len(qqids) > 1:
        return await make_response_json(500, "Internal Error: duplicate url_key")
    qqid = qqids[0]
    config = dic[qqid]
    return await make_response_json(data={"qqid": qqid, "qqname": config.get('name', ""), "pcrname": config.get('pcrname', ""), "pcrid": config.get('pcrid', "")})


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


@auto_pcr_web.route('/404')
async def not_found():
    error_code = request.args.get('error_code', "")
    message = request.args.get('message', "")
    return await render_template("404.html", error_code=error_code, message=message)


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
