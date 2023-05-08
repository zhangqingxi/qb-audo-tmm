===========
种子自动管理
===========

# 种子状态
```
error	            发生一些错误，适用于暂停的种子
missingFiles	    种子数据文件丢失
uploading	        种子正在播种，数据传输
pausedUP	        种子已暂停并已完成下载
queuedUP	        队列已启用，种子已排队等待上传
stalledUP	        种子正在播种，但没有建立任何连接
checkingUP	        洪流已完成下载并正在检查中
forcedUP	        洪流被迫上传并忽略队列限制
allocating	        Torrent 正在分配磁盘空间以供下载
downloading	        正在下载种子并传输数据
metaDL	            洪流刚刚开始下载并正在获取元数据
pausedDL	        种子已暂停，尚未完成下载
queuedDL	        队列已启用，种子已排队等待下载
stalledDL	        正在下载种子，但没有建立连接
checkingDL	        与检查相同，但种子尚未完成下载
forcedDL	        洪流被迫下载以忽略队列限制
checkingResumeData	在 qBt 启动时检查恢复数据
moving	            洪流正在转移到另一个位置
unknown	            未知状态
```

# 国外VPS 需要注意时区、系统编码
### - 设置上海时区 sudo timedatectl set-timezone Asia/ShangHai
### - 设置系统编码 apt-get install locales  dpkg-reconfigure locales  空格键选择en_US UTF-8、zh-CN UTF-8
