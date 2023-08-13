from ..data import star6_data
from typing import Union
from copy import deepcopy


def get_map_2_item_id(map_id: Union[int, str]) -> int:
    '''
    :returns: 13018001 -> 32058
    :raise Exception: 未查询到map_id的六星碎片信息
    '''
    map_id = int(map_id)
    if map_id not in star6_data.map2id:
        raise Exception(f'地图{map_id}未查询到六星碎片信息')
    return star6_data.map2id[map_id]


def get_map_2_item_dict() -> dict:
    '''
    :returns: {13018001: 32058, ..., 13034003: 32047}
    '''
    return deepcopy(star6_data.map2id)
