"""
QB下载器API
"""
import json
import os
import re
import time
from urllib.parse import urlparse, unquote

from tool.file import File
from tool.request import Request

from tool.tool import Tool


# 解析站点域名
def parse_domain(tracker=None, magnet_uri=None):
    domain = tracker
    if tracker is None or tracker == '':
        domain = re.findall(r"&tr=(.+)?", unquote(magnet_uri), re.S | re.M)[0]
    return urlparse(domain).netloc


# 获取最小的的一个文件
def get_least_content(data=None, index=None):
    item = None
    for row in data:
        if index is not None and row['index'] == index:
            continue

        # 过滤小于1GB
        if row['size'] <= 1024 * 1024:
            continue

        if item is None:
            item = row
            continue

        if item['size'] > row['size']:
            item = row

    return item


# 返回可下载的文件序号
def get_download_content_index(content=None, least_size=0, content_index="", limit_split_torrent_download_size=None):
    least_content = get_least_content(data=content)
    least_size += Tool(number=least_content['size']).change_byte(2).value
    content_index = str(least_content['index']) + '|'
    if int(limit_split_torrent_download_size[0]) > least_size:
        get_download_content_index(
            content=content,
            least_size=least_size,
            content_index=content_index,
            limit_split_torrent_download_size=limit_split_torrent_download_size)

    return content_index


# 记录日志
def log_content(item=None):
    info = {
        'state': item['state'],
        'completed': Tool(number=item['completed']).change_byte(2).text,
        'uploaded': Tool(number=item['uploaded']).change_byte(2).text,
        'downloaded': Tool(number=item['downloaded']).change_byte(2).text,
        'progress': round(item['progress'], 2),
        'ratio': round(item['ratio'], 2),
        'time_active': Tool(number=item['time_active']).change_second(2).text,
        'upload_speed': Tool(number=item['upspeed']).change_byte(2).text,
        'download_speed': Tool(number=item['dlspeed']).change_byte(2).text,
        'num_complete': item['num_complete'],
        'num_incomplete': item['num_incomplete'],
        'num_leechs': item['num_leechs'],
    }

    # 记录种子
    file = File(dirname="torrents", category=item['category'])

    data = file.get_file(filename=item['name'] + '.json').response

    if data is None:
        data = {
            'name': item['name'],
            'category': item['category'],
            'hash': item['hash'],
            'domain': item['domain'],
            'choose_size': Tool(number=item['size']).change_byte(2).text,
            'total_size': Tool(number=item['total_size']).change_byte(2).text,
            'add_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item['added_on'])),
            'completion_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item['completion_on'])) if item['completion_on'] > 0 else 0,
            'seeding_time': round(item['seeding_time'] / 60, 2),
            'info': [info]
        }
    else:
        data['info'].append(info)

    file.write_file(filename=item['name'] + '.json', data=data)

    return True


