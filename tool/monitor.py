"""
监控
"""
import os
import time
import re
from tool.tool import Tool
from tool.file import File


class Monitor:
    # 监控 TG TOKEN
    tg_token = ''
    # 监控 频道ID
    tg_chat_id = ''
    # 所有文件
    files = {}
    # 所有下载器
    download_tools = []
    
    '''
    实例化
    :param qb_name 配置的下载器名称
    '''

    def __init__(self):
        self.tg_token = os.getenv('MONITOR_TG_TOKEN')
        self.tg_chat_id = os.getenv('MONITOR_TG_CHAT_ID')
        self.download_tools = os.getenv('DOWNLOAD_TOOLS').split(',')

    '''
    所有文件
    '''
    def get_categroy_files(self):
        self.files = File(dirname='torrents').get_category_dir_all_files()
        
    
    '''
    当日删除种子
    '''
    def get_today_delete_torrents(self):
        categories = File(dirname='logs').get_category_dir_all_files().categories
        self.analysis_file(categories=categories, today=True)
        # 计算进入
        


    def analysis_file(self, categories=None, today=None):
        
        
        for category, files in categories.items():
            for filename in files:
                if today is not None:
                    today_filename = time.strftime("%Y-%m-%d", time.localtime()) + '.log'
                    if filename != today_filename:
                        continue
                
                file_content = File(dirname='logs', category=category).get_file(filename=filename) 
                
                print(category)
                # 流量统计
                rxtx = re.findall(r'流量统计:(.*)?', file_content.response.replace(' ', '').replace('↑', '').replace('↓', ''))
                
                for row in rxtx:
                    row = row.split('/')
                    tx = Tool().text_to_byte(text=row[0]).value
                    rx = Tool().text_to_byte(text=row[1]).value
                    
                    #TX为上行流量
                    #RX为下行流量
                    print(row[0], tx, row[1], rx)

        
        
        
        
        
        # self.files = File(dirname='torrents').get_all_category_files()    
        
