from flask import Flask, request
from openai import OpenAI
from traceback import format_exc
from datetime import datetime
from ollama import Client
from requests import post
from time import sleep, time, localtime
from json import loads, dumps
from threading import Thread
from queue import Queue
from random import randint, choice, uniform
from os import _exit
from re import sub, DOTALL
from emoji import emoji_list

power = True  # 电源
msg_queue = Queue()  # msg队列
chat_list = []  # 消息列表
sex_list = []  # 色色模式备份消息
role_system = {"role": "system", "content": open('role_setting.txt', 'r', encoding='utf-8').read()}  # 角色设定
sex_system = {"role": "system", "content": open('sese_setting.txt', 'r', encoding='utf-8').read()}  # 角色设定
sex_mode = False  # 色色
dnd = False  # 睡觉
sleep_time = 25200  # 睡眠时间
sleep_start_time = time()  # 开始睡觉
sleep_start_clock = [23, 0]  # 睡觉时间


########################################################################################################################
#
# 小组件
#

###########
# 日志记录 #
##########
def log(msg):
    # 日志记录
    open('AIE.log', 'a', encoding='utf-8').write(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{msg}\n')
    print(msg)
def plog(msg):
    # 如果批准上报
    if config.get('allow_post'):
        # 上报
        send_private_msg(msg)
    log(msg)

###########
# 文件读写 #
##########
def chat_io(read=False):
    global chat_list

    # 如果只是读取
    if read:
        # 读取加载配置文件
        try:
            tmp = loads(open('AIE_clst.json', 'r', encoding='utf-8').read())
            # 写入变量
            chat_list = tmp
        # 如果出错了（或者没有）
        except:
            # 不管
            chat_list = []
    # 如果是写入
    else:
        open('AIE_clst.json', 'w', encoding='utf-8').write(dumps(chat_list, indent=4, ensure_ascii=False))

###########
# 在线检测 #
##########
def monitor_status():
    global power

    def get_status():
        try:
            r = loads(post(url=f'http://127.0.0.1:{port}/get_status', data={}, timeout=3).text)
            if r['data']['online'] == True:
                return True
            else:
                return False
        except:
            return False

    notice = False
    while power:
        tmp = get_status()
        if tmp:
            if notice:
                plog('你老婆重新上线了.')
                notice = False
        else:
            if not notice:
                plog('你老婆掉线啦！')
                notice = True
        start = time()
        if power and (time() - start) < 10:
            sleep(0.1)

###########
# 消息发送 #
##########
def send_private_msg(msg):
    if msg:
        # 发送
        try:
            r = loads(post(
                url=f'http://127.0.0.1:{port}/send_private_msg', data={'user_id': target_id,'message': msg}, timeout=3
            ).text)
            # 如果发送不成功
            if r['status'] != 'ok':
                # 掉了？
                log(f'信息发送失败，信息：\"{msg}\"，返回结果：{r}')
        # 发不出去
        except:
            # 寄了？
            log('信息发送失败，请检查账号状态.')

###########
# 睡眠设置 #
##########
def sleep_set():
    global sleep_time
    global sleep_start_clock

    # 抽到失眠，且昨天没失眠
    if 1 <= randint(1, 10) <= 2 and sleep_time >= 21600:
        # 那就睡3-5小时
        sleep_time = randint(10800, 18000)
    # 如果抽到正常时间
    else:
        # 设置正常数字
        sleep_time = randint(21600, 32400)
    # 随机抽取一个睡觉时间
    sleep_start_clock = [choice([23, 0, 1, 2]), randint(0, 59)]

    log(f'设定睡眠{sleep_time},{sleep_start_clock}')

########################################################################################################################
#
# prompt IO处理
#

#########
# flask #
#########
def user_msg_io():
    app = Flask(__name__)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        # 传入队列
        msg_queue.put({'type': 'user', 'data': loads(request.get_data().decode('utf-8'))})
        return ''

    app.run(host='0.0.0.0', port=flask_port)

#########
# 指令集 #
#########
def shell(cmd):

    #########
    # 清除对话
    def reset_communicate(c):

        global role_system
        global sex_system
        global chat_list
        global sex_list
        global sex_mode

        log('root重置了系统.')
        # 重置所有项
        role_system = {"role": "system", "content": open('role_setting.txt', 'r', encoding='utf-8').read()}
        sex_system = {"role": "system", "content": open('sese_setting.txt', 'r', encoding='utf-8').read()}
        chat_list = []
        sex_list = []
        chat_io()
        sex_mode = False

        return '完成.'
    #########
    # 切换模式
    def switch_model(c):

        global sex_mode

        log('root切换了模式')
        sex_mode = not sex_mode
        return '1.'
    #########
    # 结束做爱
    def do_end(c):

        global sex_list

        # 重置对话
        sex_list = []
        # 切换模式
        switch_model(c)
        # 交流
        log(f'文爱结束')
        msg_queue.put(
            {'type': 'system', 'cmd': 'notice', 'notice': '（系统消息：你们刚刚经历了一场文爱.现在你们回归正常交流）'})
        return 'sex_end'
    #########
    # 关机维护
    def shutdown(c):

        global power

        log('root让关机')
        power = False
        return '再见喵~.'

    ### 指针 ###
    cmd_list = {
        '重置': [reset_communicate, '重置对话(更新角色文件)'],
        '切换': [switch_model, '切换普通模式/做爱模式'],
        '（色色结束）': [do_end, '结束色色对话'],
        '维护': [shutdown, '关闭机器人']
    }

    ### 解码 ###
    # 如果是帮助
    if cmd == 'help':
        tmp = ''
        # 打印
        for i in cmd_list:
            tmp += f'{i}: {cmd_list[i][1]}\n'
        # 返回
        return tmp
    # 如果不是
    else:
        # 读取指令
        try:
            cmd = cmd.split(' ')
            return cmd_list[cmd[0]][0](cmd)
        except:
            return None

########
# chat #
########
def chat():
    global sex_mode
    global dnd
    global sleep_start_time
    global tc

    #########
    # 删除标签
    def remove_think_tag(text):
        # 使用正则表达式移除<think>标签及其内容
        clean_text = sub(r'<think>.*?</think>', '', text, flags=DOTALL).strip()
        return clean_text
    ##########
    # 删除时间戳
    def remove_timestamp(text):
        # 正则表达式匹配 "YYYY-MM-DD HH:MM:SS" 格式的时间戳
        timestamp_pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]'

        # 使用re.sub()来替换匹配到的字符串为空字符串
        text_without_timestamp = sub(timestamp_pattern, '', text)

        return text_without_timestamp
    ###########
    # 删除emoji
    def remove_emoji(text):
        # 将字符串转换为emoji标记的列表
        emoji_chat = emoji_list(text)
        # 获取所有Emoji的字符位置
        emoji_chars = {e['emoji'] for e in emoji_chat}
        # 构建新字符串
        return ''.join(char for char in text if char not in emoji_chars)
    ##########
    # 相似度比较
    def is_similar(str1, str2):

        # 如果有一个字符串为空，直接返回False
        if not str1 or not str2:
            return False

        # 确定哪个是短句，哪个是长句
        short, long = (str1, str2) if len(str1) < len(str2) else (str2, str1)

        # 计算短句中有多少字在长句中出现
        match_count = 0
        for char in short:
            if char in long:
                match_count += 1

        # 计算相似度（匹配字符数除以短句长度）
        similarity = match_count / len(short)

        return similarity  # 相似度
    ################
    # deep_sex本地推理
    def sex_local(msg):

        generation_config = {
            "temperature": 0.4,
            "top_p": 0.6,
            "repetition_penalty": 1.17,
            "max_new_tokens": 1536,
            "do_sample": True
        }

        client = Client(host=f'http://127.0.0.1:{config.get("ollama")[1]}')
        # 尝试连接推理
        try:
            content = client.chat(model='deepsex', messages=msg, options=generation_config)
            return remove_think_tag(content.message.content)
        # 如果推理失败
        except:
            plog('ollama出错.')
            return None
    #########
    # 本地推理
    def chat_local(msg):

        generation_config = {
            "temperature": 1
        }

        client = Client(host=f'http://127.0.0.1:{config.get("ollama")[1]}')
        # 尝试连接推理
        try:
            content = client.chat(model='deepseek-r1:14b', messages=msg, options=generation_config)
            return remove_think_tag(content.message.content)
        # 如果推理失败
        except:
            # 出错
            plog('ollama出错.')
            return None

    ### 色色模式 ###
    if sex_mode:

        chat_cache = [sex_system]

        ### # 拼接消息 ###
        for i in sex_list:
            # 如果类型和列表-1对应
            if i['role'] == chat_cache[-1]['role']:
                # 合并添加
                chat_cache[-1]['content'] += f'\\{i["msg"]}'
            # 如果不对应
            else:
                # 创建
                chat_cache.append({'role': i['role'], 'content': i['msg']})

        ### # 对话 ###
        while True:
            result = sex_local(chat_cache)

            # 对话重复检测
            similar = False
            for i in chat_cache:
                # 计算相似度
                similar_percent = is_similar(result, i.get('content'))
                # 如果相似度大于80%
                if similar_percent >= 0.8:
                    tmp = i.get('content')
                    log(f'"{result}" 和 "{tmp}" 的相似度为{similar_percent}，重新生成.')
                    # 汇报
                    similar = True
                    break
            # 如果重复了
            if similar:
                # 重新生成
                continue
            else:
                # 退出
                break
        # 如果有料
        if result:
            # 分段输出
            for i in result.split('\\'):
                # 过滤
                i = remove_timestamp(i)
                # 字词延迟
                sleep(len(i) * 0.5)
                # 发送
                msg_queue.put({'type': 'assistant', 'data': i})
        # 如果为空
        else:
            # 删除user字段
            while len(sex_list) > 0:
                if sex_list[-1]['role'] == 'user':
                    # 删除
                    del sex_list[-1]
                else:
                    break

    ### 正常模式 ###
    else:

        chat_cache = [role_system]

        ### # 拼接消息 ###
        for i in chat_list:
            # 如果类型和列表-1对应
            if i['role'] == chat_cache[-1]['role']:
                # 合并添加
                chat_cache[-1]['content'] += f'\\{i["msg"]}'
            # 如果不对应
            else:
                # 创建
                chat_cache.append({'role': i['role'], 'content': i['msg']})

        ### # 对话 ###
        try:
            log('在线生成.')
            result = OpenAI(api_key=api_key, base_url=api_host).chat.completions.create(
                model=api_model, messages=chat_cache, stream=False).choices[0].message.content
        # 对话失败
        except Exception as e:
            # 如果要调用本地模型
            if config.get('ollama')[0]:
                # 调用本地模型
                log('在线生成出错，开始本地生成.')
                result = chat_local(chat_list)
            # 如果不需要
            else:
                plog(f'在线生成出错：{e}')
                result = None
        # 如果输出不为空
        if result:
            # 如果是色色
            if result == 'use_sex':
                # 切换指示器
                log('色色！')
                sex_mode = True
                # 处理交流表
                sex_list.append({
                    'role': 'user',
                    'msg': chat_cache[-1]["content"],
                })
                # 运行
                chat()
            # 如果是睡觉
            elif result == 'sleep':
                # 发送
                msg_queue.put({'type': 'system', 'cmd': 'sleep'})
            # 如果不是
            else:
                # 过滤
                result = remove_emoji(result)
                # 分段输出
                for i in result.split('\\'):

                    ### ## 过滤 ###
                    i = remove_timestamp(i)

                    # 排除提示词
                    if i not in ['use_sex', 'sleep']:
                        # 字词延迟
                        sleep_count = 0
                        for e in list(i):
                            sleep_count += uniform(0.5, 2)
                        sleep(sleep_count)
                        # 发送
                        msg_queue.put({'type': 'assistant', 'data': i})
                        # 停顿
                        sleep(uniform(1, 3))
        # 如果为空
        else:
            # 删除user字段
            while len(chat_list) > 0:
                if chat_list[-1]['role'] == 'user':
                    # 删除
                    del chat_list[-1]
                else:
                    break

    ### 刷新线程 ###
    tc = Thread(target=chat)

