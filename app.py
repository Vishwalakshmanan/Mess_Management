from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length
from database import db, Admin, Student, MealAttendance, Menu, Bill
from datetime import date, datetime, timedelta
import calendar
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mess.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class StudentForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    room_number = StringField('Room Number', validators=[DataRequired()])
    course = StringField('Course', validators=[DataRequired()])
    submit = SubmitField('Add Student')

class MealForm(FlaskForm):
    student_id = SelectField('Student', coerce=int)
    breakfast = BooleanField('Breakfast')
    lunch = BooleanField('Lunch')
    dinner = BooleanField('Dinner')
    submit = SubmitField('Record Meal')

class MenuForm(FlaskForm):
    menu_date = StringField('Date (YYYY-MM-DD)', validators=[DataRequired()])
    breakfast_menu = TextAreaField('Breakfast Menu')
    lunch_menu = TextAreaField('Lunch Menu')
    dinner_menu = TextAreaField('Dinner Menu')
    submit = SubmitField('Add Menu')

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            login_user(admin)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    total_students = Student.query.count()
    today = date.today()
    today_meals = db.session.query(MealAttendance).filter(MealAttendance.attendance_date == today).count()
    pending_bills = Bill.query.filter_by(paid=False).count()
    today_date = date.today().strftime('%A, %B %d, %Y')
    return render_template('dashboard.html', total_students=total_students, 
                          today_meals=today_meals, pending_bills=pending_bills, today_date=today_date)

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    form = StudentForm()
    if form.validate_on_submit():
        if Student.query.filter_by(student_id=form.student_id.data).first():
            flash('Student ID exists')
        else:
            student = Student(
                student_id=form.student_id.data,
                name=form.name.data,
                room_number=form.room_number.data,
                course=form.course.data
            )
            db.session.add(student)
            db.session.commit()
            flash('Student added successfully')
        return redirect(url_for('students'))
    students_list = Student.query.all()
    return render_template('students.html', form=form, students=students_list)

@app.route('/delete_student/<int:student_id>')
@login_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    MealAttendance.query.filter_by(student_id=student_id).delete()
    Bill.query.filter_by(student_id=student_id).delete()
    db.session.delete(student)
    db.session.commit()
    flash('Student deleted')
    return redirect(url_for('students'))

@app.route('/generate_bill/<int:student_id>/<string:bill_month>')
@login_required
def generate_bill(student_id, bill_month):
    student = Student.query.get_or_404(student_id)
    year_month = datetime.strptime(bill_month, '%Y-%m')
    start_date = year_month.replace(day=1)
    _, last_day = calendar.monthrange(year_month.year, year_month.month)
    end_date = year_month.replace(day=last_day)
    
    attendances = MealAttendance.query.filter(
        MealAttendance.student_id == student_id,
        MealAttendance.attendance_date >= start_date,
        MealAttendance.attendance_date <= end_date
    ).all()
    
    breakfast_count = sum(1 for a in attendances if a.breakfast)
    lunch_count = sum(1 for a in attendances if a.lunch)
    dinner_count = sum(1 for a in attendances if a.dinner)
    
    total = breakfast_count * 30 + lunch_count * 50 + dinner_count * 40
    
    existing_bill = Bill.query.filter_by(student_id=student_id, bill_month=bill_month).first()
    if existing_bill:
        existing_bill.total_amount = total
    else:
        bill = Bill(student_id=student_id, bill_month=bill_month, total_amount=total)
        db.session.add(bill)
    db.session.commit()
    
    flash(f'Bill generated: ₹{total}')
    return redirect(url_for('billing'))

@app.route('/meals', methods=['GET', 'POST'])
@login_required
def meals():
    students_list = Student.query.all()
    form = MealForm()
    form.student_id.choices = [(s.id, f"{s.student_id} - {s.name}") for s in students_list] if students_list else []
    attendances = MealAttendance.query.order_by(MealAttendance.attendance_date.desc()).limit(50).all()
    if request.method == 'POST':
        if form.validate_on_submit():
            att = MealAttendance(
                student_id=form.student_id.data,
                breakfast=form.breakfast.data,
                lunch=form.lunch.data,
                dinner=form.dinner.data,
                attendance_date=date.today()
            )
            db.session.add(att)
            db.session.commit()
            flash('Attendance recorded')
            return redirect(url_for('meals'))
    return render_template('meals.html', form=form, attendances=attendances)


@app.route('/menu', methods=['GET', 'POST'])
@login_required
def menu():
    form = MenuForm()
    if form.validate_on_submit():
        try:
            mdate = date.fromisoformat(form.menu_date.data)
            menu = Menu(
                menu_date=mdate,
                breakfast_menu=form.breakfast_menu.data,
                lunch_menu=form.lunch_menu.data,
                dinner_menu=form.dinner_menu.data
            )
            db.session.add(menu)
            db.session.commit()
            flash('Menu added successfully')
        except ValueError:
            flash('Invalid date format (use YYYY-MM-DD)')
    menus = Menu.query.order_by(Menu.menu_date.desc()).all()
    menus_json = []
    for m in menus:
        menus_json.append({
            'menu_date': m.menu_date.isoformat(),
            'breakfast_menu': m.breakfast_menu,
            'lunch_menu': m.lunch_menu,
            'dinner_menu': m.dinner_menu
        })
    return render_template('menu.html', form=form, menus=menus, menus_data=menus_json)

@app.route('/billing')
@login_required
def billing():
    bills = Bill.query.outerjoin(Student).add_columns(Student.name.label('student_name')).order_by(Bill.bill_month.desc()).all()
    return render_template('billing.html', bills=bills)


with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Default admin created: username=admin, password=admin123')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
