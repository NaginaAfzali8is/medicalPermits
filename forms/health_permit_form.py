from wtforms import StringField, DateField, SelectField, FileField
from wtforms import Form, StringField, SelectField, DateField, FileField, validators

# Define the HealthPermitForm using WTForms
class HealthPermitForm(Form):
    patient_name = StringField('Patient_Name', [validators.DataRequired()])
    # position = StringField('Position', [validators.Optional()])
    # department = SelectField('Department', choices=[('IT', 'IT'), ('HR', 'HR')], validators=[validators.DataRequired()])
    date_of_joining = DateField('Date_of_Joining', format='%Y-%m-%d', validators=[validators.DataRequired()])
    phone_number = StringField('Phone_Number', [validators.DataRequired(), validators.Regexp(r'^\d{10}$', message="Invalid phone number")])
    email_address = StringField('Email_Address', [validators.DataRequired(), validators.Email()])
    passport_no = StringField('Passport_Number', [validators.DataRequired()])
    passport_exp_date = DateField('Passport_Expiry_Date', format='%Y-%m-%d', validators=[validators.DataRequired()])
    # blood_group = StringField('Blood_Group', [validators.DataRequired()])
    # allergy_history = StringField('Allergy_History', [validators.Optional()])
    # chronic_conditions = StringField('Chronic_Conditions', [validators.Optional()])
    primary_doctor = StringField('Primary_Doctor', [validators.Optional()])
    Martial_status = StringField('Martial_status', [validators.Optional()])
    Urgent_need = StringField('Urgent_need', [validators.Optional()])
    # identification_doc = FileField('identification_doc', [validators.DataRequired()])
    # medical_doc = FileField('medical_doc', [validators.DataRequired()])
    # authorization_letter = FileField('authorization_letter', [validators.DataRequired()])
# Patient Name
# Hospital Name
# Preferred Language:
# Date of Joining
# Additional Details
# Martial Status
# Phone Number: (Active your Whatsapp Number)
# Urgent Need:
# Doctor Name
# Passport Number
# Passport Expiry Date
