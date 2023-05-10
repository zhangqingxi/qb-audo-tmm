"""
文件类封装
"""
import json
import os
import re


# 修复文件名
def repair_filename(filename=None):
    return filename.replace(' ', '.').replace('\'', '').replace('[', '').replace(']', '').replace('(', '').replace(')', '').replace('&', '-')


class File:
    dirname = None
    response = None
    files = []
    categories = {}

    '''
    实例化
    :param dirname 目录
    :param category_dir 分类目录
    '''
    def __init__(self, dirname=None, category_dir=None):
        self.dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if dirname is not None:
            self.dirname += '/' + str(dirname)

        if category_dir is not None:
            self.dirname += '/' + str(category_dir)

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
        
        # 修复文件名
        filename = repair_filename(filename=filename)
        
        with open(filename, 'w', encoding='utf-8') as f:
            if isinstance(data, dict):
                json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                f.write(data)

        return self
        
    '''
    获取所有分类目录下文件
    :param dirname 目录
    '''
    def get_category_dir_all_files(self, dirname=None):
        if dirname is not None:
            self.dirname = self.dirname + '/' + dirname
        if os.path.isdir(self.dirname):
            categories = os.listdir(self.dirname)
            for category in categories:
                filename = self.dirname + "/" + category
                self.categories[category] = os.listdir(filename)
        return self  
        
    
    '''
    获取目录下所有文件
    :param dirname 目录
    '''
    def get_dir_all_files(self, dirname=None):
        if dirname is not None:
            self.dirname = self.dirname + '/' + dirname
        if os.path.isdir(self.dirname):
            self.files = os.listdir(self.dirname)
        return self     
        
    '''    
    文件重命名
    '''
    def file_rename(self):
        for category, files in self.categories.items():
            for file in files:
                if re.search(r'\s|\&|\(|\)|\[|\]|\'', file):
                    old_file = self.dirname + '/' + category + '/' + file
                    new_file = self.dirname + '/' + category + '/' + repair_filename(filename=file)
                    os.rename(old_file, new_file)