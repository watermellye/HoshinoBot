
from pathlib import Path
import asyncio
import logging
import json

from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement
import zhconv

from utils_web import fetch_html_and_save_async, fetch_htmls_and_save_async

gs_current_dir = Path(__file__).parent
gs_data_dir = gs_current_dir / "data"
if not gs_data_dir.exists():
    gs_data_dir.mkdir()
gs_output_dir = gs_data_dir / "output"
if not gs_output_dir.exists():
    gs_output_dir.mkdir()

gk_web_root = r"https://pcredivewiki.tw"

async def _get_area_id2url_async(download_if_exists: bool) -> dict[str, dict[int, str]]:
    """
    Returns:
        Dict[difficulty: str, Dict[area_id: int, map_url: str]]
    """
    logging.debug(f"get_map_name2url [download_if_exists={download_if_exists}] started")
    map_url = gk_web_root + r"/Map"
    filepath = gs_data_dir / "map.html"
    map_html = await fetch_html_and_save_async(map_url, filepath, download_if_exists)
    map_bs = BeautifulSoup(map_html, 'html.parser')

    def get_id2url(key: str, id_base: int) -> dict[int, str]:
        def map_tag_filter(tag: Tag) -> bool:
            return tag.name == "h3" and "item-title" in tag.get("class", []) and key in tag.text

        map_tag = map_bs.find(map_tag_filter)
        if not map_tag:
            logging.error(f"h3 [{key}] not found in map page")
            return {}

        def map_url_tag_filter(tag: Tag) -> bool:
            if tag.name != "a":
                return False
            if not tag.get("href", "").startswith(r"/Map/Detail/"):
                return False
            if "btn-map" not in tag.get("class", []):
                return False
            return True

        map_url_tags = map_tag.find_parent().find_all(map_url_tag_filter)
        if not map_url_tags:
            logging.error(f"No map_url found in [{key}]")
            return {}
        
        id2url: dict[int, str] = {}
        for i, tag in enumerate(map_url_tags):
            area_id_str: str = tag.text.strip().split('.')[0]
            assert area_id_str.isdigit(), f"Map [{tag.text}] not starts with a digit"
            id2url[id_base + int(area_id_str)] = gk_web_root + tag["href"]
        
        return id2url

    
    n = get_id2url("普通模式", 11000)
    h = get_id2url("困難模式", 12000)
    vh = get_id2url("VH模式", 13000)

    return {"n": n, "h": h, "vh": vh}

async def get_normal_area_id2url_async() -> dict[int, str]:
    return (await _get_area_id2url_async(download_if_exists=False))["n"]

async def get_hard_area_id2url_async() -> dict[int, str]:
    return (await _get_area_id2url_async(download_if_exists=False))["h"]

async def get_vh_area_id2url_async() -> dict[int, str]:
    return (await _get_area_id2url_async(download_if_exists=False))["vh"]

class EquipInfo:
    def __init__(self, name: str, icon_url: str, full_id: int, fragment_id: int):
        self.name = name
        self.icon_url = icon_url
        self.full_id = full_id
        self.fragment_id = fragment_id

    def __repr__(self):
        return f"{self.name}({self.full_id})"

