from enum import IntEnum, unique
from typing import Union
import re


class PCRMap:
    def __init__(self):
        self.subtype = None
        self.major = 0
        self.minor = 0
        self.event_id = 0

    @property
    def name(self) -> str:  # 请重写该函数
        raise Exception("Base Class")

    @property
    def id(self) -> int:  # 请重写该函数
        raise Exception("Base Class")

    @property
    def stamina(self) -> int:
        '''
        扫荡一次该地图所需的体力
        '''
        return 0

    # @property
    # def max_clear_count(self) -> int:
    #     return 0

    # @property
    # def max_recovery_count(self) -> int:
    #     return 0

    def is_rerun(self) -> bool:
        '''
        该地图是复刻活动图
        '''
        return False


class MainPCRMap(PCRMap):  # 主线
    @unique
    class MainPCRMapSubType(IntEnum):
        N = 11000000
        H = 12000000
        VH = 13000000

    def __init__(self, subtype: Union[str, MainPCRMapSubType], major: int, minor: int):
        '''
        :param subtype: enum("N", "H", "VH")
        '''
        super().__init__()
        if type(subtype) == str:
            assert subtype in self.MainPCRMapSubType.__members__, f'无法识别的地图子类：{subtype}'
            subtype = self.MainPCRMapSubType[subtype]
        self.subtype = subtype
        self.major = major
        self.minor = minor

    @property
    def name(self) -> str:
        return f'{self.subtype.name}{self.major}-{self.minor}'

    @property
    def id(self) -> int:  # "N33-6" -> 11033006
        return self.subtype.value + self.major * 1000 + self.minor

    @property
    def stamina(self) -> int:
        '''
        扫荡一次该地图所需的体力
        '''
        if self.subtype == self.MainPCRMapSubType.N:
            if self.id == 11001001:
                return 6
            if self.major <= 3:
                return 8
            if self.major <= 6:
                return 9
            return 10
        if self.subtype == self.MainPCRMapSubType.H:
            if self.major <= 3:
                return 16
            if self.major <= 6:
                return 18
            return 20
        if self.subtype == self.MainPCRMapSubType.VH:
            return 20
        return 0


class EventPCRMap(PCRMap):  # 活动
    @unique
    class EventPCRMapSubType(IntEnum):
        N = 100
        H = 200

    def __init__(self, subtype: Union[str, EventPCRMapSubType], minor: int, event_id: int):
        '''
        :param subtype: enum("N", "H")
        '''
        super().__init__()
        if type(subtype) == str:
            assert subtype in self.EventPCRMapSubType.__members__, f'无法识别的地图子类：{subtype}'
            subtype = self.EventPCRMapSubType[subtype]
        self.subtype = subtype
        self.major = 1
        self.minor = minor
        self.event_id = event_id

    @property
    def name(self) -> str:
        return f'{"复刻"if self.is_rerun() else ""}活动{self.event_id}|{self.subtype.name}{self.major}-{self.minor}'

    @property
    def id(self) -> int:  # "活动H1-3" -> xxxxx203
        return self.event_id * 1000 + self.subtype.value + self.minor

    @property
    def stamina(self) -> int:
        '''
        扫荡一次该地图所需的体力
        '''
        if self.subtype == self.EventPCRMapSubType.N:
            if self.minor <= 5:
                return 8
            if self.minor <= 10:
                return 9
            return 10
        if self.subtype == self.EventPCRMapSubType.H:
            if self.minor <= 2:
                return 16
            if self.minor <= 4:
                return 18
            return 20
        return 0

    def is_rerun(self) -> bool:
        return 20000 < self.event_id < 29999


class ExplorePCRMap(PCRMap):  # 调查
    @unique
    class ExplorePCRMapSubType(IntEnum):
        心碎 = 18001000
        星球杯 = 19001000
        MANA = 21001000
        EXP = 21002000

    def __init__(self, subtype: Union[str, ExplorePCRMapSubType], minor: int):
        '''
        :param subtype: enum("心碎", "星球杯", "MANA", "EXP")
        '''
        super().__init__()
        if type(subtype) == str:
            assert subtype in self.ExplorePCRMapSubType.__members__, f'无法识别的地图子类：{subtype}'
            subtype = self.ExplorePCRMapSubType[subtype]
        self.subtype = subtype
        self.minor = minor

    @property
    def name(self) -> str:
        return f'{self.subtype.name}{self.minor}'

    @property
    def id(self) -> int:  # "星球杯2" -> 19001002
        return self.subtype.value + self.minor

    @property
    def stamina(self) -> int:
        '''
        扫荡一次该地图所需的体力
        '''
        if self.subtype in [self.ExplorePCRMapSubType.心碎, self.ExplorePCRMapSubType.星球杯]:
            return 15


def from_id(map_id: Union[int, str]) -> PCRMap:
    '''
    :returns: 由于python没有虚函数，因此实际返回的是PCRMap的某个子类。写成返回PCRMap基类，是为了为了语法提示能工作。
    :raise Exception: map_id无法匹配任何已知的地图
    '''

    map_id = str(map_id)
    res = re.findall(r"11(\d{3})(\d{3})", map_id)
    if res:
        return MainPCRMap("N", int(res[0][0]), int(res[0][1]))
    res = re.findall(r"12(\d{3})(\d{3})", map_id)
    if res:
        return MainPCRMap("H", int(res[0][0]), int(res[0][1]))
    res = re.findall(r"13(\d{3})(\d{3})", map_id)
    if res:
        return MainPCRMap("VH", int(res[0][0]), int(res[0][1]))

    res = re.findall(r"18001(\d{3})", map_id)
    if res:
        return ExplorePCRMap("心碎", int(res[0]))
    res = re.findall(r"19001(\d{3})", map_id)
    if res:
        return ExplorePCRMap("星球杯", int(res[0]))
    res = re.findall(r"21001(\d{3})", map_id)
    if res:
        return ExplorePCRMap("MANA", int(res[0]))
    res = re.findall(r"21002(\d{3})", map_id)
    if res:
        return ExplorePCRMap("EXP", int(res[0]))

    res = re.findall(r"([1|2]0\d{3})1(\d{2})", map_id)
    if res:
        return EventPCRMap("N", int(res[0][1]), int(res[0][0]))
    res = re.findall(r"([1|2]0\d{3})2(\d{2})", map_id)
    if res:
        return EventPCRMap("H", int(res[0][1]), int(res[0][0]))
    raise Exception(f'无法识别地图{map_id}')


if __name__ == "__main__":
    pass
