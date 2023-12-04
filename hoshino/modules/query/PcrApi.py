#basic
import asyncio
import json
from enum import IntEnum, unique
from os.path import dirname, join, exists
from traceback import print_exc
from datetime import datetime
from typing import List, Tuple, Union, Optional, Dict
#3rd
from pydantic import BaseModel, Field, validator
#relative
from ..autopcr_db.typing import *
from .pcr_client import PcrClientManager, PcrClient
from ..priconne import chara
from .utils import item_utils, map_utils
from ..utils import output

class PcrApiException(Exception):
    """
    所有和BCR服务器交互过程中产生的异常
    """
    def __str__(self):
        original_message = super().__str__()
        if original_message:
            return original_message
        if self.__cause__:
            return str(self.__cause__)
        print_exc()
        return "" 
    
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
            if isinstance(postData, str):
                postData = json.loads(postData)
            res = await self._pcrClient.CallApi(url, postData, True)
        except Exception as e:
            print_exc()
            raise PcrApiException from e
        return PcrApi.CallApiFullResponse(res[1], res[0])
    
    async def CallApi(self, url: str, postData: dict = {}) -> dict:
        """
        Raises:
            PcrApiException
        """
        return (await self.CallApiFull(url, postData)).data
    
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
        description: str = Field(default="请多关照。")
        join_condition: int = Field(default=3)
        activity: int = Field(default=1)
        clan_battle_mode: int = Field(default=0)
        

    class CreateClanResponse(BaseModel):
        clan_id: int = Field(..., alias="clan_id")
        clan_status: Optional[int] = None

        @validator('clan_id', pre=True, always=True)
        def convert_clan_id(cls, v):
            return int(v) # pcr有时会返回str，将其转为int

    async def CreateClan(self, request: CreateClanRequest) -> CreateClanResponse:
        """
        创建一个公会。
        加入方式为“仅限邀请”，会战模式为行会模式。

        Raises:
            PcrApiException
        """
        res = PcrApi.CreateClanResponse(**(await self.CallApi("/clan/create", request.model_dump_json())))
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
        await self.CallApi("/clan/invite", request.model_dump_json())
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
        res = json.loads(json.dumps(res, ensure_ascii=False)) # pcr有时会返回None:1。将所有key转为str，避免**clan报错
        return [PcrApi.InvitedClanResponse(**clan) for clan in res['list']]
        
    async def AcceptClanInvite(self, clan_id: int) -> None:
        """
        Raises:
            PcrApiException
        """
        others_info = await self.CallApi("/clan/others_info", {"clan_id": clan_id}) # 真实API触发顺序
        res = await self.CallApi("/clan/join", {"clan_id": clan_id, "from_invite": 1})
        FarmInfo.update(clanid_cache=clan_id).where(FarmInfo.pcrid == self.Pcrid).execute()
        try:
            ClanInfo.update(clan_member_count_cache=1 + others_info["clan"]["detail"]["member_num"]).where(ClanInfo.clanid == clan_id).execute()
            ClanInfo.update(clan_name_cache=others_info["clan"]["detail"]["clan_name"]).where(ClanInfo.clanid == clan_id).execute()
        except Exception as e:
            pass
    
    class CharaLoveInfoResponse(BaseModel):
        chara_id: int = Field(..., description="角色的4位ID")
        chara_love: int = Field(..., description="当前经验值 升级所需：175, 245, 280, 700, 700, 700, 1400, 2100, 2800, 3500, 4200")
        love_level: int = Field(..., description="当前等级 1-12")
        
    async def GetCharaLoveInfoList(self) -> List[CharaLoveInfoResponse]:
        """
        Raises:
            PcrApiException
        """
        res = await self.GetLoadIndexRaw()
        return [PcrApi.CharaLoveInfoResponse(**x) for x in res.get("user_chara_info", [])]
    
    async def GetCharaLoveInfoDict(self) -> Dict[int, CharaLoveInfoResponse]:
        """
        Raises:
            PcrApiException
        Return:
            int: 角色4位ID
        """
        return {x.chara_id: x for x in await self.GetCharaLoveInfoList()}
    
    class ItemInfoRequest(BaseModel):
        item_id: int = Field(...)
        item_num: int = Field(..., description="需要使用的数量")
        current_item_num: int = Field(..., description="当前拥有的数量")

    class MultiGiveGiftRequest(BaseModel):
        unit_id: int = Field(..., description="6位角色ID")
        item_info: List['PcrApi.ItemInfoRequest'] = Field(...)

    async def MultiGiveGift(self, request: MultiGiveGiftRequest) -> None:
        await self.CallApi("/room/multi_give_gift", request.model_dump_json())

    class UnitInfoResponse(BaseModel):
        id: int = Field(..., description="角色6位ID")
        unit_rarity: int = Field(..., description="实际星级")
        battle_rarity: int = Field(..., description="当前设置的战斗星级。若同实际星级则为0")
        unit_level: int = Field(..., description="当前等级")
        promotion_level: int = Field(..., description="当前Rank")
        exceed_stage: int
        unit_exp: int
        get_time: int
        union_burst: List[Dict]
        main_skill: List[Dict]
        ex_skill: List[Dict]
        free_skill: List[Dict]
        equip_slot: List[Dict]
        unique_equip_slot: List[Dict]
        skin_data: Dict
        favorite_flag: int

    async def GetUnitInfoList(self) -> List[UnitInfoResponse]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.GetLoadIndexRaw()).get("unit_list", [])
        res = json.loads(json.dumps(res, ensure_ascii=False)) # pcr有时会返回None:1。将所有key转为str，避免**clan报错
        return [PcrApi.UnitInfoResponse(**x) for x in res]
    
    async def GetUnitInfo(self, chara_id: int) -> UnitInfoResponse:
        """
        Args:
            chara_id: 角色6位ID
        Raises:
            PcrApiException
            ValueError: 该账号未查询到此角色
        """
        character = next((x for x in await self.GetUnitInfoList() if x.id == chara_id), None)
        if character is None:
            raise ValueError(f"该账号未查询到角色{PcrApi.CharaOutputName(chara_id)}")
        return character
    
    async def GetUnitInfoDict(self) -> Dict[int, UnitInfoResponse]:
        """
        Raises:
            PcrApiException
        Return:
            int: 角色6位ID
        """
        return {x.id: x for x in await self.GetUnitInfoList()}
    
    class ItemInfoResponse(BaseModel):
        type: int = Field(..., description="==2")
        id: int = Field(..., description="5位")
        stock: int
        
    async def GetItemInfoList(self) -> List[ItemInfoResponse]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.GetLoadIndexRaw()).get("item_list", [])
        return [PcrApi.ItemInfoResponse(**x) for x in res]
        
    async def GetItemId2Stock(self) -> Dict[int, int]:
        """
        Raises:
            PcrApiException
        Returns:
            int, int: 5位ID -> 数量
        """
        return {x.id: x.stock for x in await self.GetItemInfoList()}
    
    async def GetItemStock(self, item_id: int) -> int:
        """
        Args:
            item_id: 5位ID
        Raises:
            PcrApiException
        """
        return (await self.GetItemId2Stock()).get(item_id, 0)

    class UserEquipResponse(BaseModel):
        type: int = Field(..., description="==4")
        id: int = Field(..., description="6位")
        stock: int
        
    async def GetUserEquipList(self) -> List[UserEquipResponse]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.GetLoadIndexRaw()).get("user_equip", [])
        return [PcrApi.UserEquipResponse(**x) for x in res]
        
    async def GetUserEquipId2Stock(self) -> Dict[int, int]:
        """
        Raises:
            PcrApiException
        Returns:
            int, int: 6位ID -> 数量
        """
        return {x.id: x.stock for x in await self.GetUserEquipList()}
    
    async def GetUserEquipStock(self, user_equip_id: int) -> int:
        """
        Args:
            user_equip_id: 6位ID
        Raises:
            PcrApiException
        """
        return (await self.GetUserEquipId2Stock()).get(user_equip_id, 0)
    
    async def ReadStory(self, story_id: int) -> None:
        """
        Args:
            story_id (int): 7位ID。前四位为角色id，后三位为剧情id
        Raises:
            PcrApiException
        """
        await self.CallApi("/story/check", {"story_id": story_id}) # 每次读取剧情前都要先调用check
        await self.CallApi("/story/start", {"story_id": story_id}) # 只有第一次读剧情获取奖赏才需要 # 其实有返回，告诉你获得多少钻石
    
    class EventStatus(BaseModel):
        event_type: int = Field(..., description="只应该为1")
        event_id: int = Field(..., description="5位ID。10xxx为当前/复刻活动，20xxx为外传")
        period: int = Field(..., description="1=没开放，2=开放中，3=已结束（不能刷图，可以换票和看剧情）")

    class StoryStatus(BaseModel):
        story_id: int = Field(..., description="7位ID。1开头=角色剧情，2开头=主线剧情，5开头=活动剧情，7开头=露娜塔剧情。")
        is_unlocked: bool
        is_readed: bool

    class ItemInfo(BaseModel):
        id: int
        type: int
        stock: int

    class BossBattleInfo(BaseModel):
        boss_id: int = Field(..., description="7位ID。前5位为活动ID，后2位为bossID（01=N，02=H，03=VH，04=SP，05=表演赛）")
        is_unlocked: bool
        appear_num: Optional[int] = 0
        attack_num: Optional[int] = 0
        kill_num: Optional[int] = 0
        daily_kill_count: Optional[int] = 0
        oneblow_kill_count: Optional[int] = 0
        remain_time: Optional[int] = 90
        is_force_unlocked: Optional[bool] = False

    class EventInfoResponse(BaseModel):
        event_status: 'PcrApi.EventStatus'
        opening: 'PcrApi.StoryStatus'
        ending: 'PcrApi.StoryStatus'
        stories: List['PcrApi.StoryStatus']
        boss_ticket_info: 'PcrApi.ItemInfo'
        boss_battle_info: List['PcrApi.BossBattleInfo']
        boss_enemy_info: List[Dict]
        # login_bonus: Optional[List[Dict] | Dict] = None
        # missions: List[Dict]
        # is_hard_quest_unlocked: Optional[bool] = False
        # special_battle_info: Optional[Dict] = {}
        # release_minigame: Optional[List[int]] = []
        
    async def GetEventInfo(self, event_id: int) -> EventInfoResponse:
        """
        Args:
            event_id (int): 5位ID。10xxx
        Raises:
            PcrApiException
        """
        return PcrApi.EventInfoResponse(**(await self.CallApi("/event/hatsune/top", {"event_id": event_id})))
    
    async def GetEvents(self) -> List[EventStatus]:
        """
        Raises:
            PcrApiException
        """
        return [PcrApi.EventStatus(**x) for x in (await self.GetLoadIndexRaw()).get("event_statuses", [])]


    class EatPuddingGameCookingInfo(BaseModel):
        frame_id: int = Field(..., description="坑位，1~24")
        pudding_id: int
        start_time: str


    class EatPuddingGameOwnInfo(BaseModel):
        pudding_id: int
        count: int
        flavor_status: int = Field(..., description="解锁文案数。0~3")
        read_status: bool

    class EatPuddingGameDramaInfo(BaseModel):
        drama_id: int
        read_status: bool

    # EatPuddingGameInfoResponse model with nested structures
    class EatPuddingGameInfoResponse(BaseModel):
        psy_setting: Dict
        cooking_status: List['PcrApi.EatPuddingGameCookingInfo']
        total_count: int
        pudding_note: List['PcrApi.EatPuddingGameOwnInfo']
        pudding_type_num: int
        drama_list: List['PcrApi.EatPuddingGameDramaInfo']

    async def GetEatPuddingGameInfo(self) -> EatPuddingGameInfoResponse:
        """
        Raises:
            PcrApiException
        """
        return PcrApi.EatPuddingGameInfoResponse(**(await self.CallApi("/psy/top", {"from_system_id": 6001})))
    
    async def EatPuddingGameReadDrama(self, drama_id: int) -> None:
        """
        Args:
            drama_id (int): 1~11
        Raises:
            PcrApiException
        """
        await self.CallApi("/psy/read_drama", {"drama_id": drama_id, "from_system_id": 6001})
    
    async def EatPuddingGameStartCook(self, start_cooking_frame_id_list: List[int], get_pudding_frame_id_list: List[int]) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/psy/start_cooking", {"start_cooking_frame_id_list": start_cooking_frame_id_list, "get_pudding_frame_id_list": get_pudding_frame_id_list, "from_system_id": 6001})

    @staticmethod
    def CharaOutputName(chara_id: int) -> str:
        chara_id = int(chara_id)
        if 100000 <= chara_id <= 999999:
            chara_id //= 100
        return f'[{chara.fromid(chara_id).name}]({chara_id})'