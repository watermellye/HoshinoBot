from ..data import item_data
from typing import List, Union


def get_item_name(item_id: Union[int, str]) -> str:
    if int(item_id) in item_data.id2name:
        return item_data.id2name[int(item_id)]

    item_id_str = str(item_id)
    if len(item_id_str) == 6:
        item_id_str = item_id_str[:1] + '0' + item_id_str[2:]
    return item_data.id2name.get(int(item_id_str), str(item_id))


def get_item_2_map_list(item_id: Union[int, str]) -> List[int]:
    return item_data.id2maplist.get(int(item_id), [])


def get_map_2_item_list(map_id: Union[int, str]) -> List[int]:
    return item_data.map2idlist.get(int(map_id), [])