async def get_equip_info_async(download_if_exists: bool) -> list[EquipInfo]:
    logging.debug(f"get_equip_info_async [download_if_exists={download_if_exists}] started")
    map_url = gk_web_root + r"/Equipment"
    filepath = gs_data_dir / "equipment.html"
    map_html = await fetch_html_and_save_async(map_url, filepath, download_if_exists)
    map_bs = BeautifulSoup(map_html, 'html.parser')

    def equip_tag_filter(tag: Tag) -> bool:
        return tag.name == "h3" and "item-title" in tag.get("class", []) and "裝備一覽" in tag.text

    equip_tag = map_bs.find(equip_tag_filter)
    if not equip_tag:
        logging.error(f"h3 [裝備一覽] not found in equipment page")
        return []

    def equip_tag_filter(tag: Tag) -> bool:
        return tag.name == "img" and "img-fluid" in tag.get("class", []) and tag.get("data-src", "").startswith(r"/static/images/equipment/icon_equipment_") and tag.get("data-src", "").endswith(r".png")

    equip_tags = equip_tag.find_parent().find_all(equip_tag_filter)
    if not equip_tags:
        logging.error(f"equip_tags not found in map page")
        return []
    
    equips: list[EquipInfo] = []
    for equip_tag in equip_tags:
        assert equip_tag.get("title", -1) == equip_tag.get("alt", -2), f"equip_tag title [{equip_tag.get('title', '<unknown>')}] != alt [{equip_tag.get('alt', r'<unknown>')}]"
        name = equip_tag["title"].strip()
        icon_url = equip_tag["data-src"]
        full_id_str = icon_url.split(r"/static/images/equipment/icon_equipment_")[-1].split(r".png")[0]
        assert full_id_str.isdigit(), f"Equip icon [{icon_url}] does not have a valid ID"
        equips.append(EquipInfo(zhconv.convert(name, "zh-hans"), gk_web_root + icon_url, int(full_id_str), 0))

    return equips

def output_equip_name(equips: list[EquipInfo]) -> None:
    equip_id2name = {e.full_id: e.name for e in equips}
    
    filepath = gs_output_dir / "equip_name.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(equip_id2name, f, ensure_ascii=False, indent=4)


class MapDropItem:
    def __init__(self, fragment_id: int, drop_rate: float):
        self.fragment_id = fragment_id
        self.drop_rate = drop_rate


class MapDrop:
    def __init__(self, map_id: int, drop_items: list[MapDropItem]):
        self.map_id = map_id
        self.drop_items: list[MapDropItem] = drop_items

    def __repr__(self):
        output = f"MapDrop {self.map_id}: "
        drop_items_parsed = [f"{item.fragment_id}({int(item.drop_rate * 100)}%)" for item in self.drop_items[:3]]
        if len(self.drop_items) > 3:
            return output + ", ".join(drop_items_parsed[:3]) + ", ..."
        else:
            return output + ", ".join(drop_items_parsed)

def get_map_drop(map_id: int, map_tag: PageElement) -> MapDrop:
    def drop_item_filter(tag: Tag) -> bool:
        return tag.name == "div" and "p-1" in tag.get("class", []) and "order-1" in tag.get("class", [])

    drop_items = map_tag.find_parent().find_all(drop_item_filter)
    if not drop_items:
        logging.error(f"drop_items not found in map [{map_id}]")
    # logging.debug(f'map [{map_id}] found [{len(drop_items)}] drop items')

    def get_map_drop_item(drop_item: PageElement) -> MapDropItem:
        def img_filter(tag: Tag) -> bool:
            return tag.name == "img" and tag.get("data-src", "").startswith(r"/static/images/equipment/icon_equipment_") and tag.get("data-src", "").endswith(r".png")

        img_tag = drop_item.find(img_filter)
        assert img_tag, f"img_tag not found in drop_item [{drop_item}] of map_id [{map_id}]"
        icon_url: str = img_tag["data-src"]
        full_id_str = icon_url.split(r"/static/images/equipment/icon_equipment_")[-1].split(r".png")[0]
        assert full_id_str.isdigit(), f"img_tag of drop_item [{drop_item}] of map_id [{map_id}] got invalid id [{full_id_str}]"
        full_id = int(full_id_str)
        
        def drop_rate_filter(tag: Tag) -> bool:
            return tag.name == "h6" and "%" in tag.text

        drop_rate_tag = drop_item.find(drop_rate_filter)
        assert drop_rate_tag, f'drop_rate_tag not found in drop_item [{drop_item}] of map_id [{map_id}]'
        drop_rate_str: str = drop_rate_tag.text.split('%')[0]
        assert drop_rate_str.isdigit(), f"drop_rate_tag of drop_item [{drop_item}] of map_id [{map_id}] got invalid rate [{drop_rate_str}]"
        drop_rate = float(drop_rate_str) / 100
        
        return MapDropItem(full_id, drop_rate)

    return MapDrop(map_id, [get_map_drop_item(item) for item in drop_items])

