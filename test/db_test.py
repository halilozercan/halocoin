import custom
import database
import tools

DB = custom.DB
cmd = database.DatabaseProcess(
        DB['heart_queue'],
        custom.database_name,
        tools.log,
        custom.database_port)

cmd.start()

tools.db_put('test', 'deneme')
print tools.db_get('test')