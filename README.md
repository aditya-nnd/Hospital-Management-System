# Hospital-Management-System

This Hospital Management System is a web-based application designed to streamline the management of hospital operations. It provides a centralized platform for Admins, Doctors, and Patients to interact efficiently. The system facilitates user management, appointment booking with conflict prevention, medical history tracking, and doctor availability management.

The application is built using Flask and follows a strict Model-View-Controller (MVC) architecture. It utilizes server-side rendering with Jinja2, ensuring all logic is handled securely on the backend.

**Project layout**
- `app.py`: Flask application entrypoint.
- `models/database.py`: SQLAlchemy models (User, Patient, Doctor, Appointment, Treatment, Availability).
- `templates/`: Jinja2 HTML templates (dashboard, appointment pages, auth pages, etc.).
- `static/`: static assets (e.g. `style.css`).

**Features**
- User authentication (roles: patient, doctor, admin).
- Patient and doctor profiles.
- Book and manage appointments.
- Track treatments/diagnosis and prescriptions.
- Manage doctor availability.

Requirements
- Python 3.8+
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Werkzeug

Quick setup (PowerShell)

```powershell
# create venv
python -m venv venv

# activate (PowerShell)
venv\Scripts\Activate.ps1

# install dependencies (create a requirements.txt or install directly)
pip install Flask Flask-Login Flask-SQLAlchemy Werkzeug

# (optional) if you add a requirements.txt
# pip install -r requirements.txt
```

Database
- The app uses SQLAlchemy. To create the database tables interactively:

```powershell
$env:FLASK_APP = "app.py"
python -c "from models.database import db; from app import app; \
with app.app_context(): db.create_all()"
```

Running the app

```powershell
# Option A: using Flask CLI
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
flask run

# Option B: directly (if `app.py` runs app.run())
python app.py
```

Key files to edit
- `app.py`: app routes and startup.
- `models/database.py`: database models and relationships.
- `templates/`: HTML templates for UI; edit to change views.

Notes and tips
- The `User` model stores `password_hash`; use `set_password` to set a password and `check_password` to verify.
- Templates included: `admin_dashboard.html`, `doctor_dashboard.html`, `patient_dashboard.html`, `login.html`, `register.html`, `book_appointment.html`, `my_appointments.html`, `manage_doctors.html`, `manage_patients.html`, `manage_availability.html`, etc.
- Consider adding `Flask-Migrate` for schema migrations if you plan to evolve the DB schema.

Next steps
- Add a `requirements.txt` with pinned versions and (optionally) `Flask-Migrate` for DB migrations.
- If you want, I can run a quick sanity check or start the app locally and verify routes.
