from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from extensions import db

# 加载环境变量
load_dotenv()

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///school_schedule.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)
CORS(app)

# 导入模型
from models import User, Course, AdjustmentRequest

# 全局变量存储当前登录用户
current_user = None

# 路由 - 登录页面
@app.route('/', methods=['GET', 'POST'])
def login():
    global current_user
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        # 查找用户
        user = User.query.filter_by(username=user_id).first()
        if user:
            current_user = user
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('screen_display', class_id=user_id))
        return render_template('login.html', error='用户不存在')
    return render_template('login.html')

# 路由 - 教师仪表盘
@app.route('/teacher/dashboard')
def teacher_dashboard():
    if not current_user or current_user.role != 'teacher':
        return redirect(url_for('login'))
    # 获取教师的课程
    courses = Course.query.filter_by(teacher_id=current_user.username).all()
    # 获取其他教师
    other_teachers = User.query.filter_by(role='teacher').filter(User.username != current_user.username).all()
    return render_template('teacher_dashboard.html', courses=courses, other_teachers=other_teachers)

# 路由 - 班级大屏显示
@app.route('/screen/<class_id>')
def screen_display(class_id):
    # 验证班级ID格式
    if not class_id or len(class_id) < 2:
        return redirect(url_for('login'))
    return render_template('screen_display.html', class_id=class_id)

# API - 获取班级课程
@app.route('/api/class/<class_id>/courses')
def get_class_courses(class_id):
    courses = Course.query.filter_by(class_name=class_id).all()
    result = []
    for course in courses:
        # 检查是否有调课申请
        adjustment = AdjustmentRequest.query.filter_by(
            course_id=course.id, status='approved'
        ).order_by(AdjustmentRequest.approved_at.desc()).first()
        
        course_data = {
            'id': course.id,
            'time_slot': course.time_slot,
            'subject': course.subject,
            'original_teacher': course.teacher.username,
            'current_teacher': adjustment.new_teacher.username if adjustment else course.teacher.username,
            'adjustment': adjustment.to_dict() if adjustment else None
        }
        result.append(course_data)
    return jsonify(result)

# API - 提交调课申请
@app.route('/api/adjustment/request', methods=['POST'])
def submit_adjustment():
    if not current_user or current_user.role != 'teacher':
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    data = request.json
    course_id = data.get('course_id')
    target_teacher_id = data.get('target_teacher_id')
    
    # 验证课程是否存在且属于当前教师
    course = Course.query.get(course_id)
    if not course or course.teacher_id != current_user.username:
        return jsonify({'status': 'error', 'message': '课程不存在或无权操作'}), 400
    
    # 检查目标教师是否存在
    target_teacher = User.query.filter_by(username=target_teacher_id, role='teacher').first()
    if not target_teacher:
        return jsonify({'status': 'error', 'message': '目标教师不存在'}), 400
    
    # 检查时间冲突
    # (简化版冲突检查，实际应用需更复杂逻辑)
    
    # 创建调课申请
    new_request = AdjustmentRequest(
        course_id=course_id,
        from_teacher_id=current_user.username,
        to_teacher_id=target_teacher_id,
        status='pending'
    )
    
    db.session.add(new_request)
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': '调课申请已提交', 'request_id': new_request.id})

# API - 获取教师的调课申请
@app.route('/api/teacher/adjustments')
def get_teacher_adjustments():
    if not current_user or current_user.role != 'teacher':
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    # 获取收到的申请
    received_requests = AdjustmentRequest.query.filter_by(
        to_teacher_id=current_user.username
    ).all()
    
    # 获取发送的申请
    sent_requests = AdjustmentRequest.query.filter_by(
        from_teacher_id=current_user.username
    ).all()
    
    return jsonify({
        'received': [req.to_dict() for req in received_requests],
        'sent': [req.to_dict() for req in sent_requests]
    })

