import pathlib
from peewee import *


class _AutopcrDatabase:
    _s_database = None

    def __init__(self):
        dirPath = pathlib.Path(__file__).resolve().parent
        dbPath = dirPath / "autopcr.sqlite"
        self._s_database = SqliteDatabase(dbPath)  # 默认配置下，在使用需要链接数据库的api时会自动链接（autoConnect==True）

    def DropAllTables(self):
        tables = self._s_database.get_tables()
        for table in tables:
            self._s_database.execute_sql(f"DROP TABLE IF EXISTS {table}")


_gs_autopcrDatabaseInstance = _AutopcrDatabase()


