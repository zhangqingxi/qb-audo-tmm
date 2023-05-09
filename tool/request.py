"""
通用工具类封装
"""
from io import BytesIO
from urllib import parse
import pycurl


class Request:
    url = None
    data = None
    response = {}
    
    '''
    实例化
    :param url 接口URL
    :param data 接口数据
    '''
    def __init__(self, url=None, data=None):
        self.url = url
        self.data = data

    '''
    发送curl请求
    :param cookie cookie信息
    '''

    def curl(self, cookie=None):
        body_res = BytesIO()
        herder_res = BytesIO()

        c = pycurl.Curl()
        # 设置URL
        c.setopt(pycurl.URL, self.url)

        # 设置最大重定向次数
        c.setopt(pycurl.MAXREDIRS, 5)

        # 设置超时
        c.setopt(pycurl.CONNECTTIMEOUT, 60)
        c.setopt(pycurl.TIMEOUT, 300)

        # 设置header
        # header = ['Content-Type: text/plain; charset=UTF-8']
        # c.setopt(pycurl.HTTPHEADER, header)

        if self.data is not None:
            c.setopt(pycurl.POSTFIELDS, parse.urlencode(self.data))

        if cookie is not None:
            c.setopt(pycurl.COOKIE, cookie)

        c.setopt(pycurl.HEADERFUNCTION, herder_res.write)  # 将返回的HTTP HEADER定向到回调函数getheader

        c.setopt(pycurl.WRITEFUNCTION, body_res.write)

        c.perform()

        self.response['header'] = str(herder_res.getvalue(), 'UTF-8')
        self.response['code'] = c.getinfo(pycurl.HTTP_CODE)
        self.response['content'] = str(body_res.getvalue(), 'UTF-8')
        body_res.close()
        herder_res.close()
        c.close()

        return self
