from traceback import print_exc
from typing import Tuple
import json
import time
import hashlib
import urllib
from hoshino.aiorequests import post, get
from ._captcha_verifier import LuluAutoCaptchaVerifier, EllyeAutoCaptchaVerifier, EllyeManualCaptchaVerifier, LuluManualCaptchaVerifier, gs_lulu_token, gs_ellye_token
from hoshino import logger
from ..autopcr_db.typing import *
from datetime import datetime
import asyncio

bililogin = "https://line1-sdk-center-login-sh.biligame.net/"

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
import base64

# 加密
class RsaCr:
    @staticmethod
    def RsaCreate(message, public_key) -> str:
        rsakey = RSA.importKey(public_key)
        cipher = Cipher_pkcs1_v1_5.new(rsakey)  # 创建用于执行pkcs1_v1_5加密或解密的密码
        cipher_text = base64.b64encode(cipher.encrypt(message.encode('utf-8')))
        text = cipher_text.decode('utf-8')
        return text


async def SendPost(url, data) -> dict:
    header = {"User-Agent": "Mozilla/5.0 BSGameSDK", "Content-Type": "application/x-www-form-urlencoded", "Host": "line1-sdk-center-login-sh.biligame.net"}
    res = await (await post(url=url, data=data, headers=header)).content
    return json.loads(res)


def SetSign(data) -> str:
    data["timestamp"] = int(time.time())
    data["client_timestamp"] = int(time.time())
    sign = ""
    data2 = ""
    for key in data:
        if key == "pwd":
            pwd = urllib.parse.quote(data["pwd"])
            data2 += f"{key}={pwd}&"
        data2 += f"{key}={data[key]}&"
    for key in sorted(data):
        sign += f"{data[key]}"
    data = sign
    sign = sign + "fe8aac4e02f845b8ad67c427d48bfaf1"
    sign = hashlib.md5(sign.encode()).hexdigest()
    data2 += "sign=" + sign
    return data2


gs_modolRsa = '{"operators":"5","merchant_id":"1","isRoot":"0","domain_switch_count":"0","sdk_type":"1","sdk_log_type":"1","timestamp":"1613035485639","support_abis":"x86,armeabi-v7a,armeabi","access_key":"","sdk_ver":"3.4.2","oaid":"","dp":"1280*720","original_domain":"","imei":"227656364311444","version":"1","udid":"KREhESMUIhUjFnJKNko2TDQFYlZkB3cdeQ==","apk_sign":"e89b158e4bcf988ebd09eb83f5378e87","platform_type":"3","old_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","android_id":"84567e2dda72d1d4","fingerprint":"","mac":"08:00:27:53:DD:12","server_id":"1592","domain":"line1-sdk-center-login-sh.biligame.net","app_id":"1370","version_code":"90","net":"4","pf_ver":"6.0.1","cur_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","c":"1","brand":"Android","client_timestamp":"1613035486888","channel_id":"1","uid":"","game_id":"1370","ver":"2.4.10","model":"MuMu"}'
gs_modolLogin = '{"operators":"5","merchant_id":"1","isRoot":"0","domain_switch_count":"0","sdk_type":"1","sdk_log_type":"1","timestamp":"1613035508188","support_abis":"x86,armeabi-v7a,armeabi","access_key":"","sdk_ver":"3.4.2","oaid":"","dp":"1280*720","original_domain":"","imei":"227656364311444","gt_user_id":"fac83ce4326d47e1ac277a4d552bd2af","seccode":"","version":"1","udid":"KREhESMUIhUjFnJKNko2TDQFYlZkB3cdeQ==","apk_sign":"e89b158e4bcf988ebd09eb83f5378e87","platform_type":"3","old_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","android_id":"84567e2dda72d1d4","fingerprint":"","validate":"84ec07cff0d9c30acb9fe46b8745e8df","mac":"08:00:27:53:DD:12","server_id":"1592","domain":"line1-sdk-center-login-sh.biligame.net","app_id":"1370","pwd":"rxwA8J+GcVdqa3qlvXFppusRg4Ss83tH6HqxcciVsTdwxSpsoz2WuAFFGgQKWM1+GtFovrLkpeMieEwOmQdzvDiLTtHeQNBOiqHDfJEKtLj7h1nvKZ1Op6vOgs6hxM6fPqFGQC2ncbAR5NNkESpSWeYTO4IT58ZIJcC0DdWQqh4=","version_code":"90","net":"4","pf_ver":"6.0.1","cur_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","c":"1","brand":"Android","client_timestamp":"1613035509437","channel_id":"1","uid":"","captcha_type":"1","game_id":"1370","challenge":"efc825eaaef2405c954a91ad9faf29a2","user_id":"doo349","ver":"2.4.10","model":"MuMu"}'
gs_modolCaptch = '{"operators":"5","merchant_id":"1","isRoot":"0","domain_switch_count":"0","sdk_type":"1","sdk_log_type":"1","timestamp":"1613035486182","support_abis":"x86,armeabi-v7a,armeabi","access_key":"","sdk_ver":"3.4.2","oaid":"","dp":"1280*720","original_domain":"","imei":"227656364311444","version":"1","udid":"KREhESMUIhUjFnJKNko2TDQFYlZkB3cdeQ==","apk_sign":"e89b158e4bcf988ebd09eb83f5378e87","platform_type":"3","old_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","android_id":"84567e2dda72d1d4","fingerprint":"","mac":"08:00:27:53:DD:12","server_id":"1592","domain":"line1-sdk-center-login-sh.biligame.net","app_id":"1370","version_code":"90","net":"4","pf_ver":"6.0.1","cur_buvid":"XZA2FA4AC240F665E2F27F603ABF98C615C29","c":"1","brand":"Android","client_timestamp":"1613035487431","channel_id":"1","uid":"","game_id":"1370","ver":"2.4.10","model":"MuMu"}'


