import json
import os
import time

import tornado
from hashlib import sha1
from tornado import web, ioloop, httpserver
import os
import time
import random

from tornado.websocket import WebSocketHandler


# 用户信息
USER_INFO = {}

# 可用房间
ROOMS = { '%d' % key: {} for key in range(1, 1001)}

# 已用房间
USING_ROOMS = {}

# 游戏配置
# PLAYER_ROLE = []       # 默认 PLAYER_SETTING[0] 预言家个数  PLAYER_SETTING[1] 女巫个数  PLAYER_SETTING[2] 猎人个数   PLAYER_SETTING[3] 守卫个数   PLAYER_SETTING[4] 狼人个数  PLAYER_SETTING[5] 平民个数

class WebSocketGameHandler(WebSocketHandler):

    instances = {}  # 用于存储实例的类变量
    def open(self, room_num):
        # 在 WebSocket 连接建立时调用
        self.room_num = room_num
        self.room_info = USING_ROOMS.get(room_num, {})

        # if not self.room_info:
        #     self.close()  # 如果房间不存在，关闭连接
        #     return

        self.room_info.setdefault('websockets', []).append(self)

        WebSocketGameHandler.instances[self.room_num] = self

        self.send_update()

        print(f"WebSocket connection opened for room {room_num}")

    def on_message(self, message):
        # 当接收到 WebSocket 消息时调用
        pass

    def on_close(self):
        pass
        # 当 WebSocket 连接关闭时调用
        # 连接关闭时从类变量中删除实例
        if self.room_num in WebSocketGameHandler.instances:
            del WebSocketGameHandler.instances[self.room_num]
        else:
            print("WebSocket connection was already closed.")

    def send_update(self):
        # 向同一房间内的所有连接客户端发送更新
        if self.room_info:
            if self.ws_connection and not self.ws_connection.close:
                update_message = {'action': 'update', 'room_info': self.room_info}
                for ws_instance in self.room_info.get('websockets', []):
                    if ws_instance != self:
                        ws_instance.write_message(update_message)

                print(f"Sent update to room {self.room_num}: {update_message}")

                self.write_message(update_message)
            else:
                print("WebSocket connection is closed. Unable to send message.")

class MainPageHandler(web.RequestHandler):
    def get(self, *args, **kwargs):
        # 给身份
        person_id = self.get_cookie('person_id')
        if not person_id:
            # 第一次来，分配身份
            person_id = sha1(("%s%s" % (os.urandom(16), time.time())).encode('utf-8')).hexdigest()
            # 设置到cookie
            self.set_cookie('person_id', person_id)

        # 将用户添加到信息字典
        if person_id not in USER_INFO:
            USER_INFO[person_id] = {
                'time': time.time(),
                'name': ''
            }
        self.render('1_HOME.html')

class CreateRoomHandler(web.RequestHandler):
    def get(self, *args, **kwargs):

        self.render('2_CreateRoom.html')

class JoinRoomHandler(web.RequestHandler):
    def get(self, *args, **kwargs):

        self.render('2_JoinRoom.html')

