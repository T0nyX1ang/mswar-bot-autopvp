from autopvp import AutoPVPApp
from log import logger
import account_config
import asyncio
import traceback

app = AutoPVPApp(config=account_config, bvs=2.0)
bot_restart_counter = 1

try:
	while True:
		logger.info('Bot running count: %d' % (bot_restart_counter))
		asyncio.run(app.run())
except KeyboardInterrupt as e:
	logger.info('Bot stopped now ...')
except Exception as e:
	logger.critical(traceback.format_exc())
