from base64 import b64encode
from board import get_board, get_board_result
from log import logger
import os
import json
import time
import aiohttp
import hashlib

class AutoPVPApp(object):
    def __init__(self, config, bvs=2.0):
        self.__uid = config.uid
        self.__token = config.token
        self.__host = '119.29.91.152:8080'
        self.__url = 'http://' + self.__host + '/MineSweepingWar/socket/pvp/' + self.__uid
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

    def __default_room_config(self):
        default = {
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
            'title': '自动对战(暂时勿进)(%s)' % os.urandom(4).hex(),
            'password': '',
        }
        return default

    def __format_message(self, message):
        ready = json.dumps(message, separators=(',', ':'), sort_keys=True)
        logger.debug('[Send][->]: %s' % str(ready))
        return ready

    def __get_enter_room_message(self) -> str:
        logger.info('The bot is entering the whole pvp room ...')
        enter_room = {'version': 107, 'url': "enter"}
        return self.__format_message(enter_room)

    def __get_create_room_message(self) -> str:
        logger.info('The bot is creating a single battle room ... ')
        create_room = self.__default_room_config()
        create_room['url'] = 'room/minesweeper/create'
        return self.__format_message(create_room)

    def __get_edit_room_message(self, row: int=8, column: int=8, mines: int=10, bvs: float=2.0) -> str:
        logger.info('The bot is changing the room configurations ...')
        self.__bvs = bvs
        edit_room = self.__default_room_config()
        edit_room.pop('anonymous')
        edit_room.pop('limitRank')
        edit_room['column'] = column
        edit_room['row'] = row
        edit_room['mines'] = mines
        edit_room['url'] = 'room/minesweeper/edit'
        return self.__format_message(edit_room)

    def __get_ready_status_message(self, ready: bool=True) -> str:
        if ready:
            logger.info('The bot is getting ready ... ')
        else:
            logger.info('The bot is not getting ready ... ')
        ready_status = {'ready': ready, 'url': 'room/ready'}
        return self.__format_message(ready_status)

    def __get_start_battle_message(self) -> str:
        logger.info('The bot is starting a battle ...')
        start_battle = {'url': 'room/start'}
        return self.__format_message(start_battle)

    def __get_battle_board_message(self) -> str:
        logger.info('The bot is analyzing the board ...')
        battle_board = {'url': 'minesweeper/info'}
        return self.__format_message(battle_board)

    def __get_battle_progress_message(self, current_bv: int) -> str:
        logger.info('The bot is solving %d bv ...' % (current_bv))
        battle_progress = {'bv': current_bv, 'url': 'minesweeper/progress'}
        return self.__format_message(battle_progress)

    def __get_bot_success_message(self, map_bv: int, finish_time: float) -> str:
        logger.info('The bot is ready to finish the battle ...')
        time_in_millisec = int(finish_time * 1000)
        real_bvs = round(map_bv / finish_time, 3)
        bot_success = {'time': time_in_millisec, 'url': 'minesweeper/success', 'bvs': real_bvs}
        return self.__format_message(bot_success)

    def __get_room_edit_warning_message(self) -> str:
        logger.warning('The bot detected violation of the room rules ...')
        room_edit_warning = {'url': 'room/message', 'msg': '机器人仅支持“双人，非匿名，无雷币，回合数为1，无加密，自动开局，不强制NF，不限制排名”的房间，请重新设置房间，否则机器人不会准备游戏。'}
        return self.__format_message(room_edit_warning)

    def __get_exit_room_message(self) -> str:
        logger.info('The bot is exiting the battle room ...')
        exit_room = {'url': 'room/exit'}
        return self.__format_message(exit_room)

    async def run(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url=self.__url, heartbeat=10.0, headers=self.__generate_headers()) as ws:
                await ws.send_str(self.__get_enter_room_message())

                opponent_uid = ''
                is_gaming = False

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        logger.debug('[Recv][<-]: %s' % str(msg.data))
                        text_message = json.loads(msg.data)

                        if 'url' in text_message:
                            if not is_gaming:
                                current_game_started_time = 0
                                current_game_finished_time = 0
                                current_game_bv = 0

                                if text_message['url'] == 'pvp/enter':
                                    await ws.send_str(self.__get_create_room_message())
                                elif text_message['url'] == 'pvp/room/user/enter' and self.__uid != text_message['user']['pvp']['uid']:
                                    opponent_uid = text_message['user']['pvp']['uid']
                                    logger.info('An opponent entered the room ...')
                                elif text_message['url'] == 'pvp/room/user/exit' and opponent_uid == text_message['user']['pvp']['uid']:
                                    logger.info('The opponent exited the room ...')
                                    # await ws.send_str(self.__get_edit_room_message())
                                    await ws.send_str(self.__get_exit_room_message())
                                elif text_message['url'] == 'pvp/room/ready' and opponent_uid == text_message['uid'] and text_message['ready']:
                                    logger.info('The opponent got ready ...')
                                    await ws.send_str(self.__get_start_battle_message())
                                elif text_message['url'] == 'pvp/room/update' and self.__uid in text_message['room']['userIdList']:
                                    # logger.info(text_message['room']['userIdList'])
                                    logger.info('The room status has been updated ...')
                                    if text_message['room']['expired']:
                                        logger.info('The room has expired ...')
                                    if text_message['room']['gaming']:
                                        is_gaming = True
                                        await ws.send_str(self.__get_battle_board_message())
                                    else:
                                        if opponent_uid == text_message['room']['users'][0]['pvp']['uid']:
                                            if text_message['room']['coin'] == 0 and len(text_message['room']['password']) == 0 and text_message['room']['minesweeperAutoOpen'] and not text_message['room']['minesweeperFlagForbidden'] and text_message['room']['round'] == 1 and text_message['room']['maxNumber'] == 2: 
                                                await ws.send_str(self.__get_ready_status_message())
                                            else:
                                                await ws.send_str(self.__get_room_edit_warning_message())
                                elif text_message['url'] == 'pvp/room/exit':
                                    # keep alive
                                    logger.info('The bot left the room ...')
                                    logger.info('Re-creating the room ...')
                                    await ws.send_str(self.__get_create_room_message())

                            else:
                                if text_message['url'] == 'pvp/minesweeper/info':
                                    board = get_board(text_message['cells'][0].split('-')[0: -1])
                                    board_result = get_board_result(board)
                                    current_game_bv = board_result['bv']
                                    await ws.send_str(self.__get_battle_progress_message(1))
                                    logger.info('The battle is ready to start, wait for 6 seconds ...')
                                    time.sleep(6) # first preparation cold time
                                    current_game_started_time = time.time()
                                    logger.info('The battle is started ...')
                                elif text_message['url'] == 'pvp/minesweeper/progress':
                                    if text_message['uid'] == self.__uid:
                                        if text_message['bv'] == current_game_bv:
                                            current_game_finished_time = time.time()
                                            await ws.send_str(self.__get_bot_success_message(current_game_bv, current_game_finished_time - current_game_started_time))
                                        else:
                                            await ws.send_str(self.__get_battle_progress_message(text_message['bv'] + 1))
                                            time.sleep(1 / self.__bvs) # cold time by bvs
                                    elif text_message['uid'] == opponent_uid:
                                        logger.info('The opponent is solving %d bv ...' % (text_message['bv']))
                                    else:
                                        logger.debug('This is another game out of the room ...')
                                elif text_message['url'] == 'pvp/minesweeper/win':
                                    is_gaming = False
                                    winner_uid = text_message['users'][0]['pvp']['uid']
                                    if winner_uid == self.__uid:
                                        logger.info('The bot won the battle ...')
                                    elif winner_uid == opponent_uid:
                                        logger.info('The opponent won the battle ...')

                        else:
                            logger.warning('Something weird is happening, HTTP code: %d.' % text_message['code'])

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(str(msg.data))
                        break
