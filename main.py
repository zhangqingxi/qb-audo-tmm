import argparse
import os.path
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname((os.path.dirname(os.path.abspath(__file__)))))
from tool.qb import *

qb_name = None
base_url = None
username = None
password = None
token = None
chat_id = None
disk_space = None
less_disk_space = None
limit_active_torrent_num = None


# 解析参数
def args():
    global qb_name, base_url, username, password, token, chat_id, disk_space, less_disk_space, limit_active_torrent_num
    ARGP = argparse.ArgumentParser(
        description='这是一个自动化种子管理',
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    ARGP.add_argument('-h', '--help', action='help', help='这是提示信息')
    ARGP.add_argument('-n', '--qb_name', required=True, help='下载器的名称. .env文件配置的前缀名称')

    argp = ARGP.parse_args()
    qb_name = argp.qb_name

    # 加载env文件
    load_dotenv(verbose=True)


if __name__ == '__main__':
    args()
    qb = Qb(qb_name=qb_name)
    qb.login()

    tries = 1
    if qb.cookie is None and tries <= 5:
        tries = tries + 1
        qb.login()

    if qb.cookie is None:
        print('登录失败，请检查用户信息')
        exit(-1)

    # 处理种子
    qb.get_torrents().delete_torrent()

    print('Done')
