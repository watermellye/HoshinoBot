from typing import Any, Callable, Optional
from pathlib import Path
from datetime import datetime

from peewee import SqliteDatabase, Model, IntegerField, CharField, chunked

MODULE_DIR = Path(__file__).parent.parent
DATA_DIR = MODULE_DIR / "data"
DB_PATH = DATA_DIR / "ingame_data.sqlite"

DATA_DIR.mkdir(exist_ok=True)
(MODULE_DIR / "daily_result").mkdir(exist_ok=True)

db = SqliteDatabase(DB_PATH)

class StringDateTimeField(CharField):
    """
    为方便阅读和编辑，将时间以 "YYYYMMDD HH:MM" 字符串的格式存入数据库。
    """
    def db_value(self, value):
        # Python 写入 SQLite
        if isinstance(value, datetime):
            return value.strftime("%Y%m%d %H:%M")
        return str(value) if value else value

    def python_value(self, value):
        # SQLite 读到 Python
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y%m%d %H:%M")
        except ValueError as e:
            raise ValueError(f"[db_io.py] [StringDateTimeField] Failed to parse datetime string from database. [{value}] found. [YYYYMMDD HH:MM] expected.") from e

class BaseModel(Model):
    class Meta:
        database = db

class KVStore(BaseModel):
    key = CharField(primary_key=True)
    value = CharField() 

class CharaStory(BaseModel):
    story_id = IntegerField(primary_key=True, help_text="e.g. 1001001")

class TalentQuest(BaseModel):
    quest_type = IntegerField(primary_key=True, help_text="e.g. 81001000")
    max_cleared_id = IntegerField(help_text="e.g. 81001070")

class SevenEvent(BaseModel):
    "新版活动"
    event_id = IntegerField(primary_key=True)
    schedule_id = IntegerField()
    gacha_id = IntegerField()
    event_start_time = StringDateTimeField()
    event_close_time = StringDateTimeField()

db.create_tables([KVStore, CharaStory, TalentQuest, SevenEvent])

class _DbIo:
    def __init__(self):
        self.set_seven_event(event_id=10201, schedule_id=1001, gacha_id=1020101, start_time="20260331 11:00", close_time="20260423 04:59")
    
    def _get_kv(self, key: str, default_val: Any, val_type: Callable = str) -> Any:
        record = KVStore.get_or_none(KVStore.key == key)
        return default_val if record is None else val_type(record.value)
    
    def _bulk_replace(self, model: Model, data: list[dict], batch_size: int = 100):
        """通用辅助方法：清空表并分块批量写入新数据"""
        with db.atomic():
            model.delete().execute()
            if data:
                for batch in chunked(data, batch_size):
                    model.insert_many(batch).execute()

    def _set_kv(self, key: str, value: Any):
        KVStore.insert(key=key, value=str(value)).on_conflict_replace().execute()

    @property
    def CharaStoryList(self) -> list[int]:
        return [st.story_id for st in CharaStory.select()]
    
    @CharaStoryList.setter
    def CharaStoryList(self, value: list[int]):
        data = [{'story_id': v} for v in value]
        self._bulk_replace(CharaStory, data)

    @property
    def MaxExploreLevel(self) -> int:
        return self._get_kv('max_explore_level', default_val=3, val_type=int)
            
    @MaxExploreLevel.setter
    def MaxExploreLevel(self, value: int):
        self._set_kv('max_explore_level', value)

    def get_talent_quest_type2max_cleared_id(self) -> dict[int, int]:
        return {tq.quest_type: tq.max_cleared_id for tq in TalentQuest.select()}

    def set_talent_quest_type2max_cleared_id(self, value: dict[int, int]):
        data = [{'quest_type': k, 'max_cleared_id': v} for k, v in value.items()]
        self._bulk_replace(TalentQuest, data)

    def get_latest_birthday_story_id(self) -> int:
        return self._get_kv('latest_birthday_story_id', default_val=4010000, val_type=int)
            
    def set_latest_birthday_story_id(self, story_id: int):
        self._set_kv('latest_birthday_story_id', story_id)

    def get_current_seven_event(self) -> Optional[SevenEvent]:
        """
        获取当前的新版活动。
        """
        now_str = datetime.now().strftime("%Y%m%d %H:%M")
        return SevenEvent.select().where((SevenEvent.event_start_time <= now_str) & (SevenEvent.event_close_time >= now_str)).first()

    def set_seven_event(self, event_id: int, schedule_id: int, gacha_id: int, 
                        start_time: str | datetime, close_time: str | datetime):
        SevenEvent.insert(
            event_id=event_id,
            schedule_id=schedule_id,
            gacha_id=gacha_id,
            event_start_time=start_time,
            event_close_time=close_time
        ).on_conflict_replace().execute()

gs_db = _DbIo()

if __name__ == "__main__":
    ...
    
    # gs_db.set_seven_event(event_id=10201, schedule_id=1001, gacha_id=1020101, start_time="20260331 11:00", close_time="20260423 04:59")
    # db.execute_sql("UPDATE sevenevent SET event_start_time = '2026-03-31 WRONG DATA' WHERE event_id = 10201")
    # try:
    #     bad_event = gs_db.get_current_seven_event()
    #     print(f"AssertionError: Expected a ValueError due to bad datetime format, but got [{bad_event.event_start_time}] instead.")
    # except Exception as e:
    #     print(f'Successfully caught a data parsing error due to bad datetime format! Error message: {str(e)}')
    # gs_db.set_seven_event(event_id=10201, schedule_id=1001, gacha_id=1020101, start_time="20260331 11:00", close_time="20260423 04:59")
    
    # print("--- Testing db_io.py ---")

    # print("Clearing existing data")
    # KVStore.delete().execute()
    # CharaStory.delete().execute()
    # TalentQuest.delete().execute()
    
    # print("Starting tests")
    
    # # ======== Step 1: Testing default values when no data is set ========
    # print("Step 1: Testing default values when no data is set")
    # print(f"MaxExploreLevel default value: {gs_db.MaxExploreLevel}") # 3
    # print(f"get_latest_birthday_story_id default value: {gs_db.get_latest_birthday_story_id()}") # 4010000
    # print(f"CharaStoryList default value: {gs_db.CharaStoryList}") # []
    # print(f"get_talent_quest_type2max default value: {gs_db.get_talent_quest_type2max_cleared_id()}") # {}
    # print()

    # # ======== Step 2: Setting values and verifying consistency ========
    # print("Step 2: Testing data consistency after setting values")

    # gs_db.MaxExploreLevel = 18
    # v_max_explore = gs_db.MaxExploreLevel
    # print(f"MaxExploreLevel after change: {v_max_explore} (Type: {type(v_max_explore)})") # 18, <class 'int'>

    # gs_db.set_latest_birthday_story_id(4010166)
    # print(f"get_latest_birthday_story_id after change: {gs_db.get_latest_birthday_story_id()}") # 4010166

    # gs_db.CharaStoryList = [1001001, 1001002, 1900999]
    # print(f"CharaStoryList after change: {gs_db.CharaStoryList}")

    # test_talent_quest = {
    #     81001000: 81001070,
    #     82001000: 82001070,
    #     83001000: 83001070
    # }
    # gs_db.set_talent_quest_type2max_cleared_id(test_talent_quest)
    # print(f"get_talent_quest_type2max_cleared_id after change: {gs_db.get_talent_quest_type2max_cleared_id()}")
    # print()
    
    # print("Clearing existing data")
    # KVStore.delete().execute()
    # CharaStory.delete().execute()
    # TalentQuest.delete().execute()

    # print("--- Self-test completed ---")