from flask_sqlalchemy import SQLAlchemy
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    course = db.Column(db.String(50), nullable=False)

class MealAttendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    attendance_date = db.Column(db.Date, default=date.today)
    breakfast = db.Column(db.Boolean, default=False)
    lunch = db.Column(db.Boolean, default=False)
    dinner = db.Column(db.Boolean, default=False)
    student = db.relationship('Student', backref='attendances')

class Menu(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    menu_date = db.Column(db.Date, nullable=False)
    breakfast_menu = db.Column(db.Text)
    lunch_menu = db.Column(db.Text)
    dinner_menu = db.Column(db.Text)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    bill_month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    total_amount = db.Column(db.Float, default=0.0)
    paid = db.Column(db.Boolean, default=False)
    student = db.relationship('Student', backref='bills')