########################################################################################################################
# 主程序 #
########
def aie_main():

    ### 变量定义 ###
    global power
    global dnd
    global sleep_start_time
    global sleep_time
    global sex_mode
    global tc

    tc = Thread(target=chat)

    user_time = time()  # 用户最后一次发言
    chat_time = randint(15, 30)  # 缓存超时计时器
    user_alive = True  # 理我呜~
    user_alive_time = randint(10800, 18000)  # 用户限制超时计时器
    chat_io(True)  # 读取对话列表

    ### 启动组件线程 ###
    sleep_set()
    Thread(target=user_msg_io).start()
    tm = Thread(target=monitor_status)
    tm.start()

    log('AIQ启动')

    ### 消息循环 ###
    while power:
        # 接收消息
        try:
            data = msg_queue.get(False)
        # 如果没有
        except:

            if len(chat_list) > 0 and not sex_mode:

                ### # 列表处理 ###
                # 如果列表超过2048句话 或 开头的是assistant
                while len(chat_list) >= 2048 or chat_list[0]['role'] == 'assistant':
                    # 删除
                    del chat_list[0]

                ### # 检测发送 ###
                # 如果当前时间超过阈值 且 最后的语句为user 且 我没睡觉和色色
                if (time() - user_time > chat_time and chat_list[-1]['role'] == 'user'
                ) and not (dnd or tc.is_alive()):
                    # 重设计时器
                    chat_time = randint(15, 30)
                    # chat
                    tc.start()

            ### # 色色模式 ###
            if sex_mode and len(sex_list) > 0:
                # 如果当前时间超过阈值 且 最后的语句为user
                if (time() - user_time > 52 and sex_list[-1]['role'] == 'user'
                ) and not tc.is_alive():
                    # chat
                    tc.start()

            ### # 好困 ###
            # 如果到点睡觉了 且 还没睡 且 不在做爱
            if (localtime().tm_hour == sleep_start_clock[0] and
                localtime().tm_min == sleep_start_clock[1]) and not (dnd or sex_mode):
                log('到点睡觉了')

                # 防止重复报错
                sleep_start_clock[0] = 22
                # 发送系统消息
                msg_queue.put({'type': 'system', 'cmd': 'notice', 'notice': '（系统消息：你太困了）'})

            ### # 睡觉 ###
            # 如果睡着了 且 睡够了
            if dnd and time() - sleep_start_time >= sleep_time:
                log('醒了.')

                # 苏醒
                dnd = False
                # 重设时间
                sleep_set()
                user_time = time()
                # 发送系统消息
                msg_queue.put({'type': 'system', 'cmd': 'notice', 'notice': '（系统消息：你睡醒了，此时对方可能还没醒。）'})

            ### # 超时检测 ###
            # 如果超过阈值 且 不在睡觉和色色
            if time() - user_time > user_alive_time and user_alive and not (dnd or sex_mode):
                user_alive = False
                user_alive_time = randint(10800, 18000)
                # 发送系统消息
                log(f'人不见了.')
                msg_queue.put({'type': 'system', 'cmd': 'notice', 'notice': '（系统消息：对方好久没发言了）'})

            ### # 防过载 ###
            sleep(0.1)
        # 接收到了
        else:

            # 在线
            user_alive = True

            ### # system消息 ###
            if data['type'] == 'system':
                # 如果要睡觉了
                if data['cmd'] == 'sleep':
                    log('进入睡觉模式力')
                    # 设置
                    dnd = True
                    sleep_start_time = time()
                    # 添加缓冲
                    chat_list.append({
                        'role': 'assistant',
                        'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]晚安~'
                    })
                    chat_io()
                    # 发送
                    send_private_msg('晚安~')
                # 如果是系统消息
                elif data['cmd'] == 'notice':
                    # 添加缓冲
                    chat_list.append({
                        'role': 'user',
                        'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{data["notice"]}'
                    })
                    chat_io()
                    # 刷新用时
                    user_time = time()

            ### # user消息 ###
            elif data['type'] == 'user':

                ### ## 解码缓冲 ###
                data = data['data']

                user_id = data.get('user_id')
                message_id = data.get('message_id')
                message_type = data.get('message_type')
                notice_type = data.get('notice_type')
                raw_message = data.get('raw_message')
                message = data.get('message')

                ### ## 检查消息类型 ###
                # 如果是私聊
                if message_type == 'private' and user_id == target_id:

                    # 检查是否为纯文字
                    if len(message) == 1 and raw_message[0] != '[':

                        log(f'用户输入: {raw_message}')

                        # 辨别是否是指令
                        tmp = shell(raw_message)
                        # 如果是指令 且 不是色色提示词
                        if tmp and tmp != 'sex_end':
                            # 发送结果
                            send_private_msg(tmp)
                        # 如果不是
                        else:
                            # 色色模式
                            if sex_mode:
                                # 添加缓冲
                                sex_list.append({
                                    'role': 'user',
                                    'msg_id': message_id,
                                    'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{raw_message}'
                                })
                                # 刷新用时
                                user_time = time()
                            # 正常模式
                            else:
                                # 添加缓冲
                                chat_list.append({
                                    'role': 'user',
                                    'msg_id': message_id,
                                    'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{raw_message}'
                                })
                                chat_io()
                                # 刷新用时
                                user_time = time()
                    # 如果是回复
                    elif len(message) == 2:
                        if message[0].get('type') == 'reply' and message[1].get('type') == 'text':
                            # 加载原文
                            raw_message = message[1].get('data').get('text')
                            # 色色模式
                            if sex_mode:

                                log(f'用户输入: {raw_message}')

                                # 添加缓冲
                                sex_list.append({
                                    'role': 'user',
                                    'msg_id': message_id,
                                    'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{raw_message}'
                                })
                                # 刷新用时
                                user_time = time()
                            # 正常模式
                            else:

                                # 获取原消息
                                try:
                                    tmp = loads(post(f'http://127.0.0.1:{port}/get_msg', dumps({
                                        'message_id': message[0].get('data').get('id')
                                    })).text)
                                    # 如果获取成功
                                    if tmp['status'] == 'ok':
                                        # raw_msg添加前缀
                                        raw_message = '{回复你的消息:"' + tmp["data"][
                                            "raw_message"] + '"}' + raw_message
                                # 获取失败
                                except:
                                    # 不管
                                    pass

                                log(f'用户输入: {raw_message}')

                                # 添加缓冲
                                chat_list.append({
                                    'role': 'user',
                                    'msg_id': message_id,
                                    'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{raw_message}'
                                })
                                chat_io()
                                # 刷新用时
                                user_time = time()
                # 如果是撤回
                elif notice_type == 'friend_recall' and user_id == target_id:
                    # 匹配删除
                    try:
                        for i in range(len(chat_list)):
                            if chat_list[i].get('msg_id') == message_id:
                                log(f'用户撤回: {chat_list[i]["msg"]}')
                                del chat_list[i]
                                break
                        chat_io()
                    # 找不到
                    except:
                        log(f'信息撤回失败，id为{message_id}')
                        # 不管
                        pass
                    # 刷新用时
                    user_time = time()

            ### # assistant消息 ###
            elif data['type'] == 'assistant':

                log(f'模型输出: {data["data"]}')

                # 如果是色色模式
                if sex_mode:
                    # 添加缓冲
                    sex_list.append({
                        'role': 'assistant',
                        'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{data["data"]}'
                    })
                    # 发送
                    send_private_msg(data['data'])
                # 如果不是
                else:
                    # 添加缓冲
                    chat_list.append({
                        'role': 'assistant',
                        'msg': f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]{data["data"]}'
                    })
                    chat_io()
                    # 发送
                    send_private_msg(data['data'])

    ### 关机收尾 ###
    chat_io()
    log('等待轮询监视器结束')
    tm.join()
    log('关机')
    _exit(0)

########################################################################################################################
def aie_main_start(tmp):
    
    global power, port, flask_port, target_id, api_host, api_model, api_key, config
    
    # 加载环境变量
    config = tmp

    port = config['front_port']
    flask_port = config['back_port']
    target_id = config['communicate_user']
    api_host = config['chat'][0]
    api_model = config['chat'][1]
    api_key = config['chat'][2]
    
    # 运行
    try:
        aie_main()
    except KeyboardInterrupt:
        log('用户自行退出')
    except:
        plog(f'出错了,未知错误：{format_exc()}')
        power = False
        _exit(1)