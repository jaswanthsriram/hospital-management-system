import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
database_url = os.environ.get("DATABASE_URL", "sqlite:///hospital_local.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Department(db.Model):
    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), nullable=False, unique=True)
    location = db.Column(db.String(120))
    head_doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.doctor_id", ondelete="SET NULL"))
    doctors = db.relationship("Doctor", backref="department", foreign_keys="Doctor.dept_id")


class Doctor(db.Model):
    doctor_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(25))
    email = db.Column(db.String(150), unique=True)
    dept_id = db.Column(db.Integer, db.ForeignKey("department.dept_id", ondelete="SET NULL"))
    consultation_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0)


class Patient(db.Model):
    patient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    gender = db.Column(db.String(30))
    dob = db.Column(db.Date)
    phone = db.Column(db.String(25))
    address = db.Column(db.Text)
    blood_group = db.Column(db.String(5))
    registration_date = db.Column(db.Date, nullable=False, default=date.today)


class Appointment(db.Model):
    appointment_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.patient_id", ondelete="CASCADE"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor.doctor_id", ondelete="RESTRICT"), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Scheduled")
    patient = db.relationship("Patient", backref="appointments")
    doctor = db.relationship("Doctor", backref="appointments")


class Treatment(db.Model):
    treatment_id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.appointment_id", ondelete="CASCADE"), nullable=False, unique=True)
    diagnosis_desc = db.Column(db.Text, nullable=False)
    treatment_desc = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, default=date.today)
    appointment = db.relationship("Appointment", backref=db.backref("treatment", uselist=False))


class Medicine(db.Model):
    medicine_id = db.Column(db.Integer, primary_key=True)
    medicine_name = db.Column(db.String(150), nullable=False)
    manufacturer = db.Column(db.String(150))
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    expiry_date = db.Column(db.Date)


class Prescription(db.Model):
    prescription_id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey("treatment.treatment_id", ondelete="CASCADE"), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicine.medicine_id", ondelete="RESTRICT"), nullable=False)
    dosage = db.Column(db.String(100))
    duration = db.Column(db.String(100))
    treatment = db.relationship("Treatment", backref="prescriptions")
    medicine = db.relationship("Medicine")


class Billing(db.Model):
    bill_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.patient_id", ondelete="RESTRICT"), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointment.appointment_id", ondelete="RESTRICT"), nullable=False, unique=True)
    consultation_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    medicine_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    bill_date = db.Column(db.Date, nullable=False, default=date.today)
    patient = db.relationship("Patient")
    appointment = db.relationship("Appointment", backref=db.backref("billing", uselist=False))
    payments = db.relationship("Payment", backref="bill", cascade="all, delete-orphan")


class Payment(db.Model):
    payment_id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("billing.bill_id", ondelete="CASCADE"), nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    payment_mode = db.Column(db.String(30), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)


class Staff(db.Model):
    staff_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "staff_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "staff_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in roles:
                flash("Your role does not have permission for that action.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.template_filter("money")
def money(value):
    try:
        return f"₹{Decimal(value or 0):,.2f}"
    except Exception:
        return "₹0.00"


@app.context_processor
def inject_globals():
    return {"current_role": session.get("role"), "current_user": session.get("name")}


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = Staff.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session.update(staff_id=user.staff_id, role=user.role, name=user.name)
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if "staff_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    stats = {
        "patients": Patient.query.count(),
        "doctors": Doctor.query.count(),
        "appointments": Appointment.query.filter_by(appointment_date=today).count(),
        "revenue": db.session.query(func.coalesce(func.sum(Payment.amount_paid), 0)).scalar(),
        "medicines": Medicine.query.count(),
        "low_stock": Medicine.query.filter(Medicine.stock_quantity <= 10).count(),
    }
    upcoming = Appointment.query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).limit(8).all()
    low_stock_items = Medicine.query.filter(Medicine.stock_quantity <= 10).order_by(Medicine.stock_quantity.asc()).limit(5).all()
    return render_template("dashboard.html", stats=stats, upcoming=upcoming, low_stock_items=low_stock_items)


