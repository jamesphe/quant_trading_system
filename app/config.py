import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 邮件配置 - 使用 QQ 邮箱
    MAIL_SERVER = 'smtp.qq.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = '108499115@qq.com'  # 替换为您的QQ邮箱
    MAIL_PASSWORD = 'hglnvlbuqjftbhgd'  # 替换为您的QQ邮箱授权码
    MAIL_DEFAULT_SENDER = '108499115@qq.com'  # 替换为您的QQ邮箱
    
    # MySQL
    SQLALCHEMY_DATABASE_URI = (
        'mysql://username:password@localhost/your_database_name'
    )

    # 或 PostgreSQL
    SQLALCHEMY_DATABASE_URI = (
        'postgresql://username:password@localhost/your_database_name'
    )