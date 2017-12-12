import logging
import sys
from tracker import addr_from_args, Tracker

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    tracker = Tracker(*addr_from_args(sys.argv))
    tracker.start()