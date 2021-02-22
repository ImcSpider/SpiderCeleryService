import subprocess
import shlex
import pytz
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import os
import json
import smtplib
from email.mime.text import MIMEText
import importlib
from apscheduler.schedulers.blocking import BlockingScheduler
from foo.helper import common

importlib.reload(sys)


def starts():
    command = shlex.split("python " + "main.py")
    res = subprocess.Popen(command)
    pid = res.pid
    while True:
        status = res.poll()
        if status is not None:
            break
    msg_from = '2850341698@qq.com'  # 发送方邮箱
    passwd = 'laaqmyfavrvadgdd'  # 填入发送方邮箱的授权码(填入自己的授权码，相当于邮箱密码)
    msg_to = ['729949301@qq.com', '2885176384@qq.com']  # 收件人邮箱

    subject = "WISH主账单及账单明细春节爬虫采集信息反馈"  # 主题
    # 获取失败店铺列表:
    cur_path = os.path.abspath(os.path.dirname(__file__))
    crawl_account_path = os.path.join(cur_path, 'spiderMsg', 'wish.txt')
    with open(crawl_account_path, 'r', encoding='utf-8') as fp:
        crawl_list = [x.strip() for x in fp.readlines()]
    store_list = list()
    failist = common.get_failed_spider()
    for msg in failist:
        item_msg = json.loads(msg)
        store_list.append(item_msg["browserName"])
    total_length = len(set(crawl_list))
    fail_length = len(set(store_list))
    success_length = total_length - fail_length
    content = "总任务数：{}  成功数： {}  失败数： {}  成功率： {}  失败店铺： {}".format(total_length, success_length, fail_length,
                                                                    success_length / total_length,
                                                                    ','.join(store_list))
    # 生成一个MIMEText对象（还有一些其它参数）
    msg = MIMEText(content)
    # 放入邮件主题
    msg['Subject'] = subject
    # 也可以这样传参
    # msg['Subject'] = Header(subject, 'utf-8')
    # 放入发件人
    msg['From'] = msg_from
    try:
        # 通过ssl方式发送，服务器地址，端口
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        # 登录到邮箱
        s.login(msg_from, passwd)
        # 发送邮件：发送方，收件方，要发送的消息
        for st in msg_to:
            msg['To'] = st
        s.sendmail(msg_from, msg_to, msg.as_string())
        print('成功')
    except Exception as e:
        print(e)
    sched.shutdown(wait=False)


if __name__ == "__main__":
    sched = BlockingScheduler()
    sched.add_job(starts, "date", run_date="2021-02-17 10:18`   `111111r54ty67p-0=[:00", misfire_grace_time=1800)
    sched.start()
