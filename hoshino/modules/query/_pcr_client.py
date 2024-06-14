from traceback import print_exc
from typing import Tuple
from msgpack import packb, unpackb
#from hoshino.aiorequests import post
import aiohttp
from random import randint
from json import loads
from hashlib import md5
from Crypto.Cipher import AES
from base64 import b64encode, b64decode
from ._bili_game_sdk import TryLogin
from asyncio import sleep, TimeoutError
import re
from os.path import dirname, join, exists
from os import makedirs
from copy import deepcopy
from datetime import datetime
from ..autopcr_db.typing import *

gs_apiRoot = 'http://le1-prod-all-gs-gzlj.bilibiligame.net'
gs_debugging = False
gs_curpath = dirname(__file__)
g_nowVersion = "4.9.7"
gs_versionCachePath = join(gs_curpath, 'data/version.txt')
if exists(gs_versionCachePath):
    with open(gs_versionCachePath, 'r', encoding='utf-8') as fp:
        g_nowVersion = fp.read().strip()
gs_defaultHeaders = {
    'Accept-Encoding': 'gzip',
    'User-Agent': 'Dalvik/2.1.0 (Linux, U, Android 5.1.1, PCRT00 Build/LMY48Z)',
    'X-Unity-Version': '2018.4.30f1',
    'APP-VER': g_nowVersion,
    'BATTLE-LOGIC-VERSION': '4',
    'BUNDLE-VER': '',
    'DEVICE': '2',
    'DEVICE-ID': '7b1703a5d9b394e24051d7a5d4818f17',
    'DEVICE-NAME': 'OPPO PCRT00',
    'EXCEL-VER': '1.0.0',
    'GRAPHICS-DEVICE-NAME': 'Adreno (TM) 640',
    'IP-ADDRESS': '10.0.2.15',
    'KEYCHAIN': '',
    'LOCALE': 'CN',
    'PLATFORM-OS-VERSION': 'Android OS 5.1.1 / API-22 (LMY48Z/rel.se.infra.20200612.100533)',
    'REGION-CODE': '',
    'RES-KEY': 'ab00a0a6dd915a052a2ef7fd649083e5',
    'RES-VER': '10002200',
    'SHORT-UDID': '0'
}


class ApiException(Exception):
    def __init__(self, message:str, code:int):
        super().__init__(message)
        self.code = code


class BiliSdkClient:
    def __init__(self, account:str, password:str, platform:int, channel:int, qqid:int = None):
        self.account = account
        self.password = password
        self.platform = platform
        self.channel = channel
        self.qqid = qqid

    async def BiliLogin(self) -> Tuple[str, str]:
        """
        B服登录。若成功则返回信息，若失败跑出异常。

        Returns:
            Tuple[str, str]: uid, accessKey
        
        Raises:
            Exception: 用户名或密码错误
            TryLogin()中可能抛出的异常
            CaptchaVerifier()中可能抛出的异常
        
        Returns:
            uid: int | str, access_key: str
        """
        return await TryLogin(self.account, self.password, self.qqid)


async def fetch_post(url, data, headers, timeout):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data, headers=headers, timeout=timeout) as resp:
            return await resp.content.read()
        
        