class CreateGameHandler(web.RequestHandler):
    def post(self, *args, **kwargs):
        print(self.request.arguments)
        # 判断此人有没有去前端登记
        person_id = self.get_cookie('person_id')
        if not person_id or person_id not in USER_INFO:
            self.render('error.html', info={
                'status' : False,
                'info' : '超时刷新',
                'second' : 2,
                'url': '/'
            })
            return
        # 创建房间
        try:
            # room_num, room_info = ROOMS.popitem()
            room_num = random.choice(list(ROOMS.keys()))
            room_info = ROOMS.pop(room_num)

        except Exception as e:
            print(e)
            self.render('error.html', info={
                'status': False,
                'info': '房间已用完，请稍后访问！',
                'second': 2,
                'url': '/'
            })
            return

        # 获取游戏人员配置
        try:
            PLAYER_ROLE = []  # 默认 PLAYER_SETTING[0] 预言家个数  PLAYER_SETTING[1] 女巫个数  PLAYER_SETTING[2] 猎人个数   PLAYER_SETTING[3] 守卫个数   PLAYER_SETTING[4] 狼人个数  PLAYER_SETTING[5] 平民个数

            predictor_num = int(self.get_argument('yu_num'))
            PLAYER_ROLE.append(predictor_num)
            witch_num = int(self.get_argument('nv_num'))
            PLAYER_ROLE.append(witch_num)
            hunter_num = int(self.get_argument('lie_num'))
            PLAYER_ROLE.append(hunter_num)
            guard_num = int(self.get_argument('shou_num'))
            PLAYER_ROLE.append(guard_num)
            wolf_num = int(self.get_argument('lang_num'))
            PLAYER_ROLE.append(wolf_num)
            civilian_num = int(self.get_argument('ping_num'))
            PLAYER_ROLE.append(civilian_num)

            total_num = 0
            for i in range(len(PLAYER_ROLE)):
                total_num += PLAYER_ROLE[i]


        except Exception as e:
            print(e)
            # print('初始化游戏人员失败')
            self.render('error.html', info={
                'status': False,
                'info': '初始化游戏人员失败！请稍后尝试',
                'second': 2,
                'url': '/'
            })
            return
        # 生成房间信息
        room_info['time'] = time.time()
        room_info['num'] = room_num
        # room_info['judge'] = person_id
        room_info['player_list'] = []
        room_info['total_num'] = total_num
        room_info['cur_num'] = 1
        ws_instance = WebSocketGameHandler(application, self.request)
        ws_instance.open(room_num)
        room_info['websockets'] = [ws_instance]

        # 整个字典
        PLAYER_SEETING = {
            total_num : {'预言家' : PLAYER_ROLE[0], '女巫' : PLAYER_ROLE[1], '猎人': PLAYER_ROLE[2], '守卫' : PLAYER_ROLE[3], '狼人' : PLAYER_ROLE[4], '平民' : PLAYER_ROLE[5]}
        }
        player_seeting = PLAYER_SEETING[total_num]

        # 生成座位
        for key in player_seeting:
            if player_seeting[key]:  # 排除人数为0的角色
                for i in range(player_seeting[key]):
                    room_info['player_list'].append(
                        {'role': key, 'player' : 'no one', 'person_id' : ''}
                    )

        # 打乱顺序
        random.shuffle(room_info['player_list'])

        # 给创建房间的人分配一个角色
        for player_dict in room_info['player_list']:
            if not player_dict['person_id']:
                player_dict['person_id'] = person_id
                player_dict['player'] = self.get_argument('player_name')
                USER_INFO[person_id]['role'] = player_dict['role']
                break

        # 更新房间信息
        USING_ROOMS[room_num] = room_info

        # 更新用户信息
        USER_INFO[person_id]['room_num'] = room_num

        # 更新时间
        USER_INFO[person_id]['time'] = room_info['time']

        # 通知所有连接的客户端关于房间更新的信息
        for ws_instance in USING_ROOMS[room_num].get('websockets', []):
            ws_instance.send_update()

        # 处理成json，传给前端
        player_list_json = json.dumps(room_info['player_list'])

        self.render('4_Game.html', room_num=room_num,
                    player_list=room_info['player_list'],
                    seetings=player_seeting,
                    role=USER_INFO[person_id]['role'],
                    room_info=room_info,
                    player_list_json=player_list_json)

    get = post

class JoinGameHandler(web.RequestHandler):
    def post(self, *args, **kwargs):
        # 判断此人有没有去前端登记
        person_id = self.get_cookie('person_id')
        if not person_id or person_id not in USER_INFO:
            self.render('error.html', info={
                'status': False,
                'info': '超时刷新',
                'second': 2,
                'url': '/'
            })
            return

        # 尝试加入房间，判断输入合法
        try:
            room_num = self.get_argument('room_number')
            print(room_num)
            if room_num not in USING_ROOMS:
                self.render('error.html', info={
                    'status': False,
                    'info': '加入房间失败！房间号无效，请稍后尝试！',
                    'second': 2,
                    'url': '/'
                })
                return

            room_info = USING_ROOMS[room_num]
            room_info['cur_num'] += 1

            if room_info['cur_num'] > room_info['total_num']:
                self.render('error.html', info={
                    'status': False,
                    'info': '加入房间失败！房间已满，请稍后尝试！',
                    'second': 2,
                    'url': '/'
                })
                return

            # 处理此人加入的信息
            USER_INFO[person_id]['room_num'] = room_num

            # 给此人分配角色
            for player_dict in room_info['player_list']:
                if not player_dict['person_id']:
                    player_dict['person_id'] = person_id
                    player_dict['player'] = self.get_argument('player_name')
                    USER_INFO[person_id]['role'] = player_dict['role']
                    break

        except Exception as e:
            print(e)
            self.render('error.html', info={
                'status': False,
                'info': '加入房间失败！请稍后尝试！',
                'second': 2,
                'url': '/'
            })
            return

        # 通知所有连接的客户端关于房间更新的信息
        for ws_instance in USING_ROOMS[room_num].get('websockets', []):
            ws_instance.send_update()

        # 处理成json，传给前端
        player_list_json = json.dumps(room_info['player_list'])

        self.render('4_Game.html', room_num=room_num,
                    player_list=room_info['player_list'],
                    role=USER_INFO[person_id]['role'],
                    player_list_json=player_list_json)

    get = post



settings = {
    'template_path': 'template',
    'static_path': 'static',
}

application = web.Application([
    (r"/", MainPageHandler),
    (r"/CreateRoom", CreateRoomHandler),
    (r"/JoinRoom", JoinRoomHandler),
    # (r"/ChooseImage", )
    (r"/Game", CreateGameHandler),
    (r"/JoinGame", JoinGameHandler),
    (r"/websocket/([^/]+)", WebSocketGameHandler),
], **settings)


if __name__ == "__main__":
    http_server = httpserver.HTTPServer(application)
    http_server.listen(8080)
    ioloop.IOLoop.current().start()