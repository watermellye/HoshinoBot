#basic
import json
from traceback import print_exc
from typing import List, Tuple, Union, Optional, Dict
#3rd
from pydantic import BaseModel, Field, validator
#relative
from ..autopcr_db.typing import *
from .pcr_client import PcrClientManager
from ..priconne import chara
from .utils import map_utils
from ..utils.output import Outputs, Output, OutputFlag

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


    async def Login(self, still_try_login_even_if_record_is_invalid: bool = False, always_call_login_and_check: bool = False) -> None:
        """
        Raises:
            PcrApiException
        """
        try:
            await self._pcrClient.LoginAndCheck(still_try_login_even_if_record_is_invalid=still_try_login_even_if_record_is_invalid, always_call_login_and_check=always_call_login_and_check)
        except Exception as e:
            raise PcrApiException from e
        if self._record is None:
            self._UpdateRecord()
            try:
                await self.u_get_username_async()
            except Exception as e:
                pass

    
    class CallApiFullResponse:
        def __init__(self, data_header: dict = {}, data: dict = {}):
            self.data_header = data_header
            self.data = json.loads(json.dumps(data, ensure_ascii=False)) # pcr有时会返回None:1。将所有key转为str，避免**clan报错


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
    def pcrid(self) -> int:
        assert self._pcrClient._viewerId != 0, f'获取账号[{self.Account}]Pcrid失败，请先登录'
        return self._pcrClient._viewerId

    async def u_get_pcrid_async(self):
        if self._record is not None:
            return self._record.pcrid
        await self.Login()
        return self._pcrClient._viewerId

    async def u_get_username_async(self) -> str:
        return (await self.load__index_async())["user_info"]["user_name"]

    async def u_get_server_time_async(self) -> int:
        res = await self.CallApiFull("/gacha/index", {})
        return int(res.data_header["servertime"])

    async def home__index_async(self) -> dict:
        res = await self.CallApi("/home/index", {'message_id': 1, 'tips_id_list': [], 'is_first': 1, 'gold_history': 0})
        FarmInfo.update(clanid_cache=res.get("user_clan", {}).get("clan_id", 0)).where(FarmInfo.pcrid == self.pcrid).execute()
        return res

    async def load__index_async(self) -> dict:
        res = await self.CallApi("/load/index", {'carrier': 'OPPO'})
        PcrAccountInfo.update(pcrname_cache=res["user_info"]["user_name"]).where(PcrAccountInfo.pcrid == self.pcrid).execute()
        return res

    class home__index__talent_quest_area_info__item(BaseModel):
        talent_id: int = Field(description="1=火 2=水 3=风 4=光 5=暗")
        daily_bonus_use_count: int = Field(...)
        daily_clear_count: int = Field(...)
        daily_recovery_count: int = Field(...)

    async def home__index__talent_quest_area_info_async(self) -> list['PcrApi.home__index__talent_quest_area_info__item']:
        """
        Raises:
            PcrApiException
            AssertionError
        """
        home_index = await self.home__index_async()
        assert "talent_quest_area_info" in home_index, f'/home/index response has no `talent_quest_area_info` info.'
        return [PcrApi.home__index__talent_quest_area_info__item(**info) for info in home_index["talent_quest_area_info"]]
    
    async def home__index__cleared_talent_quest_id_list_async(self) -> list[map_utils.TalentPCRMap]:
        """
        Raises:
            PcrApiException
            AssertionError
        """
        home_index = await self.home__index_async()
        assert "cleared_talent_quest_id_list" in home_index, f'/home/index response has no `cleared_talent_quest_id_list` info.' # 没通关过任何深域则为 []
        return [map_utils.from_id(talent_quest_id) for talent_quest_id in home_index["cleared_talent_quest_id_list"]]

    class load__index__user_info(BaseModel):
        viewer_id: int = Field(description="13位pcrid")
        user_name: str = Field(description="用户名")
        user_comment: str = Field(description="用户签名")
        team_level: int = Field(description="用户等级")
        user_stamina: int = Field(description="当前体力")
        max_stamina: int = Field(description="自动回复的最大体力") # 356
        team_exp: int = Field(description="当前经验")
        favorite_unit_id: int = Field(description="头像6位ID")
        tutorial_flag: int = Field(...) # 100
        invite_accept_flag: int = Field(...) # 0
        user_birth: int = Field(...) # 0
        platform_id: int = Field(...) # 1
        channel_id: int = Field(...) # 1000
        last_ac: str = Field(description="上一次访问的API") # /room/start
        last_ac_time: int = Field(description="上一次访问API的时间") # 1759788139
        server_id: int = Field(...) # 20001
        reg_time: int = Field(description="注册时间") # 1587091509
        emblem: dict = Field(...) # { "emblem_id": 10201110, "ex_value": 0 }
        stamina_full_recovery_time: int = Field(description="体力完全恢复的时间") # 1759915198

    async def load__index__user_info_async(self) -> 'PcrApi.load__index__user_info':
        """
        Raises:
            PcrApiException
            AssertionError
        """
        load_index = await self.load__index_async()
        assert "user_info" in load_index, f'/load/index response has no `user_info` info.'
        return PcrApi.load__index__user_info(**load_index["user_info"])
    
    async def u_get_current_stamina_async(self) -> int:
        """
        Raises:
            PcrApiException
            AssertionError
        """
        user_info = await self.load__index__user_info_async()
        return user_info.user_stamina

    class load__index__shop__alchemy(BaseModel):
        max_count: int = Field(...) # 70
        exec_count: int = Field(...) # 0
    
    class load__index__shop__recover_stamina(BaseModel):
        count: int = Field(description="最大购买次数") # 40
        max_count: int = Field(description="最大购买次数") # 40
        exec_count: int = Field(description="今日已购买次数") # 0
        recovery: int = Field(description="每次恢复的体力值") # 120
        cost: int = Field(description="购买下一管消耗的钻石") # 40
    
    class load__index__shop(BaseModel):
        alchemy: 'PcrApi.load__index__shop__alchemy'
        recover_stamina: 'PcrApi.load__index__shop__recover_stamina'

    async def load__index__shop__async(self) -> 'PcrApi.load__index__shop':
        """
        Raises:
            PcrApiException
            AssertionError
        """
        load_index = await self.load__index_async()
        assert "shop" in load_index, f'/load/index response has no `shop` info.'
        return PcrApi.load__index__shop(**load_index["shop"])
    
    async def shop__recover_stamina_async(self, current_currency_num: Optional[int]) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/shop/recover_stamina", {"current_currency_num": current_currency_num or await self.u_get_total_jewel_async()})
    
    async def u_recover_stamina_once_async(self, user_allow_recover_count: int) -> tuple[Outputs, int]:
        """
        Raises:
            PcrApiException
            AssertionError
        Returns:
            tuple(Outputs, int): 
                Outputs=操作日志。保证Outputs.__bool__为真。
                int=操作后体力。仅当Outputs.__bool__为真时有效。（目前本函数保证返回的Outputs总是为真）
        """
        user_current_stamina = await self.u_get_current_stamina_async()
        if user_allow_recover_count == 0:
            return Outputs.FromStr(OutputFlag.Skip, f'用户允许的购买体力次数为0，放弃购买。'), user_current_stamina
        
        shop_info = await self.load__index__shop__async()
        if user_current_stamina + shop_info.recover_stamina.recovery > 999:
            return Outputs.FromStr(OutputFlag.Skip, f'当前体力{user_current_stamina}，购买体力会导致溢出，放弃购买。'), user_current_stamina

        outputs = Outputs()
        if user_allow_recover_count > shop_info.recover_stamina.max_count:
            outputs.append(OutputFlag.Warning, f'用户允许的购买体力次数{user_allow_recover_count}大于商店最大购买次数{shop_info.recover_stamina.max_count}，将其视为{shop_info.recover_stamina.max_count}。')
            user_allow_recover_count = shop_info.recover_stamina.max_count
        if shop_info.recover_stamina.exec_count >= user_allow_recover_count:
            outputs.append(OutputFlag.Skip, f'今日已购买体力{shop_info.recover_stamina.exec_count}/{user_allow_recover_count}次，无法购买更多。')
            return outputs, user_current_stamina        
        
        jewel = await self.u_get_total_jewel_async()
        if jewel < shop_info.recover_stamina.cost:
            outputs.append(OutputFlag.Warn, f'用户当前钻石数量{jewel}少于购买体力所需数量{shop_info.recover_stamina.cost}，放弃购买。')
            return outputs, user_current_stamina
        
        await self.shop__recover_stamina_async(jewel)
        user_current_stamina += shop_info.recover_stamina.recovery
        outputs.append(OutputFlag.Succeed, f'花费{shop_info.recover_stamina.cost}钻购买1管体力成功（今日{shop_info.recover_stamina.exec_count + 1}/{user_allow_recover_count}）。当前体力{user_current_stamina}')
        return outputs, user_current_stamina
        
    async def u_recover_stamina_to_target_async(self, user_allow_recover_count: int, target_stamina: int) -> tuple[Outputs, int]:
        """
        Raises:
            PcrApiException
            AssertionError
        Returns:
            tuple(Outputs, int): 
                Outputs=操作日志
                int=操作后体力。仅当Outputs.__bool__为真时有效
        """
        assert 0 < target_stamina <= 999, f'目标体力{target_stamina}不在(0, 999]范围内'
        
        user_current_stamina = await self.u_get_current_stamina_async()
        outputs = Outputs()
        while user_current_stamina < target_stamina:
            outputs_once, user_current_stamina_new = await self.u_recover_stamina_once_async(user_allow_recover_count)
            outputs += outputs_once
            if user_current_stamina_new == user_current_stamina:
                break
            user_current_stamina = user_current_stamina_new
            
        if user_current_stamina < target_stamina:
            outputs.append(OutputFlag.Info, f'当前体力{user_current_stamina}，未达到目标体力{target_stamina}。')
        return outputs, user_current_stamina

    class load__index__ini_setting__talent_quest(BaseModel):
        daily_bonus_use_limit_count: int = Field(...)
        daily_clear_limit_count: int = Field(...)
        recovery_max_count: int = Field(...)
        recovery_cost: int = Field(...)

    async def get_load__index__ini_setting__talent_quest_async(self) -> 'PcrApi.load__index__ini_setting__talent_quest':
        """
        Raises:
            PcrApiException
            AssertionError
        """
        load_index = await self.load__index_async()
        talent_quest_raw = load_index.get("ini_setting", {}).get("talent_quest", {})
        assert talent_quest_raw, f'/load/index response has no `ini_setting.talent_quest` info.'
        return PcrApi.load__index__ini_setting__talent_quest(**talent_quest_raw)

    class clan__create_request(BaseModel):
        clan_name: str = Field(...)
        description: str = Field(default="请多关照。")
        join_condition: int = Field(default=3)
        activity: int = Field(default=1)
        clan_battle_mode: int = Field(default=0)

    class clan__create_response(BaseModel):
        clan_id: int = Field(..., alias="clan_id")
        clan_status: Optional[int] = None

        @validator('clan_id', pre=True, always=True)
        def convert_clan_id(cls, v):
            return int(v) # pcr有时会返回str，将其转为int

    async def clan__create__async(self, request: clan__create_request) -> clan__create_response:
        """
        创建一个公会。
        加入方式为“仅限邀请”，会战模式为行会模式。

        Raises:
            PcrApiException
        """
        res = PcrApi.clan__create_response(**(await self.CallApi("/clan/create", request.model_dump_json())))
        ClanInfo.create(clanid=res.clan_id, clan_name_cache=request.clan_name, clan_member_count_cache=1, leader_pcrid_cache=self.pcrid)
        FarmInfo.update(clanid_cache=res.clan_id).where(FarmInfo.pcrid == self.pcrid).execute()
        return res


    async def profile__get_profile_raw_async(self, target_viewer_id: int) -> dict:
        """
        Raises:
            PcrApiException
        """
        return await self.CallApi("/profile/get_profile", {"target_viewer_id": target_viewer_id})

    class profile__get_profile__quest_info__talent_quest_item(BaseModel):
        talent_id: int = Field(description="1=火 2=水 3=风 4=光 5=暗")
        clear_count: int = Field(description="最高通关关卡序号") # 30 = 3-10
        
    class profile__get_profile__user_info(BaseModel):
        viewer_id: int
        user_name: str
        user_comment: str
        team_level: int
        team_exp: int
        emblem: 'PcrApi.clan__info__clan__members__emblem'
        last_login_time: int
        arena_rank: int
        arena_group: int
        arena_time: int
        grand_arena_rank: int
        grand_arena_group: int
        grand_arena_time: int
        open_story_num: int
        unit_num: int
        total_power: int
        tower_cleared_floor_num: int
        tower_cleared_ex_quest_count: int
        friend_num: int
        princess_knight_rank_total_exp: int = Field(description="公主骑士(深域)经验值", default=0)

    class profile__get_profile__quest_info(BaseModel):
        normal_quest: Tuple[int, int, int] = Field(..., description="1/2/3星通关关卡数量")
        hard_quest: Tuple[int, int, int] = Field(..., description="1/2/3星通关关卡数量")
        very_hard_quest: Tuple[int, int, int] = Field(..., description="1/2/3星通关关卡数量")
        byway_quest: int = Field(..., description="支线关卡通关数量")
        talent_quest: List['PcrApi.profile__get_profile__quest_info__talent_quest_item']
        
    class profile__get_profile(BaseModel):
        user_info: 'PcrApi.profile__get_profile__user_info'
        quest_info: 'PcrApi.profile__get_profile__quest_info'
        clan_name: str
        clan_battle_id: int
        clan_battle_mode: int
        clan_battle_own_score: int
        friend_support_units: List[Dict]
        clan_support_units: List[Dict]
    
    async def profile__get_profile_async(self, target_viewer_id: int) -> profile__get_profile:
        """
        Raises:
            PcrApiException
        """
        res = PcrApi.profile__get_profile(**(await self.profile__get_profile_raw_async(target_viewer_id)))
        PcrAccountInfo.update(pcrname_cache=res.user_info.user_name).where(PcrAccountInfo.pcrid == target_viewer_id).execute()
        return res


    async def profile__rename_async(self, new_name: str) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/profile/rename", {"user_name": new_name}) # returns None
        PcrAccountInfo.update(pcrname_cache=new_name).where(PcrAccountInfo.pcrid == self.pcrid).execute()


    @staticmethod
    def _update_clan_info_static(clan_info: dict) -> None:
        if clan_info.get("clan", {}).get("detail", {}).get("clan_id", None) is None:
            return;
        clan_detail = clan_info["clan"]["detail"]
        clan_id = clan_detail["clan_id"]
        
        existing_clan: ClanInfo = ClanInfo.get_or_none(ClanInfo.clanid == clan_id)
        if existing_clan is not None and \
        existing_clan.clan_name_cache == clan_detail["clan_name"] and \
        existing_clan.clan_member_count_cache == clan_detail["member_num"] and \
        existing_clan.leader_pcrid_cache == clan_detail["leader_viewer_id"]:
            ...
        else:
            ClanInfo.delete().where(ClanInfo.clanid == clan_id).execute()
            ClanInfo.create(
                clanid=clan_id,
                clan_name_cache=clan_detail["clan_name"],
                clan_member_count_cache=clan_detail["member_num"],
                leader_pcrid_cache=clan_detail["leader_viewer_id"])


    async def u_update_clan_database_async(self) -> dict:
        """
        Raises:
            PcrApiException
        """
        return await self.clan__info_raw_async()


    async def clan__info_raw_async(self) -> dict:
        """
        Raises:
            PcrApiException
        """
        res = await self.CallApi("/clan/info", {"clan_id": 0, "get_user_equip": 0}) # 别动，就是0
        
        self._update_clan_info_static(res)
        try:
            clan_id = res["clan"]["detail"]["clan_id"]
            FarmInfo.update(clanid_cache=clan_id).where(FarmInfo.pcrid == self.pcrid).execute()
            FarmBind.update(permitted_clanid=clan_id).where(FarmBind.pcrid == self.pcrid).execute()
        except Exception as e:
            print_exc()
        
        return res
    
    class clan__info__clan__members__emblem(BaseModel):
        emblem_id: int
        ex_value: int

    class clan__info__clan__members__favorite_unit__skin_data(BaseModel):
        icon_skin_id: int
        sd_skin_id: int
        still_skin_id: int
        motion_id: int

    class clan__info__clan__members__favorite_unit(BaseModel):
        id: int
        unit_rarity: int
        battle_rarity: int
        unit_level: int
        promotion_level: int
        exceed_stage: int
        skin_data: 'PcrApi.clan__info__clan__members__favorite_unit__skin_data'
    
    class clan__info__clan__detail(BaseModel):
        clan_id: int
        leader_name: str
        leader_viewer_id: int
        clan_name: str
        description: str
        join_condition: int
        activity: int
        clan_battle_mode: int
        member_num: int
    
    class clan__info__clan__members(BaseModel):
        viewer_id: int
        name: str
        emblem: 'PcrApi.clan__info__clan__members__emblem'
        level: int
        role: int
        favorite_unit: 'PcrApi.clan__info__clan__members__favorite_unit'
        last_login_time: int
        total_power: int

    class clan__info__clan(BaseModel):
        detail: 'PcrApi.clan__info__clan__detail'
        members: List['PcrApi.clan__info__clan__members']

    class clan__info(BaseModel):
        # have_join_request: int
        clan: 'PcrApi.clan__info__clan'
        clan_status: int
        current_period_ranking: int
        last_total_ranking: int
        grade_rank: int
        current_clan_battle_mode: int
        last_clan_battle_mode: int
        current_battle_joined: int
        last_battle_joined: int
        clan_point: int
        remaining_count: int
        unread_liked_count: int

    async def clan__info_async(self) -> clan__info:
        """
        Raises:
            PcrApiException
        """
        return PcrApi.clan__info(**(await self.clan__info_raw_async()))


    async def u_get_clan_id_async(self) -> int:
        """
        Raises:
            PcrApiException
            AssertionError
        """
        res = await self.clan__info_raw_async()
        assert res.get("clan", {}).get("detail", {}).get("clan_id", None) is not None, 'No ["clan"]["detail"]["clan_id"] field in response.'
        return res["clan"]["detail"]["clan_id"]
    
    
    class clan__invite_request(BaseModel):
        invited_viewer_id: int = Field(...)
        invite_message: str = Field(...)

        def __init__(self, invited_viewer_id: int, invite_message: str = "请多关照。"):
            super().__init__(
                invited_viewer_id=invited_viewer_id,
                invite_message=invite_message)


    async def clan__invite_async(self, request: clan__invite_request) -> None:
        """
        邀请某人加入自己的公会
        self 应为会长
        
        Raises:
            PcrApiException
        """
        await self.CallApi("/clan/invite", request.model_dump_json()) # returns None


    async def clan__cancel_invite_async(self, invite_id: int) -> None:
        """
        取消自己曾经发起的 将某人加入自己的公会的邀请
        self 应为会长
        
        Raises:
            PcrApiException
        """
        await self.CallApi("/clan/cancel_invite", {"invite_id": invite_id}) # returns None


    class clan__invite_user_list_response(BaseModel):
        invite_id: int = Field(...)
        viewer_id: int = Field(...)
        create_time: str = Field(...) # "2024-05-03 16:30:08",
        update_time: str = Field(...) # "2024-05-03 16:30:08",
        user_name: str = Field(...)
        emblem: 'PcrApi.clan__info__clan__members__emblem'
        favorite_unit: 'PcrApi.clan__info__clan__members__favorite_unit'
        team_level: int
        user_last_login_time: int # 1714724966
    
    async def clan__invite_user_list_async(self, clan_id: int) -> list[clan__invite_user_list_response]:
        """
        获取自己发起的 邀请他人加入自己公会的邀请
        self 应为会长
        
        Raises:
            PcrApiException
        """
        res = await self.CallApi("/clan/invite_user_list", {"clan_id": clan_id, "page": 0, "oldest_time": 0})
        return [PcrApi.clan__invite_user_list_response(**clan) for clan in res.get("list", [])]

    class clan__invited_clan_list_response(BaseModel):
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
        
    async def clan__invited_clan_list_async(self) -> list[clan__invited_clan_list_response]:
        """
        获取其他会长向你发起的加入公会的邀请
        
        Raises:
            PcrApiException
        """
        home_index = await self.home__index_async()
        if home_index.get("have_clan_invitation", 0) == 0:
            return []
        res = await self.CallApi("/clan/invited_clan_list", {"page": 0})
        return [PcrApi.clan__invited_clan_list_response(**clan) for clan in res.get("list", [])]
        
    async def u_accept_clan_invite_async(self, clan_id: int) -> None:
        """
        同意其他会长发起的加入公会的邀请

        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/clan/others_info", {"clan_id": clan_id}) # 真实API触发顺序
        _ = await self.CallApi("/clan/join", {"clan_id": clan_id, "from_invite": 1})
        await self.u_update_clan_database_async()
        
    async def u_apply_for_clan_async(self, clan_id: int) -> None:
        """
        申请加入一个公会。
        （可能需要审核，也可能不需要。都是这个API和data）
        
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/clan/others_info", {"clan_id": clan_id}) # 真实API触发顺序
        _ = await self.CallApi("/clan/join", {"clan_id": clan_id, "from_invite": 0})

    class clan__join_request_list_response(BaseModel):
        viewer_id: int = Field(...)
        name: str = Field(...)
        emblem: 'PcrApi.clan__info__clan__members__emblem'
        level: int = Field(...)
        comment: str = Field(...)
        favorite_unit: 'PcrApi.clan__info__clan__members__favorite_unit'
        
    async def clan__join_request_list_async(self, clan_id: int) -> List[clan__join_request_list_response]:
        """
        获取申请加入自己公会的人的列表
        self 应为会长
        
        Raises:
            PcrApiException
        """
        res = await self.CallApi("/clan/join_request_list", {"clan_id": clan_id, "page": 0, "oldest_time": 0})
        return [PcrApi.clan__join_request_list_response(**clan) for clan in res.get("list", [])]

    async def clan__join_request_reject_async(self, clan_id: int, applicant_pcrid: int) -> None:
        """
        拒绝他人发起的加入自己公会的申请
        self 应为会长
        
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/clan/join_request_reject", {"request_viewer_id": applicant_pcrid, "clan_id": clan_id}) # returns None


    async def clan__remove_async(self, member_pcrid: int) -> None:
        """
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/clan/remove", {"clan_id": await self.u_get_clan_id_async(), "remove_viewer_id": member_pcrid}) # returns None
        await self.u_update_clan_database_async()
        FarmInfo.update(clanid_cache=0).where(FarmInfo.pcrid == member_pcrid).execute()
        FarmBind.update(permitted_clanid=0).where(FarmBind.pcrid == member_pcrid).execute()
        
    
    class load__index__user_chara_into_item(BaseModel):
        chara_id: int = Field(..., description="角色的4位ID")
        chara_love: int = Field(..., description="当前经验值 升级所需：175, 245, 280, 700, 700, 700, 1400, 2100, 2800, 3500, 4200")
        love_level: int = Field(..., description="当前等级 1-12")
        
    async def load__index__user_chara_info_async(self) -> list[load__index__user_chara_into_item]:
        """
        Raises:
            PcrApiException
        """
        res = await self.load__index_async()
        return [PcrApi.load__index__user_chara_into_item(**x) for x in res.get("user_chara_info", [])]
    
    async def u_get_user_chara_info_dict_async(self) -> dict[int, load__index__user_chara_into_item]:
        """
        Raises:
            PcrApiException
        Return:
            int: 角色4位ID
        """
        return {x.chara_id: x for x in await self.load__index__user_chara_info_async()}
    
    class room__multi_give_gift__item_info(BaseModel):
        item_id: int = Field(...)
        item_num: int = Field(..., description="需要使用的数量")
        current_item_num: int = Field(..., description="当前拥有的数量")

    class room__multi_give_gift_request(BaseModel):
        unit_id: int = Field(..., description="6位角色ID")
        item_info: List['PcrApi.room__multi_give_gift__item_info'] = Field(...)

    async def room__multi_give_gift_async(self, request: room__multi_give_gift_request) -> None:
        await self.CallApi("/room/multi_give_gift", request.model_dump_json())

    class load__index__unit_list_item(BaseModel):
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

    async def load__index__unit_list_async(self) -> list[load__index__unit_list_item]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.load__index_async()).get("unit_list", [])
        return [PcrApi.load__index__unit_list_item(**x) for x in res]


    async def u_get_unit_info_async(self, chara_id: int) -> load__index__unit_list_item:
        """
        Args:
            chara_id: 角色6位ID
        Raises:
            PcrApiException
            ValueError: 该账号未查询到此角色
        """
        character = next((x for x in await self.load__index__unit_list_async() if x.id == chara_id), None)
        if character is None:
            raise ValueError(f"该账号未查询到角色{PcrApi.u_get_chara_friendly_output(chara_id)}")
        return character
    
    async def u_get_all_unit_info_async(self) -> Dict[int, load__index__unit_list_item]:
        """
        Raises:
            PcrApiException
        Return:
            int: 角色6位ID
        """
        return {x.id: x for x in await self.load__index__unit_list_async()}
    
    class load__index__item_list_item(BaseModel):
        type: int = Field(..., description="==2")
        id: int = Field(..., description="5位")
        stock: int
        
    async def load__index__item_list_async(self) -> list[load__index__item_list_item]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.load__index_async()).get("item_list", [])
        return [PcrApi.load__index__item_list_item(**x) for x in res]
        
    async def u_get_item_id2stock_async(self) -> dict[int, int]:
        """
        Raises:
            PcrApiException
        Returns:
            int, int: 5位ID -> 数量
        """
        return {x.id: x.stock for x in await self.load__index__item_list_async()}
    
    async def u_get_item_stock_async(self, item_id: int) -> int:
        """
        Args:
            item_id: 5位ID
        Raises:
            PcrApiException
        """
        return (await self.u_get_item_id2stock_async()).get(item_id, 0)
    
    async def u_get_ticket_stock_async(self) -> int: # 扫荡券
        """
        Raises:
            PcrApiException
        """
        return await self.u_get_item_stock_async(23001)

    class load__index_user_equip_item(BaseModel):
        type: int = Field(..., description="==4")
        id: int = Field(..., description="6位")
        stock: int
        
    async def load__index_user_equip_async(self) -> List[load__index_user_equip_item]:
        """
        Raises:
            PcrApiException
        """
        res = (await self.load__index_async()).get("user_equip", [])
        return [PcrApi.load__index_user_equip_item(**x) for x in res]
        
    async def u_get_user_equip_id2stock_async(self) -> dict[int, int]:
        """
        Raises:
            PcrApiException
        Returns:
            int, int: 6位ID -> 数量
        """
        return {x.id: x.stock for x in await self.load__index_user_equip_async()}
    
    async def u_get_user_equip_stock_async(self, user_equip_id: int) -> int:
        """
        Args:
            user_equip_id: 6位ID
        Raises:
            PcrApiException
        """
        return (await self.u_get_user_equip_id2stock_async()).get(user_equip_id, 0)
    
    
    async def story__check_async(self, story_id: int) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/story/check", {"story_id": story_id})
    
    async def story__start_async(self, d: dict) -> None:
        """
        阅读不同剧情的参数不同

        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/story/start", d) # 其实有返回，告诉你获得多少钻石
    
    async def u_read_chara_story_async(self, story_id: int) -> None:
        """
        Args:
            story_id (int): 7位ID。前四位为角色id，后三位为剧情id
        Raises:
            PcrApiException
        """
        await self.story__check_async(story_id) # 每次读取剧情前都要先调用check
        await self.story__start_async({"story_id": story_id}) # 只有第一次读剧情获取奖赏才需要
    
    class event__hatsune__top__event_status(BaseModel):
        event_type: int = Field(..., description="只应该为1")
        event_id: int = Field(..., description="5位ID。10xxx为当前/复刻活动，20xxx为外传")
        period: int = Field(..., description="1=没开放，2=开放中，3=已结束（不能刷图，可以换票和看剧情）")

    class event__hatsune__top__story(BaseModel):
        story_id: int = Field(..., description="7位ID。1开头=角色剧情，2开头=主线剧情，5开头=活动剧情，7开头=露娜塔剧情。")
        is_unlocked: bool
        is_readed: bool

    class event__hatsune__top__boss_ticket_info(BaseModel):
        id: int
        type: int
        stock: int

    class event__hatsune__top_boss_battle_info_item(BaseModel):
        boss_id: int = Field(..., description="7位ID。前5位为活动ID，后2位为bossID（01=N，02=H，03=VH，04=SP，05=表演赛）")
        is_unlocked: bool
        appear_num: Optional[int] = 0
        attack_num: Optional[int] = 0
        kill_num: Optional[int] = 0
        daily_kill_count: Optional[int] = 0
        oneblow_kill_count: Optional[int] = 0
        remain_time: Optional[int] = 90
        is_force_unlocked: Optional[bool] = False

    class event__hatsune__top(BaseModel):
        event_status: 'PcrApi.event__hatsune__top__event_status'
        opening: 'PcrApi.event__hatsune__top__story'
        ending: 'PcrApi.event__hatsune__top__story'
        stories: list['PcrApi.event__hatsune__top__story']
        boss_ticket_info: 'PcrApi.event__hatsune__top__boss_ticket_info'
        boss_battle_info: list['PcrApi.event__hatsune__top_boss_battle_info_item']
        boss_enemy_info: list[dict]
        # login_bonus: Optional[List[Dict] | Dict] = None
        # missions: List[Dict]
        # is_hard_quest_unlocked: Optional[bool] = False
        # special_battle_info: Optional[Dict] = {}
        # release_minigame: Optional[List[int]] = []
        
    async def event__hatsune__top_async(self, event_id: int) -> event__hatsune__top:
        """
        Args:
            event_id (int): 5位ID。10xxx
        Raises:
            PcrApiException
        """
        return PcrApi.event__hatsune__top(**(await self.CallApi("/event/hatsune/top", {"event_id": event_id})))
    
    async def load__index__event_statuses_async(self) -> list[event__hatsune__top__event_status]:
        """
        Raises:
            PcrApiException
        """
        return [PcrApi.event__hatsune__top__event_status(**x) for x in (await self.load__index_async()).get("event_statuses", [])]

    class load__index__resident_info(BaseModel):
        exchange_num: int
        max_exchange_num: int
        end_time: int
        original_gacha_id: int
        gacha_point_info: dict
        # "gacha_point_info": {
        #     "exchange_id": 999999,
        #     "current_point": 9,
        #     "max_point": 120
        # }
        supply_unit_id_list: list[int]
        server_time: int
        
    async def load__index__resident_info_async(self) -> Optional[load__index__resident_info]:
        """
        Raises:
            PcrApiException
        """
        res = await self.CallApiFull("/load/index", {'carrier': 'OPPO'})
        load_index_raw = res.data

        if "resident_info" not in load_index_raw:
            return None
        
        resident_info = load_index_raw["resident_info"]
        resident_info["server_time"] = res.data_header["servertime"]
        
        return PcrApi.load__index__resident_info(**resident_info)

    class gacha__resident__gacha_info__recommend_unit(BaseModel):
        unit_id: int
        display_order: int

    class gacha__resident__gacha_info(BaseModel):
        null: int
        id: int
        type: int
        start_time: int
        end_time: int
        cost_num_single: int
        ticket_id: int
        free_gacha_interval_time: int
        discount_price: int
        exchange_id: int
        ticket_id_10: int
        original_gacha_id: int
        url_param: str
        free_exec_times: int
        last_free_gacha_time: int
        discount_exec_times: int
        last_discount_gacha_time: int
        recommend_unit: List['PcrApi.gacha__resident__gacha_info__recommend_unit']

    class gacha__resident__free_gacha_info(BaseModel):
        fg1_exec_cnt: int
        fg1_last_exec_time: int
        fg10_exec_cnt: int
        fg10_last_exec_time: int

    class gacha__resident(BaseModel):
        gacha_info: List['PcrApi.gacha__resident__gacha_info']
        free_gacha_info: 'PcrApi.gacha__resident__free_gacha_info'
        exchange_num: int
        max_exchange_num: int

    async def gacha__resident_async(self) -> gacha__resident:
        """
        Raises:
            PcrApiException
        """
        return PcrApi.gacha__resident(**(await self.CallApi("/gacha/resident")))
    
    class gacha__exec_request(BaseModel):
        gacha_id: int = Field(..., description="奖池ID")
        gacha_times: int = Field(..., description="单抽=1，十连抽=10")
        exchange_id: int = Field(..., description="抽取此池所用的物品的ID（奖池信息里会写）")
        draw_type: int = Field(..., description="普通免费碎片扭蛋=1 150钻单抽/1500钻抽十连=2 单抽券/十连券单抽=3 免费十连=6 付费50钻=4 付费1500钻抽星3=<?> 特别凭证扭蛋=9005(不知道是否会变)")
        current_cost_num: int = Field(..., description="抽取此池所用的物品的当前剩余数量（注意：不是使用数量）（每日免费碎片扭蛋=-1 钻石抽=剩余钻石数量 单抽券抽=剩余单抽券数量 免费十连抽=剩余免费十连次数")
        campaign_id: int = Field(..., description='每日免费碎片扭蛋=0 特别凭证扭蛋=0 其他=/gacha/index["campaign_info"]["campaign_id"]')
        last_gacha_index_time: int = Field(..., description="0")
    
    # class ExchangeData(BaseModel):
    #     unit_id: str
    #     rarity: str
    #     count: str

    class gacha__exec__gacha_point_info(BaseModel):
        exchange_id: int
        current_point: int
        max_point: int

    class gacha__exec__user_gold(BaseModel):
        gold_id_free: int
        gold_id_pay: int

    class gacha__exec_response(BaseModel):
        reward_info_list: list[dict] # list['PcrApi.reward']
        gacha_point_info: 'PcrApi.gacha__exec__gacha_point_info'
        user_gold: 'PcrApi.gacha__exec__user_gold'
    
    async def gacha__exec_async(self, request: gacha__exec_request) -> gacha__exec_response:
        """
        Raises:
            PcrApiException
        """
        return PcrApi.gacha__exec_response(**(await self.CallApi("/gacha/exec", request.model_dump_json())))

    class psy__top__cooking_status_item(BaseModel):
        frame_id: int = Field(..., description="坑位，1~24")
        pudding_id: int
        start_time: str

    class psy__top__pudding_note_item(BaseModel):
        pudding_id: int
        count: int
        flavor_status: int = Field(..., description="解锁文案数。0~3")
        read_status: bool

    class psy__top__drama_list_item(BaseModel):
        drama_id: int
        read_status: bool

    class psy__top(BaseModel):
        psy_setting: dict
        cooking_status: list['PcrApi.psy__top__cooking_status_item']
        total_count: int
        pudding_note: list['PcrApi.psy__top__pudding_note_item']
        pudding_type_num: int
        drama_list: list['PcrApi.psy__top__drama_list_item']

    async def psy__top_async(self) -> psy__top:
        """
        吃布丁小游戏信息
        Raises:
            PcrApiException
        """
        return PcrApi.psy__top(**(await self.CallApi("/psy/top", {"from_system_id": 6001})))
    
    async def psy__read_drama_async(self, drama_id: int) -> None:
        """
        Args:
            drama_id (int): 1~11
        Raises:
            PcrApiException
        """
        await self.CallApi("/psy/read_drama", {"drama_id": drama_id, "from_system_id": 6001})
    
    async def psy__start_cooking_async(self, start_cooking_frame_id_list: list[int], get_pudding_frame_id_list: list[int]) -> None:
        """
        Raises:
            PcrApiException
        """
        await self.CallApi("/psy/start_cooking", {"start_cooking_frame_id_list": start_cooking_frame_id_list, "get_pudding_frame_id_list": get_pudding_frame_id_list, "from_system_id": 6001})

    @staticmethod
    def u_get_chara_friendly_output(chara_id: int) -> str:
        chara_id = int(chara_id)
        if 100000 <= chara_id <= 999999:
            chara_id //= 100
        return f'[{chara.fromid(chara_id).name}]({chara_id})'
    
    class travel__top__travel_quest(BaseModel):
        travel_id: int = Field(..., description="第几次新发起的出征", example=10)
        travel_quest_id: int = Field(..., description="探险目标地图", example=11001003)
        travel_start_time: int # 1730900178
        travel_end_time: int # 1731411892 # endtime不会随着decrease_time改变
        total_lap_count: int = Field(..., description="当前出征完成时循环的次数", example=14)
        decrease_time: int # 0 # 3600
        received_count: int = Field(..., description="当前出征已收菜的次数", example=9)
        total_power: int = Field(..., description="队伍总战力", example=543281)
        travel_deck: list[int] = Field(..., description="出征阵容。1-10个元素，每个元素为6位ID。", example=[122901, 107101, 106801, 103201, 100301, 102201, 102101, 101101, 104401, 104001])

    class travel__start__travel_quest(BaseModel):
        travel_quest_id: int
        travel_id: int
        travel_start_time: int
        travel_end_time: float # 1731411892.0 # 我们cy程序员是这样的
        total_lap_count: int
        decrease_time: int # 0 # 3600
        received_count: int
        total_power: int
        # 没有 travel_deck
    
    class travel__top__top_event(BaseModel):
        top_event_appear_id: int = Field(..., description="第几次事件") # 25
        event_group: int # 1
        top_event_id: int # 3001 # 4005 # 4011
        top_event_pos_id: int # 8 # 4 # 5
        top_event_rarity: int # 1
        top_event_choice_flag: int # 0/1 # 当0时，choice_number应为0；当1时，choice_number应为1/2
        # top_event_choice_flag为1的事件如下：
        # top_event_id=4007：choice_number=1：60% 获得 3 金装，40% 获得 1 金装；choice_number=2：总是获得 2 金装。
        # top_event_id=4009：choice_number=1：30% 获得 1000 特别武器币，70% 获得 200 币；choice_number=2：总是获得 400 币。
        top_event_skin_id_list: list[int] # [103011, 103711] # [118111] # [105211]
    
    class travel__top__round_event_data(BaseModel):
        round_event_id: int = Field(..., description="金字塔事件ID") # 截至 20250703 总是 1
        skin_id_list: list[int] = Field(default_factory=list) # [105411, 106811, 107111, 107011]
        round: int = Field(..., description="当前在第几层", examples=[1, 2, 3])
        left_door_effect_id: int = Field(..., examples=[900000])
        right_door_effect_id: int = Field(..., examples=[900000])
        expect_reward_list: list[dict] = Field(default_factory=list) 
        
    class travel__top(BaseModel):
        travel_quest_list: list['PcrApi.travel__top__travel_quest'] = []
        appear_secret_quest_list: list = [] # 目前为 []
        top_event_list: list['PcrApi.travel__top__top_event'] = []
        remain_daily_retire_count: int = Field(..., description="当日剩余可撤退次数", example=10)
        priority_unit_list: list[int] = Field(default_factory=list, description="碎片优先角色。0-15个元素，每个元素为6位ID。")
        remain_daily_decrease_count_ticket: int = Field(..., description="当日剩余可使用券缩短时间次数", example=36)
        remain_daily_decrease_count_jewel: int = Field(..., description="当日剩余可使用宝石缩短时间次数", example=36)
        ex_equip_id_list: list[int] = Field(default_factory=list, description="仅当get_ex_equip_album_flag=1时响应中包含此字段", example=[4101101, 4101102, ..., 4305302])
        ex_event_still_id_list: list[int] = Field(default_factory=list, description="至今为止发现的回忆事件列表") # [8000001, ...]
        # campaign_list: list = Field(default_factory=list)
        round_event_data: Optional['PcrApi.travel__top__round_event_data'] = Field(None, description="金字塔事件。如果没有的话则为 None")

    async def travel__top_async(self, travel_area_id: int, get_ex_equip_album_flag: int = 1) -> travel__top:
        """
        Args:
            travel_area_id (int): 11001(朱庇特树海) 11002(玛丘利湾口) 11003(斯卡蒂亚山脉)
            get_ex_equip_album_flag (int): 0/1 客户端第一次进入传1 后续传0
        Raises:
            PcrApiException
        """
        return PcrApi.travel__top(**(await self.CallApi("/travel/top", {"travel_area_id": travel_area_id, "get_ex_equip_album_flag": get_ex_equip_album_flag})))

    class travel__receive_top_event_reward__reward__ex_equip(BaseModel):
        serial_id: int # 390
        ex_equipment_id: int # 4110301
        enhancement_pt: int # 0
        rank: int # 0
        protection_flag: int # 1

    class travel__receive_top_event_reward__reward(BaseModel):
        id: int
        type: int
        count: int
        stock: int
        received: int
        ex_equip: Optional['PcrApi.travel__receive_top_event_reward__reward__ex_equip'] = None # 有此字段的 id 示例：4110301
        # exchange_data: Optional['PcrApi.ExchangeData'] = None # 抽奖抽到旧角色，自动变为母猪石时有此字段

    class travel__receive_top_event_reward__user_jewel(BaseModel):
        free_jewel: int # 351192
        jewel: int # 2648
    
    class travel__receive_top_event_reward__user_gold(BaseModel):
        gold_id_free: int # 984007926
        gold_id_pay: int # 47258

    class travel__receive_top_event_reward(BaseModel):
        reward_list: list['PcrApi.travel__receive_top_event_reward__reward']
        drama_id: int # 0
        user_jewel: 'PcrApi.travel__receive_top_event_reward__user_jewel'
        user_gold: 'PcrApi.travel__receive_top_event_reward__user_gold'
        
    async def travel__receive_top_event_reward_async(self, top_event_appear_id: int, choice_number: int) -> travel__receive_top_event_reward:
        """
        Args:
            top_event_appear_id (int): 25
            choice_number (int): 当 top_event_choice_flag 为 0 时，choice_number 应为 0；当为 1 时，choice_number 应为1/2。
                4007 事件：choice_number=1：60% 获得 3 金装，40% 获得 1 金装；choice_number=2：总是获得 2 金装。
                4009 事件：choice_number=1：30% 获得 1000 特别武器币，70% 获得 200 币；choice_number=2：总是获得 400 币。
                其余事件：choice_number=0。
        Raises:
            PcrApiException
        """
        return PcrApi.travel__receive_top_event_reward(**(await self.CallApi("/travel/receive_top_event_reward", {"top_event_appear_id": top_event_appear_id, "choice_number": choice_number})))

    class travel__result_round_event__current_round_result(BaseModel):
        result: int = Field(..., description="1=成功 2=失败")
        result_drama_id: int = Field(..., examples=[3000, 3100])
        reward_list: Optional[list['PcrApi.travel__receive_top_event_reward__reward']] = None
        
    class travel__result_round_event__next_round_event_data(BaseModel):
        round: int = Field(..., description="当前在第几层", examples=[1, 2, 3])
        left_door_effect_id: int = Field(..., examples=[900000])
        right_door_effect_id: int = Field(..., examples=[900000])
        expect_reward_list: list[dict] = Field(default_factory=list)
        
    class travel__result_round_event(BaseModel):
        current_round_result: 'PcrApi.travel__result_round_event__current_round_result'
        next_round_event_data: Optional['PcrApi.travel__result_round_event__next_round_event_data'] = None
        
    async def travel__result_round_event_async(self, round: int, select_door_id: int) -> travel__result_round_event:
        """
        金字塔事件
        Args:
            round (int): 当前在第几层
            select_door_id (int): 选左门=1，选右门=2
        Raises:
            PcrApiException
        """
        return PcrApi.travel__result_round_event(**(await self.CallApi("/travel/result_round_event", {"round": round, "select_door_id": select_door_id})))

    # 后续测试
    class ex_auto_recycle_option(BaseModel):
        rarity: list # []
        frame: list # []
        category: list # []

    # 探险回忆事件
    class travel__receive_all__travel_result_item__appear_event(BaseModel):
        still_id: int = Field(..., description="回忆事件ID") # 8000002
        reward_list: List['PcrApi.travel__receive_top_event_reward__reward']
    
    # 临时命名
    class travel__receive_all__travel_result_item(BaseModel):
        travel_quest_id: int # 见 travel_quest.travel_quest_id
        travel_id: int # 见 travel_quest.travel_id
        lap_count: int # 1
        acquired_gold: int # 30000
        appear_event_list: list['PcrApi.travel__receive_all__travel_result_item__appear_event'] # 无内容时返回 []，有内容时返回 { "null": 1, "0": { ... }, "1": { ... } } 
        reward_list: list['PcrApi.travel__receive_top_event_reward__reward']
        
        @validator('appear_event_list', pre=True, always=True)
        def convert_appear_event_list(cls, v):
            if isinstance(v, dict):
                v.pop('null', None)
                # 只提取 "0", "1", ... 等键的值，并返回为列表
                return list(v.values())
            return v
        
    class travel__receive_all(BaseModel):
        travel_result: List['PcrApi.travel__receive_all__travel_result_item']
        # travel_quest_list: list # []
        user_gold: 'PcrApi.travel__receive_top_event_reward__user_gold'
        # campaign_list: list # []
        
    async def travel__receive_all_async(self, ex_auto_recycle_option: ex_auto_recycle_option) -> travel__receive_all:
        """
        没有可以确认归来的队伍时，调用此接口会抛出异常：data_headers.result_code=205, data={'server_error': {'status': 3, 'title': '错误提示', 'message': '发生了错误。\\n回到标题界面。'}}
        
        Args:
            ex_auto_recycle_option (ex_auto_recycle_option): 自动分解设定。全部字段留空表示不分解
        Raises:
            PcrApiException
        """
        return PcrApi.travel__receive_all(**(await self.CallApi("/travel/receive_all", {"ex_auto_recycle_option": json.loads(ex_auto_recycle_option.model_dump_json())})))

    # 探险缩短时间次数
    class travel__start__start_travel_quest__decrease_time_item(BaseModel):
        jewel: int = Field(..., description="使用宝石缩短时间次数") # 0~36
        item: int = Field(..., description="使用券缩短时间次数") # 0~36

    class travel__start__start_travel_quest(BaseModel):
        travel_quest_id: int # 见 travel_quest.travel_quest_id
        travel_deck: List[int] # 见 travel_quest.travel_deck
        decrease_time_item: 'PcrApi.travel__start__start_travel_quest__decrease_time_item'
        total_lap_count: int = Field(..., description="出征循环次数") # 1~5

    class travel__start__add_lap_travel_quest(BaseModel):
        travel_id: int # 见 travel_quest.travel_id
        add_lap_count: int = Field(..., description="追加循环次数") # 1~4

    # 在 10.7.1(20250930) 版本中由 dict 改为了 int
    # class action_type(BaseModel):
    #     value__: int = Field(..., description="从地图中选中单个目的地出发=1 从一键确认归来面板中归来后重新出发=2 从一键出发面板中配新队出发=3（即使只出发一队） 从一键确认归来面板中追加=8 从一键确认归来面板中既有重新出发又有追加=9")

    class travel__start__current_currency_num(BaseModel):
        jewel: int = Field(..., description="用户拥有的免费+付费宝石总量") # 351192
        item: int = Field(..., description="用户拥有的券总量") # 137

    class travel__start__campaign(BaseModel):
        travel_id: int # 见 travel_quest.travel_id
        start_lap: int = Field(..., description="当前正在第几轮循环") # >=1
        end_lap: int = Field(..., description="总共循环几轮后结束") # >=start_lap
        # campaign_id_list: list # [] # TODO: figure it out

    class travel__start(BaseModel):
        travel_quest_list: List['PcrApi.travel__start__travel_quest']
        # item_list: Optional[List['PcrApi.item']] = None # [{"id": 23002, "type": 2, "count": 0, "stock": 161}]
        remain_daily_decrease_count_ticket: Optional[int] = None # 见 travel__top.remain_daily_decrease_count_ticket。如果未使用券则无此字段
        remain_daily_decrease_count_jewel: Optional[int] = None # 见 travel__top.remain_daily_decrease_count_jewel。如果未使用宝石则无此字段
        campaign_list: List['PcrApi.travel__start__campaign']

    async def travel__start_async(
        self, 
        start_travel_quest_list: list[travel__start__start_travel_quest],
        add_lap_travel_quest_list: list[travel__start__add_lap_travel_quest],
        start_secret_travel_quest_list: list, # [] # TODO: figure it out
        action_type: int, # 从地图中选中单个目的地出发=1 从一键确认归来面板中归来后重新出发=2 从一键出发面板中配新队出发=3（即使只出发一队） 从一键确认归来面板中追加=8 从一键确认归来面板中既有重新出发又有追加=9
        current_currency_num: travel__start__current_currency_num
    ) -> travel__start:
        """
        Raises:
            PcrApiException
        """
        request_data = {
            "start_travel_quest_list": [quest.model_dump() for quest in start_travel_quest_list],
            "add_lap_travel_quest_list": [quest.model_dump() for quest in add_lap_travel_quest_list],
            "start_secret_travel_quest_list": start_secret_travel_quest_list,
            "action_type": action_type,
            "current_currency_num": current_currency_num.model_dump()
        }
        response = await self.CallApi("/travel/start", request_data)
        return PcrApi.travel__start(**response)

    class home__index__quest(BaseModel):
        quest_id: int # N1-1: 11001001
        clear_flg: int = Field(..., description="几星通关（[0,3]），其中0星为未通关")
        result_type: int # home_index 中的均为 2
        daily_clear_count: int = Field(..., description="当日通关次数")
        daily_recovery_count: int = Field(..., description="当日回复次数")
    
    async def home__index__quest_list_async(self) -> list[home__index__quest]:
        """
        Raises:
            PcrApiException
        """
        home_index = await self.home__index_async()
        return [PcrApi.home__index__quest(**quest) for quest in home_index.get("quest_list", [])]
    
    async def u_get_quest_dict_async(self) -> dict[int, home__index__quest]:
        """
        Raises:
            PcrApiException
        Returns:
            int: quest_id
        """
        return {quest.quest_id: quest for quest in await self.home__index__quest_list_async()}
    
    async def u_get_quest_async(self, quest_id: int) -> Optional[home__index__quest]:
        """
        Raises:
            PcrApiException
        """
        quest_list = await self.home__index__quest_list_async()
        return next((x for x in quest_list if x.quest_id == quest_id), None)
    
    async def u_is_quest_cleared_async(self, quest_id: int) -> bool:
        """
        Raises:
            PcrApiException
        """
        quest = await self.u_get_quest_async(quest_id)
        return quest is not None and quest.clear_flg > 0
    
    async def u_get_free_jewel_async(self) -> int:
        """
        Raises:
            PcrApiException
        """
        return (await self.load__index_async()).get("user_jewel", {}).get("free_jewel", 0)
    
    async def u_get_paid_jewel_async(self) -> int:
        """
        Raises:
            PcrApiException
        """
        return (await self.load__index_async()).get("user_jewel", {}).get("paid_jewel", 0)
    
    async def u_get_total_jewel_async(self) -> int:
        """
        Raises:
            PcrApiException
        """
        load_index = await self.load__index_async()
        user_jewel = load_index.get("user_jewel", {})
        return user_jewel.get("free_jewel", 0) + user_jewel.get("paid_jewel", 0)
    
    async def talent_quest__recover_challenge_async(self, talent_id: int, current_currency_num: Optional[int]) -> None:
        """
        Args:
            talent_id (int): 1=火 2=水 3=风 4=光 5=暗
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/talent_quest/recover_challenge", {"talent_id": talent_id, "current_currency_num": current_currency_num or await self.u_get_total_jewel_async()})

    async def talent_quest__quest_skip_async(self, quest_id: int, use_ticket_num: int, current_ticket_num: int) -> None:
        """
        Args:
            quest_id (int): 8位ID。e.g. 85001009 = 暗1-9
            use_ticket_num (int): 使用的扫荡券数量（扫荡次数）。
            current_ticket_num (int): 当前用户拥有的扫荡券数量。
        Raises:
            PcrApiException
        """
        _ = await self.CallApi("/talent_quest/quest_skip", {"quest_id": quest_id, "use_ticket_num": use_ticket_num, "current_ticket_num": current_ticket_num})

    async def load__index__read_story_ids_async(self) -> List[int]:
        """
        Raises:
            PcrApiException
        Returns:
            List[int]: 已读剧情ID列表
        """
        return (await self.load__index_async()).get("read_story_ids", [])
    
    class seven__top__mission(BaseModel):
        mission_id: int = Field(..., examples=[20101])
        mission_status: int = Field(..., examples=[2])
        clear_num: int = Field(..., examples=[1])

    class seven__top__boss_info(BaseModel):
        quest_id: int = Field(..., examples=[10201101])
        appear_num: int = Field(..., examples=[3])
        attack_num: int = Field(..., examples=[0])
        enemy_unit: Optional[list[dict]] = None
        mode: Optional[int] = None
        enemy_point: Optional[int] = None
    
    class seven__top__clear_quest(BaseModel):
        quest_id: int = Field(..., examples=[10201001])
        clear_flg: int =Field(..., description="几星通关（[0,3]），其中0星为未通关", examples=[3])
        daily_clear_count: int = Field(..., examples=[0])
    
    class seven__top(BaseModel):
        login_bonus: Optional[dict] = None
        missions: list['PcrApi.seven__top__mission']
        unlocked_sub_contents: Optional[list[int]] = None
        boss_info: list['PcrApi.seven__top__boss_info']
        clear_quest_list: list['PcrApi.seven__top__clear_quest']

    async def seven__top_async(self, schedule_id: int) -> seven__top:
        """
        七冠活动首页
        Args:
            schedule_id (int): see SevenEvent.schedule_id in db_io.py
        Raises:
            PcrApiException
        """
        return PcrApi.seven__top(**(await self.CallApi("/seven/top", {"schedule_id": schedule_id})))
    
    class seven__quest_skip_multiple__skip_list__item(BaseModel):
        quest_id: int = Field(..., examples=[10201101])
        skip_count: int = Field(..., examples=[3])
    
    async def seven__quest_skip_multiple_async(
        self,
        schedule_id: int, # see SevenEvent.schedule_id in db_io.py
        skip_list: list['PcrApi.seven__quest_skip_multiple__skip_list__item'],
        exec_type: int, # 1=单个关卡面板扫荡 2=扫荡面板扫荡
        current_ticket_num: int) -> None:
        """
        七冠活动扫荡
        Raises:
            PcrApiException
        """
        request_data = {
            "schedule_id": schedule_id,
            "skip_list": [item.model_dump() for item in skip_list],
            "exec_type": exec_type,
            "current_ticket_num": current_ticket_num
        }
        _ = await self.CallApi("/seven/quest_skip_multiple", request_data)