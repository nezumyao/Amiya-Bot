import os
import time
import traceback

from core import AmiyaBot, Chain
from core.util import log
from core.util.common import insert_zero, TimeRecorder
from core.config import func_setting
from core.util.imageCreator import temp_dir
from core.database.models import User, Upload, Message, Intellect, GroupSetting

from dataSource.sourceBank import SourceBank
from handlers.functions.weibo import Weibo

weibo = Weibo()


class AutomaticEvents:
    def __init__(self, bot: AmiyaBot):
        self.bot = bot
        self.times = 0

    def exec_all_tasks(self, times):
        setting = func_setting().weiboSetting

        self.times += 1
        if self.times >= setting.checkRate / 30 and setting.weiboAutoPush:
            self.times = 0
            self.push_new_weibo()

        self.intellect_full_alarm()
        self.maintain()

    def maintain(self):
        now = time.localtime(time.time())
        hour = now.tm_hour
        mint = now.tm_min
        try:
            if hour == 4 and mint == 0:
                bot_maintain(self.bot)
        except Exception as e:
            log.error(traceback.format_exc())
            self.bot.send_to_admin(f'维护发生错误：{repr(e)}')

    def push_new_weibo(self):
        try:
            ignore = SourceBank.get_ignore()
            new_id = weibo.requests_content(0, only_id=True)
            group_list = [item['group_id'] for item in self.bot.http.get_group_list()]
            enables_list = [int(item.group_id) for item in GroupSetting.select().where(GroupSetting.send_weibo == 1)]

            record = ignore['weibo_download']
            target = list(
                set(group_list).intersection(
                    set(enables_list)
                )
            )

            if not isinstance(new_id, str) or new_id in ignore['weibo_download']:
                return False

            record.append(new_id)
            record = record[-5:] if len(record) >= 5 else record
            ignore['weibo_download'] = record
            SourceBank.save_ignore(ignore)

            self.bot.send_to_admin(f'开始推送微博:\n{new_id}\n目标群数: {len(target)}')

            time_rec = TimeRecorder()
            result, detail_url, pics_list = weibo.requests_content(0)

            for group_id in target:
                with self.bot.send_custom_message(group_id=group_id) as reply:
                    reply: Chain
                    reply.text(detail_url + '\n')
                    reply.text(result)
                    if pics_list:
                        for pic in pics_list:
                            reply.image(pic)
                time.sleep(0.5)

            self.bot.send_to_admin(f'微博推送结束，耗时{time_rec.total()}')

        except IndexError:
            pass
        except Exception as e:
            log.error(traceback.format_exc())
            self.bot.send_to_admin(f'微博推送发生错误：{repr(e)}')

    def intellect_full_alarm(self):
        try:
            conditions = (Intellect.status == 0, Intellect.full_time <= int(time.time()))
            results = Intellect.select().where(*conditions)
            if results:
                Intellect.update(status=1).where(*conditions).execute()
                for item in results:
                    item: Intellect
                    text = f'博士！博士！您的理智已经满{item.full_num}了，快点上线查看吧～'
                    with self.bot.send_custom_message(item.user_id, item.group_id, item.message_type) as reply:
                        reply: Chain
                        reply.at().text(text)

        except Exception as e:
            log.error(traceback.format_exc())
            self.bot.send_to_admin(f'理智提醒发生错误：{repr(e)}')


def bot_maintain(bot: AmiyaBot, force=False):
    now = time.localtime(time.time())
    record = maintain_record()
    now_time = int(f'{now.tm_year}{insert_zero(now.tm_mon)}{insert_zero(now.tm_mday)}')

    if record < now_time or force:
        # 重置签到和心情值
        User.update(sign_in=0, user_mood=15).execute()

        # 清空图片记录及一个月前的消息记录
        last_time = int(time.time()) - 31 * 86400
        Message.delete().where(Message.msg_time <= last_time).execute()
        Upload.truncate_table()

        # 清除缓存
        log.clean_log(3, extra=[temp_dir])

        # 记录维护时间
        maintain_record(str(now_time))

        msg = f'维护完成，最后维护时间：{now_time}'
        bot.send_to_admin(msg)

        return msg


def maintain_record(date: str = None):
    rc_path = 'log/maintainRecord.txt'

    if date:
        with open(rc_path, mode='w+') as rc:
            rc.write(date)
            return True

    if os.path.exists(rc_path):
        with open(rc_path, mode='r+') as rc:
            return int(rc.read())

    return 0
