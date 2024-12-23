import openai
import json
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Set your OpenAI API key
# openai.api_key =api_key

# Configure file upload settings
UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {"pdf", "jpg", "png"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# In-memory storage for permit data
permit_data = {}

@app.route("/upload", methods=["POST"])
def upload_file():
    user_id = request.form.get("user_id")  # Get user_id from the form data
    if not user_id or user_id not in permit_data:
        return jsonify({"response": "Invalid user session."})

    if "file" not in request.files:
        return jsonify({"response": "No file part in the request."})
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"response": "No file selected."})
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Update user state to move to the next question
        current_field = permit_data[user_id]["current_field"]
        form = permit_data[user_id]["form"]

        if current_field == "Identification Documents":
            form["Identification Documents"] = filename
            response = "File uploaded successfully! Please upload your Medical Documents."
            permit_data[user_id]["current_field"] = "Medical Documents"
        elif current_field == "Medical Documents":
            form["Medical Documents"] = filename
            response = "File uploaded successfully! Please upload your Authorization Letter."
            permit_data[user_id]["current_field"] = "Authorization Letter"
        elif current_field == "Authorization Letter":
            form["Authorization Letter"] = filename
            permit_data[user_id]["state"] = "confirmation"
            response = (
                f"File uploaded successfully! Here’s what you’ve entered so far:\n"
                f"{json.dumps(form, indent=2)}\n\nConfirm and Submit or Edit your details."
            )

        return jsonify({"response": response})
    else:
        return jsonify(
            {"response": "Invalid file type. Only PDF, JPG, or PNG allowed."}
        )


# Helper function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to validate date format
def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

@app.route("/")
def home():
    return render_template("index.html")  # Serve the chatbot HTML