class Qb:
    qb_name = None
    url = None
    cookie = None
    response = {}
    torrents = {}
    total_torrent_num = 0
    pause_torrent_num = 0
    active_torrent_num = 0
    less_disk_space = 0

    """
    已选择文件下载总空间大小  byte 字节
    """
    total_download_choose_file_size = 0

    """
    :param url 接口地址
    """

    def __init__(self, qb_name=qb_name, cookie=None):
        self.qb_name = qb_name
        self.url = os.getenv(qb_name + '_URL')
        self.username = os.getenv(qb_name + '_USERNAME')
        self.password = os.getenv(qb_name + '_PASSWORD')
        self.disk_space = os.getenv(qb_name + '_DISK_SPACE')
        self.less_disk_space = os.getenv(qb_name + '_LESS_DOSK_SPACE')
        self.limit_active_torrent_num = os.getenv(qb_name + '_LIMIT_ACTIVE_TORRENT_NUM')
        self.cookie = cookie

        # token = os.getenv(qb_name + '_TG_TOKEN')
        # chat_id = os.getenv(qb_name + '_TG_CHAT_ID')

    """
    登录
    :param username 用户名
    :param password 用户密码
    """

    def login(self):
        api_name = '/api/v2/auth/login'
        data = {
            'username': self.username,
            'password': self.password
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            r = re.findall(r"set-cookie: (.+?);", self.response['header'], re.S | re.M)
            self.cookie = r[0] if len(r) > 0 else None
        return self

    """
    获取种子列表
    """

    def get_torrents(self):
        api_name = '/api/v2/torrents/info'
        self.curl_request(api_name=api_name)
        if self.response['code'] == 200:
            self.torrents = json.loads(self.response['content'])

            # 总数
            self.total_torrent_num = len(self.torrents)

            for row in self.torrents:
                # 活跃种子数
                if row['state'] in ['uploading', 'downloading', 'stalledDL', 'stalledUP']:
                    self.total_download_choose_file_size += row['size']
                    self.active_torrent_num += 1

                # 暂停种子数
                if row['state'] in ['pausedDL']:
                    self.pause_torrent_num += 1

        # byte值转换
        # tool = Tool(self.total_download_choose_file_size).change_byte(2)
        # self.total_download_choose_file_size = tool.value
        return self

    #
    """
    删除种子
    """

    def delete(self, torrent_hash=None, delete_files=None):
        api_name = '/api/v2/torrents/delete'
        data = {
            'hashes': torrent_hash,
            'deleteFiles': True if delete_files is None else False
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return True
        return False

    """
    继续种子
    """

    def resume(self, torrent_hash=None):
        api_name = '/api/v2/torrents/resume'
        data = {
            'hashes': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return True
        return False

    """
    暂停种子
    """

    def pause(self, torrent_hash=None):
        api_name = '/api/v2/torrents/pause'
        data = {
            'hashes': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return True
        return False

    """
    种子通用属性
    """

    def properties(self, torrent_hash=None):
        api_name = '/api/v2/torrents/properties'
        data = {
            'hash': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return json.loads(self.response['content'])
        return {}

    """
    处理种子
    """

    def handle_torrents(self):
        for row in self.torrents:
            # 解析域名
            row['domain'] = parse_domain(tracker=row['tracker'], magnet_uri=row['magnet_uri'])
            # 记录日志
            log_content(item=row)
            # 查询暂停数 ===> 能拆包的种子
            if row['state'] == 'pausedDL' and row['hash'] == '5a138efe8b3a76615271be49d51ff8f500bba815':
                print(1111111)
                self.torrent_content(item=row)

                # 、连接数小于1，做种数不等于1 leechs = os.getenv(category + "_LEECHS")
                # 且文件大于 ,连接数小于{leechs}, 做种数不等于1
                # item['num_complete'] != 1 and item['num_leechs'] > leechs
                # group = os.getenv(category + "_GROUP").replace(',', '|')
                #                 r = re.findall(rf"{group}", "Fear.the.Walking.Dead.S05.2019.1080p.BluRay.AVC.DTS-HD.MA.5.1-DIY@Audie1s", re.S | re.M)
                #                 # 种子不在官组, 文件大于给定值
        # total_torrent_num = len(lists)
        # for row in lists:
        #     # r = properties(row['hash'])
        #     # row['properties'] = r
        #     if row['state'] == 'pausedDL':
        #         pause_torrent_num += 1
        #
        #     if row['state'] in ['uploading', 'downloading', 'stalledDL', 'stalledUP']:
        #         choose_file_size += row['size']
        #
        #

        # byte值转换
        # tool = Tool(self.total_download_choose_file_size).change_byte(2)
        # self.total_download_choose_file_size = tool.value
        return self

    """
    种子内容
    """

    def torrent_content(self, item=None):
        api_name = '/api/v2/torrents/files'
        data = {
            'hash': item['hash'],
        }
        category = str(item['category']).upper()
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            content = json.loads(self.response['content'])
            # 文件不可拆分
            print(len(content))
            if len(content) == 1:
                black_torrent_domain = os.getenv("BLACK_TORRENT_DOMAIN")
                # 属于黑种站点
                if item['domain'] in black_torrent_domain:
                    Tool(qb_name=self.qb_name).send_message(item=item, rule='文件不可拆分, 且属于黑种站点')
                    self.delete(torrent_hash=item['hash'])
                    return True

                size = Tool(number=item['total_size']).change_byte(2).value
                limit_black_torrent_download_size = int(os.getenv(self.qb_name + "_LIMIT_BLACK_TORRENT_DOWNLOAD_SIZE"))
                # 文件太大
                if size >= limit_black_torrent_download_size:
                    Tool(qb_name=self.qb_name).send_message(item=item, rule=f'文件不可拆分, 且文件大于{limit_black_torrent_download_size}GB')
                    self.delete(torrent_hash=item['hash'])
                    return True
            # 文件可拆分
            else:
                limit_split_torrent_download_size = str(os.getenv(self.qb_name + "_LIMIT_SPLIT_TORRENT_DOWNLOAD_SIZE")).split(',')
                index = get_download_content_index(content=content, limit_split_torrent_download_size=limit_split_torrent_download_size)

                print(index)
                for row in content:
                    print(row)

                # # 文件不可拆分， 且文件大于
                # if len(content) == 1 and domain in black_torrent_domain:
                #     print(111)
                #     exit(-1)
                #     Tool(qb_name=self.qb_name).send_message(item=item, rule='文件不可拆分， 且属于黑种站点')
                #     self.delete(torrent_hash=item['hash'])
                #     return True
        return False

    def curl_request(self, api_name=None, data=None):
        self.response = Request(url=self.url + api_name, data=data).curl(cookie=self.cookie).response
        return self
