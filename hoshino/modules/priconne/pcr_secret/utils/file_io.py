from typing import Any
from pathlib import Path
import json
from datetime import datetime
import hoshino
import threading

# def GetNowTimestamp() -> int:
#     return int(datetime.timestamp(datetime.now()))

class _FileIo:
    def __init__(self):
        self.moduleDir = Path(__file__).parent.parent
        self.dataDir = self.moduleDir / "data"
        self.configFilepath = self.moduleDir / "config.json"
        self._ingame_data_lock = threading.Lock()
        self.InitPath()
    
    def InitPath(self):
        if not self.dataDir.exists():
            self.dataDir.mkdir()
        if not (self.dataDir / "ingame_data.json").exists():
            with open(self.dataDir / "ingame_data.json", "w", encoding="utf-8") as fp:
                json.dump({}, fp, indent=4, ensure_ascii=False)
                
        if not (self.moduleDir / "daily_result").exists():
            (self.moduleDir / "daily_result").mkdir()
        
        if not (self.moduleDir / "config.json").exists():
            with open(self.moduleDir / "config.json", "w", encoding="utf-8") as fp:
                json.dump({}, fp, indent=4, ensure_ascii=False)

    @property
    def IngameData(self) -> dict[str, Any]:
        with self._ingame_data_lock:
            with open(self.dataDir / "ingame_data.json", "r", encoding="utf-8") as fp:
                try:
                    return json.load(fp)
                except Exception as e:
                    hoshino.logger.error(f'AutoPcr: 读取{"ingame_data.json"}失败：{e}')
                    raise
    
    @IngameData.setter
    def IngameData(self, value: dict[str, Any]):
        with self._ingame_data_lock:
            with open(self.dataDir / "ingame_data.json", "w", encoding="utf-8") as fp:
                try:
                    json.dump(value, fp, indent=4, ensure_ascii=False)
                except Exception as e:
                    hoshino.logger.error(f'AutoPcr: 写入{"ingame_data.json"}失败：{e}')
                    raise
            # shutil.copy(self.dataDir / filename, self.dataDir / "ingame_data.json")        
            # # 此文件中的数据都是从游戏中缓存的，且易于重建，因此无需过于复杂的IO机制。
            # # 真正重要的数据应该直接上数据库。            
    
    @property
    def CharaStoryList(self) -> list[int]:
        return self.IngameData.get("chara_story_list", [])
    
    @CharaStoryList.setter
    def CharaStoryList(self, value: list[int]):
        d = self.IngameData
        d["chara_story_list"] = value
        self.IngameData = d
    
    @property
    def MaxExploreLevel(self) -> int:
        return self.IngameData.get("max_explore_level", 3)
    
    @MaxExploreLevel.setter
    def MaxExploreLevel(self, value: int):
        d = self.IngameData
        d["max_explore_level"] = value
        self.IngameData = d
        
    def get_talent_quest_type2max_cleared_id(self) -> dict[int, int]:
        d: dict[str, int] = self.IngameData.get("talent_quest_type2max_cleared_id", {})
        return {int(k): v for k, v in d.items()}
    
    def set_talent_quest_type2max_cleared_id(self, value: dict[int, int]):
        d = self.IngameData
        d["talent_quest_type2max_cleared_id"] = value
        self.IngameData = d
    
    @property
    def Config(self) -> dict[str, Any]:
        with open(self.configFilepath, "r", encoding="utf-8") as fp:
            return json.load(fp)
    
    def get_latest_birthday_story_id(self) -> int:
        d = self.IngameData
        return d.get("latest_birthday_story_id", 4010000)
    
    def set_latest_birthday_story_id(self, story_id: int):
        d = self.IngameData
        d["latest_birthday_story_id"] = story_id
        self.IngameData = d

gs_fileIo = _FileIo()