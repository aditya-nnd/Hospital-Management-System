import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from models.database import db, User, Patient, Doctor, Appointment, Treatment, Availability
from werkzeug.security import generate_password_hash
from datetime import time, datetime, date, timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hospital.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'secret key'

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')

            if not user.is_active:
                    flash('This account has been deactivated. Please contact an admin.', 'danger')
                    return redirect(url_for('login'))
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, role='patient')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        new_patient = Patient(name=name, phone=phone, user_id=new_user.id)
        db.session.add(new_patient)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged Out Successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('index'))
    doctor_count = User.query.filter_by(role='doctor', is_active=True).count()
    patient_count = User.query.filter_by(role='patient', is_active=True).count()
    appointment_count = Appointment.query.count()
    return render_template(
        'admin_dashboard.html',
        doctor_count=doctor_count, 
        patient_count=patient_count, 
        appointment_count=appointment_count
    )

@app.route('/doctor/dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    
    doctor = current_user.doctor
    
    upcoming_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, 
        status='Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    past_appointments = Appointment.query.filter_by(
        doctor_id=doctor.id, 
        status='Completed'
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    return render_template(
        'doctor_dashboard.html', 
        upcoming_appointments=upcoming_appointments, 
        past_appointments=past_appointments
    )

@app.route('/patient/dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('index'))
    return render_template('patient_dashboard.html')

@app.route('/book-appointment')
@login_required
def book_appointment():
    search_query = request.args.get('search_query')
    #exclude blacklisted doctors
    query = Doctor.query.join(User).filter(User.is_active == True)
    if search_query:
        query = query.filter(
            or_(
                Doctor.name.ilike(f'%{search_query}%'),
                Doctor.specialization.ilike(f'%{search_query}%')
            )
        )
    doctors = query.all()
    return render_template('book_appointment.html', doctors=doctors)
    
@app.route('/book-appointment/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def book_details(doctor_id):
    if current_user.role != 'patient':
        flash('You must be a patient to book appointments.', 'danger')
        return redirect(url_for('index'))
        
    doctor = Doctor.query.get_or_404(doctor_id)

    if request.method == 'POST':
        try:
            date_str = request.form['date']
            time_str = request.form['time']
            # Already Booked Slots Checks
            existing_app_count = Appointment.query.filter_by(       
                doctor_id=doctor.id, 
                date=date_str, 
                time=time_str,
                status='Booked'
            ).count()
            
            if existing_app_count >= 40:
                flash('Sorry, that session is now full. Please select another.', 'danger')
                return redirect(url_for('book_details', doctor_id=doctor.id, selected_date=date_str))
            
            patient_already_booked = Appointment.query.filter_by(
                patient_id=current_user.patient.id,
                doctor_id=doctor.id,
                date=date_str,
                time=time_str,
            ).first()

            if patient_already_booked:
                flash('You have already booked this session.', 'info')
                return redirect(url_for('book_details', doctor_id=doctor.id, selected_date=date_str))

            new_appt = Appointment(
                patient_id=current_user.patient.id,
                doctor_id=doctor.id,
                date=date_str,
                time=time_str,
                status='Booked'
            )
            db.session.add(new_appt)
            db.session.commit()
            
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('my_appointments'))

        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('book_details', doctor_id=doctor.id))

    today = date.today()
    end_date = today + timedelta(days=7)
    availability_slots = Availability.query.filter(
        Availability.doctor_id == doctor.id,
        Availability.date >= today.isoformat(),
        Availability.date < end_date.isoformat()
    ).order_by(Availability.date, Availability.start_time).all()

    selected_date_str = request.args.get('selected_date')
    available_sessions_for_day = []

    if selected_date_str:
        slots_for_that_day = Availability.query.filter_by(
            doctor_id=doctor.id, 
            date=selected_date_str
        ).all()
        
        for slot in slots_for_that_day:
            start_time_str = slot.start_time.strftime('%H:%M')
            
            booked_count = Appointment.query.filter_by(
                doctor_id=doctor.id, 
                date=selected_date_str, 
                time=start_time_str,
                status='Booked'
            ).count()
            
            if booked_count < 40:
                available_sessions_for_day.append((slot, booked_count))
    
    return render_template(
        'book_details.html', 
        doctor=doctor, 
        availability_slots=availability_slots,
        available_slots=available_sessions_for_day,
        selected_date_str=selected_date_str
    )

@app.route('/my-appointments')
@login_required
def my_appointments():
    patient_id = current_user.patient.id
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('my_appointments.html', appointments=appointments)

@app.route('/appointment-details/<int:appointment_id>')
@login_required
def appointment_details(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    treatment = Treatment.query.filter_by(appointment_id=appointment.id).first()
    return render_template('appointment_details.html', appointment=appointment, treatment=treatment)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    patient = current_user.patient
    if request.method == 'POST':
        patient.name = request.form['name']
        patient.phone = request.form['phone']
        db.session.add(patient)
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    return render_template('edit_profile.html', patient=patient)


@app.route('/admin/manage-doctors', methods=['GET', 'POST'])
@login_required
def manage_doctors():
    if request.method == 'POST':
        name = request.form['name']
        specialization = request.form['specialization']
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('manage_doctors'))
        new_user = User(username=username, role='doctor')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        new_doctor = Doctor(name=name, specialization=specialization, user_id=new_user.id)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        return redirect(url_for('manage_doctors'))
    search_query = request.args.get('search_query')
    query = Doctor.query.join(User).filter(User.is_active == True)
    if search_query:
        query = query.filter(
            or_(
                Doctor.name.ilike(f'%{search_query}%'),
                Doctor.specialization.ilike(f'%{search_query}%')
            )
        )
    doctors = query.all()
    return render_template('manage_doctors.html', doctors=doctors)
    
@app.route('/complete-appointment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required
def complete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.doctor_id != current_user.doctor.id:
        flash('You do not have permission to modify this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    if request.method == 'POST':
        new_treatment = Treatment(
            appointment_id=appointment.id,
            diagnosis=request.form['diagnosis'],
            prescription=request.form['prescription'],
            notes=request.form['notes']
        )
        db.session.add(new_treatment)
        db.session.commit()
        db.session.add(appointment)
        db.session.commit()
        appointment.status = 'Completed'
        db.session.commit()
        flash('Appointment marked as complete!', 'success')
        return redirect(url_for('doctor_dashboard'))
    return render_template('complete_appointment.html', appointment=appointment)

@app.route('/cancel-appointment/<int:appointment_id>')
@login_required
def cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status == 'Completed':
        flash('Cannot cancel an already completed appointment.', 'danger')
        return redirect(url_for('my_appointments'))
    db.session.delete(appointment)
    db.session.commit()
    flash('Appointment canceled successfully.', 'success')
    return redirect(url_for('my_appointments'))

@app.route('/manage-availability', methods=['GET', 'POST'])
@login_required
def manage_availability():
    if current_user.role != 'doctor':
        flash('You must be a doctor to access this page.', 'danger')
        return redirect(url_for('index'))
    
    doctor = current_user.doctor

    today = date.today()
    todya_str = today.isoformat()

    delete_count = Availability.query.filter(
        Availability.doctor_id == doctor.id,
        Availability.date < todya_str
    ).delete()

    if delete_count > 0:
        db.session.commit()
    
    slots = {
        'slot1': {'start': time(8, 0), 'end': time(12, 0), 'label': '08:00 - 12:00'},
        'slot2': {'start': time(15, 0), 'end': time(19, 0), 'label': '15:00 - 19:00'}
    }
    
    days = [(today + timedelta(days=i)) for i in range(7)]
    
    if request.method == 'POST':
        try:
            date_strings = [d.isoformat() for d in days]
            
            Availability.query.filter(
                Availability.doctor_id == doctor.id,
                Availability.date.in_(date_strings)
            ).delete(synchronize_session=False)
            
            db.session.commit()
            
            selected_slots = request.form.getlist('slots')
            new_slots_list = []
            
            if selected_slots:
                for slot_str in selected_slots:
                    date_iso, slot_key = slot_str.split('_')
                    
                    if slot_key in slots:
                        slot_times = slots[slot_key]
                        new_slot = Availability(
                            doctor_id=doctor.id,
                            date=date_iso,
                            start_time=slot_times['start'],
                            end_time=slot_times['end']
                        )
                        new_slots_list.append(new_slot)
                
                if new_slots_list:
                    # Add all the slots and commit once
                    db.session.bulk_save_objects(new_slots_list)
                    db.session.commit()
                
            flash('Your availability has been updated successfully!', 'success')
            return redirect(url_for('doctor_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'danger')
            return redirect(url_for('manage_availability'))

    current_availability_query = Availability.query.filter(
        Availability.doctor_id == doctor.id,
        Availability.date.in_([d.isoformat() for d in days])
    ).all()
    
    existing_slots = set()
    for slot in current_availability_query:
        if slot.start_time == slots['slot1']['start']:
            existing_slots.add(f"{slot.date}_slot1")
        elif slot.start_time == slots['slot2']['start']:
            existing_slots.add(f"{slot.date}_slot2")

    return render_template(
        'manage_availability.html', 
        days=days, 
        slots=slots, 
        existing_slots=existing_slots
    )

@app.route('/admin/manage-patients', methods=['GET', 'POST'])
@login_required
def manage_patients():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        phone = request.form['phone']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('manage_patients'))
        new_user = User(username=username, role='patient')
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        new_patient = Patient(name=name, phone=phone, user_id=new_user.id)
        db.session.add(new_patient)
        db.session.commit()
        flash('Patient added successfully!', 'success')
        return redirect(url_for('manage_patients'))
    search_query = request.args.get('search_query')
    query = Patient.query.join(User).filter(User.is_active == True)
    if search_query:
        query = query.filter(
            or_(
                Patient.name.ilike(f'%{search_query}%'),
                User.username.ilike(f'%{search_query}%'),
                Patient.phone.ilike(f'%{search_query}%'),
                Patient.id.ilike(f'%{search_query}%')
            )
        )
    patients = query.all()
    return render_template('manage_patients.html', patients=patients)

@app.route('/admin/all-appointments')
@login_required
def all_appointments():
    appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('all_appointments.html', appointments=appointments)

@app.route('/patient-history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    appointments = Appointment.query.filter_by(
        patient_id=patient.id,
        status='Completed'
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('patient_history.html', patient=patient, appointments=appointments)

@app.route('/admin/delete-doctor/<int:doctor_id>')
@login_required
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user = User.query.get(doctor.user_id)
    if not doctor:
        flash('Doctor not found.', 'danger')
        return redirect(url_for('manage_doctors'))
    Availability.query.filter_by(doctor_id=doctor.id).delete()
    Appointment.query.filter_by(doctor_id=doctor.id, status='Booked').update({"status": "Cancelled"})
    db.session.delete(doctor)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash('Doctor and all associated data have been deleted.', 'success')
    return redirect(url_for('manage_doctors'))

@app.route('/admin/edit-doctor/<int:doctor_id>', methods=['GET', 'POST'])
@login_required
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    user = doctor.user
    if request.method == 'POST':
        doctor.name = request.form['name']
        doctor.specialization = request.form['specialization']
        new_username = request.form['username']
        if new_username != user.username:
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                flash('That username is already taken. Please choose another.', 'danger')
                return render_template('edit_doctor.html', doctor=doctor)
            user.username = new_username
        new_password = request.form['password']
        if new_password:
            user.set_password(new_password)
        db.session.add(doctor)
        db.session.add(user)
        db.session.commit()
        flash('Doctor profile updated successfully!', 'success')
        return redirect(url_for('manage_doctors'))
    return render_template('edit_doctor.html', doctor=doctor)

@app.route('/doctor/cancel-appointment/<int:appointment_id>')
@login_required
def doctor_cancel_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.doctor_id != current_user.doctor.id:
        flash('You do not have permission to cancel this appointment.', 'danger')
        return redirect(url_for('doctor_dashboard'))
    appointment.status = 'Cancelled'
    db.session.add(appointment)
    db.session.commit()
    flash('Appointment has been cancelled.', 'success')
    return redirect(url_for('doctor_dashboard'))

@app.route('/admin/edit-patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    user = patient.user
    if request.method == 'POST':
        patient.name = request.form['name']
        patient.phone = request.form['phone']
        new_username = request.form['username']
        if new_username != user.username:
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                flash('That username is already taken. Please choose another.', 'danger')
                return render_template('edit_patient.html', patient=patient)
            user.username = new_username
        new_password = request.form['password']
        if new_password:
            user.set_password(new_password)
        db.session.add(patient)
        db.session.add(user)
        db.session.commit()
        flash('Patient profile updated successfully!', 'success')
        return redirect(url_for('manage_patients'))
    return render_template('edit_patient.html', patient=patient)

@app.route('/admin/delete-patient/<int:patient_id>')
@login_required
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    user = User.query.get(patient.user_id)
    
    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('manage_patients'))
    Appointment.query.filter_by(patient_id=patient.id).delete()
    db.session.delete(patient)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash('Patient and all their appointments have been deleted.', 'success')
    return redirect(url_for('manage_patients'))

@app.route('/admin/toggle-active/<int:user_id>')
@login_required
def toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot blacklist yourself.', 'danger')
        return redirect(request.referrer or url_for('admin_dashboard'))
    user.is_active = not user.is_active
    db.session.add(user)
    db.session.commit()
    status = "re-activated" if user.is_active else "blacklisted"
    flash(f'User {user.username} has been {status}.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/blacklisted-users')
@login_required
def blacklisted_users():
    users = User.query.filter_by(is_active=False).all()
    return render_template('blacklisted_users.html', users=users)

def setup_database(app_context):
    with app_context:
        db.create_all() 
        if not User.query.filter_by(role='admin').first():
            print("Creating admin user...")
            admin = User(username='admin', role='admin')
            admin.set_password('admin123') 
            db.session.add(admin)
        db.session.commit()
        print("Database setup complete.")


if __name__ == '__main__':
    setup_database(app.app_context())
    app.run(debug=True)