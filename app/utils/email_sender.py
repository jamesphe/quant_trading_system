from flask_mail import Mail, Message
import random
import string
from datetime import datetime, timedelta

mail = Mail()

def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(app, to_email, verification_code):
    """发送验证码邮件"""
    with app.app_context():
        msg = Message(
            '验证您的账号',
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        msg.body = f'''您好！
        
您的验证码是：{verification_code}

该验证码将在10分钟内有效。

如果这不是您的操作，请忽略此邮件。
'''
        mail.send(msg) 