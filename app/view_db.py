from app import app
from models import db, User
from tabulate import tabulate

def view_database(email=None):
    with app.app_context():
        if email:
            # 查询特定用户
            user = User.query.filter_by(email=email).first()
            if user:
                user_data = [[
                    user.id,
                    user.email,
                    '已验证' if user.is_verified else '未验证',
                    '是' if user.is_admin else '否',
                    user.verification_code,
                    user.verification_code_expires,
                    user.created_at
                ]]
                headers = ['ID', '邮箱', '验证状态', '管理员', '验证码', '验证码过期时间', '创建时间']
                print(f"\n用户 {email} 的数据:")
                print(tabulate(user_data, headers=headers, tablefmt='grid'))
            else:
                print(f"\n未找到邮箱为 {email} 的用户")
        else:
            # 获取所有用户
            users = User.query.all()
            user_data = []
            for user in users:
                user_data.append([
                    user.id,
                    user.email,
                    '已验证' if user.is_verified else '未验证',
                    '是' if user.is_admin else '否',
                    user.verification_code,
                    user.verification_code_expires,
                    user.created_at
                ])
            
            headers = ['ID', '邮箱', '验证状态', '管理员', '验证码', '验证码过期时间', '创建时间']
            print("\n所有用户数据:")
            print(tabulate(user_data, headers=headers, tablefmt='grid'))
            print(f"\n总用户数: {len(users)}")

if __name__ == "__main__":
    import sys
    email = sys.argv[1] if len(sys.argv) > 1 else None
    view_database(email) 