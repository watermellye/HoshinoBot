'''
依赖方式：from __file__ import AutopcrDatabaseTable
'''

from traceback import print_exc
from typing import Union
from ._autopcr_database_table import *
from ..query.pcr_client import PcrClientManager, PcrClient
from ..query import query
#from datetime import datetime

class AutopcrDatabaseTable:
    '''
    均为静态方法。
    调用方式：AutopcrDatabaseTable.<SomeStaticMethod>
    '''
    
    # @staticmethod
    # def GetFriendListModel():
    #     '''
    #     TODO 显式调用bot.send_private_msg前先判断是否为好友
    #     '''
    #     return friend_list

    # @staticmethod
    # def GetGroupListModel():
    #     '''
    #     TODO 接收消息时判断，如果为群聊消息且 now_timestamp <= mute_expire_timestamp 则过滤
    #     '''
    #     return group_list

    # @staticmethod
    # def GetQqAccountInfoModel():
    #     return qq_account_info
    
    # @staticmethod
    # def GetPcrAccountInfoModel():
    #     return pcr_account_info
    
    @staticmethod
    async def UpdatePcrAccountInfoModel(accountDict: dict) -> int:
        """
        验证传入的dict。若能登录成功，插入或更新数据库记录。

        Args:
            accountDict (dict): {"account": str, "password": str}
        
        Raises:
            AssertionError: accountDict中缺少字段
            Query模块获取游戏内数据时可能抛出的异常

        Returns:
            int: pcrid
        """        
        pcr_account_info.delete().where(pcr_account_info.account == accountDict["account"]).execute()
        client = await query.VerifyAccount(accountDict)
        # pcrid = await query.get_pcrid(accountDict)
        # pcrName = await query.get_username(accountDict)
        # pcr_account_info.create(pcrid = pcrid, account = accountDict["account"], password = accountDict["password"], update_time = str(datetime.now()), is_valid = True, pcrname_cache = pcrName)
        return client._viewerId
                        
    @staticmethod
    def TryGetPcridFromAccount(account: str) -> Union[int, None]:
        pcrAccount:pcr_account_info = pcr_account_info.get_or_none(pcr_account_info.account == account)
        return None if pcrAccount is None else pcrAccount.pcrid
    
    @staticmethod
    def GetAccountDictFromPcrid(pcrid: str) -> dict:
        """
        在PcrAccountInfoModel中查找pcrid对应的记录。

        Raises:
            KeyError: 数据库中没有传入的pcrid
            AssertionError: 数据库中pcrid对应记录的is_valid字段为假

        Returns:
            dict: {"account": str, "password": str}
        """
        pcrAccount:pcr_account_info = pcr_account_info.get_or_none(pcr_account_info.pcrid == pcrid)
        if pcrAccount == None:
            raise KeyError(f'数据库中没有{pcrid}')
        assert pcrAccount.is_valid, f'{pcrid}被标记为不合法，请先更新数据库记录'
        return {"account": pcrAccount.account, "password": pcrAccount.password}

    @staticmethod
    def GetPcrClientFromPcrid(pcrid: int) -> PcrClient:
        """
        Raises:
            KeyError: 数据库中没有传入的pcrid
            AssertionError: 数据库中pcrid对应记录的is_valid字段为假
        
        Returns:
            PcrClient: 不会验证PcrClient是否可以登录
        """
        return PcrClientManager.FromDict(AutopcrDatabaseTable.GetAccountDictFromPcrid(pcrid))
                                
    # @staticmethod
    # def GetArenaBindModel():
    #     '''
    #     TODO 新开函数。在新增row时，若pcrid在pcrid_arena_info表中不存在，新建。
    #     TODO 新开函数。在删除row时，若pcrid在arena_bind中不再出现，相应删除pcrid_arena_info。
    #     '''
    #     return arena_bind

    # @staticmethod
    # def GetArenaInfoModel():
    #     return arena_info

    # @staticmethod
    # def GetDailyBindModel():
    #     return daily_bind

    # @staticmethod
    # def GetDailyInfoModel():
    #     return daily_info
    
    # @staticmethod
    # def GetFarmInfoModel():
    #     return farm_info

    @staticmethod
    async def UpdateFarmInfoModel(pcrid: int, alsoTryUpdateClanInfoModel = True) -> int:
        """
        更新pcrid在FarmInfoModel中对应的记录，
        以及该pcrid对应的clan_id在ClanInfoModel中对应的记录。

        Raises:
            KeyError: 数据库中没有传入的pcrid
            AssertionError: 数据库中pcrid对应记录的is_valid字段为假
            Query模块获取游戏内数据时可能抛出的异常

        Returns:
            int: clan_id
        """
        farm_info.delete().where(farm_info.pcrid == pcrid).execute()
        pcrAccount = AutopcrDatabaseTable.GetAccountDictFromPcrid(pcrid)
        home_index = await query.get_home_index(pcrAccount)
        clanid = home_index["user_clan"]["clan_id"] # 可能没有公会而抛出异常
        farm_info.create(pcrid=pcrid, clanid_cache=clanid)
        
        if alsoTryUpdateClanInfoModel:
            try:
                await query.get_clan_info(pcrAccount, clanid)
            except:
                print_exc()
            
        return clanid
    
    # @staticmethod
    # def GetFarmBindModel():
    #     return farm_bind
    
    # @staticmethod
    # def GetClanInfoModel():
    #     return clan_info