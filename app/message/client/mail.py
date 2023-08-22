import smtplib
from email.mime.text import MIMEText

import log
from app.message.client._base import _IMessageClient
from app.utils import ExceptionUtils


class Mail(_IMessageClient):
    schema = "mail"

    def __init__(self, config):
        self._client_config = config
        self.init_config()

    def init_config(self):
        self.mail_server=self._client_config.get('mail_server') # 邮件服务器
        self.mail_pass=self._client_config.get('mail_pass') # key
        self.mail_sender=self._client_config.get('mail_sender') # 发件人
        self.mail_receiver=self._client_config.get('mail_receiver') # 收件人

    @classmethod
    def match(cls, ctype):
        return True if ctype == cls.schema else False

    def send_msg(self, title, text="", image="", url="", user_id=None):
        """
        邮件消息发送入口，支持文本、图片、链接跳转、指定发送对象
        :param title: 消息标题
        :param text: 消息内容
        :param image: 图片地址
        :param url: 点击消息跳转URL
        :param user_id: 消息发送对象的ID，为空则发给所有人
        :return: 发送状态，错误信息
        """
        message = MIMEText(text, 'plain', 'utf-8')  # 内容, 格式, 编码
        message['From'] = "{}".format(self.mail_sender)
        message['To'] = self.mail_receiver
        message['Subject'] = title

        try:
            smtpObj = smtplib.SMTP_SSL(self.mail_server, 465)  # 启用SSL发信, 端口一般是465
            smtpObj.login(self.mail_sender, self.mail_pass)  # 登录验证
            smtpObj.sendmail(self.mail_sender, self.mail_receiver, message.as_string())  # 发送
            log.info("邮件发送成功")
            return True, ""
        except smtplib.SMTPException as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)

    def send_list_msg(self, medias: list, user_id="", title="", **kwargs):
        """
        发送列表类消息
        """
        try:
            return self.send_msg(title="列表消息",text="mail.send_list_msg发送的消息，未实现具体逻辑")

        except Exception as msg_e:
            ExceptionUtils.exception_traceback(msg_e)
            return False, str(msg_e)
