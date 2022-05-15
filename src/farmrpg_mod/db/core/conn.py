import databases
import orm

# DATABASE_URL = "sqlite:///db.sqlite"
DATABASE_URL = "postgresql://postgres:secret@nuc1.local/farmrpg_mod"
database = databases.Database(DATABASE_URL)
registry = orm.ModelRegistry(database=database)
