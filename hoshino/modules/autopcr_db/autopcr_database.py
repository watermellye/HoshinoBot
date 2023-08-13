'''
依赖方式：from __file__ import AutopcrDatabase
'''
from ._autopcr_database_table import _gs_autopcrDatabaseInstance
class AutopcrDatabase:
    '''
    调用方式：AutopcrDatabase.GetInstance().<SomeClassMember>
    '''

    @staticmethod
    def GetInstance():
        return _gs_autopcrDatabaseInstance