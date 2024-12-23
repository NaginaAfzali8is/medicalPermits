import requests
import os
# from openai import OpenAI
from flask import Flask, redirect, request, jsonify, render_template
from flask_socketio import SocketIO
from mongoengine import connect
import models as models
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, FileField
from wtforms.validators import DataRequired, Email
from pymongo import MongoClient
import datetime
from werkzeug.utils import secure_filename
from forms.health_permit_form import HealthPermitForm
import json
from flask_cors import CORS

# MongoDB setup
# client = MongoClient('mongodb://admin:admin123@35.183.49.252:27017/')
# db = client['admin']
# HealthPermitForm = db['health_permits']  # Replace with your collection name

# Initialize Flask app
app = Flask(__name__)

CORS(app)
# creates a Flask web app
app.secret_key = "Nim123??"  # Set a secret key for session management
connected_clients = set()  # Set to store connected client IDs

# connected_clients=None  # Set to store connected client IDs

socketio = SocketIO(app, ping_timeout=300000)  # 5 minutes

# Set OpenAI API Key (Replace 'YOUR_OPENAI_API_KEY' with your key)
# openai.api_key = api_key  # Replace with your actual API key
# client = OpenAI(
#     api_key=api_key,  # This is the default and can be omitted
# )

def get_client_ip():
    """Retrieve the client's IP address."""
    if "X-Forwarded-For" in request.headers:
        return request.headers["X-Forwarded-For"].split(",")[0]
    elif "X-Real-IP" in request.headers:
        return request.headers["X-Real-IP"]
    return request.remote_addr

def get_location_by_ip(ip):
    """Fetch location details for the given IP using ip-api."""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        data = response.json()
        if data["status"] == "success":
            return f"{data['city']}, {data['regionName']}, {data['country']}"
        else:
            return "Location not found"
    except Exception as e:
        return f"Error fetching location: {e}"

@app.route('/')
def home():
    try:
        requests = list(models.HealthPermitForm.find({}, {'_id': 0}))
        if requests:
            return render_template('list.html', requests=requests)
        else:
            requests = []
            return render_template('list.html', requests=requests)
    except Exception as e:
        print("error", str(e))
        requests = []
        return render_template('list.html', requests=requests)


@app.route('/createForm')
def createForm():
    try:
       return render_template('createForm.html', requests=requests)
        
    except Exception as e:
        print("error", str(e))
        requests = []
        return render_template('createForm.html', requests=requests)
    


@app.route('/chatBotMy')
def index():
    """Render the main chat page."""
    return render_template('indexMyChatBot.html')


# @app.route('/chat', methods=['POST'])
# def chat():
#     """Handles incoming chat messages from the user."""
#     user_message = request.json.get('message')

#     print(f"User: {user_message}")

#     # Use OpenAI API to generate a response
#     try:
#         # response = openai.ChatCompletion.create(
#         #     model="gpt-4",  # Use GPT-4 or GPT-3.5-turbo
#         #     messages=[{"role": "user", "content": user_message}]
#         # )
#         response = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "user",
#                     "content": user_message,
#                 }
#             ],
#             model="gpt-4o",
#         )
#         reply = response.choices[0].message.content
        
#     except Exception as e:
#         print(f"Error: {e}")
#         reply = "Sorry, there was an error generating a response. Please try again later."
    
#     print(f"Bot: {reply}")
    
#     return jsonify({'reply': reply})


@app.route('/chatNew', methods=['POST'])
def chatNew():
    """Handles incoming chat messages from the user."""
    
    # Get the user's message from the incoming JSON request
    user_message = request.json.get('message', '').strip()

    # Check if the message is valid
    if not user_message:
        return jsonify({'reply': "Please provide a valid message."})
    
    print(f"User: {user_message}")

    # Use OpenAI API to generate a response
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Correct model name
            messages=[
                {"role": "user", "content": user_message}  # Use the user's message here
            ]
        )

        # Correctly access the response message content
        reply = response.choices[0].message['content']
        
    except Exception as e:
        print(f"Error: {e}")
        reply = "Sorry, there was an error generating a response. Please try again later."
    
    print(f"Bot: {reply}")
    
    return jsonify({'reply': reply})


@app.route("/ipAddress")
def ipAddress():
    client_ip = get_client_ip()
    if client_ip == "127.0.0.1":  # Localhost testing case
        return "Localhost detected. Use a real IP to test location."
    location = get_location_by_ip(client_ip)
    return f"Detected IP Address: {client_ip} <br> Location: {location}"


# API Routes

# Configure file upload settings
UPLOAD_FOLDER = 'uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'docx'}  # Add the allowed file extensions

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
    

