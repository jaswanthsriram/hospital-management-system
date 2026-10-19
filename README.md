# MediCore — Hospital Management System

A Flask + PostgreSQL web application for the Hospital Management System Design Review project. It follows the entities, attributes, relationships and requirements in the supplied Review 1 PDF.

## Features included

- Premium blue/teal responsive dashboard with sidebar, KPI cards and tables
- Ten core entities: Patient, Doctor, Department, Appointment, Treatment/Diagnosis, Prescription, Medicine, Billing, Payment, Staff/Admin
- Primary keys, foreign keys, uniqueness and non-negative value constraints
- Patient registration, search, edit and admin delete; doctor add/edit/admin delete and department directory
- Appointment booking, rescheduling with doctor/time-slot conflict checking and status updates
- Treatment/diagnosis records; one treatment per appointment
- Prescription management with medicine stock deduction and low-stock warnings
- Bill generation and full/partial payments
- Reports: total revenue collected, appointments per doctor, daily appointments, patient visit counts
- Role-aware navigation and routes for Admin, Receptionist, Doctor and Pharmacist
- Password hashing for staff accounts; `/health` endpoint for database connectivity

## Important demo warning

This is an academic demonstration, not a production clinical system. Use only fictional sample data. Before any public use, remove or protect `/setup-demo`, change the demo password, add CSRF protection, review access permissions, configure backups, and obtain appropriate security/privacy review. Do not store real patient information in the demo deployment.

## Run locally (Windows)

1. Install Python 3.12+ from python.org.
2. Extract this project ZIP.
3. Open Command Prompt in the extracted `hospital_management_system` folder.
4. Create and activate a virtual environment:

   ```bat
   py -m venv .venv
   .venv\\Scripts\\activate
   ```

5. Install dependencies:

   ```bat
   pip install -r requirements.txt
   ```

6. For the easiest local start, leave `DATABASE_URL` unset. The app uses a local SQLite file (`hospital_local.db`) for development. For PostgreSQL locally, create a database and set `DATABASE_URL` using `.env` or your terminal environment.
7. Start Flask:

   ```bat
   python app.py
   ```

8. Open `http://127.0.0.1:5000/setup-demo` once. This creates demo data and the admin login. Then go to `http://127.0.0.1:5000/login`.
9. Demo credentials: `admin` / `ChangeMe123!`. Change this before exposing the application publicly.
10. Test the pages: Overview, Patients, Doctors, Departments (Admin), Appointments, Treatments, Pharmacy & Stock, Prescriptions, Billing & Payments, Reports, Staff & Access (Admin).

## Test checklist

- [ ] `/health` returns `{"status":"ok","database":"connected"}`
- [ ] Login using demo admin
- [ ] Patient: register a new patient; verify it appears in the table
- [ ] Doctor: add a doctor with a unique email
- [ ] Department: add a new department
- [ ] Appointment: book an appointment; try same doctor/date/time again and confirm conflict message
- [ ] Appointment: change status to Completed or Cancelled
- [ ] Treatment: add a diagnosis for an appointment; try a second treatment for same appointment
- [ ] Pharmacy: add medicine and restock it
- [ ] Prescription: issue medicine and verify stock decreases; try to issue more than available stock
- [ ] Billing: generate a bill, add a partial payment, then pay remaining balance
- [ ] Reports: verify revenue and appointment counts change after test operations
- [ ] Role access: create a Pharmacist/Doctor/Receptionist account and verify sidebar/module permissions

## Deploy on GitHub + Render

### GitHub
1. Create a new GitHub repository, for example `hospital-management-system`.
2. Upload all project files and folders from this extracted folder (not the ZIP file itself).
3. Ensure `app.py`, `requirements.txt`, `render.yaml`, `schema.sql`, `templates/`, and `static/` are in the repository root.

### Render
1. Sign in to Render and choose **New + → Blueprint** (recommended because `render.yaml` creates the web service and PostgreSQL database together).
2. Connect your GitHub repository and deploy the Blueprint.
3. Wait for the build and deployment to finish.
4. Open the Render service URL and append `/setup-demo` once to seed the demo admin and sample records.
5. Log in using `admin` / `ChangeMe123!`.
6. Open `/health` to confirm database connectivity.
7. Immediately change the demo password / remove demo setup before sharing widely. The `/setup-demo` route is intentionally blocked after the first staff account exists, but production hardening is still required.

### If deploying without Blueprint
Create a Render PostgreSQL database and a Render Web Service from the GitHub repo. Set:
- `DATABASE_URL` = Render database's **internal** connection string (if web service and DB are in the same region)
- `SECRET_KEY` = a long random secret
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

## Database entities and relationships

- Department 1:M Doctor
- Doctor 1:M Appointment
- Patient 1:M Appointment
- Appointment 1:1 Treatment
- Treatment 1:M Prescription
- Medicine 1:M Prescription
- Patient 1:M Billing
- Appointment 1:1 Billing
- Billing 1:M Payment (partial payments supported)

The supplied Review 1 identifies a Staff/Admin entity. The application models this as `staff` and uses hashed passwords rather than storing plaintext passwords.

## SQL script

`schema.sql` provides PostgreSQL DDL. The Flask app also creates tables from its SQLAlchemy models on startup, so manual schema execution is not required for the standard app flow. Avoid running `schema.sql` on top of an already populated schema without checking for conflicts.

## Files

- `app.py` — Flask backend and routes
- `templates/` — pages for all modules
- `static/style.css` — responsive blue/teal design
- `schema.sql` — PostgreSQL schema for DBMS lab discussion/evidence
- `render.yaml` — Render Blueprint definition
