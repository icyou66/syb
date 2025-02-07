import base64
import glob
import json
import os
import random
import threading
import time
import traceback
import config
import cv2
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Sdk:
    def __init__(self, account, password):
        self.sign = "654f4a23833cb4b4199660e4c21cd75f"
        self.client_id = "5hDBRB78Mki8zSMY31DLpzC3"
        self.client_key = "iBSbnbIXQssSAOeVgURmwyWcHvPpGTEo"
        self.user = account
        self.pwd = password
        self.token = None
        self.random = None
        self.com_id = None
        self.kcid = None
        self.progress = 0
        self.read = False
        self.semaphore = threading.Semaphore(config.thread_semaphore)
        self.session = requests.session()
        self.session.headers.update({
            "referer": "https://servicewechat.com/wxf650a3a67eea156d/78/page-frame.html",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 MicroMessenger/7.0.20.1781(0x6700143B) NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF WindowsWechat(0x63090a13) XWEB/9105"
        })
        self.url1 = "https://www.chinazsxs.com:60/api/api/index.asp"
        self.url2 = "https://www.chinazsxs.com:60/api/api/index2.asp"
        if self.login():
            self.start()

    def result(self):
        if not self.read:
            self.read = True
            print(f"全部任务已完成, 当前课程进度：{self.progress}%")
            print("—————————————————注意事项—————————————————")
            print("1，程序刷完之后微信小程序需要退出登录后再重新登录才能正常使用，否则将会提示重复登录！\n")
            print("2，若发现课程进度为非100，证明还有章节未完成，重新运行一下程序即可解决\n")

    def start(self):
        self.fetch_course()
        task_list = self.fetch_task()

        # 多线程模式
        if config.thread_api:
            thread_list = []
            for item in task_list:
                thread_list.append(threading.Thread(target=self.run, args=(item,)))
            for item in thread_list:
                item.start()
                time.sleep(1)
            for item in thread_list:
                item.join()
        else:
            for item in task_list:
                self.run(item)

        data = dict(
            action="getCourseList",
            id=self.user,
            com_id=self.com_id
        )
        result = self.session.post(self.url1, data=data, verify=False).content.decode('utf-8')
        result = json.loads(result)
        self.progress = result['data'][0]['list'][0]['bili']
        if int(self.progress) < 100:
            print("\n——————————————————")
            print("\n检测到存在任务点未完成，即将重新执行..\n")
            self.start()
        self.result()

    def run(self, item):
        with self.semaphore:
            vid = item['id']
            view_time = float(item['lastViewLength']) if item['lastViewLength'] else 0
            max_time = float(item['maxplayTime']) if item['maxplayTime'] else 0
            length = float(item['length'])
            print(f"章节：{item['title']}已经启动 【{view_time}/{max_time}/{length}】")

            # 通用data方法
            data = dict(
                action="savePlayTime",
                id=self.user,
                com_id=self.com_id,
                vid=vid,
                kcid=self.kcid,
                flag=0,
                sign=self.sign,
                sysversion="0.5.8.release",
                random=self.random
            )
            play_time = view_time
            diff = int(length - view_time / 30) + 1
            for i in range(diff):
                if length - play_time < 10:
                    break
                data['playTime'] = play_time
                data['maxplayTime'] = play_time
                try:
                    result = self.session.post(self.url1, data=data, verify=False).content.decode('utf-8')
                    result = json.loads(result)
                except:
                    print(f"【{item['title']}】上报视频时长点位：{play_time} 时异常，跳过")
                    continue

                if config.face_api:
                    bool_list = [
                        720 - 15 <= play_time < 720 + 15,
                        1440 - 15 <= play_time < 1440 + 15,
                        2160 - 15 <= play_time < 2160 + 15,
                        2880 - 15 <= play_time < 2880 + 15,
                        3600 - 15 <= play_time < 3600 + 15,
                        4320 - 15 <= play_time < 4320 + 15,
                        5040 - 15 <= play_time < 5040 + 15,
                    ]
                    if any(bool_list):
                        self.face_func(vid, play_time, item['title'])

                if result['status'] == 1:
                    print(f"【{item['title']}】上报视频时长点位：{play_time} |　总时长：{length}")
                else:
                    print(f"【{item['title']}】上报进度失败！【{result}】")
                play_time += 30
                time.sleep(config.interval)

            data['playTime'] = int(length)
            data['maxplayTime'] = int(length)
            data['flag'] = 1
            result = self.session.post(self.url2, data=data, verify=False).content.decode('utf-8')
            result = json.loads(result)
            if result['status'] == 1:
                print(f"【{item['title']}】已完成视频任务")
            else:
                print(f"【{item['title']}】完成任务失败【{result}】")

    def face_func(self, vid, play_time, title):
        # 开始人脸识别
        data = dict(
            action="getFaceCompareConfig",
            vid=vid,
            id=self.user
        )
        try:
            result = self.session.post(self.url2, data=data, verify=False).content.decode("utf-8")
            time.sleep(1)
            result = json.loads(result)

            if result['status'] == '1':
                bizcode = result['data']['bizCode']
            else:
                bizcode = ""
        except:
            bizcode = ""

        url = "https://aip.baidubce.com/oauth/2.0/token"
        data = dict(
            grant_type="client_credentials",
            client_id=self.client_id,
            client_secret=self.client_key
        )
        result = self.session.post(url, data=data, verify=False).content.decode("utf-8")
        result = json.loads(result)
        access_token = result['access_token']
        time.sleep(1)
        path = self.random_file_from_folder("image")
        b64_str = self.image_to_base64(path)

        url = f"https://aip.baidubce.com/rest/2.0/face/v3/match?access_token={access_token}"
        data = [
            {
                "image": self.token,
                "image_type": "FACE_TOKEN"
            },
            {
                "image": b64_str,
                "image_type": "BASE64",
                "liveness_control": "NONE"
            }
        ]
        self.session.post(url, json=data, verify=False)

        url = f"https://aip.baidubce.com/rest/2.0/face/v3/faceverify?access_token={access_token}"
        data = [
            {
                "image": b64_str,
                "image_type": "BASE64",
                "option": "COMMON"
            }
        ]
        result = self.session.post(url, json=data, verify=False).content.decode('utf-8')
        result = json.loads(result)
        score = result['result']['face_list'][0]['liveness']['livemapscore']

        data = dict(
            action="saveFaceImg",
            id=self.user,
            pic=b64_str,
            type="video",
            vid=vid,
            playtime=play_time,
            bizcode=bizcode
        )
        self.session.post(self.url2, data=data, verify=False)
        time.sleep(1)
        data = dict(
            action="saveLiveness",
            uid=self.user,
            com_id=self.com_id,
            aid=vid,
            score=score
        )
        result = self.session.post(self.url1, data=data, verify=False).content
        result = result.decode('utf-8')
        result = json.loads(result)
        if result['status'] == 1:
            print(f"【{title}】人脸识别成功！当前视频时间：{play_time}, 本次采集的人脸图片路径为：{path}")
        else:
            print(f"【{title}】人脸采集失败！【{result}】")
        time.sleep(1)

    def login(self):
        data = dict(
            action="Login",
            sn=self.user,
            pwd=self.pwd
        )
        result = self.session.post(self.url1, data=data, verify=False).content.decode('utf-8')
        result = json.loads(result)
        if result['status'] == 1:
            self.random = result['data'][0]['random']
            self.com_id = result['data'][0]['com_id']
            self.token = result['data'][0]['token']
            login_info = f"【random:{self.random} | com_id:{self.com_id} | token:{self.token}】"
            print(f"登录成功，欢迎您，亲爱的{result['data'][0]['nickname']}同学！ {login_info}")
            return True
        else:
            print(f"登录失败！【{result['message']}】")
            return False

    def fetch_course(self):
        data = dict(
            action="getCourseList",
            id=self.user,
            com_id=self.com_id
        )
        result = self.session.post(self.url1, data=data, verify=False).content.decode('utf-8')
        result = json.loads(result)
        item = result['data'][0]['list'][0]
        self.kcid = item['kc_id']
        print(f"当前进入课程：{item['title']}")

    def fetch_task(self):
        data = dict(
            action="getCourseShow",
            kc_id=self.kcid,
            id=self.user,
            com_id=self.com_id
        )
        result = self.session.post(self.url1, data=data, verify=False).content.decode('utf-8')
        result = json.loads(result)

        task_list = []
        for row in result['data'][0]['videos']:
            if row['Flag'] != "1":
                task_list.append(row)

        print(f"共发现{len(task_list)}个任务！")
        return task_list

    @staticmethod
    def random_file_from_folder(folder_path):
        # 获取文件夹中的所有文件列表
        files = os.listdir(folder_path)

        # 从文件列表中随机选择一个文件名
        random_file = random.choice(files)

        # 返回选定的文件的完整路径
        return os.path.join(folder_path, random_file)

    @staticmethod
    def image_to_base64(image_path):
        with open(image_path, "rb") as img_file:
            # 读取图片文件的二进制数据
            img_binary = img_file.read()
            # 将二进制数据转换为Base64编码
            base64_encoded = base64.b64encode(img_binary)
            # 将Base64编码解码为字符串并返回
            return base64_encoded.decode('utf-8')


