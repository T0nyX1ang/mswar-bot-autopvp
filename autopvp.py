from base64 import b64encode
from board import get_board, get_board_result
from log import logger
from ban import ban_list
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import os
import math
import json
import time
import aiohttp
import hashlib
import traceback

class AutoPVPApp(object):
    def __init__(self, config):
        logger.info('Initializing bot, loading account and establishing websocket connection ...')
        self.__uid = config.uid
        self.__token = config.token
        self.__host = config.host
        self.__compat_version = config.version
        self.__salt = config.salt
        self.__url = 'http://' + self.__host + '/MineSweepingWar/socket/pvp/' + self.__uid
        self.__level = 2.0
        self.__level_hold_on = False
        self.__MAX_LEVEL = config.max_level
        self.__MIN_LEVEL = config.min_level
        self.__INC_FACTOR = config.inc_factor
        self.__DEC_FACTOR = config.dec_factor
        self.__RESUMED = True
        self.__AES_enc = AES.new(config.key.encode(), AES.MODE_ECB)
        self.__AES_dec = AES.new(config.key.encode(), AES.MODE_ECB)
        self.__USER_LIST = {}
        self.__NORMAL_COUNTS = config.normal_max
        self.__VIP_COUNTS = config.vip_max

    def aes_encrypt(self, message):
        return self.__AES_enc.encrypt(pad(message, AES.block_size)).hex().upper()

    def aes_decrypt(self, message):
        return unpad(self.__AES_dec.decrypt(message), AES.block_size)

    def __generate_headers(self):
        timestamp = str(int(time.time() * 1000))
        api_key_resource = self.__uid + self.__token + timestamp + 'api'
        headers = {
            "Host": self.__host, 
            "User-Agent": "okhttp/4.7.2",
            "Accept-Encoding": "gzip", 
            "api-key": hashlib.md5(api_key_resource.encode()).hexdigest(),
            "channel": "Android", 
            "device": "",
            "version": str(self.__compat_version), 
            "time-stamp": timestamp, 
            "token": self.__token, 
            "uid": self.__uid,
            "Connection": "Upgrade", 
            "Upgrade": "websocket", 
            "Sec-WebSocket-Extensions": "permessage-deflate",
            "Sec-WebSocket-Key": b64encode(os.urandom(16)),
            "Sec-WebSocket-Version": "13"
        }
        return headers

    def __default_room_config(self, generate_id=False):
        if generate_id:
            self.__room_id = os.urandom(2).hex()
        default = {
            'anonymous': False,
            'autoOpen': True,
            'coin': 0,
            'column': 16,
            'row': 16,
            'mine': 40,
            'flagForbidden': False,
            'limitRank': 0,
            'maxNumber': 2,
            'round': 1,
            'title': '自动对战测试(%s)' % self.__room_id,
            'password': '',
        }
        return default

    def __format_message(self, message):
        ready = json.dumps(message, separators=(',', ':'))
        logger.debug('[Encrypt]: %s' % ready)
        encrypted = self.aes_encrypt(ready.encode())
        ready_to_hash = encrypted + self.__salt
        encrypted_hash = hashlib.md5(ready_to_hash.encode()).hexdigest()
        message = encrypted_hash + encrypted
        logger.debug('[Send][->]: %s' % message)
        return message

    def __get_enter_room_message(self) -> str:
        logger.info('The bot is entering the whole pvp room ...')
        enter_room = {'version': self.__compat_version, 'url': "enter"}
        return self.__format_message(enter_room)

    def __get_hello_message(self) -> str:
        logger.info('The bot is sending a hello message ...')
        hello_message = {'url': 'room/message', 'msg': '--- 请忽略上方信息 ---\n欢迎进入自动对战房间，此房间尚在测试阶段，可能有较多bug，如遇bug，请联系项目开发者tonyXFY。'}
        return self.__format_message(hello_message)

    def __get_create_room_message(self) -> str:
        logger.info('The bot is creating a single battle room ... ')
        create_room = self.__default_room_config(generate_id=True)
        create_room['url'] = 'room/minesweeper/create'
        return self.__format_message(create_room)

    def __get_edit_room_message(self, mode=2) -> str:
        logger.info('The bot is resuming the room configurations ...')
        edit_room = self.__default_room_config(generate_id=False)
        edit_room.pop('anonymous')
        edit_room.pop('limitRank')
        edit_room['url'] = 'room/minesweeper/edit'
        if mode == 1:
            edit_room['row'] = 8
            edit_room['column'] = 8
            edit_room['mine'] = 10
        elif mode == 3:
            edit_room['row'] = 30
            edit_room['column'] = 16
            edit_room['mine'] = 99
        elif mode == 4:
            edit_room['row'] = 16
            edit_room['column'] = 30
            edit_room['mine'] = 99
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

    def __get_room_kick_out_message(self, uid) -> str:
        logger.info('The bot is kicking out a banned user ...')
        room_kick_out = {'uid': uid, 'url': 'room/kick'}
        return self.__format_message(room_kick_out)

    def __get_exit_room_message(self) -> str:
        logger.info('The bot is exiting the battle room ...')
        exit_room = {'url': 'room/exit'}
        return self.__format_message(exit_room)

    def __get_level_status_message(self) -> str:
        logger.info('The bot is getting level status ...')
        self.__level = abs(self.__level) # not sure why a complex is generated, change the sentence for safety.
        level_status = {'url': 'room/message', 'msg': '当前等级: LV %.3f' % self.__level}
        return self.__format_message(level_status)

    def __get_error_command_message(self) -> str:
        logger.info('The bot is getting level status ...')
        error_command = {'url': 'room/message', 'msg': '错误的语法指令'}
        return self.__format_message(error_command)

    def __get_left_games_message(self, uid) -> str:
        logger.info('The bot is reminding left games...')
        left_games = {'url': 'room/message', 'msg': '剩余游戏局数: %d，玩家将在本小时内无法游戏。' % self.__USER_LIST[uid]['left']}
        return self.__format_message(left_games)

    def __user_message_parser(self, split_arg) -> tuple:
        logger.info('The bot is parsing user-input configurations ...')
        argc = len(split_arg)
        try:
            if split_arg[0] in ['level', 'lv', 'lvl'] and argc >= 2:
                if split_arg[1] in ['up', 'u']:
                    self.__level = self.__level + 0.5 if self.__level <= self.__MAX_LEVEL - 0.5 else self.__MAX_LEVEL
                    logger.info('Leveling up to %.3f...' % self.__level)
                elif split_arg[1] in ['down', 'd']:
                    self.__level = self.__level - 0.5 if self.__level >= self.__MIN_LEVEL + 0.5 else self.__MIN_LEVEL
                    logger.info('Leveling down to %.3f...' % self.__level)
                elif split_arg[1] in ['status', 's']:
                    logger.info('Level status: %.3f...' % self.__level)
                elif split_arg[1] in ['holdon', 'n']:
                    logger.info('Level will not change automatically ...')
                    self.__level_hold_on = True
                elif split_arg[1] in ['holdoff', 'f']:
                    logger.info('Level will change automatically ...')
                    self.__level_hold_on = False
                else:
                    level = float(split_arg[1])
                    if level > self.__MAX_LEVEL or level < self.__MIN_LEVEL:
                        logger.warning('Bound exceeded, will not change level ...')
                        return False
                    else:
                        logger.info('Changing level to %.3f ...' % level)
                        self.__level = level
                return self.__get_level_status_message()
            elif split_arg[0] in ['level', 'lv', 'lvl'] and argc == 1:
                logger.info('Level status: %.3f...' % self.__level)
                return self.__get_level_status_message()
            elif split_arg[0] in ['beg', 'b', 'int', 'i', 'exp-v', 'ev', 'e1', 'exp-h', 'eh', 'e2']:
                mode_ref = {
                    'beg': 1, 'b': 1, 'int': 2, 'i': 2, 
                    'exp-v': 3, 'ev': 3, 'e1': 3, 'exp-h': 4, 'eh': 4, 'e2': 4, 
                }
                mode = mode_ref[split_arg[0]]
                logger.info('Setting room mode: %d' % mode)
                return self.__get_edit_room_message(mode=mode)
            else:
                return self.__get_error_command_message()

        except Exception as e:
            logger.error(traceback.format_exc())
            return self.__get_error_command_message()

    def __get_est_bvs(self, level, difficulty, bv):
        score = level * 10
        qg_ref = {
            'exph': 435.001 / 1.000 / score,
            'expv': 435.001 / 1.000 / score,
            'int': 153.730 / 1.020 / score,
            'beg': 47.299 / 1.765 / score,
        }
        qg = qg_ref[difficulty]
        est_time = (qg * bv) ** (1 / 1.7)
        est_bvs = bv / est_time
        return est_bvs

    def __get_est_level(self, difficulty, time, solved_bv, bv):
        qg_est = time ** 1.7 / solved_bv * math.sqrt(solved_bv / bv)
        score_ref = {
            'exph': 435.001 / 1.000 / qg_est,
            'expv': 435.001 / 1.000 / qg_est,
            'int': 153.730 / 1.020 / qg_est,
            'beg': 47.299 / 1.765 / qg_est,        
        }
        score = score_ref[difficulty]
        est_level = score / 10
        return est_level

    def __get_default_level(self, user_level):
        level = 0.5 * user_level + 0.5 if user_level >= 0 else 4.0
        if level > 4.0:
            level = 4.0
        return level

    def reset_user_list(self):
        logger.info('Resuming user list ...')
        for user in self.__USER_LIST.keys():
            self.__USER_LIST[user]['left'] = self.__USER_LIST[user]['original']
        logger.debug('Current user list: %s' % self.__USER_LIST)

    async def run(self):
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url=self.__url, heartbeat=10.0, headers=self.__generate_headers()) as ws:
                await ws.send_str(self.__get_enter_room_message())

                opponent_uid = ''
                is_gaming = False

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        decrypt_message = self.aes_decrypt(bytes.fromhex(msg.data[32:]))
                        text_message = json.loads(decrypt_message)
                        logger.debug('[Recv][<-]: %s' % text_message)

                        if 'url' in text_message:
                            if not is_gaming:
                                current_game_started_time = 0
                                current_game_finished_time = 0
                                current_game_bv = 0
                                current_game_bvs = 0
                                current_game_opponent_solved_bv = 1 # This should avoid bugs in calcuation
                                current_game_difficulty = ''

                                if text_message['url'] == 'pvp/enter':
                                    await ws.send_str(self.__get_create_room_message())
                                elif text_message['url'] == 'pvp/room/enter/event' and self.__uid != text_message['user']['pvp']['uid']:
                                    opponent_uid = text_message['user']['pvp']['uid']
                                    logger.info('An opponent entered the room ...')
                                    await ws.send_str(self.__get_hello_message())
                                    self.__RESUMED = False
                                    self.__level = self.__get_default_level(text_message['user']['user']['timingLevel'])
                                    if opponent_uid not in self.__USER_LIST:
                                        self.__USER_LIST[opponent_uid] = {}
                                        if text_message['user']['user']['vip']:
                                            self.__USER_LIST[opponent_uid]['original'] = self.__VIP_COUNTS
                                            self.__USER_LIST[opponent_uid]['left'] = self.__VIP_COUNTS
                                        else:
                                            self.__USER_LIST[opponent_uid]['original'] = self.__NORMAL_COUNTS
                                            self.__USER_LIST[opponent_uid]['left'] = self.__NORMAL_COUNTS
                                    if opponent_uid in ban_list or self.__USER_LIST[opponent_uid]['left'] <= 0:
                                        logger.info('The opponent is in the ban list ...')
                                        await ws.send_str(self.__get_room_kick_out_message(uid=opponent_uid))
                                elif text_message['url'] == 'pvp/room/exit/event' and opponent_uid == text_message['user']['pvp']['uid']:
                                    if opponent_uid in ban_list:
                                        logger.info('The opponent is kicked out of the room ...')
                                    else:
                                        logger.info('The opponent exited the room ...')
                                elif text_message['url'] == 'pvp/room/ready' and opponent_uid == text_message['uid'] and text_message['ready']:
                                    logger.info('The opponent got ready ...')
                                    await ws.send_str(self.__get_start_battle_message())
                                elif text_message['url'] == 'pvp/room/update' and self.__uid in text_message['room']['userIdList']:
                                    if text_message['room']['expired']:
                                        logger.info('The room has expired ...')
                                    if text_message['room']['gaming']:
                                        is_gaming = True
                                        await ws.send_str(self.__get_battle_board_message())
                                        self.__USER_LIST[opponent_uid]['left'] -= 1
                                    else:
                                        logger.info('The room status has been updated ...')
                                        if not self.__RESUMED:
                                            await ws.send_str(self.__get_level_status_message())
                                        if opponent_uid and self.__USER_LIST[opponent_uid]['left'] <= 3:
                                            await ws.send_str(self.__get_left_games_message(uid=opponent_uid))
                                        if opponent_uid and self.__USER_LIST[opponent_uid]['left'] <= 0:
                                            await ws.send_str(self.__get_exit_room_message())
                                        if opponent_uid == text_message['room']['users'][0]['pvp']['uid']:
                                            if text_message['room']['coin'] == 0 and len(text_message['room']['password']) == 0 and text_message['room']['minesweeperAutoOpen'] and not text_message['room']['minesweeperFlagForbidden'] and text_message['room']['round'] == 1 and text_message['room']['maxNumber'] == 2: 
                                                await ws.send_str(self.__get_ready_status_message())
                                            else:
                                                await ws.send_str(self.__get_room_edit_warning_message())
                                        if len(opponent_uid) != 0 and (len(text_message['room']['userIdList']) != 2 or opponent_uid not in text_message['room']['userIdList']) and opponent_uid not in ban_list and not self.__RESUMED:
                                            await ws.send_str(self.__get_edit_room_message())
                                            self.__RESUMED = True

                                elif text_message['url'] == 'pvp/room/exit':
                                    # keep alive
                                    self.__level_hold_on = False
                                    self.__INC_FACTOR = 0.24
                                    self.__DEC_FACTOR = 0.08
                                    opponent_uid = ''
                                    logger.info('The bot left the room ...')
                                    logger.info('Re-creating the room ...')
                                    await ws.send_str(self.__get_create_room_message())
                                elif text_message['url'] == 'pvp/room/message' and opponent_uid == text_message['msg']['user']['uid']:
                                    message = text_message['msg']['message'].strip().split()
                                    if message:
                                        result = self.__user_message_parser(message)
                                        await ws.send_str(result)

                            else:
                                if text_message['url'] == 'pvp/minesweeper/info':
                                    tmp_level = self.__level
                                    board = get_board(text_message['cells'][0].split('-')[0: -1])
                                    board_result = get_board_result(board)
                                    current_game_bv = board_result['bv']
                                    current_game_difficulty = board_result['difficulty']
                                    current_game_bvs = self.__get_est_bvs(tmp_level, current_game_difficulty, current_game_bv)
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
                                            time.sleep(1 / current_game_bvs) # cold time by bvs
                                    elif text_message['uid'] == opponent_uid:
                                        current_game_opponent_solved_bv = text_message['bv']
                                        logger.info('The opponent is solving %d bv ...' % (current_game_opponent_solved_bv))
                                    else:
                                        logger.debug('This is another game out of the room ...')
                                elif text_message['url'] == 'pvp/minesweeper/win':
                                    is_gaming = False
                                    winner_uid = text_message['users'][0]['pvp']['uid']
                                    if winner_uid == self.__uid:
                                        logger.info('The bot won the battle ...')
                                        if not self.__level_hold_on:
                                            est_level = self.__get_est_level(current_game_difficulty, current_game_finished_time - current_game_started_time, current_game_opponent_solved_bv, current_game_bv)
                                            prev_level = self.__level
                                            self.__level = self.__level - (self.__level - est_level) * self.__DEC_FACTOR
                                            if self.__level < self.__MIN_LEVEL:
                                                self.__level = self.__MIN_LEVEL
                                            logger.info('Level changes a bit [%.3f -> %.3f] ...' % (prev_level, self.__level))
                                            self.__INC_FACTOR = self.__INC_FACTOR / 2.0 if self.__INC_FACTOR > 0.07 else 0.06
                                            self.__DEC_FACTOR = self.__DEC_FACTOR * 2.0 if self.__DEC_FACTOR < 0.31 else 0.32
                                            logger.info('The increasing factor is set to: %.3f' % (self.__INC_FACTOR))
                                            logger.info('The decreasing factor is set to: %.3f' % (self.__DEC_FACTOR))

                                    elif winner_uid == opponent_uid:
                                        logger.info('The opponent won the battle ...')
                                        if not self.__level_hold_on:
                                            current_game_finished_time = time.time()
                                            est_level = self.__get_est_level(current_game_difficulty, current_game_finished_time - current_game_started_time, current_game_opponent_solved_bv, current_game_bv)
                                            prev_level = self.__level
                                            self.__level = self.__level + (est_level - self.__level) * self.__INC_FACTOR
                                            if self.__level > self.__MAX_LEVEL:
                                                self.__level = self.__MAX_LEVEL
                                            logger.info('Level changes a bit [%.3f -> %.3f] ...' % (prev_level, self.__level))
                                            self.__INC_FACTOR = self.__INC_FACTOR * 2.0 if self.__INC_FACTOR < 0.47 else 0.48
                                            self.__DEC_FACTOR = self.__DEC_FACTOR / 2.0 if self.__DEC_FACTOR > 0.05 else 0.04
                                            logger.info('The increasing factor is set to: %.3f' % (self.__INC_FACTOR))
                                            logger.info('The decreasing factor is set to: %.3f' % (self.__DEC_FACTOR))

                                elif text_message['url'] == 'pvp/room/user/exit' and opponent_uid == text_message['user']['pvp']['uid']:
                                    logger.info('The opponent ran away ...')

                        else:
                            code = text_message['code']
                            logger.warning('Something weird is happening, HTTP code: %d' % code)
                            if code == 10100:
                                logger.error('Incompatible version type, please update your version number.')
                            break

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.warning('The websocket connection encounters an error: %s' % msg.data)
                        break