@app.route("/patients", methods=["GET", "POST"])
@login_required
def patients():
    if request.method == "POST":
        try:
            p = Patient(
                name=request.form["name"].strip(),
                gender=request.form.get("gender") or None,
                dob=date.fromisoformat(request.form["dob"]) if request.form.get("dob") else None,
                phone=request.form.get("phone") or None,
                address=request.form.get("address") or None,
                blood_group=request.form.get("blood_group") or None,
            )
            db.session.add(p)
            db.session.commit()
            flash("Patient registered successfully.", "success")
            return redirect(url_for("patients"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save patient. Check required fields and unique constraints. ({exc.__class__.__name__})", "error")
    q = request.args.get("q", "").strip()
    query = Patient.query
    if q:
        query = query.filter(Patient.name.ilike(f"%{q}%"))
    return render_template("patients.html", patients=query.order_by(Patient.patient_id.desc()).all(), q=q)


@app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
@login_required
def edit_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    if request.method == "POST":
        try:
            patient.name = request.form["name"].strip()
            patient.gender = request.form.get("gender") or None
            patient.dob = date.fromisoformat(request.form["dob"]) if request.form.get("dob") else None
            patient.phone = request.form.get("phone") or None
            patient.address = request.form.get("address") or None
            patient.blood_group = request.form.get("blood_group") or None
            db.session.commit()
            flash("Patient record updated.", "success")
            return redirect(url_for("patients"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update patient. ({exc.__class__.__name__})", "error")
    return render_template("edit_patient.html", patient=patient)


@app.route("/patients/<int:patient_id>/delete", methods=["POST"])
@login_required
@role_required("Admin")
def delete_patient(patient_id):
    patient = db.get_or_404(Patient, patient_id)
    try:
        db.session.delete(patient)
        db.session.commit()
        flash("Patient record deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Cannot delete patient while linked records exist. ({exc.__class__.__name__})", "error")
    return redirect(url_for("patients"))


@app.route("/doctors", methods=["GET", "POST"])
@login_required
def doctors():
    if request.method == "POST":
        try:
            doctor = Doctor(
                name=request.form["name"].strip(),
                specialization=request.form["specialization"].strip(),
                phone=request.form.get("phone") or None,
                email=request.form.get("email") or None,
                dept_id=int(request.form["dept_id"]) if request.form.get("dept_id") else None,
                consultation_fee=Decimal(request.form.get("consultation_fee") or "0"),
            )
            db.session.add(doctor)
            db.session.commit()
            flash("Doctor added successfully.", "success")
            return redirect(url_for("doctors"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save doctor. Check fields/email uniqueness. ({exc.__class__.__name__})", "error")
    return render_template("doctors.html", doctors=Doctor.query.order_by(Doctor.doctor_id.desc()).all(), departments=Department.query.order_by(Department.dept_name).all())


@app.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def edit_doctor(doctor_id):
    doctor = db.get_or_404(Doctor, doctor_id)
    if request.method == "POST":
        try:
            doctor.name = request.form["name"].strip()
            doctor.specialization = request.form["specialization"].strip()
            doctor.phone = request.form.get("phone") or None
            doctor.email = request.form.get("email") or None
            doctor.dept_id = int(request.form["dept_id"]) if request.form.get("dept_id") else None
            doctor.consultation_fee = Decimal(request.form.get("consultation_fee") or "0")
            db.session.commit()
            flash("Doctor record updated.", "success")
            return redirect(url_for("doctors"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update doctor. Check email uniqueness and fee. ({exc.__class__.__name__})", "error")
    return render_template("edit_doctor.html", doctor=doctor, departments=Department.query.order_by(Department.dept_name).all())


@app.route("/doctors/<int:doctor_id>/delete", methods=["POST"])
@login_required
@role_required("Admin")
def delete_doctor(doctor_id):
    doctor = db.get_or_404(Doctor, doctor_id)
    try:
        db.session.delete(doctor)
        db.session.commit()
        flash("Doctor record deleted.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Cannot delete doctor while linked appointments exist. ({exc.__class__.__name__})", "error")
    return redirect(url_for("doctors"))


@app.route("/departments", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def departments():
    if request.method == "POST":
        try:
            db.session.add(Department(dept_name=request.form["dept_name"].strip(), location=request.form.get("location") or None))
            db.session.commit()
            flash("Department added.", "success")
            return redirect(url_for("departments"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not add department. ({exc.__class__.__name__})", "error")
    return render_template("departments.html", departments=Department.query.order_by(Department.dept_name).all())


@app.route("/appointments", methods=["GET", "POST"])
@login_required
def appointments():
    if request.method == "POST":
        try:
            patient_id = int(request.form["patient_id"])
            doctor_id = int(request.form["doctor_id"])
            appt_date = date.fromisoformat(request.form["appointment_date"])
            appt_time = datetime.strptime(request.form["appointment_time"], "%H:%M").time()
            collision = Appointment.query.filter_by(doctor_id=doctor_id, appointment_date=appt_date, appointment_time=appt_time).filter(Appointment.status != "Cancelled").first()
            if collision:
                flash("That doctor already has an appointment in this time slot. Choose another time.", "error")
            else:
                appt = Appointment(patient_id=patient_id, doctor_id=doctor_id, appointment_date=appt_date, appointment_time=appt_time)
                db.session.add(appt)
                db.session.commit()
                flash("Appointment booked.", "success")
                return redirect(url_for("appointments"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not book appointment. Check selected patient, doctor, date and time. ({exc.__class__.__name__})", "error")
    rows = Appointment.query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc()).all()
    return render_template("appointments.html", appointments=rows, patients=Patient.query.order_by(Patient.name).all(), doctors=Doctor.query.order_by(Doctor.name).all())


@app.route("/appointments/<int:appointment_id>/reschedule", methods=["POST"])
@login_required
def reschedule_appointment(appointment_id):
    appt = db.get_or_404(Appointment, appointment_id)
    try:
        appt_date = date.fromisoformat(request.form["appointment_date"])
        appt_time = datetime.strptime(request.form["appointment_time"], "%H:%M").time()
        collision = Appointment.query.filter(Appointment.appointment_id != appointment_id, Appointment.doctor_id == appt.doctor_id, Appointment.appointment_date == appt_date, Appointment.appointment_time == appt_time, Appointment.status != "Cancelled").first()
        if collision:
            flash("That doctor already has an appointment in this time slot.", "error")
        else:
            appt.appointment_date = appt_date
            appt.appointment_time = appt_time
            appt.status = "Rescheduled"
            db.session.commit()
            flash("Appointment rescheduled.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not reschedule appointment. ({exc.__class__.__name__})", "error")
    return redirect(url_for("appointments"))


@app.route("/appointments/<int:appointment_id>/status", methods=["POST"])
@login_required
def appointment_status(appointment_id):
    appt = db.get_or_404(Appointment, appointment_id)
    status = request.form.get("status")
    if status in {"Scheduled", "Completed", "Cancelled", "Rescheduled"}:
        appt.status = status
        db.session.commit()
        flash("Appointment status updated.", "success")
    return redirect(url_for("appointments"))


@app.route("/treatments", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Doctor")
def treatments():
    if request.method == "POST":
        try:
            appointment_id = int(request.form["appointment_id"])
            if Treatment.query.filter_by(appointment_id=appointment_id).first():
                flash("A treatment record already exists for that appointment.", "error")
            else:
                item = Treatment(
                    appointment_id=appointment_id,
                    diagnosis_desc=request.form["diagnosis_desc"].strip(),
                    treatment_desc=request.form.get("treatment_desc") or None,
                    date=date.fromisoformat(request.form["date"]) if request.form.get("date") else date.today(),
                )
                db.session.add(item)
                db.session.commit()
                flash("Treatment/diagnosis recorded.", "success")
                return redirect(url_for("treatments"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not save treatment. ({exc.__class__.__name__})", "error")
    rows = Treatment.query.order_by(Treatment.date.desc()).all()
    eligible = Appointment.query.filter(~Appointment.appointment_id.in_(db.session.query(Treatment.appointment_id))).order_by(Appointment.appointment_date.desc()).all()
    return render_template("treatments.html", treatments=rows, appointments=eligible)


@app.route("/pharmacy", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Pharmacist")
def pharmacy():
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "add":
                med = Medicine(
                    medicine_name=request.form["medicine_name"].strip(),
                    manufacturer=request.form.get("manufacturer") or None,
                    unit_price=Decimal(request.form.get("unit_price") or "0"),
                    stock_quantity=int(request.form.get("stock_quantity") or 0),
                    expiry_date=date.fromisoformat(request.form["expiry_date"]) if request.form.get("expiry_date") else None,
                )
                db.session.add(med)
                db.session.commit()
                flash("Medicine added to inventory.", "success")
            elif action == "restock":
                med = db.get_or_404(Medicine, int(request.form["medicine_id"]))
                amount = int(request.form["quantity"])
                if amount <= 0:
                    raise ValueError("Quantity must be positive")
                med.stock_quantity += amount
                db.session.commit()
                flash("Stock updated.", "success")
            return redirect(url_for("pharmacy"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not update medicine inventory. ({exc.__class__.__name__})", "error")
    return render_template("pharmacy.html", medicines=Medicine.query.order_by(Medicine.medicine_name).all())


@app.route("/prescriptions", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Doctor", "Pharmacist")
def prescriptions():
    if request.method == "POST":
        try:
            med = db.get_or_404(Medicine, int(request.form["medicine_id"]))
            quantity = int(request.form.get("quantity") or 1)
            if quantity < 1 or med.stock_quantity < quantity:
                flash("Not enough stock for this prescription.", "error")
            else:
                item = Prescription(
                    treatment_id=int(request.form["treatment_id"]),
                    medicine_id=med.medicine_id,
                    dosage=request.form.get("dosage") or None,
                    duration=request.form.get("duration") or None,
                )
                med.stock_quantity -= quantity
                db.session.add(item)
                db.session.commit()
                flash(f"Prescription recorded and stock reduced by {quantity}.", "success")
                return redirect(url_for("prescriptions"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not record prescription. ({exc.__class__.__name__})", "error")
    return render_template("prescriptions.html", prescriptions=Prescription.query.order_by(Prescription.prescription_id.desc()).all(), treatments=Treatment.query.order_by(Treatment.date.desc()).all(), medicines=Medicine.query.filter(Medicine.stock_quantity > 0).order_by(Medicine.medicine_name).all())


@app.route("/billing", methods=["GET", "POST"])
@login_required
@role_required("Admin", "Receptionist")
def billing():
    if request.method == "POST":
        try:
            appt = db.get_or_404(Appointment, int(request.form["appointment_id"]))
            if Billing.query.filter_by(appointment_id=appt.appointment_id).first():
                flash("A bill already exists for this appointment.", "error")
            else:
                consult = Decimal(request.form.get("consultation_charge") or "0")
                medicine = Decimal(request.form.get("medicine_charge") or "0")
                if consult < 0 or medicine < 0:
                    raise ValueError("Charges cannot be negative")
                bill = Billing(patient_id=appt.patient_id, appointment_id=appt.appointment_id, consultation_charge=consult, medicine_charge=medicine, total_amount=consult + medicine)
                db.session.add(bill)
                db.session.commit()
                flash("Bill generated.", "success")
                return redirect(url_for("billing"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not generate bill. ({exc.__class__.__name__})", "error")
    eligible = Appointment.query.filter(~Appointment.appointment_id.in_(db.session.query(Billing.appointment_id))).order_by(Appointment.appointment_date.desc()).all()
    bills = Billing.query.order_by(Billing.bill_id.desc()).all()
    balances = {}
    for b in bills:
        paid = sum((p.amount_paid for p in b.payments), Decimal("0"))
        balances[b.bill_id] = (paid, max(Decimal("0"), b.total_amount - paid))
    return render_template("billing.html", bills=bills, eligible=eligible, balances=balances)


@app.route("/billing/<int:bill_id>/payment", methods=["POST"])
@login_required
@role_required("Admin", "Receptionist")
def add_payment(bill_id):
    bill = db.get_or_404(Billing, bill_id)
    try:
        amount = Decimal(request.form["amount_paid"])
        paid = sum((p.amount_paid for p in bill.payments), Decimal("0"))
        balance = bill.total_amount - paid
        if amount <= 0 or amount > balance:
            flash(f"Payment must be greater than zero and no more than the remaining balance ({balance}).", "error")
        else:
            db.session.add(Payment(bill_id=bill_id, amount_paid=amount, payment_mode=request.form["payment_mode"], payment_date=date.today()))
            db.session.commit()
            flash("Payment recorded.", "success")
    except Exception as exc:
        db.session.rollback()
        flash(f"Could not record payment. ({exc.__class__.__name__})", "error")
    return redirect(url_for("billing"))


@app.route("/reports")
@login_required
def reports():
    revenue = db.session.query(func.coalesce(func.sum(Payment.amount_paid), 0)).scalar()
    appt_count = db.session.query(Doctor.name, func.count(Appointment.appointment_id)).outerjoin(Appointment, Doctor.doctor_id == Appointment.doctor_id).group_by(Doctor.name).order_by(func.count(Appointment.appointment_id).desc()).all()
    daily = db.session.query(Appointment.appointment_date, func.count(Appointment.appointment_id)).group_by(Appointment.appointment_date).order_by(Appointment.appointment_date.desc()).limit(10).all()
    patient_visits = db.session.query(Patient.name, func.count(Appointment.appointment_id)).outerjoin(Appointment, Patient.patient_id == Appointment.patient_id).group_by(Patient.name).order_by(func.count(Appointment.appointment_id).desc()).limit(10).all()
    return render_template("reports.html", revenue=revenue, appt_count=appt_count, daily=daily, patient_visits=patient_visits)


@app.route("/staff", methods=["GET", "POST"])
@login_required
@role_required("Admin")
def staff():
    if request.method == "POST":
        try:
            user = Staff(name=request.form["name"].strip(), role=request.form["role"], username=request.form["username"].strip(), password=generate_password_hash(request.form["password"]))
            db.session.add(user)
            db.session.commit()
            flash("Staff account created.", "success")
            return redirect(url_for("staff"))
        except Exception as exc:
            db.session.rollback()
            flash(f"Could not create staff account. Username may already exist. ({exc.__class__.__name__})", "error")
    return render_template("staff.html", staff=Staff.query.order_by(Staff.staff_id).all())


@app.route("/setup-demo")
def setup_demo():
    # One-time demo setup: only allowed when there are no staff accounts.
    if Staff.query.count() > 0:
        return "Demo setup is disabled because staff accounts already exist. Please log in.", 403
    db.create_all()
    admin = Staff(name="Hospital Administrator", role="Admin", username="admin", password=generate_password_hash("ChangeMe123!"))
    db.session.add(admin)
    db.session.commit()
    if Department.query.count() == 0:
        d1 = Department(dept_name="Cardiology", location="Block A")
        d2 = Department(dept_name="General Medicine", location="Block B")
        db.session.add_all([d1, d2])
        db.session.flush()
        doc1 = Doctor(name="Dr. Ananya Rao", specialization="Cardiology", phone="9000000001", email="ananya.demo@example.com", dept_id=d1.dept_id, consultation_fee=Decimal("700"))
        doc2 = Doctor(name="Dr. Kiran Kumar", specialization="General Medicine", phone="9000000002", email="kiran.demo@example.com", dept_id=d2.dept_id, consultation_fee=Decimal("500"))
        db.session.add_all([doc1, doc2])
        db.session.flush()
        d1.head_doctor_id = doc1.doctor_id
        d2.head_doctor_id = doc2.doctor_id
        p1 = Patient(name="Aarav Sharma", gender="Male", dob=date(2000, 4, 12), phone="9000000011", address="Demo Address", blood_group="B+", registration_date=date.today())
        p2 = Patient(name="Meera Reddy", gender="Female", dob=date(1997, 8, 22), phone="9000000012", address="Demo Address", blood_group="O+", registration_date=date.today())
        db.session.add_all([p1, p2])
        db.session.flush()
        a1 = Appointment(patient_id=p1.patient_id, doctor_id=doc1.doctor_id, appointment_date=date.today(), appointment_time=datetime.now().replace(minute=0, second=0, microsecond=0).time(), status="Scheduled")
        a2 = Appointment(patient_id=p2.patient_id, doctor_id=doc2.doctor_id, appointment_date=date.today(), appointment_time=datetime.now().replace(minute=0, second=0, microsecond=0).time(), status="Scheduled")
        db.session.add_all([a1, a2])
        m1 = Medicine(medicine_name="Paracetamol 500mg", manufacturer="Demo Pharma", unit_price=Decimal("3.50"), stock_quantity=45, expiry_date=date(2027, 12, 31))
        m2 = Medicine(medicine_name="Vitamin C", manufacturer="Demo Pharma", unit_price=Decimal("2.00"), stock_quantity=8, expiry_date=date(2027, 6, 30))
        db.session.add_all([m1, m2])
        db.session.commit()
    return redirect(url_for("login"))


@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}, 200
    except Exception as exc:
        return {"status": "error", "message": exc.__class__.__name__}, 500


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
