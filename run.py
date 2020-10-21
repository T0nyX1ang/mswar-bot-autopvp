# -*- coding: utf-8 -*-

from autopvp import AutoPVPApp
from log import logger
from aiohttp.client_exceptions import ClientConnectorError
from apscheduler.schedulers.background import BackgroundScheduler
import account_config
import asyncio
import traceback
import time

app = AutoPVPApp(config=account_config)
bot_restart_counter = 1
scheduler = BackgroundScheduler()
scheduler.add_job(func=app.reset_user_list, trigger='cron', hour='*', misfire_grace_time=30)
scheduler.start()
logger.info('Scheduler has been activated ...')

while True:
    logger.info('Bot running count: %d' % (bot_restart_counter))
    restart_interval = 3

    try:    
        asyncio.run(app.run())
    except ClientConnectorError:
        logger.warning('The connection is down, please check your connection ...')
        restart_interval = 30
    except KeyboardInterrupt:
        break
    except Exception:
        logger.critical(traceback.format_exc())
        restart_interval = 300

    bot_restart_counter += 1

    logger.info('Restarting the bot in %d seconds ...' % restart_interval)
    time.sleep(restart_interval)

logger.info('Bot stopped now ...')
scheduler.shutdown()
logger.info('Scheduler has been deactivated ...')