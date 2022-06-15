import os

import databases
import orm

if "TESTING" in os.environ:
    DATABASE_URL = os.environ["TEST_DATABASE_URI"]
    database = databases.Database(DATABASE_URL, force_rollback=True)
else:
    DATABASE_URL = os.environ["DATABASE_URI"]
    database = databases.Database(DATABASE_URL)
registry = orm.ModelRegistry(database=database)
