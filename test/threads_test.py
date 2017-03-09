import time
import threading
import threads
import tools

thread = threading.Thread(target=lambda: threads.main("brainwallet"))
thread.start()

print "Thread started"

time.sleep(3)

print "Stopping"
tools.db_put('stop', True)
