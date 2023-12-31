import os
import time

import tornado
from hashlib import sha1
from tornado import web, ioloop, httpserver, websocket
import os
import time
import random
import cv2
import asyncio
import base64
import subprocess
import psutil

# 用户信息
USER_INFO = {}

# 可用房间
ROOMS = { '%d' % key: {} for key in range(1, 1001)}

# 已用房间
USING_ROOMS = {}

# 游戏配置
# PLAYER_ROLE = []       # 默认 PLAYER_SETTING[0] 预言家个数  PLAYER_SETTING[1] 女巫个数  PLAYER_SETTING[2] 猎人个数   PLAYER_SETTING[3] 守卫个数   PLAYER_SETTING[4] 狼人个数  PLAYER_SETTING[5] 平民个数

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

        # mediapipe_show();

        self.render('4_Game.html', room_num=room_num,
                    player_list=room_info['player_list'],
                    seetings=player_seeting,
                    role=USER_INFO[person_id]['role'])

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

        self.render('4_Game.html', room_num=room_num,
                    player_list=room_info['player_list'],
                    role=USER_INFO[person_id]['role'])

    get = post

class mediapipeHandler(web.RequestHandler):
    # process1 = None
    # process2 = None
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH1 = os.path.join(BASE_DIR, "Live2DVtuber", "Live2D_V2.0", "VtuberLive2D.exe")
    EXE_PATH2 = os.path.join(BASE_DIR, "Live2DVtuber", "py_V2.3", "dist", "main", "main.exe")

    def __init__(self, *args, **kwargs):
        super(mediapipeHandler, self).__init__(*args, **kwargs)
        self.process1 = None
        self.process2 = None

    def post(self, *args, **kwargs):
        action = self.get_argument("action", default=None)

        if action == "start":
            self.start_process()
            self.write("虚拟形象向你问好！")
        elif action == "stop":
            self.stop_process()
            self.write("虚拟形象跟你告别！")
        else:
            self.write("Invalid action.")

    get = post

    def start_process(self):
        if self.process1 is None or self.process1.poll() is not None:
            # 如果进程未启动或已终止，启动新的进程
            self.process1 = subprocess.Popen([self.EXE_PATH1])
            # command = ["python", self.EXE_PATH2]
            # self.process = subprocess.Popen(command)

        if self.process2 is None or self.process2.poll() is not None:
            self.process2 = subprocess.Popen([self.EXE_PATH2])

    def stop_process(self):
        self.terminate_process(self.process1)
        # self.terminate_process(self.process2)

    def terminate_process(self, process):
        if process:
            try:
                parent = psutil.Process(process.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                psutil.wait_procs(children, timeout=5)
                parent.kill()
                parent.wait(timeout=5)
                time.sleep(2)
            except psutil.NoSuchProcess:
                pass
            subprocess.run(["taskkill", "/F", "/PID", str(process.pid)], shell=True)

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
    (r"/Show", mediapipeHandler),
], **settings)


if __name__ == "__main__":
    http_server = httpserver.HTTPServer(application)
    http_server.listen(8080)
    ioloop.IOLoop.current().start()