import databases
import orm

DATABASE_URL = "sqlite:///db.sqlite"
database = databases.Database(DATABASE_URL)
registry = orm.ModelRegistry(database=database)
