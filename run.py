from autopvp import AutoPVPApp
import account_config
import asyncio
import logging

# Enable the logging facility
logging.basicConfig()
logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

app = AutoPVPApp(config=account_config, bvs=2.0)

try:
	while True:
		asyncio.run(app.run())
except KeyboardInterrupt as e:
	logging.info('Bot stopped now ...')
	
