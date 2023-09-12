import asyncio
import json
from enum import IntEnum, unique
from os.path import dirname, join, exists
from traceback import print_exc
from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import List, Tuple, Union, Optional

from ..autopcr_db.typing import *
from .pcr_client import PcrClientManager, PcrClient
from ..priconne import chara
from .utils import item_utils, map_utils

class PcrApiException(Exception):
    """
    所有和BCR服务器交互过程中产生的异常
    """
    ...
    
class PcrApi:
    def __init__(self, accountInfo: Union[dict, int, PcrAccountInfo]):
        self._pcrClient = PcrClientManager.Get(accountInfo)
        self._UpdateRecord()
        

    @property
    def Account(self) -> str:
        return self._pcrClient.biliSdkClient.account
    
    
    @property
    def Password(self) -> str:
        return self._pcrClient.biliSdkClient.password
    
    @property
    def OutputName(self) -> str:
        if self._record is not None:
            return f'[{self._record.pcrname_cache}]({self._record.pcrid})'
        if self._pcrClient._viewerId != 0:
            return f'[{self._pcrClient._viewerId}]'
        return f'[{self._pcrClient.biliSdkClient.account}]'
    
        
    def _UpdateRecord(self) -> None:
        self._record: PcrAccountInfo = PcrAccountInfo.get_or_none(PcrAccountInfo.account == self.Account)


    async def Login(self, force: bool = False) -> None:
        """
        Raises:
            PcrApiException
        """
        try:
            await self._pcrClient.LoginAndCheck(forceTry=force)
        except Exception as e:
            raise PcrApiException from e
        if self._record is None:
            self._UpdateRecord()
            try:
                await self.GetUsername()
            except Exception as e:
                pass

    
    class CallApiFullResponse:
        def __init__(self, data_header: dict = {}, data: dict = {}):
            self.data_header = data_header
            self.data = data

    async def CallApiFull(self, url: str, postData: dict = {}) -> CallApiFullResponse:
        """
        Raises:
            PcrApiException
        """
        await self.Login()
        try:
            res = await self._pcrClient.CallApi(url, postData, True)
        except Exception as e:
            raise PcrApiException from e
        return PcrApi.CallApiFullResponse(res[1], res[0])
    
    async def CallApi(self, url: str, postData: dict = {}) -> dict:
        """
        Raises:
            PcrApiException
        """
        await self.Login()
        try:
            return await self._pcrClient.CallApi(url, postData)
        except Exception as e:
            raise PcrApiException from e

    
    @property
    def Pcrid(self) -> int:
        assert self._pcrClient._viewerId != 0, f'获取账号[{self.Account}]Pcrid失败，请先登录'
        return self._pcrClient._viewerId
        
    async def GetPcrid(self):
        if self._record is not None:
            return self._record.pcrid
        await self.Login()
        return self._pcrClient._viewerId
        
    
    async def GetUsername(self) -> str:
        return (await self.GetLoadIndexRaw())["user_info"]["user_name"]
    
    
    async def GetHomeIndexRaw(self) -> dict:
        res = await self.CallApi("/home/index", {'message_id': 1, 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})
        FarmInfo.update(clanid_cache=res.get("user_clan", {}).get("clan_id", 0)).where(FarmInfo.pcrid == self.Pcrid).execute()
        return res
    
    async def GetLoadIndexRaw(self) -> dict:
        res = await self.CallApi("/load/index", {'carrier': 'OPPO'})
        self._record.pcrname_cache = res["user_info"]["user_name"]
        self._record.save()
        return res


    class CreateClanRequest(BaseModel):
        clan_name: str = Field(...)
        description: str = Field(...)
        join_condition: int = Field(...)
        activity: int = Field(...)
        clan_battle_mode: int = Field(...)

        def __init__(self, clan_name: str, description: str = ""):
            super().__init__(
                clan_name=clan_name,
                description=description, 
                join_condition=3, 
                activity=1,
                clan_battle_mode=0)

    class CreateClanResponse(BaseModel):
        clan_id: int = Field(..., alias="clan_id")
        clan_status: Optional[int] = None

        @validator('clan_id', pre=True, always=True)
        def convert_clan_id(cls, v):
            return int(v)

    async def CreateClan(self, request: CreateClanRequest) -> CreateClanResponse:
        """
        创建一个公会。
        加入方式为“仅限邀请”，会战模式为行会模式。

        Raises:
            PcrApiException
        """
        res = PcrApi.CreateClanResponse(**(await self.CallApi("/clan/create", request.model_dump())))
        ClanInfo.create(clanid=res.clan_id, clan_name_cache=request.clan_name, clan_member_count_cache=1, leader_pcrid_cache=self.Pcrid)
        FarmInfo.update(clanid_cache=res.clan_id).where(FarmInfo.pcrid == self.Pcrid).execute()
        return res


    async def GetProfile(self, target_viewer_id: int) -> dict:
        """
        Raises:
            PcrApiException
        """
        return await self.CallApi("/profile/get_profile", {"target_viewer_id": target_viewer_id})
    
    
    class ClanInviteRequest(BaseModel):
        invited_viewer_id: int = Field(...)
        invite_message: str = Field(...)

        def __init__(self, invited_viewer_id: int, invite_message: str = "请多关照。"):
            super().__init__(
                invited_viewer_id=invited_viewer_id,
                invite_message=invite_message)

    async def ClanInvite(self, request: ClanInviteRequest) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/clan/invite", request.model_dump())
        # TODO 更新数据库
    
    
    class InvitedClanResponse(BaseModel):
        invite_id: int = Field(...)
        clan_id: int = Field(...)
        invite_message: str = Field(...)
        leader_viewer_id: int = Field(...)
        clan_name: str = Field(...)
        description: str = Field(...)
        join_condition: int = Field(...)
        activity: int = Field(...)
        clan_battle_mode: int = Field(...)
        member_num: int = Field(...)
        member_num_range: int = Field(...)
        leader_name: str = Field(...)
        grade_rank: int = Field(...)
        
    async def GetInvitedClans(self) -> List[InvitedClanResponse]:
        """
        Raises:
            PcrApiException
        """
        home_index = await self.GetHomeIndexRaw()
        if home_index.get("have_clan_invitation", 0) == 0:
            return []
        res = await self.CallApi("/clan/invited_clan_list", {"page": 0})
        res = json.loads(json.dumps(res, ensure_ascii=False)) # 将所有key转为str，避免**clan报错
        return [PcrApi.InvitedClanResponse(**clan) for clan in res['list']]
        
    async def AcceptClanInvite(self, clan_id: int) -> None:
        """
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/clan/others_info", {"clan_id": clan_id}) # 走个过场，模拟真实API触发顺序
        res = await self.CallApi("/clan/join", {"clan_id": clan_id, "from_invite": 1})
        FarmInfo.update(clanid_cache=clan_id).where(FarmInfo.pcrid == self.Pcrid).execute()