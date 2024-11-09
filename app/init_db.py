from app import app, db
from models import User
from datetime import datetime

def init_database():
    with app.app_context():
        # 删除所有表
        db.drop_all()
        print("已删除所有表！")
        
        # 创建所有表
        db.create_all()
        print("数据库表创建成功！")
        
        # 创建管理员账号
        admin = User(
            email='admin@microdev.cn',
            is_verified=True,
            is_admin=True,
            created_at=datetime.utcnow()
        )
        admin.set_password('666666')
        
        # 添加到数据库
        db.session.add(admin)
        db.session.commit()
        print("管理员账号创建成功！")

if __name__ == "__main__":
    init_database() 