class VideoTran:

    def __init__(self):
        self.video_path = "video.mp4"
        self.folder = "image"
        self.extract()

    def extract(self):
        video = cv2.VideoCapture(self.video_path)
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        # 删除文件夹下的所有文件
        self.del_folder()

        count = 0
        success, image = video.read()
        while success:
            if count % 2 == 0:
                # 保存帧图片
                cv2.imwrite(f"{self.folder}/frame_{count}.jpg", image)
            success, image = video.read()
            count += 1

        # 释放视频对象
        video.release()

    def del_folder(self):
        files_pattern = os.path.join(self.folder, '*')
        files = glob.glob(files_pattern)
        for file in files:
            try:
                os.remove(file)
            except:
                pass


if __name__ == "__main__":
    try:
        user = input("请输入账号：")
        while not user:
            user = input("请输入账号：")
        pwd = input("请输入密码：")
        while not pwd:
            pwd = input("请输入密码：")

        if config.face_api:
            print("请保证软件的同目录下有你自己录制的视频，视频的名字需要为：video.mp4")
            input("操作完成之后按回车键继续...")
            print(f"\n请稍等..正在生成图片文件...")
            VideoTran()
            print(f"\n图片生成完成，请打开同目录下image文件夹，检查图片。")
            input("确认无误后按回车键开始执行刷课..")

        Sdk(user, pwd)

    except:
        print(f"{traceback.format_exc()}")
        print("问题异常，请将上述错误异常截图提交issue！")

    input("按回车键结束程序..")
