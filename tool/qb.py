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
        index = group[1].find('.')
        if index > 0:
            return group[1][:index]  
        return group[1]    
    return name   


# 是否属于热门官组/站点官组
def check_group(name=None, category=None):
    group = get_torrent_group(name=name)
    if category is not None:
        groups = os.getenv(str(category).upper() + '_GROUP')
    else:
        groups = os.getenv('ALL_GROUP')
    
    if groups is not None:
        groups = groups.split(',')
    return group in groups


# 是否属于HR种子
def check_hr_group(domain=None, name=None, category=None):
    hr_domains = os.getenv('HR_DOMAIN').split(',')
    hr_groups = os.getenv(category + '_HR_GROUP')
    if domain in hr_domains and hr_groups is not None:
        hr_groups = hr_groups.split(',')
        group = get_torrent_group(name=name)
        return group in hr_groups
    return False
    

# 最近几次的上传速度
def get_recently_avg_upspeed(item=None, number=10):
    file = File(dirname='torrents', category_dir=item['domain'])
    data = file.get_file(filename=item['name'] + '.json').response
    if data is not None and len(data['info']) > number:
        info = data['info'][len(data['info']) - number:]
        total_update_speed = 0
        for row in info:
            total_update_speed += float(row['upspeed'])
        avg_update_speed = int(total_update_speed / number)
        return avg_update_speed
    return False    


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
    # 拆包过滤最大文件 (GB)
    torrent_split_filter_max_size = 0
    # 拆包过滤最小文件 (GB)
    torrent_split_filter_min_size = 0
    # 拆包的站点
    torrent_split_domain=[]
    # 限制选种大小
    limit_torrent_download_size = 0
    # 黑种站点
    black_torrent_domain = []
    # HR站点
    hr_domain = []
    # HR选种大小
    hr_limit_size = 0
    # 所有官组
    all_group = []
    # 已选择文件下载总空间大小  byte 字节
    total_download_choose_file_size = 0
    # 排除不删种的站点
    torrent_filter_delete_domain = 0

    '''
    实例化
    :param qb_name 配置的下载器名称
    '''

    def __init__(self, qb_name=None):
        self.qb_name = qb_name
        self.url = os.getenv(qb_name + '_URL')
        self.username = os.getenv(qb_name + '_USERNAME')
        self.password = os.getenv(qb_name + '_PASSWORD')
        self.disk_space = int(os.getenv(qb_name + '_DISK_SPACE'))
        self.less_disk_space = int(os.getenv(qb_name + '_LESS_DOSK_SPACE'))
        self.limit_active_torrent_num = int(os.getenv(qb_name + '_LIMIT_ACTIVE_TORRENT_NUM'))
        self.active_torrent_state = ['uploading', 'downloading', 'stalledDL', 'stalledUP', 'forcedDL', 'forcedUP']
        self.limit_torrent_download_size = int(os.getenv(self.qb_name + '_LIMIT_TORRENT_DOWNLOAD_SIZE'))
        
        self.torrent_split_filter_max_size = float(os.getenv('TORRENT_SPLIT_FILTER_MAX_SIZE'))
        self.torrent_split_filter_min_size = float(os.getenv('TORRENT_SPLIT_FILTER_MIN_SIZE'))
        self.torrent_split_domain = os.getenv('TORRENT_SPLIT_DOMAIN').split(',')
        self.black_torrent_domain = os.getenv('BLACK_TORRENT_DOMAIN').split(',')
        self.hr_limit_size = int(os.getenv('HR_LIMIT_MIN_CHOOSE_SIZE'))
        self.hr_domain = os.getenv('HR_DOMAIN').split(',')
        self.all_group = os.getenv('ALL_GROUP').split(',')
        self.torrent_filter_delete_domain = os.getenv('TORRENT_FILTER_DELETE_DOMAIN').split(',')
        
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
                category = str(row['category']).upper()
                row['domain'] = os.getenv(category + '_DOMAIN')
                
                # 所有活跃种子
                if row['state'] in self.active_torrent_state:
                    self.total_download_choose_file_size += row['size']

                # 下载/上传活跃种子数
                if row['state'] in ['uploading', 'downloading']:
                    self.active_torrent_num += 1
                    
                # 暂停种子数
                if row['state'] in ['pausedDL']:
                    self.pause_torrent_num += 1
        
        # 计算剩余空间
        self.free_space = Tool(number=self.disk_space).to_byte(unit='GB').value - self.total_download_choose_file_size
        return self
    
    '''
    获取种子列表
    '''
    
    def get_torrent(self, item=None):
        api_name = '/api/v2/torrents/info'
        data= {
            'hashes': item['hash']
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
             return json.loads(self.response['content'])
        return {}
    
    '''
    删除种子
    :param item 种子数据
    :param delete_files 是否连带文件一起删除
    '''

    def delete(self, item=None, delete_files=None, rule=None):
        if item['hash'] in ['19a28721af562e743a03441bbf81e4ac276f7be0']:
            return True;
        # 发送TG消息
        Tool(qb_name=self.qb_name).send_message(item=item, rule=rule)
        
        api_name = '/api/v2/torrents/delete' 
        data = {
            'hashes': item['hash'],
            'deleteFiles': True if delete_files is None else False
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.free_space += item['size']
            self.total_torrent_num -= 1
            # 暂停的种子
            if item['state'] == 'pausedDL':
                self.pause_torrent_num -= 1
            # 活跃的种子        
            elif item['state'] in ['uploading', 'downloading']:
                self.active_torrent_num -= 1
                
            return True
        return False
        
    '''
    强制汇报
    :param item 种子数据
    '''
    
    def reannounce(self, item=None):
        api_name = '/api/v2/torrents/reannounce'
        data = {
            'hashes': item['hash'],
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            return True
        return False    

    '''
    继续种子
    :param item 种子数据
    '''

    def resume(self, item=None):
        api_name = '/api/v2/torrents/resume'
        data = {
            'hashes': item['hash'],
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.pause_torrent_num -= 1
            self.active_torrent_num += 1
            return True
        return False

    '''
    暂停种子
    :param item 种子数据
    '''

    def pause(self, item=None):
        api_name = '/api/v2/torrents/pause'
        data = {
            'hashes': item['hash'],
        }
        self.curl_request(api_name=api_name, data=data)
        if self.response['code'] == 200:
            self.pause_torrent_num += 1
            return True
        return False

    '''
    种子通用属性
    :param item 种子数据
    '''

    def properties(self, item=None):
        api_name = '/api/v2/torrents/properties'
        data = {
            'hash': item['hash'],
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
            # 暂停的种子
            if row['state'] == 'pausedDL':
                self.handle_pause_torrents(item=row)
            # 种子错误            
            elif row['state'] == 'error': 
                self.handle_error_torrents(item=row)
            # 活跃的种子        
            elif row['state'] in self.active_torrent_state:
                self.handle_active_torrent(item=row)
        return self
    
    '''
    处理错误的种子
    '''
    def handle_error_torrents(self, item=None):
        self.delete(item=item, rule='种子错误')
        return True

    '''
    处理暂停的种子
    '''
    def handle_pause_torrents(self, item=None):
        category = str(item['category']).upper()
        # 属于站点官组种子
        if check_group(name=item['name'], category=category):
            if int(time.time()) - item['added_on'] > 30 * 60:
                self.delete(item=item, rule='官方种子暂停已超过30分钟')
                return True 
        else:
            if int(time.time()) - item['added_on'] > 10 * 60:
                self.delete(item=item, rule='非官方种子暂停已超过10分钟')
                return True
                
        # HR种子
        hr_torrent = check_hr_group(domain=item['domain'], name=item['name'], category=category)
        if hr_torrent and item['total_size'] < Tool(number=self.hr_limit_size).to_byte(unit='GB').value:
            self.delete(item=item, rule=f'属于HR种子, 但文件小于{self.hr_limit_size}GB')
            return True
            
        # 获取种子文件内容
        content = self.torrent_content(torrent_hash=item['hash'])
        limit_torrent_download_size = Tool(number=self.limit_torrent_download_size).to_byte(unit='GB').value
        download_size = item['total_size']
        
        # 如果设置了分类种子大小
        limit_category_torrent_download_size = os.getenv(category + '_LIMIT_MIN_CHOOSE_SIZE')
        if limit_category_torrent_download_size is not None:
            limit_torrent_download_size = Tool(number=int(limit_category_torrent_download_size)).to_byte(unit='GB').value
            if limit_torrent_download_size > item['total_size']:
                self.delete(item=item, rule=f'站点已设置最小入种体积{limit_category_torrent_download_size}GB')   
                return True
                
        # 属于拆包站点
        if item['domain'] in self.torrent_split_domain:
            # 文件不可拆分
            if len(content) > 1:
                # 拆分方式
                split_type = os.getenv(category + '_SPLIT_SINGLE_FILE')
                if split_type is not None:
                    file_content = self.get_sign_download_content_index(item=item, content=content)
                else:
                    file_content = self.get_download_content_index(item=item, content=content)
                if len(file_content['file_index']) > 0:
                    download_size = file_content['file_size']
                    no_download_index = []
                    for row in content:
                        index = str(row['index'])
                        if index not in file_content['file_index']:
                            no_download_index.append(index)
                    no_download_index = "|".join(no_download_index)
                    self.change_files_content_download(torrent_hash=item['hash'], index=no_download_index, priority=0)
                    
        # 最后文件体积是否符合下载
        category_max_download_size = os.getenv(category + '_LIMIT_MAX_DOWNLOAD_SIZE')
        if category_max_download_size is not None:
            category_max_download_size = Tool(number=int(category_max_download_size)).to_byte(unit='GB').value
            if download_size > category_max_download_size:
                self.delete(item=item, rule='选择下载文件的体积不符合规则')
                return True
                
        #category_min_download_size = os.getenv(category + '_LIMIT_MIN_DOWNLOAD_SIZE')
        #if category_min_download_size is not None:
        #    category_min_download_size = Tool(number=int(category_min_download_size)).to_byte(unit='GB').value
        #    if download_size < category_min_download_size:
        #        self.delete(item=item, rule='选择下载文件的体积不符合规则')
        #        return True
                        
        # 属于站点官组种子
        if check_group(name=item['name'], category=category) and limit_torrent_download_size >= download_size: 
            filter_torrent_name = []
            while not self.check_free_space_enough(download_size=download_size):
                lower_income_torrent = self.get_lower_income_torrent(filter_name=filter_torrent_name)
                filter_torrent_name.append(lower_income_torrent['name'])
                self.delete(item=lower_income_torrent, rule='官组种子进来了, 删除低收益种子')
                
        # 剩余空间是否允许
        if self.check_free_space_enough(download_size=download_size):
            self.resume(item=item)
        return True      
    
    '''
    处理活跃的种子
    '''
    
    def handle_active_torrent(self, item=None):
        # 记录日志
        self.log_content(item=item)
        
        category = str(item['category']).upper()
        
        # 最近几次平均速度
        avg_up_speed = get_recently_avg_upspeed(item=item, number=5)
        
        # 查询进度
        torrent_progress = round(item['downloaded'] / item['total_size'], 2)
        
        # 是否属于官组
        is_official_group = check_group(name=item['name'], category=category)
        
        # 是否属于热门官组
        is_host_group = check_group(name=item['name'])
        
        # 是否属于HR官组
        is_hr_group = check_hr_group(domain=item['domain'], name=item['name'], category=category)
        
        # 拆包后下载体积不对
        if item['domain'] in self.torrent_split_domain:
            # 分类限制文件最大体积
            category_limit_max_size = os.getenv(category + '_LIMIT_MAX_DOWNLOAD_SIZE')
            if category_limit_max_size is not None:
                category_limit_max_size = Tool(number=int(category_limit_max_size)).to_byte(unit='GB').value
                if item['size'] > category_limit_max_size:
                    self.delete(item=item, rule='错误的下载体积')
                    return True
        
        # 黑种站点跳车    
        if item['domain'] in self.black_torrent_domain:
            # 3倍分享率跳车
            if item['uploaded'] / item['total_size'] > 3:
                self.delete(item=item, rule='3倍分享率跳车')
                return True
            # 无效做种
            if item['completion_on'] > 0 and item['state'] in ['uploading', 'stalledUP']:
                # 超过一个小时的时候，并且上传小于32kb的种子
                if type(avg_up_speed) == int and avg_up_speed <= 32 * 1024 and item['upspeed'] <= 32 * 1024 and int(time.time()) - item['completion_on'] >= 60 * 60:
                    self.delete(item=item, rule='做种60分钟上传速度小于64KB')
                    return True
            return True    
            
        # HR种子跳车
        if is_hr_group:
            hr_download_size = item['total_size'] * float(int(os.getenv(category + '_HR_PROGRESS')) / 100)
            if hr_download_size - item['downloaded'] <= 5 * 1024 *1024 * 1024:
                self.delete(item=item, rule='HR种子跳车')
                return True
        
        # 等待发车            
        if item['state'] == 'stalledDL' and item['progress'] <= 0.05:
            # 非官组 10分钟不发车
            if not is_official_group and int(time.time()) - item['added_on'] > 10 * 60:
                self.delete(item=item, rule='非官组, 10分钟不发车')
                return True    
        else:
            # 最近10次平均速度小于1MB
            if type(avg_up_speed) == int and avg_up_speed < 512 * 1024 and item['upspeed'] < 512 * 1024:
                # 种子处于活动状态、活动种子数且小于限制活动种子数 
                if item['state'] in ['uploading', 'downloading'] and self.pause_torrent_num == 0 and self.active_torrent_num < self.limit_active_torrent_num:
                    return True
                self.delete(item=item, rule='最近10次平均速度小于1MB')
                return True
                
            if item['state'] == 'downloading' :
                # 种子添加小于3分钟, 判断连接数、下载人数
                if int(time.time()) - item['added_on'] < 3 * 60:
                    if not is_host_group:
                        # 下载人数
                        num_incomplete = int(os.getenv(category + '_INCOMPLETE'))
                        if item['num_incomplete'] < num_incomplete:
                            self.delete(item=item, rule=f'真实进度{round(torrent_progress * 100, 2)}%, 设置下载人数数{num_incomplete}, 当前种子下载人数{item["num_incomplete"]}')
                            return True
                            
                        # 连接数
                        num_leechs = int(os.getenv(category + '_LEECHS'))
                        if item['num_leechs'] < num_leechs:
                            self.delete(item=item, rule=f'真实进度{round(torrent_progress * 100, 2)}%, 设置连接数{num_leechs}, 当前种子连接数{item["num_leechs"]}')
                            return True 
                # 种子添加超过3分钟
                else:
                    item['upspeed'] = 1024 if item['upspeed'] == 0 else  item['upspeed']
                    ratio = round(item['dlspeed'] / item['upspeed'], 2)
                    # 不是官组、属于黑车
                    if not is_official_group and item['dlspeed'] > 10 * 1024 * 1024 and item['upspeed'] < 512 * 1024 and ratio > 1.5:
                        self.delete(item=item, rule=f'不是官组, 且属于黑车')
                        return True 
        return True
    
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
    返回单个适合下载的文件序号
    :param content 文件内容
    :param least_size 文件内容大小
    :param content_index 文件内容序号
    '''
 
    def get_sign_download_content_index(self, item=None, content=None):
        category = str(item['category']).upper()
        
        # 拆包过滤的最小、最大文件
        limit_min_size = Tool(number=self.torrent_split_filter_min_size).to_byte(unit='GB').value
        limit_max_size = Tool(number=self.torrent_split_filter_max_size).to_byte(unit='GB').value
        
        # 下载器限制文件最大体积
        limit_size = Tool(number=int(self.limit_torrent_download_size)).to_byte(unit='GB').value
        
        # 分类限制文件最大体积
        category_limit_size = os.getenv(category + '_LIMIT_MAX_DOWNLOAD_SIZE')
        
        if category_limit_size is not None:
            limit_size = Tool(number=int(category_limit_size)).to_byte(unit='GB').value
            
        # 文件从小到大排序
        content.sort(key=lambda x: x['size'])
        
        file = {"file_index": [], "file_content": [], "file_size": 0}
        
        for row in content:
            # 最小文件/最大文件过滤
            if limit_min_size >= row['size'] or row['size'] >= limit_max_size:
                continue
            
            index = str(row['index'])
            file['file_index'].append(index)
            file['file_content'].append(row['name'])
            file['file_size'] = row['size']
            break
        
        if file['file_size'] > limit_size:
            file['file_index'] = []
            file['file_content'] = []
            file['file_size'] = 0
        return file
        
    '''
    返回可下载的文件序号
    :param content 文件内容
    :param least_size 文件内容大小
    :param content_index 文件内容序号
    '''
 
    def get_download_content_index(self, item=None, content=None):
        category = str(item['category']).upper()
        
        # 拆包过滤的最小、最小文件
        limit_max_size = Tool(number=self.torrent_split_filter_max_size).to_byte(unit='GB').value
        limit_min_size = Tool(number=self.torrent_split_filter_min_size).to_byte(unit='GB').value
        
        # 下载器限制文件最大体积
        limit_size = Tool(number=int(self.limit_torrent_download_size)).to_byte(unit='GB').value
        
        # 分类限制文件最大体积
        category_limit_max_size = os.getenv(category + '_LIMIT_MAX_DOWNLOAD_SIZE')
        category_limit_min_size = os.getenv(category + '_LIMIT_MIN_DOWNLOAD_SIZE')
        if category_limit_max_size is not None:
            category_limit_max_size = Tool(number=int(category_limit_max_size)).to_byte(unit='GB').value
        else:
            category_limit_max_size = limit_size
            
        if category_limit_min_size is not None:
            category_limit_min_size = Tool(number=int(category_limit_min_size)).to_byte(unit='GB').value    
        else:
            category_limit_min_size = 20 * 1024 * 1024 * 1024
            
        # 文件从小到大排序
        content.sort(key=lambda x: x['size'])
        
        file = {"file_index": [], "file_content": [], "file_size": 0}
        
        for row in content:
            # 最小文件/最大文件过滤
            if limit_min_size >= row['size'] or row['size'] >= limit_max_size:
                continue
            
            # 超出文件体积
            if file['file_size'] + row['size'] > category_limit_max_size:
                break
            
            index = str(row['index'])
            file['file_index'].append(index)
            file['file_content'].append(row['name'])
            file['file_size'] += row['size']
            
            # 符合下载
            if file['file_size'] > category_limit_min_size:
                break
           
        return file
    
    '''
    当前低收益的种子
    '''
    def get_lower_income_torrent(self, filter_name=None):
        if filter_name is None:
            filter_name = []
        lower_income_torrent = {}
        for item in self.torrents:
            if item['domain'] in self.torrent_filter_delete_domain:
                continue
            if item['name'] in filter_name:
                continue
            if item['state'] == 'pausedDL':
                continue
            if item['upspeed'] > 2 * 1024 * 1024:
                continue
            if len(lower_income_torrent) == 0:
                lower_income_torrent = item
                continue
            
            if lower_income_torrent['upspeed'] > item['upspeed']:
                lower_income_torrent = item
        return lower_income_torrent
        
    '''
    检查剩余空间是否允许
    :param download_size 下载文件的大小
    '''
    def check_free_space_enough(self, download_size=None):
        if self.free_space - download_size >= Tool(number=self.less_disk_space).to_byte(unit='GB').value:
            return True
        return False
    
    '''
    记录日志
    :param item 种子数据
    '''
    
    def log_content(self, item=None):
        info = {}
        if item['state'] in self.active_torrent_state:
            info = {
                'state': item['state'],
                'choose_size': Tool(number=item['size']).change_byte(2).text,
                'completed': item['completed'],
                'completed_text': Tool(number=item['completed']).change_byte(2).text,
                'uploaded': item['uploaded'],
                'uploaded_text': Tool(number=item['uploaded']).change_byte(2).text,
                'downloaded': item['downloaded'],
                'downloaded_text': Tool(number=item['downloaded']).change_byte(2).text,
                'progress': round(item['progress'], 2),
                'ratio': round(item['ratio'], 2),
                'time_active': Tool(number=item['time_active']).change_second(2).text,
                'upspeed': item['upspeed'],
                'upspeed_text': Tool(number=item['upspeed']).change_byte(2).text,
                'dlspeed': item['dlspeed'],
                'dlspeed_text': Tool(number=item['dlspeed']).change_byte(2).text,
                'num_complete': item['num_complete'],
                'num_incomplete': item['num_incomplete'],
                'num_leechs': item['num_leechs'],
            }
    
        # 记录种子
        file = File(dirname='torrents', category_dir=item['domain'])
        
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
                'seeding_time': Tool(number=item['seeding_time']).change_second(2).text,
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
    