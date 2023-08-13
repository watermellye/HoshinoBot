from ._pcr_client import PcrClient
from ..autopcr_db.typing import *
from typing import Dict

_g_pcrClients: Dict[str, PcrClient] = {}

class PcrClientManager:
    @staticmethod
    def FromStr(account: str, password: str, qqid: int = None) -> PcrClient:
        """
        若PCR账号名有记录，且密码相同：返回当前记录对象。
        若PCR账号名有记录，但密码不同：则重置对象并返回。
        若PCR账号名无记录：新建并返回一个PcrClient对象。

        Args:
            account (str): PCR账号
            password (str): PCR密码

        Raises:
            AssertionError: account或password为空

        Returns:
            PcrClient: PcrClient对象
        """
        assert len(account), "账号名为空"
        assert len(password), "密码为空"
        
        if account in _g_pcrClients:
            if _g_pcrClients[account].biliSdkClient.password == password:
                return _g_pcrClients[account]
        
        client = PcrClient(account, password, qqid=qqid)
        pcrAccountInfoRecord: PcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.account == account)
        if pcrAccountInfoRecord is not None:
            if pcrAccountInfoRecord.uid_cache and pcrAccountInfoRecord.access_key_cache:
                client._needBiliLogin = False
                client._uid = pcrAccountInfoRecord.uid_cache
                client._access_key = pcrAccountInfoRecord.access_key_cache
                client._viewerId = pcrAccountInfoRecord.pcrid
        _g_pcrClients[account] = client
        return _g_pcrClients[account]
        
        
    @staticmethod        
    def FromDict(accountInfo: dict) -> PcrClient:
        """
        若PCR账号名无记录：新建并返回一个PcrClient对象。
        若PCR账号名有记录，但密码不同：则重置对象并返回。
        若PCR账号名有记录，且密码相同：返回当前记录对象。

        Args:
            accountInfo (dict): PCR账号信息 {"account": str, "password": str, "qqid": int = None}

        Raises:
            AssertionError: 未传入account或password字段或对应value为空

        Returns:
            PcrClient: PcrClient对象
        """
        
        assert "account" in accountInfo, "未传入account字段"
        assert "password" in accountInfo, "未传入password字段"
        
        return PcrClientManager.FromStr(accountInfo["account"], accountInfo["password"], accountInfo.get("qqid", None))
    

    @staticmethod        
    def FromRecord(accountInfo: PcrAccountInfo) -> PcrClient:
        """
        若PCR账号名无记录：新建并返回一个PcrClient对象。
        若PCR账号名有记录，但密码不同：则重置对象并返回。
        若PCR账号名有记录，且密码相同：返回当前记录对象。

        Args:
            accountInfo (PcrAccountInfo): PCR账号数据库记录

        Raises:
            AssertionError: 该记录被标记为不合法

        Returns:
            PcrClient: PcrClient对象
        """
        
        assert accountInfo.is_valid, f'记录[{accountInfo.pcrid}]被标记为不合法'
        return PcrClientManager.FromStr(accountInfo.account, accountInfo.password)


    @staticmethod        
    def FromPcrid(pcrid: int) -> PcrClient:
        """
        在数据库中查找pcrid对应的账号密码记录
        若PCR账号名无记录：新建并返回一个PcrClient对象。
        若PCR账号名有记录，但密码不同：则重置对象并返回。
        若PCR账号名有记录，且密码相同：返回当前记录对象。

        Args:
            pcrid (int): PCRID

        Raises:
            AssertionError: 记录不存在或被标记为不合法

        Returns:
            PcrClient: PcrClient对象
        """
        
        pcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.pcrid == pcrid)
        assert pcrAccountInfo is not None, "记录不存在"
        return PcrClientManager.FromRecord(pcrAccountInfo)