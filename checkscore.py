import base64
import sys
from bs4 import BeautifulSoup
import requests

import time

import json

import smtplib
from email.mime.text import MIMEText

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 变量设置
user_Account = ''  # 新教务系统学号
user_password = ''  # 新教务系统密码
recevie_email = ''  # 收取邮件的邮箱地址 eg:president@bupt.edu.cn
sender_email = ''  # 发送邮件的163邮箱地址 eg:1145141919810@163.com
sender_email_pass = ''  # 163邮箱的授权码

user_encode = str(base64.b64encode(bytes(user_Account, encoding='utf-8')), encoding='utf-8') + \
    '%%%' + str(base64.b64encode(bytes(user_password,
                                       encoding='utf-8')), encoding='utf-8')

try:
    with open('score.json', encoding='utf-8') as f:
        data = json.load(f)
except IOError:
    data = {'totalscore': '-1', 'resultarr': []}

changed = False

errortimes = 0


def checkscore():
    # 教务系统登录

    url = 'https://jwgl.bupt.edu.cn/jsxsd/'
    result = requests.get(url, verify=False)
    cookies = result.cookies

    url = 'https://jwgl.bupt.edu.cn/jsxsd/xk/LoginToXk'
    form_data = {
        'userAccount': user_Account,
        'userPassword': '',
        'encoded': user_encode
    }
    result = requests.post(url, cookies=cookies, data=form_data, verify=False)

    url = 'https://jwgl.bupt.edu.cn/jsxsd/kscj/cjcx_list'
    form_data = {'kksj': '', 'kcxz': '', 'kcmc': '', 'xsfs': 'all'}
    resultraw = requests.post(url,
                              data=form_data, cookies=cookies, verify=False)
    result = resultraw.text

    keyword = '所修总学分:'
    start = result.find(keyword)
    keyword = '绩点:'
    end = result.find(keyword)

    remainscore = result[start + 6: end].strip()

    soup = BeautifulSoup(result, features='html.parser')
    try:
        table = soup.select('#dataList')[0]
    except:
        print((time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
               'Results failed to obtain, may be no grades or cookies invalid, please update!').encode(encoding='utf-8'))
        sendemail('NULL', 'NULL', 'Please update the invalid cookies！', '')
        sys.exit(0)
    resultarr = []
    allrows = table.select('tr')
    for row in allrows:
        allcols = row.select('td')
        if (len(allcols) == 0):
            continue
        resultarr.append([])
        for col in allcols:
            resultarr[-1].append(col.text.strip())

    return remainscore, resultarr


def sendemail(remainscore, oldscore, title, answerstr):
    # 设置服务器所需信息
    # 163邮箱服务器地址
    mail_host = 'smtp.163.com'
    # 163用户名
    mail_user = sender_email
    # 密码(部分邮箱为授权码)
    mail_pass = sender_email_pass
    # 邮件发送方邮箱地址
    sender = sender_email
    # 邮件接受方邮箱地址，注意需要[]包裹，这意味着你可以写多个邮件地址群发
    receivers = [recevie_email]

    # 设置email信息
    # 邮件内容设置
    content = '新剩余学分为：' + remainscore + '，原剩余学分为：' + oldscore + answerstr
    message = MIMEText(content, 'plain', 'utf-8')
    # 邮件主题
    message['Subject'] = title
    # 发送方信息
    message['From'] = sender
    # 接受方信息
    message['To'] = receivers[0]

    # 登录并发送邮件
    try:
        smtpObj = smtplib.SMTP()
        # 连接到服务器
        smtpObj.connect(mail_host, 25)
        # 登录到服务器
        smtpObj.login(mail_user, mail_pass)
        # 发送
        smtpObj.sendmail(
            sender, receivers, message.as_string())
        # 退出
        smtpObj.quit()
        global changed
        print(time.strftime('%Y-%m-%d %H:%M:%S ',
                            time.localtime()) + 'Email has been sent!')
        if (title == '程序出现异常！！！！！！'):
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
                  'There are somthing wrong!!! Stop Monitor!!!!')
            changed = True
        else:
            changed = False
            data['totalscore'] = remainscore
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
                  'Current score has been updated to ' + data['totalscore'] + '. Continue monitor.')
    except smtplib.SMTPException as e:
        print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
              ' Email sending error', e)  # 打印错误


while changed == False:
    try:
        remainscore, resultarr = checkscore()
        if remainscore == data['totalscore']:
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
                  'Checked successfully, there is no change. Remain score is ' + remainscore + '.')
            changed = False
        else:
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()) +
                  'Checked successfully, there are some change! Remain score is ' + remainscore + '! Old score is ' + data['totalscore'])
            changed = True
            score_dict = {
                'totalscore': remainscore,
                'resultarr': resultarr
            }

            with open('score.json', 'w', encoding='utf-8') as json_file:
                json.dump(score_dict, json_file, ensure_ascii=False,
                          indent=4, separators=(',', ': '))

            answerstr = '\r\n\r\n以下课程有增加：\r\n'
            oldname = [x[3] for x in data['resultarr']]
            newname = [x[3] for x in resultarr]
            subject_changed = list(set(newname).difference(oldname))
            for x in subject_changed:
                for y in resultarr:
                    if (y[3] == x):
                        answerstr += y[3] + ': ' + y[5] + '\r\n'
            if data['totalscore'] != '-1':
                sendemail(remainscore, data['totalscore'], '成绩有更新', answerstr)
            else:
                changed = False
                print('First run.')
            data['totalscore'] = remainscore
            data['resultarr'] = resultarr
        time.sleep(10)
    except Exception as e:
        if errortimes < 2:
            errortimes = errortimes + 1
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()), e)
            print(time.strftime('%Y-%m-%d %H:%M:%S ',
                                time.localtime()) + 'Program is retrying...')
            time.sleep(10)
        else:
            sendemail('', '', '程序出现异常！！！！！！', '')
            print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime()), e)
