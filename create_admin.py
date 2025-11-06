from app import app, db
from app.models import User

with app.app_context():
    # 创建管理员用户
    admin = User(username='admin')
    admin.set_password('admin123')  # 设置密码为admin123
    
    db.session.add(admin)
    db.session.commit()
    
    print('管理员用户创建成功！用户名：admin，密码：admin123')