class PcrClient:
    def __init__(self, account: str, password: str, platfrom: int = 2, channel: int = 1, qqid: int = None):
        self._platform = platfrom
        self._channel = channel
        self.biliSdkClient = BiliSdkClient(account, password, platfrom, channel, qqid)
        
        self._viewerId = 0
        self._headers = deepcopy(gs_defaultHeaders)
        self._headers['PLATFORM'] = str(self._platform)
        self._headers['PLATFORM-ID'] = str(self._platform)
        self._headers['CHANNEL-ID'] = str(self._channel)
        
        self.needLoginAndCheck = True
        self._needBiliLogin = True
        
        self._homeIndexCache = None
        self._loadIndexCache = None

    async def BiliLogin(self):
        self._uid, self._access_key = await self.biliSdkClient.BiliLogin()
        self._needBiliLogin = False

    @staticmethod
    def _CreateKey() -> bytes:
        return bytes([ord('0123456789abcdef'[randint(0, 15)]) for _ in range(32)])

    @staticmethod
    def _AddTo16(b: bytes) -> bytes:
        n = len(b) % 16
        n = n // 16 * 16 - n + 16
        return b + (n * bytes([n]))

    @staticmethod
    def _Pack(data: object, key: bytes) -> bytes:
        aes = AES.new(key, AES.MODE_CBC, b'ha4nBYA2APUD6Uv1')
        return aes.encrypt(PcrClient._AddTo16(packb(data, use_bin_type=False))) + key

    @staticmethod
    def _Encrypt(data: str, key: bytes) -> bytes:
        aes = AES.new(key, AES.MODE_CBC, b'ha4nBYA2APUD6Uv1')
        return aes.encrypt(PcrClient._AddTo16(data.encode('utf8'))) + key

    @staticmethod
    def _Decrypt(data: bytes):
        data = b64decode(data.decode('utf8'))
        aes = AES.new(data[-32:], AES.MODE_CBC, b'ha4nBYA2APUD6Uv1')
        return aes.decrypt(data[:-32]), data[-32:]

    @staticmethod
    def _Unpack(data: bytes):
        data = b64decode(data.decode('utf8'))
        aes = AES.new(data[-32:], AES.MODE_CBC, b'ha4nBYA2APUD6Uv1')
        dec = aes.decrypt(data[:-32])
        return unpackb(dec[:-dec[-1]], strict_map_key=False), data[-32:]

    async def CallApi(self, apiUrl: str, postData: dict, returnDataHeader=False, raiseOnErrInData: bool = True, crypted: bool = True):
        """
        使用当前对象调用BCR API。

        Args:
            apiUrl (str): get/post的路径
            postData (dict): post的data
            returnDataHeader (bool, optional): 若为真，返回tuple(data:dict, data_header:dict)；否则仅返回data. Defaults to False.
            raiseOnErrInData (bool, optional): 若为真，当返回的data中存在server_error字段时抛出异常；否则正常返回完整data。Defaults to True.
            crypted (bool, optional): 别动. Defaults to True.

        Raises:
            ApiException: raiseOnErr==True且返回的data中存在server_error字段
            aiohttp网络传输中可能抛出的异常
            
        Returns:
            若returnDataHeader为真，返回tuple(data:dict, data_header:dict)；否则仅返回data。
        """
        
        try:
            if apiUrl == "/home/index" and self._homeIndexCache is not None:
                response = self._homeIndexCache
                data = response['data']
                data_headers = response['data_headers']
            elif apiUrl == "/load/index" and self._loadIndexCache is not None:
                response = self._loadIndexCache
                data = response['data']
                data_headers = response['data_headers']
            else:
                await sleep(0.4)
                if gs_debugging:
                    print(f'        {self.biliSdkClient.account:<20} -> {apiUrl:<20}\n            {postData}')
                key = PcrClient._CreateKey()
                if self._viewerId is not None:
                    postData['viewer_id'] = b64encode(PcrClient._Encrypt(str(self._viewerId), key)) if crypted else str(self._viewerId)
                aiohttp_url = gs_apiRoot + apiUrl
                aiohttp_data = PcrClient._Pack(postData, key) if crypted else str(postData).encode('utf8')
                aiohttp_headers = self._headers
                
                try:
                    response = await fetch_post(aiohttp_url, data=aiohttp_data, headers=aiohttp_headers, timeout=8)
                except TimeoutError:
                    raise TimeoutError("服务器响应超时")
                except Exception as e:
                    raise Exception(f'服务器报错：{e}')

                response = PcrClient._Unpack(response)[0] if crypted else loads(response)
                if gs_debugging:
                    print(f'                {str(response["data"])[:98]}')
                
                # 维护版本
                data_headers = response['data_headers']
                if "/check/game_start" == apiUrl and "store_url" in data_headers:
                    pattern = re.compile(r"\d{1,2}\.\d{1,2}\.\d{1,2}")
                    res = pattern.findall(data_headers["store_url"])
                    if len(res):
                        global g_nowVersion
                        g_nowVersion = res[0]
                        gs_defaultHeaders['APP-VER'] = g_nowVersion
                        with open(gs_versionCachePath, "w", encoding='utf-8') as fp:
                            print(g_nowVersion, file=fp)

                # 维护对象数据
                if data_headers.get('sid', '') != '':
                    t = md5()
                    t.update((data_headers['sid'] + 'c!SID!n').encode('utf8'))
                    self._headers['SID'] = t.hexdigest()
                if 'request_id' in data_headers:
                    self._headers['REQUEST-ID'] = data_headers['request_id']
                if 'viewer_id' in data_headers:
                    self._viewerId = data_headers['viewer_id']

                data = response['data']

                if gs_debugging:
                    curpath = join(dirname(__file__), f"debug/{self.biliSdkClient.account}/{apiUrl.replace('/', '-')}.json")
                    makedirs(dirname(curpath), exist_ok=True)
                    try:
                        debugInfo = {"apiurl": apiUrl, "request": postData, "headers": data_headers, "data": data}
                        with open(curpath, "w", encoding="utf-8") as fp:
                            #json.dump(debug_info, fp, ensure_ascii=False)
                            #debug_info_json = json.dumps(debug_info, ensure_ascii=False)
                            print(str(debugInfo).replace("'", '"'), file=fp)
                    except:
                        pass
                if 'server_error' in data:
                    print(f'pcrclient: {apiUrl} api failed {data}')
                    self.needLoginAndCheck = True
                    self._homeIndexCache = None
                    self._loadIndexCache = None
                    if raiseOnErrInData:
                        data = data['server_error']
                        raise ApiException(data['message'], data['status'])
                else:
                    if apiUrl == '/home/index':
                        self._homeIndexCache = response
                    elif apiUrl == '/load/index':
                        self._loadIndexCache = response
                    else: # elif apiUrl不在不会导致数据变化的白名单中：
                        self._homeIndexCache = None
                        self._loadIndexCache = None
            if returnDataHeader:
                return data, data_headers
            else:
                return data
        except Exception as e:
            self.needLoginAndCheck = True
            self._homeIndexCache = None
            self._loadIndexCache = None
            raise e
            

    async def LoginAndCheck(self, isFirstTry=True, still_try_login_even_if_record_is_invalid=False, always_call_login_and_check=False) -> bool:
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
        
        if not still_try_login_even_if_record_is_invalid:
            pcrAccountInfoRecord: PcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.account == self.biliSdkClient.account)
            if pcrAccountInfoRecord is not None:
                if pcrAccountInfoRecord.is_valid == False:
                    raise AssertionError(f'账号[{self.biliSdkClient.account}]被标记为不合法，终止登录。请重新交号。')
        
        if not always_call_login_and_check:
            if self.needLoginAndCheck == False:
                return
            
            if self._needBiliLogin:
                await self.BiliLogin()
        else:
            await self.BiliLogin()

        if 'REQUEST-ID' in self._headers:
            self._headers.pop('REQUEST-ID')

        maintenanceStatus = await self.CallApi('/source_ini/get_maintenance_status?format=json', {}, crypted=False, raiseOnErrInData=True)
        if 'maintenance_message' in maintenanceStatus:
            raise Exception(f'服务器维护中')

        self._headers['MANIFEST-VER'] = str(maintenanceStatus['required_manifest_ver'])
        
        try:
            lres = await self.CallApi('/tool/sdk_login', {'uid': str(self._uid), 'access_key': self._access_key, 'channel': str(self._channel), 'platform': str(self._platform)})
            if 'is_risk' in lres and lres['is_risk'] == 1:
                raise ApiException(f'需重新过码验证，请重试', -1)
        except ApiException as e:
            self._needBiliLogin = True
            PcrAccountInfo.update(uid_cache="", access_key_cache="").where(PcrAccountInfo.account == self.biliSdkClient.account).execute()
            if isFirstTry:
                return await self.LoginAndCheck(False)
            else:
                raise

        gamestart = await self.CallApi('/check/game_start', {'apptype': 0, 'campaign_data': '', 'campaign_user': randint(0, 99999)})

        if not gamestart['now_tutorial']:
            raise Exception("该账号没过完教程!")

        #await self.CallApi('/check/check_agreement', {})
        self.needLoginAndCheck = False
        
        pcrid = int(self._viewerId)
        pcrAccountInfoRecord: PcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.pcrid == pcrid)
        if pcrAccountInfoRecord is None:
            PcrAccountInfo.create(pcrid=pcrid, account=self.biliSdkClient.account, password=self.biliSdkClient.password, update_time = str(datetime.now()), is_valid = True, pcrname_cache=str(self._viewerId), uid_cache=str(self._uid), access_key_cache=self._access_key)
            return True
        else:
            if pcrAccountInfoRecord.uid_cache != self._uid or pcrAccountInfoRecord.access_key_cache != self._access_key:
                pcrAccountInfoRecord.account = self.biliSdkClient.account
                pcrAccountInfoRecord.password = self.biliSdkClient.password
                pcrAccountInfoRecord.uid_cache = self._uid
                pcrAccountInfoRecord.access_key_cache = self._access_key
                pcrAccountInfoRecord.update_time = str(datetime.now())
                pcrAccountInfoRecord.is_valid = True
                pcrAccountInfoRecord.save()
            return False