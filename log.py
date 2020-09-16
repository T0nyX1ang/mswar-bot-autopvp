import logging
import os
import sys
import time

run_time = time.time()
time_sec = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(run_time))
time_msec = '%03d' % ((run_time - int(run_time)) * 1000)
file_time_tag = time_sec + '-' + time_msec

logger = logging.getLogger('autopvp')
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(
    logging.Formatter('[%(asctime)s %(name)s] %(levelname)s: %(message)s'))
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler(os.path.join('log', 'autopvp(%s).log' % (file_time_tag)))
file_handler.setFormatter(
    logging.Formatter('[%(asctime)s %(name)s] %(levelname)s: %(message)s'))
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