async def TryLoginWithCaptcha(account, password, challenge, gt_user, validate) -> dict:
    data = json.loads(gs_modolRsa)
    data = SetSign(data)
    rsa = await SendPost(bililogin + "api/client/rsa", data)
    data = json.loads(gs_modolLogin)
    public_key = rsa['rsa_key']
    data["access_key"] = ""
    data["gt_user_id"] = gt_user
    data["uid"] = ""
    data["challenge"] = challenge
    data["user_id"] = account
    data["validate"] = validate
    data["seccode"] = ((validate + "|jordan") if len(validate) else "")
    data["pwd"] = RsaCr.RsaCreate(rsa['hash'] + password, public_key)
    data = SetSign(data)
    return await SendPost(bililogin + "api/client/login", data)


async def TryLoginWithoutCaptcha(account, password) -> dict:
    return await TryLoginWithCaptcha(account, password, "", "", "")


async def StartCaptcha() -> dict:
    data = json.loads(gs_modolCaptch)
    data = SetSign(data)
    return await SendPost(bililogin + "api/client/start_captcha", data)


async def TryLogin(biliAccount:str, biliPassword:str, qqid:int = None) -> Tuple[str, str]:
    """
    根据传入的账号和密码尝试登录。登录成功则返回登录信息，失败则抛出异常。

    Args:
        biliAccount (str): 账号。目前只支持ASCII字符。
        biliPassword (str): 密码。只支持ASCII字符。
        qqid (int): 触发过码的用户。降级到手动过码时使用。

    Raises:
        Exception: 用户名或密码错误
        CaptchaVerifier中可能抛出的异常

    Returns:
        uid: int | str, access_key: str
    """
    
    def VerifyRes(res:dict) -> bool:
        """
        判断登录结果。
        如果成功则返回True；如果需要过码或过码失败则返回False
        密码错误则抛出异常（防止触发不必要的fallback）
        
        Args:
            res: 调用TryLoginWithCaptcha()或TryLoginWithoutCaptcha()的返回结果
            
        Raises:
            Exception: 用户名或密码错误
            
        Returns:
            如果成功则返回True；如果需要过码或过码失败则返回False
        """
        if res.get("message", "") == "用户名或密码错误":
            logger.info(f'登录失败：用户名或密码错误')
            PcrAccountInfo.update(is_valid=False, update_time=str(datetime.now())).where(PcrAccountInfo.account == biliAccount).execute()
            raise Exception("用户名或密码错误")
        if res.get("code", -1) == 500024:
            logger.info(f'登录失败：{res.get("message", "密码不安全，请您修改密码")}')
            PcrAccountInfo.update(is_valid=False, update_time=str(datetime.now())).where(PcrAccountInfo.account == biliAccount).execute()
            raise Exception(f'登录失败：{res.get("message", "密码不安全，请您修改密码")}')
        if res.get("code", -1) == 500053:
            logger.info(f'登录失败：{res.get("message", "BCR汇报账号异常，请前往网页主站重新登录并进行验证")}')
            PcrAccountInfo.update(is_valid=False, update_time=str(datetime.now())).where(PcrAccountInfo.account == biliAccount).execute()
            raise Exception(f'登录失败：{res.get("message", "BCR汇报账号异常，请前往网页主站重新登录并进行验证")}')
    
        if res.get("code", -1) == 0:
            logger.info(f'登录成功：uid=[{res["uid"]}] access_key=[{res["access_key"]}]')
            return True

        logger.info(f'登录失败：{res}')
        return False
    
    
    try:
        logger.info(f'尝试不带码登录[{biliAccount}][{biliPassword}]')
        res = await TryLoginWithoutCaptcha(biliAccount, biliPassword)
    except Exception as e:
        logger.info(f'捕获异常：{e}')
    else:
        if VerifyRes(res):
            return res['uid'], res['access_key']
    
    if gs_lulu_token:
        try:
            logger.info(f'尝试使用[路路自动过码]登录[{biliAccount}][{biliPassword}]')
            challenge:dict = await StartCaptcha()
            validateKey = await LuluAutoCaptchaVerifier(challenge["challenge"], challenge["gt"])
            res = await TryLoginWithCaptcha(biliAccount, biliPassword, challenge["challenge"], challenge['gt_user_id'], validateKey) 
        except Exception as e:
            logger.info(f'捕获异常：{e}')
        else:
            if VerifyRes(res):
                return res['uid'], res['access_key']
    
    if gs_ellye_token:
        try:
            logger.info(f'尝试使用[怡宝自动过码]登录[{biliAccount}][{biliPassword}]')
            validateRes = await EllyeAutoCaptchaVerifier()
            res = await TryLoginWithCaptcha(biliAccount, biliPassword, validateRes["challenge"], validateRes['gt_user'], validateRes['validate'])
        except Exception as e:
            logger.info(f'捕获异常：{e}')
        else:
            if VerifyRes(res):
                return res['uid'], res['access_key']
    
    try:
        logger.info(f'尝试使用[怡宝手动过码]登录[{biliAccount}][{biliPassword}]')
        challenge:dict = await StartCaptcha()
        validateKey = await EllyeManualCaptchaVerifier(challenge['challenge'], challenge['gt'], challenge['gt_user_id'], qqid)
        res = await TryLoginWithCaptcha(biliAccount, biliPassword, challenge["challenge"], challenge['gt_user_id'], validateKey)
    except Exception as e:
        logger.info(f'捕获异常：{e}')
    else:
        if VerifyRes(res):
            return res['uid'], res['access_key']
        
    try:
        logger.info(f'尝试使用[路路手动过码]登录[{biliAccount}][{biliPassword}]')
        challenge:dict = await StartCaptcha()
        validateKey = await LuluManualCaptchaVerifier(challenge['challenge'], challenge['gt'], challenge['gt_user_id'], qqid)
        res = await TryLoginWithCaptcha(biliAccount, biliPassword, challenge["challenge"], challenge['gt_user_id'], validateKey)
    except Exception as e:
        logger.info(f'捕获异常：{e}')
        raise
    else:
        if VerifyRes(res):
            return res['uid'], res['access_key']


# async def TestEllyeManual():
#     res:dict = await StartCaptcha()
#     print(f"https://captcha.ellye.cn/?captcha_type=1&challenge={res['challenge']}&gt={res['gt']}&userid={res['gt_user_id']}&gs=1")
#     print(f'https://captcha.ellye.cn/api/get?userid={res["gt_user_id"]}')
#     print(f'https://captcha.ellye.cn/api/block?userid={res["gt_user_id"]}')
#     validateKey = await EllyeManualCaptchaVerifier(res['challenge'], res['gt'], res['gt_user_id'], 123)
#     print(validateKey)

# loop = asyncio.get_event_loop()
# res = loop.run_until_complete(TestEllyeManual())
