# -*- coding: utf-8 -*-

from autopvp import AutoPVPApp
from log import logger
from aiohttp.client_exceptions import ClientConnectorError
import account_config
import asyncio
import traceback
import time

app = AutoPVPApp(config=account_config)
bot_restart_counter = 1

while True:
    logger.info('Bot running count: %d' % (bot_restart_counter))

    try:    
        asyncio.run(app.run())
    except ClientConnectorError:
        logger.warning('The connection is down, please check your connection ...')
    except KeyboardInterrupt:
        break    
    except Exception as e:
        logger.critical(traceback.format_exc())
        break

    bot_restart_counter += 1

    logger.info('Restarting the bot in 3 seconds ...')
    time.sleep(3)

logger.info('Bot stopped now ...')
