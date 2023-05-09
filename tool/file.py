"""
文件类封装
"""
import json
import os


class File:
    dirname = None
    response = None

    '''
    实例化
    :param dirname 目录
    :param category 分类目录
    '''
    def __init__(self, dirname=None, category=None):
        self.dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if dirname is not None:
            self.dirname += '/' + str(dirname)

        if category is not None:
            self.dirname += '/' + str(category)

        if not os.path.exists(self.dirname):
            os.makedirs(self.dirname)

    '''
    读取文件
    :param filename 文件名
    '''
    def get_file(self, filename=None):
        filename = self.dirname + '/' + filename
        if os.path.exists(filename):
            f = open(filename, 'r', encoding='utf-8')
            content = f.read()
            if str(filename).find('.json') > 1:
                self.response = json.loads(content)
            else:
                self.response = content

        return self

    '''
    写入文件
    :param filename 文件名
    :param data 写入的文件内容
    '''
    def write_file(self, filename=None, data=None):
        filename = self.dirname + '/' + filename

        with open(filename, 'w', encoding='utf-8') as f:
            if isinstance(data, dict):
                json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                f.write(data)

        return self
