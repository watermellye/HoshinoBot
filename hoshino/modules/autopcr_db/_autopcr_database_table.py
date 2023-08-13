from peewee import *
from ._autopcr_database import _gs_autopcrDatabaseInstance
import time


def GetTableNameInDb(cls) -> str:
    return cls.__name__.lower()


def RenameTableIfInconsistent(cls: Model) -> None:
    if not cls.table_exists():
        return
    tableName = GetTableNameInDb(cls)
    columns = _gs_autopcrDatabaseInstance._s_database.get_columns(tableName)
    columnNames = [column.name for column in columns]

    fields: dict = cls._meta.fields
    expectedColumnNames = fields.keys()
    if set(columnNames) != set(expectedColumnNames):
        _gs_autopcrDatabaseInstance._s_database.execute_sql(f'ALTER TABLE {tableName} RENAME TO {tableName}_duplicated_{int(time.time())};')


def VerifyTable(cls: Model) -> None:
    RenameTableIfInconsistent(cls)
    if not cls.table_exists():
        _gs_autopcrDatabaseInstance._s_database.create_tables([cls])


class BaseModel(Model):
    class Meta:
        database = _gs_autopcrDatabaseInstance._s_database


class friend_list(BaseModel):
    """
    qqid:int 主码
    """
    qqid = IntegerField(primary_key=True)


class group_list(BaseModel):
    """
    gid:int 主码
    mute_expire_timestamp:int default=0
    """
    gid = IntegerField(primary_key=True)
    mute_expire_timestamp = IntegerField(default=0)


class qq_account_info(BaseModel):
    """
    qqid:int 主码
    nickname_cache:str
    contact:str
    """
    qqid = IntegerField(primary_key=True)
    nickname_cache = CharField()
    contact = CharField()


class pcr_account_info(BaseModel):
    """
    pcrid:int 主码
    account:str
    password:str
    update_time:str
    is_valid:bool
    pcrname_cache:str
    uid_cache:str
    access_key_cache:str
    """
    pcrid = IntegerField(primary_key=True)
    account = CharField()
    password = CharField()
    update_time = CharField()
    is_valid = BooleanField()
    pcrname_cache = CharField()
    uid_cache = CharField()
    access_key_cache = CharField()


class arena_bind(BaseModel):
    """
    qqid:int
    pcrid:int
    主码:qqid+pcrid
    """
    qqid = IntegerField()
    pcrid = IntegerField()

    class Meta:
        primary_key = CompositeKey('qqid', 'pcrid')


class arena_info(BaseModel):
    """
    pcrid:int 主码
    jjc_rank:int default=15001
    pjjc_rank:int default=15001
    """
    pcrid = IntegerField(primary_key=True)
    jjc_rank = IntegerField(default=15001)
    pjjc_rank = IntegerField(default=15001)


class daily_bind(BaseModel):
    """
    qqid:int
    pcrid:int
    primary_key:qqid+pcrid
    """
    qqid = IntegerField()
    pcrid = IntegerField()

    class Meta:
        primary_key = CompositeKey('qqid', 'pcrid')


class daily_info(BaseModel):
    """
    qqid:int 主码
    daily_config:str # dict{str:Any}
    url_key:str
    """
    qqid = IntegerField(primary_key=True)
    daily_config = CharField()  # dict{str:Any}
    url_key = CharField()


class daily_queue(BaseModel):
    """
    pcrid:int 主码
    """
    pcrid = IntegerField(primary_key=True)


class farm_info(BaseModel):
    """
    pcrid:int 主码
    activated:bool default=True
    clanid_cache:int
    today_donate_cache:int default=0
    """
    pcrid = IntegerField(primary_key=True)
    activated = BooleanField(default=True)
    clanid_cache = IntegerField()
    today_donate_cache = IntegerField(default=0)


class farm_bind(BaseModel):
    """
    pcrid:int 主码
    qqid:int default=0
    permitted_clanid:int default=0 (stands for forbidden)
    """
    
    pcrid = IntegerField(primary_key=True)
    qqid = IntegerField(default=0)
    permitted_clanid = IntegerField(default=0)


class clan_info(BaseModel):
    """
    clanid:int 主码
    clan_name_cache:str
    clan_member_count_cache:int
    leader_pcrid_cache:int
    """
    clanid = IntegerField(primary_key=True)
    clan_name_cache = CharField()
    clan_member_count_cache = IntegerField()
    leader_pcrid_cache = IntegerField()


def _InitTables():
    for SubModel in BaseModel.__subclasses__():
        VerifyTable(SubModel)


_InitTables()