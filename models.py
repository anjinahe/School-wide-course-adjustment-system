from extensions import db
import time

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'teacher' or 'screen'
    courses = db.relationship('Course', backref='teacher', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(10), nullable=False)  # 班级编号，如'101'
    time_slot = db.Column(db.String(20), nullable=False)  # 时间段，如'上午1'
    subject = db.Column(db.String(20), nullable=False)  # 课程名称
    teacher_id = db.Column(db.String(20), db.ForeignKey('user.username'), nullable=False)
    adjustments = db.relationship('AdjustmentRequest', backref='course', lazy=True)
    
    def __repr__(self):
        return f'<Course {self.class_name} {self.time_slot} {self.subject}>'

class AdjustmentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    from_teacher_id = db.Column(db.String(20), db.ForeignKey('user.username'), nullable=False)
    to_teacher_id = db.Column(db.String(20), db.ForeignKey('user.username'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.Float, default=time.time)
    approved_at = db.Column(db.Float)
    
    # 关联关系
    from_teacher = db.relationship('User', foreign_keys=[from_teacher_id])
    to_teacher = db.relationship('User', foreign_keys=[to_teacher_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'from_teacher': self.from_teacher_id,
            'to_teacher': self.to_teacher_id,
            'status': self.status,
            'created_at': self.created_at,
            'approved_at': self.approved_at
        }
    
    def __repr__(self):
        return f'<AdjustmentRequest {self.id} {self.status}>'