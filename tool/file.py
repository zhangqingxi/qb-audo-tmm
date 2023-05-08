"""
文件类封装
"""
import json
import os
import types


class File:
    dirname = None
    response = None

    '''
    :param dirname 目录
    '''
    def __init__(self, dirname=None, category=None):
        self.dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if dirname is not None:
            self.dirname += '/' + str(dirname)

        if category is not None:
            self.dirname += '/' + str(category)

        if not os.path.exists(self.dirname):
            os.makedirs(self.dirname)

    """
    读取文件
    """
    def get_file(self, filename=None):
        filename = self.dirname + '/' + filename
        if os.path.exists(filename):
            f = open(filename, 'r', encoding="utf-8")
            content = f.read()
            if str(filename).find('.json') > 1:
                self.response = json.loads(content)
            else:
                self.response = content

        return self

    """
    写入文件
    """
    def write_file(self, filename=None, data=None):
        filename = self.dirname + '/' + filename

        with open(filename, 'w', encoding="utf-8") as f:
            if isinstance(data, dict):
                json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                f.write(data)

        return self