def get_area_drop(area_id: int, html_content: str) -> list[MapDrop]:
    map_bs = BeautifulSoup(html_content, 'html.parser')

    def quest_tag_filter(tag: Tag) -> bool:
        return tag.name == "th" and "任務" in tag.text

    quest_tag = map_bs.find(quest_tag_filter)
    if not quest_tag:
        logging.error(f"th [任務] not found in map [{area_id}]")
        return []

    def map_filter(tag: Tag) -> bool:
        return tag.name == "h3" and "item-title" in tag.get("class", [])

    map_tags = quest_tag.find_parent().find_parent().find_all(map_filter)
    if not map_tags:
        logging.error(f"map_tags not found in map [{area_id}]")
        return []
    # logging.debug(f'area [{area_id}] found [{len(map_tags)}] maps')

    map_drops: list[MapDrop] = []
    area_friendly_id: int = area_id % 1000
    for i, map_tag in enumerate(map_tags):
        map_id_raw_expected = f'{area_friendly_id}-{i+1}' 
        map_id_raw_found: str = map_tag.text
        assert map_id_raw_found == map_id_raw_expected, f"Found map id [{map_id_raw_found}], expected [{map_id_raw_expected}]"
        map_id: int = area_id * 1000 + (i + 1)
        map_drops.append(get_map_drop(map_id, map_tag))

    return map_drops

async def get_normal_map_id2drop_async() -> dict[int, MapDrop]:
    normal_area_id2url = await get_normal_area_id2url_async()

    url2area_id = {url: id for id, url in normal_area_id2url.items()}
    url2filepath = {url: gs_data_dir / "map_pages" / f'{id}.html' for url, id in url2area_id.items()}
    url2html_content = await fetch_htmls_and_save_async(url2filepath, download_if_exists=False)

    map_id2drop = {}
    for url, area_id in url2area_id.items():
        html_content = url2html_content[url]
        map_drops = get_area_drop(area_id, html_content)
        for map_drop in map_drops:
            map_id2drop[map_drop.map_id] = map_drop

    return map_id2drop

def output_map2equip(map_id2drop: dict[int, MapDrop]) -> None:
    map_id2fragment_ids = {map_id: [drop_item.fragment_id for drop_item in map_drop.drop_items[:3]] for map_id, map_drop in map_id2drop.items()}
    map_id2fragment_ids_sorted = sorted(map_id2fragment_ids.items(), key=lambda x: x[0], reverse=True)
    map_str2fragment_ids_sorted = {f"{map_id // 1000 % 1000}-{map_id % 1000}": [f'{fragment_id}' for fragment_id in fragment_ids] for map_id, fragment_ids in map_id2fragment_ids_sorted}

    filepath = gs_output_dir / "map2equip.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(map_str2fragment_ids_sorted, f, ensure_ascii=False, indent=4)


def get_map_chara(map_id: int, map_tag: PageElement) -> int:
    def chara_fragment_img_filter(tag: Tag) -> bool:
        return tag.name == "img" and tag.get("data-src", "").startswith(r"/static/images/item/icon_item_32") and tag.get("data-src", "").endswith(r".png")

    chara_fragment_img_tag = map_tag.find_parent().find(chara_fragment_img_filter)
    if not chara_fragment_img_tag:
        logging.error(f"chara_fragment_img_tag not found in map [{map_id}]")

    icon_url: str = chara_fragment_img_tag["data-src"]
    chara_fragment_id_str = icon_url.split(r"/static/images/item/icon_item_")[-1].split(r".png")[0]
    assert chara_fragment_id_str.isdigit(), f"chara_fragment_img_tag of map_id [{map_id}] got invalid id [{chara_fragment_id_str}]"
    return int(chara_fragment_id_str)