# API - 处理调课申请
@app.route('/api/adjustment/<request_id>/handle', methods=['POST'])
def handle_adjustment(request_id):
    if not current_user or current_user.role != 'teacher':
        return jsonify({'status': 'error', 'message': '未授权'}), 401
    
    data = request.json
    action = data.get('action')  # 'approve' or 'reject'
    
    adjustment = AdjustmentRequest.query.get(request_id)
    if not adjustment or adjustment.to_teacher_id != current_user.username:
        return jsonify({'status': 'error', 'message': '申请不存在或无权操作'}), 400
    
    if adjustment.status != 'pending':
        return jsonify({'status': 'error', 'message': '申请已处理'}), 400
    
    adjustment.status = 'approved' if action == 'approve' else 'rejected'
    adjustment.approved_at = time.time() if action == 'approve' else None
    
    db.session.commit()
    
    return jsonify({'status': 'success', 'message': '申请已' + ('批准' if action == 'approve' else '拒绝')})

# 初始化数据库
@app.before_first_request
def initialize_database():
    db.create_all()
    # 检查是否已有数据
    if User.query.count() == 0:
        # 创建教师用户
        for i in range(1, 37):
            teacher_id = f'qfc{i:02d}'
            user = User(username=teacher_id, role='teacher')
            db.session.add(user)
        
        # 创建班级大屏用户
        for grade in range(1, 7):
            for class_num in range(1, 6):
                class_id = f'{grade}{class_num:02d}'
                user = User(username=class_id, role='screen')
                db.session.add(user)
        
        # 提交用户数据
        db.session.commit()

        # 初始化课程数据
        # 一年级课程
        grade1_classes = ['101', '102', '103', '104', '105']
        grade1_courses = [
            ['上午1', ['YuWen(qfc01)', 'ShuXue(qfc02)', 'YingYu(qfc03)', 'TiYu(qfc04)', 'MeiShu(qfc05)']],
            ['上午2', ['ShuXue(qfc02)', 'YuWen(qfc01)', 'TiYu(qfc04)', 'YingYu(qfc03)', 'YinYue(qfc06)']],
            ['下午1', ['YingYu(qfc03)', 'MeiShu(qfc05)', 'ShuXue(qfc02)', 'YinYue(qfc06)', 'YuWen(qfc01)']],
            ['下午2', ['TiYu(qfc04)', 'YinYue(qfc06)', 'MeiShu(qfc05)', 'YuWen(qfc01)', 'ShuXue(qfc02)']]
        ]
        
        # 二年级课程
        grade2_classes = ['201', '202', '203', '204', '205']
        grade2_courses = [
            ['上午1', ['YuWen(qfc07)', 'ShuXue(qfc08)', 'YingYu(qfc09)', 'TiYu(qfc10)', 'MeiShu(qfc11)']],
            ['上午2', ['ShuXue(qfc08)', 'YuWen(qfc07)', 'TiYu(qfc10)', 'YingYu(qfc09)', 'YinYue(qfc12)']],
            ['下午1', ['YingYu(qfc09)', 'MeiShu(qfc11)', 'ShuXue(qfc08)', 'YinYue(qfc12)', 'YuWen(qfc07)']],
            ['下午2', ['TiYu(qfc10)', 'YinYue(qfc12)', 'MeiShu(qfc11)', 'YuWen(qfc07)', 'ShuXue(qfc08)']]
        ]
        
        # 三年级课程
        grade3_classes = ['301', '302', '303', '304', '305']
        grade3_courses = [
            ['上午1', ['YuWen(qfc13)', 'ShuXue(qfc14)', 'YingYu(qfc15)', 'TiYu(qfc16)', 'KeXue(qfc17)']],
            ['上午2', ['ShuXue(qfc14)', 'YuWen(qfc13)', 'TiYu(qfc16)', 'KeXue(qfc17)', 'YinYue(qfc18)']],
            ['下午1', ['YingYu(qfc15)', 'KeXue(qfc17)', 'ShuXue(qfc14)', 'YinYue(qfc18)', 'YuWen(qfc13)']],
            ['下午2', ['TiYu(qfc16)', 'YinYue(qfc18)', 'KeXue(qfc17)', 'YuWen(qfc13)', 'ShuXue(qfc14)']]
        ]
        
        # 四年级课程
        grade4_classes = ['401', '402', '403', '404', '405']
        grade4_courses = [
            ['上午1', ['YuWen(qfc19)', 'ShuXue(qfc20)', 'YingYu(qfc21)', 'TiYu(qfc22)', 'KeXue(qfc23)']],
            ['上午2', ['ShuXue(qfc20)', 'YuWen(qfc19)', 'TiYu(qfc22)', 'KeXue(qfc23)', 'DeFa(qfc24)']],
            ['下午1', ['YingYu(qfc21)', 'KeXue(qfc23)', 'ShuXue(qfc20)', 'DeFa(qfc24)', 'YuWen(qfc19)']],
            ['下午2', ['TiYu(qfc22)', 'DeFa(qfc24)', 'KeXue(qfc23)', 'YuWen(qfc19)', 'ShuXue(qfc20)']]
        ]
        
        # 五年级课程
        grade5_classes = ['501', '502', '503', '504', '505']
        grade5_courses = [
            ['上午1', ['YuWen(qfc25)', 'ShuXue(qfc26)', 'YingYu(qfc27)', 'TiYu(qfc28)', 'KeXue(qfc29)']],
            ['上午2', ['ShuXue(qfc26)', 'YuWen(qfc25)', 'TiYu(qfc28)', 'KeXue(qfc29)', 'DeFa(qfc30)']],
            ['下午1', ['YingYu(qfc27)', 'KeXue(qfc29)', 'ShuXue(qfc26)', 'DeFa(qfc30)', 'YuWen(qfc25)']],
            ['下午2', ['TiYu(qfc28)', 'DeFa(qfc30)', 'KeXue(qfc29)', 'YuWen(qfc25)', 'ShuXue(qfc26)']]
        ]
        
        # 六年级课程
        grade6_classes = ['601', '602', '603', '604', '605']
        grade6_courses = [
            ['上午1', ['YuWen(qfc31)', 'ShuXue(qfc32)', 'YingYu(qfc33)', 'TiYu(qfc34)', 'KeXue(qfc35)']],
            ['上午2', ['ShuXue(qfc32)', 'YuWen(qfc31)', 'TiYu(qfc34)', 'KeXue(qfc35)', 'DeFa(qfc36)']],
            ['下午1', ['YingYu(qfc33)', 'KeXue(qfc35)', 'ShuXue(qfc32)', 'DeFa(qfc36)', 'YuWen(qfc31)']],
            ['下午2', ['TiYu(qfc34)', 'DeFa(qfc36)', 'KeXue(qfc35)', 'YuWen(qfc31)', 'ShuXue(qfc32)']]
        ]
        
        # 辅助函数：添加课程数据
        def add_courses(class_list, course_data):
            for i, class_id in enumerate(class_list):
                for time_slot, subjects in course_data:
                    if i < len(subjects):
                        subject_info = subjects[i]
                        # 解析课程名称和教师ID
                        subject_name = subject_info.split('(')[0]
                        teacher_id = subject_info.split('(')[1].replace(')', '')
                        
                        # 创建课程记录
                        course = Course(
                            class_name=class_id,
                            time_slot=time_slot,
                            subject=subject_name,
                            teacher_id=teacher_id
                        )
                        db.session.add(course)
        
        # 添加各年级课程
        add_courses(grade1_classes, grade1_courses)
        add_courses(grade2_classes, grade2_courses)
        add_courses(grade3_classes, grade3_courses)
        add_courses(grade4_classes, grade4_courses)
        add_courses(grade5_classes, grade5_courses)
        add_courses(grade6_classes, grade6_courses)
        
        # 提交课程数据
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)