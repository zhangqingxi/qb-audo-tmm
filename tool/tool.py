"""
通用工具类封装
"""
import os
import time
from urllib.parse import urlparse

from tool.file import File
from tool.request import Request


class Tool:
    number = None
    unit = None
    data = None
    value = None
    text = None

    '''
    数据数据量转换
    :param number 数值
    '''
    def __init__(self, qb_name=None, number=None):
        self.qb_name = qb_name
        self.number = number
        if self.number is None:
            self.number = 0

    """
    byte字节转换
    :param decimal 保留小数位
    """
    def change_byte(self, decimal=None):
        if self.number == 0:
            self.value = 0
            self.unit = ""
            self.text = 0
            return self

        if round(self.number / 1024 / 1024 / 1024 / 1024, decimal) > 1:
            self.value = round(self.number / 1024 / 1024 / 1024 / 1024, decimal)
            self.unit = 'TB'
        elif round(self.number / 1024 / 1024 / 1024, decimal) > 1:
            self.value = round(self.number / 1024 / 1024 / 1024, decimal)
            self.unit = 'GB'
        elif round(self.number / 1024 / 1024, decimal) > 1:
            self.value = round(self.number / 1024 / 1024, decimal)
            self.unit = 'MB'
        else:
            self.value = round(self.number / 1024, decimal)
            self.unit = 'KB'

        self.text = str(self.value) + ' ' + self.unit
        return self

    """
    时间转换
    :param decimal 保留小数位
    """
    def change_second(self, decimal=None):
        if round(self.number / 60 / 60 / 24, decimal) > 1:
            self.value = round(self.number / 60 / 60 / 24, decimal)
            self.unit = '天'
        elif round(self.number / 60 / 60, decimal) > 1:
            self.value = round(self.number / 60 / 60, decimal)
            self.unit = '小时'
        elif round(self.number / 60, decimal) > 1:
            self.value = round(self.number / 60, decimal)
            self.unit = '分钟'
        else:
            self.value = round(self.number, decimal)
            self.unit = '秒'

        self.text = str(self.value) + ' ' + self.unit
        return self

    """
    数据转换byte
    :param unit 单位
    """
    def to_byte(self, unit=None):
        if unit == 'TB':
            self.value = self.number * 1024 * 1024 * 1024 * 1024
        elif unit == 'GB':
            self.value = self.number * 1024 * 1024 * 1024
        elif unit == 'MB':
            self.value = self.number * 1024 * 1024
        elif unit == 'KB':
            self.value = self.number * 1024
        else:
            self.value = self.number
        return self

    """
    发送通知到TG
    :param decimal 保留小数位
    """
    def send_message(self, item=None, rule=None):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        add_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item['added_on']))
        text = f"当前时间: {current_time}\r\n" \
               f"下载器名: {self.qb_name}\r\n" \
               f"种子名称: {item['name']}\r\n" \
               f"种子大小: {Tool(number=item['total_size']).change_byte(2).text}\r\n" \
               f"选择大小: {Tool(number=item['size']).change_byte(2).text}\r\n" \
               f"已完成量: {Tool(number=item['completed']).change_byte(2).text}\r\n" \
               f"种子进度: {round(item['progress'] * 100, 2)} % \r\n" \
               f"种子状态: {item['state']}\r\n" \
               f"添加时间: {add_time}\r\n" \
               f"删除时间: {current_time}\r\n" \
               f"所属分类: {item['category']}\r\n" \
               f"流量统计: {Tool(number=item['uploaded']).change_byte(2).text} ↑ / {Tool(number=item['downloaded']).change_byte(2).text} ↓\r\n" \
               f"即时速度: {Tool(number=item['upspeed']).change_byte(2).text} ↑ / {Tool(number=item['dlspeed']).change_byte(2).text} ↓\r\n" \
               f"分享比例: {round(item['ratio'], 2)}\r\n" \
               f"站点域名: {item['domain']}\r\n" \
               f"删种规则: {rule}\r\n"

        file = File(dirname="logs", category=item['category'])
        filename = time.strftime("%Y-%m-%d", time.localtime()) + '.log'
        data = file.get_file(filename=filename).response
        if data is None:
            data = '==========================\r\n' + text
        else:
            data += '==========================\r\n' + text
        file.write_file(filename=filename, data=data)
        api_url = 'https://api.telegram.org/bot' + os.getenv(self.qb_name + '_TG_TOKEN') + '/sendMessage'
        data = {
            'chat_id': os.getenv(self.qb_name + '_TG_CHAT_ID'),
            'text': text,
        }
        Request(url=api_url, data=data).curl()