# Chatbot API endpoint
@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message")
    user_id = request.json.get("user_id")

    # Ensure user_id is provided
    if not user_id:
        return jsonify({"response": "User ID is required."})

    # Initialize data for new users
    if user_id not in permit_data:
        permit_data[user_id] = {"state": "start", "form": {}, "current_field": None}

    # Extract state, form, and current field
    state = permit_data[user_id]["state"]
    form = permit_data[user_id]["form"]
    current_field = permit_data[user_id]["current_field"]

    # Debugging output
    print(f"Received input: user_id={user_id}, message={user_input}")
    print(f"Current state: {state}, form data: {form}, current field: {current_field}")

    # Chatbot state logic
    if state == "start":
        response = (
            "Welcome to the Medical Permit Chatbot! Please select an option:\n"
            "1. Guide line\n"
            "2. Ask a Question\n"
            "3. Start Medical Permit Request"
        )
        permit_data[user_id]["state"] = "main_menu"

    elif state == "main_menu":
        if user_input.strip() == "1":
            response = (
                "Guide line: This chatbot helps you submit a medical permit request.\n"
                "1. You will be guided step-by-step to provide required information.\n"
                "2. You can upload necessary documents.\n"
                "3. Once completed, you will receive a reference ID to track your request.\n"
                "Let me know if you’d like to proceed or have questions!"
            )
            permit_data[user_id]["state"] = "start"
        elif user_input.strip() == "2":
            response = "Feel free to ask your question. I will do my best to assist you."
            permit_data[user_id]["state"] = "question_answer"
        elif user_input.strip() == "3":
            response = (
                "Welcome! What would you like to do today?\n"
                "1. Submit a New Permit Request\n"
                "2. Check Status of an Existing Request\n"
                "3. Modify/Cancel a Request"
            )
            permit_data[user_id]["state"] = "menu"
        else:
            response = "Invalid option. Please select 1, 2, or 3."

    elif state == "question_answer":
        # Here you could integrate OpenAI GPT for question-answering
        response = f"You asked: {user_input}. Unfortunately, I am unable to answer that right now. Please refer to the guideline or start your request."
        permit_data[user_id]["state"] = "start"

    elif state == "menu":
        if user_input.strip() == "1":
            response = "Great! Let’s start your medical permit request. Please provide your Full Name."
            permit_data[user_id]["state"] = "basic_info"
            permit_data[user_id]["current_field"] = "Patient Name"
        elif user_input.strip() == "2":
            response = "Submitting a ticket request is not implemented yet. Please try Request Treatment Abroad."
            permit_data[user_id]["state"] = "start"
        else:
            response = "Invalid option. Please select 1 or 2."

    elif state == "basic_info":
        if current_field == "Patient Name":
            form["Patient Name"] = user_input
            response = "Enter your Hospital Name."
            permit_data[user_id]["current_field"] = "Hospital Name"
        elif current_field == "Hospital Name":
            form["Hospital Name"] = user_input
            response = "Which language would you like to communicate in?"
            permit_data[user_id]["current_field"] = "Preferred Language"
        elif current_field == "Preferred Language":
            form["Preferred Language"] = user_input
            response = "Enter your Date of Joining (yyyy/mm/dd)."
            permit_data[user_id]["current_field"] = "Date of Joining"
        elif current_field == "Date of Joining":
            if not validate_date(user_input):  # Validate date
                response = "Invalid date format. Please provide the Date of Joining in yyyy/mm/dd format."
            else:
                form["Date of Joining"] = user_input
                response = "Enter any further clarification or details here."
                permit_data[user_id]["current_field"] = "Additional Details"
        elif current_field == "Additional Details":
            form["Additional Details"] = user_input
            response = "Please provide your Marital Status."
            permit_data[user_id]["state"] = "medical_info"
            permit_data[user_id]["current_field"] = "Marital Status"

    elif state == "medical_info":
        if current_field == "Marital Status":
            form["Marital Status"] = user_input
            response = "Enter your Phone Number (WhatsApp Enabled)."
            permit_data[user_id]["current_field"] = "Phone Number"
        elif current_field == "Phone Number":
            if not user_input.isdigit():
                response = "Phone Number must be numeric. Please provide a valid Phone Number."
            else:
                form["Phone Number"] = user_input
                response = "Do you have an urgent need? (Yes/No)"
                permit_data[user_id]["current_field"] = "Urgent Need"
        elif current_field == "Urgent Need":
            form["Urgent Need"] = user_input
            response = "Enter your Doctor Name."
            permit_data[user_id]["current_field"] = "Doctor Name"
        elif current_field == "Doctor Name":
            form["Doctor Name"] = user_input
            response = "Please provide your Passport Number."
            permit_data[user_id]["state"] = "personal_info"
            permit_data[user_id]["current_field"] = "Passport Number"

    elif state == "personal_info":
        if current_field == "Passport Number":
            form["Passport Number"] = user_input
            response = "Enter your Passport Expiry Date (yyyy/mm/dd)."
            permit_data[user_id]["current_field"] = "Passport Expiry Date"
        elif current_field == "Passport Expiry Date":
            if not validate_date(user_input):  # Validate date
                response = "Invalid date format. Please provide the Passport Expiry Date in yyyy/mm/dd format."
            else:
                form["Passport Expiry Date"] = user_input
                response = "Please upload your Identification Documents."
                permit_data[user_id]["state"] = "documents"
                permit_data[user_id]["current_field"] = "Identification Documents"

    elif state == "documents":
        if current_field == "Identification Documents":
            response = "Please upload your Medical Documents."
            permit_data[user_id]["current_field"] = "Medical Documents"
        elif current_field == "Medical Documents":
            response = "Please upload your Authorization Letter."
            permit_data[user_id]["current_field"] = "Authorization Letter"
        elif current_field == "Authorization Letter":
            response = f"Here’s what you’ve entered so far:\n{json.dumps(form, indent=2)}\n\nConfirm and Submit or Edit your details."
            permit_data[user_id]["state"] = "confirmation"

    elif state == "confirmation":
        if user_input.lower() == "confirm":
            reference_id = f"REF{len(permit_data):05d}"
            permit_data[user_id]["reference_id"] = reference_id
            response = f"Your request has been submitted successfully! Your Reference ID is {reference_id}. Use this ID to track the status of your request."
            permit_data[user_id]["state"] = "completed"
        elif user_input.lower() == "edit":
            response = "Which section would you like to edit? (Basic Information, Medical Information, Personal Info, Documents)"
            permit_data[user_id]["state"] = "edit_section"
        else:
            response = "Invalid option. Please type 'Confirm' or 'Edit'."

    else:
        response = "Something went wrong. Please start again."
        permit_data[user_id]["state"] = "start"

    print(f"Updated permit_data: {permit_data}")
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(debug=True, port=5048)