def get_area_chara(area_id: int, html_content: str) -> dict[int, int]:
    """
    Returns:
        Dict[map_id: int, chara_fragment_id: int]
    """
    map_bs = BeautifulSoup(html_content, 'html.parser')

    def quest_tag_filter(tag: Tag) -> bool:
        return tag.name == "th" and "任務" in tag.text

    quest_tag = map_bs.find(quest_tag_filter)
    if not quest_tag:
        logging.error(f"th [任務] not found in map [{area_id}]")
        return {}

    def map_filter(tag: Tag) -> bool:
        return tag.name == "h3" and "item-title" in tag.get("class", [])

    map_tags = quest_tag.find_parent().find_parent().find_all(map_filter)
    if not map_tags:
        logging.error(f"map_tags not found in map [{area_id}]")
        return {}
    # logging.debug(f'area [{area_id}] found [{len(map_tags)}] maps')

    map_id2chara_id: dict[int, int] = {}
    area_friendly_id: int = area_id % 1000
    for i, map_tag in enumerate(map_tags):
        map_id_raw_expected = f'{area_friendly_id}-{i+1}' 
        map_id_raw_found: str = map_tag.text
        assert map_id_raw_found == map_id_raw_expected, f"Found map id [{map_id_raw_found}], expected [{map_id_raw_expected}]"
        map_id: int = area_id * 1000 + (i + 1)
        map_id2chara_id[map_id] = get_map_chara(map_id, map_tag)

    return map_id2chara_id


async def get_vh_map_id2chara_fragment_id_async() -> dict[int, int]:
    vh_area_id2url = await get_vh_area_id2url_async()

    url2area_id = {url: id for id, url in vh_area_id2url.items()}
    url2filepath = {url: gs_data_dir / "map_pages" / f'{id}.html' for url, id in url2area_id.items()}
    url2html_content = await fetch_htmls_and_save_async(url2filepath, download_if_exists=False)

    map_id2chara_fragment_id = {}
    for url, area_id in url2area_id.items():
        html_content = url2html_content[url]
        for map_id, chara_fragment_id in get_area_chara(area_id, html_content).items():
            map_id2chara_fragment_id[map_id] = chara_fragment_id

    return map_id2chara_fragment_id


def output_star6_data(map_id2chara_fragment_id: dict[int, int]) -> None:
    map_id2chara_fragment_id_sorted = sorted(map_id2chara_fragment_id.items(), key=lambda x: x[0], reverse=True)
    output = ", ".join(f"{map_id}: {chara_fragment_id}" for map_id, chara_fragment_id in map_id2chara_fragment_id_sorted)
    
    filepath = gs_output_dir / "star6_data.py"
    with open(filepath, "w", encoding="utf-8") as f:
        print(f'map2id = {{{output}}}', file=f)


def output_item_data(equips: list[EquipInfo], map_id2drop: dict[int, MapDrop]) -> None:
    id2name_output = ",\n".join(f'    {e.full_id}: "{e.name}"' for e in equips)
    id2name_output = "\n".join(["id2name = {", id2name_output, "}"])
    
    map_id2fragment_ids = {map_id: [drop_item.fragment_id for drop_item in map_drop.drop_items[:3]] for map_id, map_drop in map_id2drop.items()}
    map_id2fragment_ids_sorted = sorted(map_id2fragment_ids.items(), key=lambda x: x[0], reverse=True)
    map2idlist_output = ",\n".join(f'    {map_id}: {fragment_ids}' for map_id, fragment_ids in map_id2fragment_ids_sorted)
    map2idlist_output = "\n".join(["map2idlist = {", map2idlist_output, "}"])

    filepath = gs_output_dir / "item_data.py"
    with open(filepath, "w", encoding="utf-8") as f:
        print(id2name_output + "\n\n" + map2idlist_output, file=f)

async def main():
    ##_ = await _get_area_id2url_async(download_if_exists=True) # When you want to renew the map data
    
    # equips = await get_equip_info_async(download_if_exists=False)
    # output_equip_name(equips)

    map_id2drop = await get_normal_map_id2drop_async()
    output_map2equip(map_id2drop)

    # output_item_data(equips, map_id2drop)

    # map_id2chara_fragment_id = await get_vh_map_id2chara_fragment_id_async()
    # output_star6_data(map_id2chara_fragment_id)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
