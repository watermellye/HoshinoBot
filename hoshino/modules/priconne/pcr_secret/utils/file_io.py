from typing import Dict, List, Optional, Tuple, Union, Set, Any
from pathlib import Path
import json
import shutil
from datetime import datetime
import hoshino

# def GetNowTimestamp() -> int:
#     return int(datetime.timestamp(datetime.now()))

class _FileIo:
    def __init__(self):
        self.moduleDir = Path(__file__).parent.parent
        self.dataDir = self.moduleDir / "data"
        self.configFilepath = self.moduleDir / "config.json"
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
    def IngameData(self) -> Dict[str, Any]:
        with open(self.dataDir / "ingame_data.json", "r", encoding="utf-8") as fp:
            try:
                return json.load(fp)
            except Exception as e:
                hoshino.logger.error(f'AutoPcr: 读取{"ingame_data.json"}失败：{e}')
                # hoshino.logger.error(f'AutoPcr: 读取{"ingame_data.json"}失败：{e}尝试备份文件并重置')
                # try:
                #     bak = f'ingame_data.json.{GetNowTimestamp()}.bak'
                #     shutil.copy(self.dataDir / "ingame_data.json", self.dataDir / bak)
                #     hoshino.logger.error(f'AutoPcr: 原始文件已备份至{bak}')
                # except Exception as e:
                #     hoshino.logger.error(f'AutoPcr: 备份失败：{e}')
                # else:
                #     try:
                #         with open(self.dataDir / "ingame_data.json", "w", encoding="utf-8") as fp:
                #             json.dump({}, fp, indent=4, ensure_ascii=False)
                #         hoshino.logger.error(f'AutoPcr: 重置完毕')
                #     except Exception as e:
                #         hoshino.logger.error(f'AutoPcr: 重置失败：{e}')
                raise
    
    @IngameData.setter
    def IngameData(self, value: Dict[str, Any]):
        # filename = f'ingame_data.json.{GetNowTimestamp()}'
        # with open(self.dataDir / filename, "w", encoding="utf-8") as fp:
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
    def CharaStoryList(self) -> List[int]:
        return self.IngameData.get("chara_story_list", [])
    
    @CharaStoryList.setter
    def CharaStoryList(self, value: List[int]):
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
    
    @property
    def Config(self) -> Dict[str, Any]:
        with open(self.configFilepath, "r", encoding="utf-8") as fp:
            return json.load(fp)
            
    
gs_fileIo = _FileIo()
