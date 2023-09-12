from hoshino import config, get_bot
from hoshino.aiorequests import get
from hoshino.typing import CommandSession
from nonebot import on_command
import json
import asyncio
from pathlib import Path
import httpx


gs_commandPrefix = 'cv'
g_bot = get_bot()
gs_waitTime = 90

gs_currentDir = Path(__file__).resolve().parent
gs_configPath = gs_currentDir / "config.json"

_gs_config = {"ellye_token": "", "lulu_token": ""}
if not Path.exists(gs_configPath):
    with gs_configPath.open("w", encoding="utf-8") as fp:
        json.dump(_gs_config, fp, ensure_ascii=False, indent=4)

with gs_configPath.open("r", encoding="utf-8") as fp:
    _gs_config: dict = json.load(fp)
    gs_ellye_token: str = _gs_config.get("ellye_token", "")
    gs_lulu_token: str = _gs_config.get("lulu_token", "")


g_manualResult:dict = {}


async def LuluAutoCaptchaVerifier(challenge:str, gt:str) -> str:
    """
    路路自动过码模块

    Args:
        challenge (str): 程序生成
        gt (str): 程序生成

    Raises:
        Exception: 返回结果中状态码不为-1
        Exception: 其它异常

    Returns:
        str: 过码结果字符串
    """

    try:
        res = await (await get(url=f"https://api.fuckmys.tk/geetest?token={gs_lulu_token}&gt={gt}&challenge={challenge}")).content
        res = json.loads(res)
        assert res.get("code", -1) == 0, str(res)
        return res["data"]["validate"]
    except Exception as e:
        raise Exception(f"自动过码异常：{e}") from e
    

async def EllyeAutoCaptchaVerifier():
    """
    怡宝自动过码模块
    """
    
    try:
        async with httpx.AsyncClient() as client:
            url = f'https://:{gs_ellye_token}@pcr-bilibili-api.cn.linepro6.com:843/geetest-captcha/validate'
            response = await client.get(url, timeout=60)
            response.raise_for_status()
            res = response.json()
            assert res.get("code", -1) == 0, str(res)
            return res["data"]
    except Exception as e:
        raise Exception(f"自动过码异常：{e}") from e
    

async def EllyeManualCaptchaResultListening(userId:str):
    while True:
        async with httpx.AsyncClient() as client:
            url = f'https://captcha.ellye.cn/api/block?userid={userId}'
            try:
                response = await client.get(url, timeout=28)
            except httpx.TimeoutException as e:
                pass
            else:
                if response.status_code == 200:
                    res = response.json()
                    return res["validate"]
    
    # while True:
    #     await asyncio.sleep(4)
    #     async with httpx.AsyncClient() as client:
    #         url = f'https://captcha.ellye.cn/api/get?userid={userId}'
    #         response = await client.get(url)
    #     if response.status_code == 200:
    #         res = response.json()
    #         return res["validate"]


async def EllyeManualCaptchaVerifier(challenge:str, gt:str, userId:str, qqid:int) -> str:
    """
    怡宝手动过码模块

    Args:
        challenge (str): 程序生成
        gt (str): 程序生成
        userId (str): 程序生成
        qqid (int): 发送验证链接。

    Raises:
        AssertionError: 未传入qqid
        Exception: 向[qqid]私发过码验证消息失败，可能尚未添加好友。
        Exception: 其它异常（超时等）

    Returns:
        str: 过码结果字符串
    """
    
    url = f"https://captcha.ellye.cn/?captcha_type=1&challenge={challenge}&gt={gt}&userid={userId}&gs=1"
    assert qqid, "过码模块异常"
    try:
        await g_bot.send_private_msg(user_id=qqid, message=f'pcr账号登录触发验证码，请在{gs_waitTime}秒内完成以下链接中的验证内容。')
        await g_bot.send_private_msg(user_id=qqid, message=url)
    except Exception as e:
        raise Exception(f'向{qqid}私发过码验证消息失败，可能尚未添加好友。') from e
    
    try:
        return await asyncio.wait_for(EllyeManualCaptchaResultListening(userId), gs_waitTime)
    except asyncio.TimeoutError:
        try:
            await g_bot.send_private_msg(user_id=qqid, message="手动过码获取结果超时")
        except Exception as e:
            pass
        raise RuntimeError("手动过码获取结果超时")
    except Exception as e:
        try:
            await g_bot.send_private_msg(user_id=qqid, message=f'手动过码获取结果异常：{e}')
        except Exception as e:
            pass
        raise


async def LuluManualCaptchaVerifier(challenge:str, gt:str, userId:str, qqid:int) -> str:
    """
    路路手动过码模块

    Args:
        challenge (str): 程序生成
        gt (str): 程序生成
        userId (str): 程序生成
        qqid (int): 发送验证链接。

    Raises:
        AssertionError: 未传入qqid
        Exception: 向[qqid]私发过码验证消息失败，可能尚未添加好友。
        Exception: 其它异常（超时等）

    Returns:
        str: 过码结果字符串
    """
    
    url = f"https://help.tencentbot.top/geetest_/?captcha_type=1&challenge={challenge}&gt={gt}&userid={userId}&gs=1"
    assert qqid, "过码模块异常"
    try:
        await g_bot.send_private_msg(user_id=qqid, message=f'pcr账号登录触发验证码，请在{gs_waitTime}秒内完成以下链接中的验证内容，随后将第1个方框的内容点击复制，并加上"{gs_commandPrefix} "前缀发送给机器人完成验证\n示例：{gs_commandPrefix} 123456789')
        await g_bot.send_private_msg(user_id=qqid, message=url)
    except Exception as e:
        raise Exception(f'向{qqid}私发过码验证消息失败，可能尚未添加好友。')
    
    lock = asyncio.Lock()
    await lock.acquire()
    g_manualResult[qqid] = lock
    try:
        await asyncio.wait_for(lock.acquire(), gs_waitTime)
    except asyncio.TimeoutError:
        try:
            await g_bot.send_private_msg(user_id=qqid, message="手动过码获取结果超时")
        except Exception as e:
            pass
        raise RuntimeError("手动过码获取结果超时")
    else:
        return g_manualResult[qqid]
    finally:
        if lock.locked():
            lock.release()
        g_manualResult.pop(qqid, None)


@on_command(f'{gs_commandPrefix}')
async def TryGetToken(session: CommandSession):
    qqid = int(session.ctx.user_id)
    if qqid not in g_manualResult:
        return
    token = session.ctx['message'].extract_plain_text().replace(f"{gs_commandPrefix}", "").strip().replace("|", "").replace("jordan", "")
    outp = "Received" # outp = "Received" if g_manualResult[qqid] is None else "Renewed"
    lock:asyncio.Lock = g_manualResult[qqid]
    g_manualResult[qqid] = token
    lock.release()
    await g_bot.send_private_msg(user_id=qqid, message=f'Token {token[:4]}...{token[-4:]} {outp}. Verifying...')