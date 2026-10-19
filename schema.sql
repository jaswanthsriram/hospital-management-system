-- Hospital Management System schema based on Review 1 design.
-- PostgreSQL syntax. Run after creating an empty hospital_management database.

CREATE TABLE IF NOT EXISTS department (
    dept_id SERIAL PRIMARY KEY,
    dept_name VARCHAR(100) NOT NULL UNIQUE,
    location VARCHAR(120),
    head_doctor_id INTEGER
);

CREATE TABLE IF NOT EXISTS doctor (
    doctor_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    phone VARCHAR(25),
    email VARCHAR(150) UNIQUE,
    dept_id INTEGER REFERENCES department(dept_id) ON DELETE SET NULL,
    consultation_fee NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (consultation_fee >= 0)
);

ALTER TABLE department
    DROP CONSTRAINT IF EXISTS department_head_doctor_id_fkey;
ALTER TABLE department
    ADD CONSTRAINT department_head_doctor_id_fkey
    FOREIGN KEY (head_doctor_id) REFERENCES doctor(doctor_id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS patient (
    patient_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    gender VARCHAR(30),
    dob DATE,
    phone VARCHAR(25),
    address TEXT,
    blood_group VARCHAR(5),
    registration_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS appointment (
    appointment_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patient(patient_id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES doctor(doctor_id) ON DELETE RESTRICT,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Scheduled'
        CHECK (status IN ('Scheduled','Completed','Cancelled','Rescheduled')),
    CONSTRAINT unique_doctor_slot UNIQUE (doctor_id, appointment_date, appointment_time)
);

CREATE TABLE IF NOT EXISTS treatment (
    treatment_id SERIAL PRIMARY KEY,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(appointment_id) ON DELETE CASCADE,
    diagnosis_desc TEXT NOT NULL,
    treatment_desc TEXT,
    date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS medicine (
    medicine_id SERIAL PRIMARY KEY,
    medicine_name VARCHAR(150) NOT NULL,
    manufacturer VARCHAR(150),
    unit_price NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    expiry_date DATE
);

CREATE TABLE IF NOT EXISTS prescription (
    prescription_id SERIAL PRIMARY KEY,
    treatment_id INTEGER NOT NULL REFERENCES treatment(treatment_id) ON DELETE CASCADE,
    medicine_id INTEGER NOT NULL REFERENCES medicine(medicine_id) ON DELETE RESTRICT,
    dosage VARCHAR(100),
    duration VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS billing (
    bill_id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patient(patient_id) ON DELETE RESTRICT,
    appointment_id INTEGER NOT NULL UNIQUE REFERENCES appointment(appointment_id) ON DELETE RESTRICT,
    consultation_charge NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (consultation_charge >= 0),
    medicine_charge NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (medicine_charge >= 0),
    total_amount NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    bill_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS payment (
    payment_id SERIAL PRIMARY KEY,
    bill_id INTEGER NOT NULL REFERENCES billing(bill_id) ON DELETE CASCADE,
    amount_paid NUMERIC(10,2) NOT NULL CHECK (amount_paid > 0),
    payment_mode VARCHAR(30) NOT NULL,
    payment_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE IF NOT EXISTS staff (
    staff_id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('Admin','Receptionist','Doctor','Pharmacist')),
    username VARCHAR(80) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_appointment_date ON appointment(appointment_date);
CREATE INDEX IF NOT EXISTS idx_patient_name ON patient(name);
CREATE INDEX IF NOT EXISTS idx_payment_bill ON payment(bill_id);
