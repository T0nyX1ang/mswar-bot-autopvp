from base64 import b64encode
from board import get_board, get_board_result
import os
import json
import time
import aiohttp
import hashlib
import logging

class AutoPVPApp(object):
    def __init__(self, config, bvs=2.0):
        self.__uid = config.uid
        self.__token = config.token
        self.__host = '119.29.91.152:8080'
        self.__url = 'http://' + self.__host + '/MineSweepingWar/socket/pvp/' + self.__uid
        self.__init_message()
        self.__game_going = False
        self.__bvs = bvs

    def __generate_headers(self):
        timestamp = str(int(time.time() * 1000))
        api_key_resource = self.__uid + self.__token + timestamp + 'api'
        headers = {
            "Host": self.__host, 
            "User-Agent": "okhttp/4.2.2",
            "Accept-Encoding": "gzip", 
            "api-key": hashlib.md5(api_key_resource.encode()).hexdigest(),
            "channel": "Android", 
            "device": "",
            "version": "107", 
            "time-stamp": timestamp, 
            "token": self.__token, 
            "uid": self.__uid,
            "Connection": "Upgrade", 
            "Upgrade": "websocket", 
            "Sec-WebSocket-Key": b64encode(os.urandom(16)),
            "Sec-WebSocket-Version": "13"
        }
        return headers

    def __init_message(self):
        self.__enter_room = {'version': 107, 'url': "enter"}
        self.__create_room = {
            'anonymous': False,
            'autoOpen': True,
            'coin': 0,
            'column': 8,
            'row': 8,
            'mine': 10,
            'flagForbidden': False,
            'limitRank': 0,
            'maxNumber': 2,
            'round': 1,
            'title': '自动对战测试',
            'url': 'room/minesweeper/create',            
        }
        self.__get_ready = {'ready': True, 'url': 'room/ready'}
        self.__start_room = {'url': 'room/start'}
        self.__exit_room = {'url': 'room/exit'}
        self.__room_info = {'url': 'minesweeper/info'}
        self.__progress = lambda x: {'bv': x, 'url': 'minesweeper/progress'}
        self.__bot_success = lambda bv: {'time': int(bv / self.__bvs * 1000), 'url': 'minesweeper/success', 'bvs': self.__bvs}

    def __format_message(self, message):
        return json.dumps(message, separators=(',', ':'), sort_keys=True)

    async def run(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url=self.__url, heartbeat=10.0, headers=self.__generate_headers()) as ws:
                await ws.send_str(self.__format_message(self.__enter_room))
                await ws.send_str(self.__format_message(self.__create_room))
                opponent_uid = ''

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        text_message = json.loads(msg.data)
                        logging.debug(text_message)

                        if 'ready' in text_message and not self.__game_going:
                            if text_message['ready'] and text_message['uid'] != self.__uid:
                                opponent_uid = text_message['uid']
                                await ws.send_str(self.__format_message(self.__start_room))

                        if 'cells' in text_message and not self.__game_going:
                            board = get_board(text_message['cells'][0].split('-')[0: -1])
                            board_result = get_board_result(board)
                            await ws.send_str(self.__format_message(self.__progress(1)))
                            logging.info('The battle is ready to start, wait for 6 seconds ...')
                            time.sleep(6) # first cold time
                            logging.info('The battle is started ...')
                            self.__game_going = True
                        
                        if 'bv' in text_message and self.__game_going:
                            if text_message['uid'] == self.__uid:
                                logging.info('bot solved BV: %d' % (text_message['bv']))
                                if text_message['bv'] == board_result['bv'] and self.__game_going:
                                    await ws.send_str(self.__format_message(self.__bot_success(board_result['bv'])))
                                    self.__game_going = False
                                    logging.info('The battle is ended, bot win ...')
                                    continue
                                await ws.send_str(self.__format_message(self.__progress(text_message['bv'] + 1)))
                                time.sleep(0.5) # cold time by bvs

                            elif text_message['uid'] == opponent_uid:
                                logging.info('opponent solved BV: %d' % (text_message['bv']))
                                if text_message['bv'] == board_result['bv'] and self.__game_going:
                                    self.__game_going = False
                                    logging.info('The battle is ended, opponent win ...')

                        if 'url' in text_message and text_message['url'] == 'pvp/room/start' and not self.__game_going:
                            await ws.send_str(self.__format_message(self.__room_info))

                        if 'url' in text_message and text_message['url'] == 'pvp/room/update':
                            if self.__uid in text_message['room']['userIdList']:
                                logging.info('The room status has been updated ...')
                                if self.__game_going:
                                    self.__game_going = False
                                await ws.send_str(self.__format_message(self.__get_ready))

                        if 'url' in text_message and text_message['url'] == 'pvp/room/exit':
                            # keep alive
                            await ws.send_str(self.__format_message(self.__create_room))

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logging.error(msg.data)
                        break
