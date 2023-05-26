"""
监控
"""
import os
import time
import re
from tool.tool import Tool
from tool.file import File
from tool.request import Request


class Monitor:
    # 监控 TG TOKEN
    tg_token = ''
    # 监控 频道ID
    tg_chat_id = ''
    # 所有文件
    files = {}
    # 所有下载器
    downloaders = []
    # 文件内容
    file_content = []
    
    # 下载器的数据
    downloaders_content = {}
    # 站点数据
    domain_content = {}
    # 所有数据
    total_content = {}
    
    '''
    实例化
    :param qb_name 配置的下载器名称
    '''

    def __init__(self):
        self.tg_token = os.getenv('MONITOR_TG_TOKEN')
        self.tg_chat_id = os.getenv('MONITOR_TG_CHAT_ID')
        self.downloaders = os.getenv('ALL_DOWNLOADERS').split(',')

    '''
    分析种子
    '''
    def analysis_torrent(self):
        categories = File(dirname='logs').get_category_dir_all_files().categories
        self.analysis_file(categories=categories)
        self.analysis_total()
        self.analysis_downloader()
        self.analysis_domain()
        self.send_analysis_message()
        
    '''
    发送消息
    '''
    def send_analysis_message(self):
        date = time.strftime("%Y-%m-%d", time.localtime())
        text = '************站点统计***************\r\n'
       
        # 站点数据
        for content in self.domain_content:
            today_rx = 0
            today_tx = 0
            if date in self.domain_content[content]:
                today_rx = self.domain_content[content][date]['rx_text']
                today_tx = self.domain_content[content][date]['tx_text']
            total_rx = self.domain_content[content]['total']['rx_text']
            total_tx = self.domain_content[content]['total']['tx_text']
            text += f"站点域名: {content}\r\n" \
                    f"今日流量: {today_tx}↑/ {today_rx}↓\r\n" \
                    f"累计流量: {total_tx}↑/ {total_rx}↓\r\n" \
                    f"--------------------------------------\r\n"
                    
        text += '**************下载工具**************\r\n'
        # 下载器数据
        for content in self.downloaders_content:
            today_rx = 0
            today_tx = 0
            if date in self.downloaders_content[content]:
                today_rx = self.downloaders_content[content][date]['rx_text']
                today_tx = self.downloaders_content[content][date]['tx_text']
            total_rx = self.downloaders_content[content]['total']['rx_text']
            total_tx = self.downloaders_content[content]['total']['tx_text']
            text += f"下载器名: {content}\r\n" \
                    f"今日流量: {today_tx}↑/ {today_rx}↓\r\n" \
                    f"累计流量: {total_tx}↑/ {total_rx}↓\r\n" \
                    f"--------------------------------------\r\n"
                    
        # 汇总数据
        text += '**************数据汇总**************\r\n'
        today_rx = 0
        today_tx = 0
        if date in self.total_content:
            today_rx = self.total_content[date]['rx_text']
            today_tx = self.total_content[date]['tx_text']
        total_rx = self.total_content['total']['rx_text']
        total_tx = self.total_content['total']['tx_text']
        text += f"今日流量: {today_tx}↑/ {today_rx}↓\r\n" \
                f"累计流量: {total_tx}↑/ {total_rx}↓\r\n" \
                f"--------------------------------------\r\n"
                    
        api_url = 'https://api.telegram.org/bot' + self.tg_token + '/sendMessage'
        data = {
            'chat_id': self.tg_chat_id,
            'text': text,
        }
        Request(url=api_url, data=data).curl()
                    
    '''
    分析下载器
    '''
    def analysis_downloader(self): 
        content = {}
        for item in self.file_content:
            
            if item['name'] not in content.keys():
                content[item['name']] = {}
            
            if item['date'] not in content[item['name']].keys():
                content[item['name']][item['date']] = {}
            
            if len(content[item['name']][item['date']]) == 0:
                content[item['name']][item['date']] = {
                    'rx': item['rx'],
                    'tx': item['tx']
                }
            else:
                content[item['name']][item['date']]['rx'] += item['rx']
                content[item['name']][item['date']]['tx'] += item['tx']

        for downloader in content:
            total = {'rx': 0, 'tx': 0}
            for date in content[downloader].keys():
                rx = content[downloader][date]['rx']
                content[downloader][date]['rx_text'] = Tool(number=rx).change_byte(decimal=2).text
                tx = content[downloader][date]['tx']
                content[downloader][date]['tx_text'] = Tool(number=tx).change_byte(decimal=2).text

                total['rx'] += rx
                total['tx'] += tx
            
            total['rx_text'] = Tool(number=total['rx']).change_byte(decimal=2).text
            total['tx_text'] = Tool(number=total['tx']).change_byte(decimal=2).text
            content[downloader]['total'] = total
        
        self.downloaders_content = content
        return self
        
    '''
    分析站点数据
    '''
    def analysis_domain(self): 
        content = {}
        for item in self.file_content:
            
            if item['domain'] not in content.keys():
                content[item['domain']] = {}
            
            if item['date'] not in content[item['domain']].keys():
                content[item['domain']][item['date']] = {}
            
            if len(content[item['domain']][item['date']]) == 0:
                content[item['domain']][item['date']] = {
                    'rx': item['rx'],
                    'tx': item['tx']
                }
            else:
                content[item['domain']][item['date']]['rx'] += item['rx']
                content[item['domain']][item['date']]['tx'] += item['tx']

        for downloader in content:
            total = {'rx': 0, 'tx': 0}
            for date in content[downloader].keys():
                rx = content[downloader][date]['rx']
                content[downloader][date]['rx_text'] = Tool(number=rx).change_byte(decimal=2).text
                tx = content[downloader][date]['tx']
                content[downloader][date]['tx_text'] = Tool(number=tx).change_byte(decimal=2).text

                total['rx'] += rx
                total['tx'] += tx
            
            total['rx_text'] = Tool(number=total['rx']).change_byte(decimal=2).text
            total['tx_text'] = Tool(number=total['tx']).change_byte(decimal=2).text
            content[downloader]['total'] = total
        
        self.domain_content = content
        return self    
    
    '''
    分析总数据
    '''
    def analysis_total(self): 
        content = {}
        for item in self.file_content:
            if item['date'] not in content.keys():
                content[item['date']] = {}
            
            if len(content[item['date']]) == 0:
                content[item['date']] = {
                    'rx': item['rx'],
                    'tx': item['tx']
                }
            else:
                content[item['date']]['rx'] += item['rx']
                content[item['date']]['tx'] += item['tx']

        total = {'rx': 0, 'tx': 0}
        for date in content.keys():
            rx = content[date]['rx']
            content[date]['rx_text'] = Tool(number=rx).change_byte(decimal=2).text
            tx = content[date]['tx']
            content[date]['tx_text'] = Tool(number=tx).change_byte(decimal=2).text

            total['rx'] += rx
            total['tx'] += tx
        
        total['rx_text'] = Tool(number=total['rx']).change_byte(decimal=2).text
        total['tx_text'] = Tool(number=total['tx']).change_byte(decimal=2).text
        content['total'] = total
        self.total_content = content
        return self
        
    '''
    分析文件
    '''
    def analysis_file(self, categories=None):
        for category, files in categories.items():
            for filename in files:
                file_content = File(dirname='logs', category_dir=category).get_file(filename=filename) 
                file_content = file_content.response.replace(' ', '').replace('↑', '').replace('↓', '')
                content = re.findall(r'下载器名:(.*)?[\s\S]*?流量统计:(.*)?[\s\S]*?站点域名:(.*)?', file_content)
                for row in content:
                    downloader = row[0]
                    rxtx = row[1].split('/')
                    domain = row[2]
                    # TX为上行流量
                    # RX为下行流量
                    self.file_content.append({
                        'name': downloader,
                        'category': category,
                        'domain': domain,
                        'date': filename.replace('.log', ''),
                        'tx': Tool().text_to_byte(text=rxtx[0]).value,
                        'rx': Tool().text_to_byte(text=rxtx[1]).value
                    })
        return self
    