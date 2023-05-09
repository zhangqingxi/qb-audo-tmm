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
        domain = re.findall(r'&tr=(.+)?', unquote(magnet_uri), re.S | re.M)[0]
    return urlparse(domain).netloc


# 转换时间
def time_format(unix_time=None, format_type="%Y-%m-%d %H:%M:%S"):
    if unix_time == 0:
        return unix_time
    if unix_time is None:
        return time.strftime(format_type, time.localtime())
    return time.strftime(format_type, time.localtime(unix_time))


# 截取制作组
def get_torrent_group(name=None):
    group = name.rsplit('-', 1)
    if len(group) == 2 and len(group[1].rsplit('@', 1)) == 2:
        group = group[1].rsplit('@', 1)
    if len(group) == 2:   
        return group[1]
    return name    


class Qb:
    qb_name = None
    url = None
    cookie = None
    response = {}
    # 所有种子集合
    torrents = {}
    # 所有种子数
    total_torrent_num = 0
    # 暂停种子数
    pause_torrent_num = 0
    # 当前活跃种子数
    active_torrent_num = 0
    # 限制活跃种子数
    limit_active_torrent_num = 0
    # 最小预留磁盘空间
    less_disk_space = 0
    # 磁盘总空间
    disk_space = 0
    # 剩余磁盘空间
    free_space = 0
    # 活跃种子状态集合
    active_torrent_state = []
    # 限制拆包选种大小
    limit_split_torrent_download_size = 0
    # 限制黑种选种大小
    limit_black_torrent_download_size = 0
    # 限制选种大小
    limit_torrent_download_size = 0
    # 黑种站点
    black_torrent_domain = []
    # HR站点
    hr_domain = []
    # 所有官组
    all_group = []
    # 已选择文件下载总空间大小  byte 字节
    total_download_choose_file_size = 0

    '''
    实例化
    :param qb_name 配置的下载器名称
    '''

    def __init__(self, qb_name=qb_name):
        self.qb_name = qb_name
        self.url = os.getenv(qb_name + '_URL')
        self.username = os.getenv(qb_name + '_USERNAME')
        self.password = os.getenv(qb_name + '_PASSWORD')
        self.disk_space = int(os.getenv(qb_name + '_DISK_SPACE'))
        self.less_disk_space = int(os.getenv(qb_name + '_LESS_DOSK_SPACE'))
        self.limit_active_torrent_num = int(os.getenv(qb_name + '_LIMIT_ACTIVE_TORRENT_NUM'))
        self.active_torrent_state = ['uploading', 'downloading', 'stalledDL', 'stalledUP', 'forcedUP', 'forcedDL']
        self.limit_split_torrent_download_size = int(os.getenv(self.qb_name + '_LIMIT_SPLIT_TORRENT_DOWNLOAD_SIZE'))
        self.limit_black_torrent_download_size = int(os.getenv(self.qb_name + '_LIMIT_BLACK_TORRENT_DOWNLOAD_SIZE'))
        self.limit_torrent_download_size = int(os.getenv(self.qb_name + '_LIMIT_TORRENT_DOWNLOAD_SIZE'))
        self.black_torrent_domain = os.getenv('BLACK_TORRENT_DOMAIN').split(',')
        self.hr_domain = os.getenv('HR_DOMAIN').split(',')
        self.all_group = os.getenv('ALL_GROUP').split(',')

    '''
    登录
    '''

    def login(self):
        api_name = '/api/v2/auth/login'
        data = {
            'username': self.username,
            'password': self.password
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            r = re.findall(r'set-cookie: (.+?);', self.response['header'], re.S | re.M)
            self.cookie = r[0] if len(r) > 0 else None
        return self

    '''
    获取种子列表
    '''
    
    def get_torrents(self):
        api_name = '/api/v2/torrents/info'
        self.curl_request(api_name=api_name)
        if self.response['code'] == 200:
            self.torrents = json.loads(self.response['content'])
            # 总数
            self.total_torrent_num = len(self.torrents)
            for row in self.torrents:
                # 解析域名
                row['domain'] = parse_domain(tracker=row['tracker'], magnet_uri=row['magnet_uri'])

                # 记录日志
                self.log_content(item=row)

                # 活跃种子数
                if row['state'] in self.active_torrent_state:
                    self.total_download_choose_file_size += row['size']
                    self.active_torrent_num += 1

                # 暂停种子数
                if row['state'] in ['pausedDL']:
                    self.pause_torrent_num += 1

        # 计算剩余空间
        self.free_space = Tool(number=self.disk_space).to_byte(unit='GB').value - self.total_download_choose_file_size
        return self

    '''
    删除种子
    :param torrent_hash 种子HASH
    :param delete_files 是否连带文件一起删除
    '''

    def delete(self, torrent_hash=None, delete_files=None):
        api_name = '/api/v2/torrents/delete'
        data = {
            'hashes': torrent_hash,
            'deleteFiles': True if delete_files is None else False
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.active_torrent_num -= 1
            return True
        return False

    '''
    继续种子
    :param torrent_hash 种子HASH
    '''

    def resume(self, torrent_hash=None):
        api_name = '/api/v2/torrents/resume'
        data = {
            'hashes': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.pause_torrent_num -= 1
            self.active_torrent_num += 1
            return True
        return False

    '''
    暂停种子
    :param torrent_hash 种子HASH
    '''

    def pause(self, torrent_hash=None):
        api_name = '/api/v2/torrents/pause'
        data = {
            'hashes': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.pause_torrent_num += 1
            return True
        return False

    '''
    种子通用属性
    :param torrent_hash 种子HASH
    '''

    def properties(self, torrent_hash=None):
        api_name = '/api/v2/torrents/properties'
        data = {
            'hash': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return json.loads(self.response['content'])
        return {}

    '''
    处理种子
    '''

    def handle_torrents(self):
        for row in self.torrents:
            category = str(row['category']).upper()
            # 拆包种子
            if row['state'] == 'pausedDL':
                # 获取种子文件内容
                content = self.torrent_content(torrent_hash=row['hash'])
                # 文件不可拆分
                if len(content) == 1:
                    # 属于黑种站点
                    if row['domain'] in self.black_torrent_domain:
                        Tool(qb_name=self.qb_name).send_message(item=row, rule='文件不可拆分, 且属于黑种站点')
                        self.delete(torrent_hash=row['hash'])
                        continue

                    limit_torrent_download_size = Tool(number=self.limit_torrent_download_size).to_byte(unit='GB').value
                    # 文件太大
                    if row['size'] >= limit_torrent_download_size:
                        Tool(qb_name=self.qb_name).send_message(item=row, rule=f'文件不可拆分, 且文件大于{Tool(number=row["size"]).change_byte(decimal=2).text}')
                        self.delete(torrent_hash=row['hash'])
                        continue

                    # 不属于热门官组、且符合选种范围、剩余磁盘空间允许
                    group = get_torrent_group(name=row['name'])
                    if group is not None and group not in self.all_group:
                        Tool(qb_name=self.qb_name).send_message(item=row, rule=f'文件不可拆分, 且文件不属于热门官组')
                    self.delete(torrent_hash=row['hash'])
                    continue

                    # 符合文件大小
                    if Tool(number=self.free_space).to_byte('GB').value - row['size'] > Tool(number=self.less_disk_space).to_byte('GB').value:
                        self.resume(torrent_hash=row['hash'])
                        continue
                    
                # 文件可拆分
                else:
                    # 属于黑种站点, 或者文件超过允许下载的范围
                    if row['domain'] in self.black_torrent_domain or row['size'] > Tool(number=self.limit_torrent_download_size).to_byte('GB').value:
                        download_index = self.get_download_content_index(content=content)
                        if len(download_index) > 0:
                            no_download_index = []
                            for item in content:
                                if item['index'] not in download_index:
                                    no_download_index.append(str(item['index']))
                            no_download_index = "|".join(no_download_index)
                            self.change_files_content_download(torrent_hash=row['hash'], index=no_download_index, priority=0)
                            self.resume(torrent_hash=row['hash'])
                        else:
                            Tool(qb_name=self.qb_name).send_message(item=row, rule=f'文件可拆分, 但没有拆出适合下载的文件')
                            self.delete(torrent_hash=row['hash'])
                    else:
                        self.resume(torrent_hash=row['hash'])
        return self
    
    
    '''
    删种规则
    '''
    
    def delete_torrent(self):
        # 活跃种子数小于给定值 不执行删种
        # if self.active_torrent_num < self.limit_active_torrent_num:
        #     return False
        for row in self.torrents:
            # 10分钟不发车
            if int(time.time()) - row['added_on'] > 10 * 60 and row['state'] == 'stalledDL':
                self.delete(row['hash'])
                Tool(qb_name=self.qb_name).send_message(item=row, rule='10分钟不发车')
                row['state'] = 'delete'
                continue
    
            # 种子错误
            if row['state'] == 'error':
                self.delete(row['hash'])
                Tool(qb_name=self.qb_name).send_message(item=row, rule='种子错误')
                row['state'] = 'delete'
                continue
    
            # 暂停种子已超过2个小时的
            if row['state'] == 'pausedDL' and int(time.time()) - row['added_on'] > 2 * 60 * 60:
                self.delete(row['hash'])
                Tool(qb_name=self.qb_name).send_message(item=row, rule='暂停种子已超过2个小时')
                row['state'] = 'delete'
                continue
    
            # HR种子跳车
            if row['domain'] in self.hr_domain:
                category = str(row['category']).upper()
                groups = os.getenv(category + '_HR_GROUP').split(',')
                group = get_torrent_group(name=row['name'])
                progress = int(int(os.getenv(category + '_HR_PROGRESS')) / 100)
                if group in groups and len(self.torrent_content(torrent_hash=row['hash'])) == 1 and progress - row['progress'] < 0.05:
                    self.delete(row['hash'])
                    Tool(qb_name=self.qb_name).send_message(item=row, rule='HR种子跳车')
                    row['state'] = 'delete'
                    continue
            
            # 查询前10次上报的平均上传速度
            if row['state'] in self.active_torrent_state:
                file = File(dirname='torrents', category=row['category'])
                data = file.get_file(filename=row['name'] + '.json').response
                if len(data['info']) > 10:
                    info = data['info'][len(data['info']) - 10:]
                    total_update_speed = 0
                    for item in info:
                        upload_speed = item['upload_speed'] if len(str(item['upload_speed'])) == 1 else item['upload_speed'][:-3]
                        total_update_speed += float(upload_speed)
    
                    avg_update_speed = round(total_update_speed / 10, 1)
    
                    # 最近10次平均速度小于1M
                    if avg_update_speed < 1:
                        self.delete(row['hash'])
                        Tool(qb_name=self.qb_name).send_message(item=row, rule='最近10次平均速度小于1M')
                        row['state'] = 'delete'
                        continue
        return self
    
    '''
    更改文件内容下载
    :param torrent_hash 种子HASH
    :param index 种子文件序号
    :param priority 下载权重
    '''
    
    def change_files_content_download(self, torrent_hash=None, index=None, priority=None):
        api_name = '/api/v2/torrents/filePrio'
        data = {
            'hash': torrent_hash,
            'id': index,
            'priority': priority
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return True
        return False
    
    '''
    种子内容
    :param torrent_hash 种子HASH
    '''
    
    def torrent_content(self, torrent_hash=None):
        api_name = '/api/v2/torrents/files'
        data = {
            'hash': torrent_hash,
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return json.loads(self.response['content'])
        return {}
    
    '''
    返回可下载的文件序号
    :param content 文件内容
    :param least_size 文件内容大小
    :param content_index 文件内容序号
    '''
 
    def get_download_content_index(self, content=None, least_size=0, content_index=None, time=1):
        limit_size = Tool(number=int(self.limit_split_torrent_download_size)).to_byte(unit='GB').value
        # 文件从小到大排序
        content.sort(key=lambda x: x['size'])
        content_index = []
        least_size = 0
        for row in content:
            
            # 最小文件/最大文件过滤
            if 500 * 1024 * 1024 >= row['size'] or row['size'] >= limit_size:
                continue
            
            # 文件上限
            if least_size + row['size'] <= limit_size:
                least_size += row['size']
                content_index.append(str(row['index']))
            
        # 剩余空间不足以下载
        if self.free_space - least_size <= Tool(number=self.less_disk_space).to_byte('GB').value:
            return []

        return content_index
    
    
    '''
    记录日志
    :param item 种子数据
    '''
    
    def log_content(self, item=None):
        info = {}
        if item['state'] in self.active_torrent_state:
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
        file = File(dirname='torrents', category=item['category'])
    
        data = file.get_file(filename=item['name'] + '.json').response
    
        if data is None:
            data = {
                'name': item['name'],
                'category': item['category'],
                'hash': item['hash'],
                'domain': item['domain'],
                'choose_size': Tool(number=item['size']).change_byte(2).text,
                'total_size': Tool(number=item['total_size']).change_byte(2).text,
                'add_time': time_format(item['added_on']),
                'completion_time': time_format(item['completion_on']),
                'seeding_time': round(item['seeding_time'] / 60, 2),
                'info': []
            }
            
        if len(info) > 0:   
            data['info'].append(info)
    
        file.write_file(filename=item['name'] + '.json', data=data)
    
        return True
    
    '''
    CURL 请求
    :param api_name 接口地址
    :param data 数据
    '''
    
    def curl_request(self, api_name=None, data=None):
        self.response = Request(url=self.url + api_name, data=data).curl(cookie=self.cookie).response
        return self