@app.route('/create_request', methods=['POST'])
def create_request():
    try:
        # Handle form validation and file validation
        form = HealthPermitForm(request.form)

        # Manually check for files in request.files
        file_fields = ['identification_doc', 'medical_doc', 'authorization_letter']
        file_errors = {}

        for field_name in file_fields:
            # Check if the file exists in the request
            if field_name in request.files:
                uploaded_file = request.files[field_name]
                
                # If file is not empty and has a valid extension, continue
                if uploaded_file.filename != '' and allowed_file(uploaded_file.filename):
                    continue
                elif uploaded_file.filename == '':
                    # No file uploaded for this field (optional)
                    continue
                else:
                    file_errors[field_name] = "Invalid file type"

        # If there were any file validation errors, return the error
        if file_errors:
            return {"error": "File validation failed", "details": file_errors}, 400

        # Now validate the rest of the form fields (text fields)
        if not form.validate():
            return {"error": "Validation failed", "details": form.errors}, 400

        # Prepare data for MongoDB
        data = form.data
        data['created_at'] = datetime.datetime.now()

        # Generate a unique reference number
        reference_number = f"HP-{int(datetime.datetime.now().timestamp())}"
        data['reference_number'] = reference_number

        # Set initial status to "pending"
        data['status'] = "pending"

        # Convert any datetime.date fields to datetime.datetime
        for key, value in data.items():
            if isinstance(value, datetime.date):
                data[key] = datetime.datetime.combine(value, datetime.datetime.min.time())

        # Insert into MongoDB and get the generated ObjectId as user_id
        result = models.HealthPermitForm.insert_one(data)
        user_id = str(result.inserted_id)  # Get the newly generated user ID (MongoDB ObjectId)

        # Create user-specific folder for file uploads (named using user ID)
        # user_folder = os.path.join(UPLOAD_FOLDER, f"user_{user_id}")
        # if not os.path.exists(user_folder):
        #     os.makedirs(user_folder)

        # Save uploaded files
# Handle file validation and save
        for field_name in file_fields:
            if field_name in request.files:
                uploaded_file = request.files[field_name]
                
                if uploaded_file.filename != '':
                    # Extract the original file extension
                    file_extension = os.path.splitext(uploaded_file.filename)[1].lower()  # Get the file extension
                    
                    # Create a custom file name with the original extension
                    custom_filename = f"{user_id}_{field_name}{file_extension}"
                    
                    # Full file path
                    file_path = os.path.join(UPLOAD_FOLDER, custom_filename)
                    
                    # Save the file to the designated path
                    uploaded_file.save(file_path)
                    print(f"Saved file: {file_path}")  # Debugging: Log the file save path
                    
                    # Update the file path in data
                    data[field_name] = file_path

        # Update the database with the file paths
        models.HealthPermitForm.update_one(
            {"_id": result.inserted_id},
            {"$set": {field_name: data[field_name] for field_name in file_fields if field_name in data}}
        )

        return {
            "message": "Request created successfully!",
            "user_id": user_id,
            "reference_number": reference_number,
            "status": data['status']
        }, 201
    except Exception as e:
        print("Error:", str(e))
        return {"error": "An error occurred while processing the request"}, 500

    

@app.route('/read', methods=['GET'])
def read_requests():
    requests = list(models.HealthPermitForm.find({}, {'_id': 0}))  # Exclude MongoDB ObjectID
    return jsonify(requests), 200


from datetime import datetime  # Correct import for type checking

@app.route('/edit/<string:passport_no>', methods=['GET'])
def edit_request(passport_no):
    data = models.HealthPermitForm.find_one({'passport_no': passport_no})
    if not data:
        return "Request not found", 404
    
    # Format dates to 'YYYY-MM-DD' for HTML input fields
    if 'date_of_joining' in data:
        if data['date_of_joining'] and isinstance(data['date_of_joining'], datetime):
            data['date_of_joining'] = data['date_of_joining'].strftime('%Y-%m-%d')
    if 'passport_exp_date' in data:
        if data['passport_exp_date'] and isinstance(data['passport_exp_date'], datetime):
            data['passport_exp_date'] = data['passport_exp_date'].strftime('%Y-%m-%d')

    return render_template('edit_request.html', passport_no=passport_no, data=data)




@app.route('/update/<string:passport_no>', methods=['POST'])
def update_request(passport_no):
    update_data = {key: request.form[key] for key in request.form if key != 'passport_no'}
    models.HealthPermitForm.update_one({'passport_no': passport_no}, {'$set': update_data})
    return redirect('/')


@app.route('/delete/<string:passport_no>', methods=['DELETE'])
def delete_request(passport_no):
    models.HealthPermitForm.delete_one({'passport_no': passport_no})
    return jsonify({"message": "Request deleted successfully"}), 200


@app.route("/customerService")
def customerService():
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



@socketio.on("message")
def handle_message(msg):
    print("Received message: " + msg)
    # You can add additional logic here to process the received message
    # Then, emit the processed message back to the clients
    socketio.emit("response", msg)


@socketio.on("connect")
def handle_connect():
    client_id = request.sid  # Get the client ID
    # Add the client ID to the set of connected clients
    connected_clients.add(client_id)
    print(f"Client {client_id} connected")


@socketio.on("disconnect")
def handle_disconnect():
    client_id = request.sid
    # Remove the client ID from                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            the set of connected clients
    connected_clients.remove(client_id)
    print(f"Client {client_id} disconnected")


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=5000, debug=True)
    # socketio.run(app, debug=True, port=8000)
    # socketio.run(app, debug=True, port=8000)
    socketio.run(app, port=5000)
