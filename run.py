import requests
import os
# from openai import OpenAI
from flask import Flask, redirect, request, jsonify, render_template
from flask_socketio import SocketIO
import models as models
from wtforms import StringField, DateField, SelectField, FileField
from wtforms.validators import DataRequired, Email
from pymongo import MongoClient
import datetime
from werkzeug.utils import secure_filename
from forms.health_permit_form import HealthPermitForm
import json
from flask_cors import CORS
import openai
from datetime import datetime
# from sentence_transformers import SentenceTransformer, util
from support import allowed_file, validate_date, get_dynamic_response, is_greeting, is_question
import random
import re
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

# Replace these with your Botpress details

# Botpress API configuration

BOTPRESS_API_URL = os.getenv('BOTPRESS_API_URL')
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # Replace with your Botpress access token
BOT_ID = os.getenv("BOT_ID")  # Your Bot ID


# const postData = {
#   name: workflow.name,
#   phone: workflow.phone,
#   email: workflow.emailAddress
# }

# // Make the POST request without specifying headers
# // Make the POST request
# const response2 = await axios.post('https://medical-permits.vercel.app/saveData', postData)

# // Save the response in workflow.response
# workflow.responses = response2.data



# get eprmit table data from botpress 
@app.route('/permitTable', methods=['GET'])
def get_permit_table_data():
    """
    Fetch all data from the PermitTable in Botpress
    """
    try:
        # Set headers for the request
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "x-bot-id": BOT_ID
        }

        # Make the API request to Botpress
        response = requests.post(BOTPRESS_API_URL, headers=headers)

        # Log the raw response for debugging
        print("Response Status Code:", response.status_code)
        print("Response Headers:", response.headers)
        print("Response Text:", response.text)  # Log the raw response

        # Raise an error if the request fails
        response.raise_for_status()

        # Parse and return the data as JSON
        data = response.json()
        return jsonify(data)

    except requests.exceptions.RequestException as e:
        # Handle errors gracefully
        return jsonify({"error": str(e)}), 500
    

# get ref status 
@app.route('/getStatus', methods=['GET'])
def get_status():
    """
    API to retrieve the status based on the reference ID (refID).
    """
    try:
        # Get refID from query parameters
        ref_id = request.args.get('refID')

        if not ref_id:
            return jsonify({"error": "Reference ID (refID) is required"}), 400

        # Query the database for the record with the given refID
        record = models.HealthPermitForm.find_one({"reference_number": ref_id}, {"_id": 0, "status": 1})

        if not record:
            return jsonify({"error": "No record found with the provided refID"}), 404

        # Return the status
        return jsonify({"status": record["status"]})

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An error occurred while retrieving the status", "details": str(e)}), 500


# check if email exist 
@app.route('/existData', methods=['GET'])
def check_email_existence():
    """
    API to check if a specific email exists in the database.
    """
    # Get the email from query parameters
    email = request.args.get('email')

    if not email:
        return jsonify({"error": "Email parameter is required"}), 400

    try:
        # Query MongoDB to check if the email exists
        email_exists = models.HealthPermitForm.find_one({"email_address": email}) is not None

        # Return the result as a JSON response
        return jsonify({"exists": email_exists})
    
    except Exception as e:
        # Handle any database or application errors
        return jsonify({"error": str(e)}), 500
    

    # check if phone exist 


@app.route('/existPhone', methods=['GET'])
def check_phone_existence():
    """
    API to check if a specific email exists in the database.
    """
    # Get the email from query parameters
    phone = request.args.get('phone')

    if not phone:
        return jsonify({"error": "phone parameter is required"}), 400

    try:
        # Query MongoDB to check if the phone exists
        phone_exists = models.HealthPermitForm.find_one({"phone_number": phone}) is not None

        # Return the result as a JSON response
        return jsonify({"exists": phone_exists})
    
    except Exception as e:
        # Handle any database or application errors
        return jsonify({"error": str(e)}), 500



# check if passport exist 
@app.route('/existPassport', methods=['GET'])
def check_passport_existence():
    """
    API to check if a specific email exists in the database.
    """
    # Get the email from query parameters
    passport = request.args.get('passport')

    if not passport:
        return jsonify({"error": "passport parameter is required"}), 400

    try:
        # Query MongoDB to check if the passport exists
        passport_exists = models.HealthPermitForm.find_one({"passport_no": passport}) is not None

        # Return the result as a JSON response
        return jsonify({"exists": passport_exists})
    
    except Exception as e:
        # Handle any database or application errors
        return jsonify({"error": str(e)}), 500


        # Generate a unique reference number
def generate_unique_reference():
    while True:
        reference_number = f"HP-{random.randint(10000000, 99999999)}"  # 8-digit number
        existing_entry = models.HealthPermitForm.find_one({"reference_number": reference_number})
        if not existing_entry:
            return reference_number


        # Function to extract URL from string formatted as "(Image) URL" or "(File) URL"
def extract_url(file_string):
    match = re.search(r'\((?:Image|File)\)\s+(https?://[^\s]+)', file_string)
    return match.group(1) if match else None


@app.route('/saveData', methods=['POST'])
def save_data():
    """
    API to save data to MongoDB.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid input. Please provide JSON data."}), 400

        # Validate required fields
        required_fields = [
            'patient_name',  # Should be an object with 'first' and 'last'
            'phone_number', 'email_address', 'country', 'passport_no', 
            'hospital', 'medical_doc', 'identification_doc',
            'authorization_letter', 'visaAssistant'
        ]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Validate patient_name as an object with 'first' and 'last' keys
        # Validate and merge patient_name
        if not isinstance(data.get('patient_name'), dict) or 'first' not in data['patient_name']:
            return jsonify({"error": "Invalid patient_name. Must be an object with 'first' and optionally 'last' keys."}), 400

        # Merge first and last name into a single string
        first_name = data['patient_name'].get('first', '').strip()
        last_name = data['patient_name'].get('last', '').strip()
        data['patient_name'] = f"{first_name} {last_name}".strip()

        # Extract URLs for file fields
        data['medical_doc'] = extract_url(data.get('medical_doc', ''))
        data['identification_doc'] = extract_url(data.get('identification_doc', ''))
        data['authorization_letter'] = extract_url(data.get('authorization_letter', ''))


        # Generate a unique reference number
        def generate_unique_reference():
            while True:
                reference_number = f"HP-{random.randint(10000000, 99999999)}"  # 8-digit number
                existing_entry = models.HealthPermitForm.find_one({"reference_number": reference_number})
                if not existing_entry:
                    return reference_number

        # Assign the generated reference number
        data['reference_number'] = generate_unique_reference()

        # Add timestamps
        now = datetime.utcnow()
        data['created_at'] = now
        data['updated_at'] = now

        # Set default status
        data['status'] = 'pending'

        # Insert the data into MongoDB
        result = models.HealthPermitForm.insert_one(data)

        return jsonify({
            "message": "Data saved successfully",
            "reference_number": data['reference_number'],  # Return the generated reference number
            "id": str(result.inserted_id)  # Return the inserted document's ID
        }), 201

    except Exception as e:
        print({"error": str(e)})
        return jsonify({"error": str(e)}), 500
    


@app.route('/Treatment_Abroad', methods=['POST'])
# @app.route('/check_data_existence', methods=['GET'])
# def check_data_existence():
#     # Get query parameters
#     email = request.args.get('email')
#     passport_no = request.args.get('passport_no')
#     phone_number = request.args.get('phone_number')

#     # Dictionary to hold the result
#     result = {
#         'email_exists': False,
#         'passport_exists': False,
#         'phone_number_exists': False
#     }

#     # Check each field in the database
#     if email:
#         result['email_exists'] = db_session.query(User).filter_by(email=email).first() is not None
#     if passport_no:
#         result['passport_exists'] = db_session.query(User).filter_by(passport_no=passport_no).first() is not None
#     if phone_number:
#         result['phone_number_exists'] = db_session.query(User).filter_by(phone_number=phone_number).first() is not None

#     return jsonify(result)


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


# model = SentenceTransformer('all-MiniLM-L6-v2')


# # Load Knowledge Base
# with open("knowledge_base.json", "r") as f:
#     knowledge_base = json.load(f)

# faq_entries = knowledge_base["inquiries_received_by_beneficiaries"]  # List of FAQs

# faq_texts = [
#     entry["request_type"] + " " + entry.get("details", "") for entry in faq_entries
# ]

# faq_questions = []
# faq_answers = []

# for category in knowledge_base["faq"]:
#     for question_item in category["questions"]:
#         faq_questions.append(question_item["question"])
#         faq_answers.append(question_item["answer"])

# faq_question_embeddings = model.encode(faq_questions, convert_to_tensor=True)


# def get_faq_response(user_input):
#     for i, question in enumerate(faq_questions):
#         if user_input.lower() in question.lower(): 
#             return faq_answers[i]

#     query_embedding = model.encode(user_input, convert_to_tensor=True)
#     similarities = util.pytorch_cos_sim(query_embedding, faq_question_embeddings)[0]
#     best_match_idx = similarities.argmax().item()

#     if similarities[best_match_idx] < 0.5:  
#         return "I'm sorry, I couldn't find a matching answer. Could you please rephrase your question?"

#     return faq_answers[best_match_idx]


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

    

@app.route('/getAllUsersData', methods=['GET'])
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


@app.route('/getUserData/<string:passport_no>', methods=['GET'])
def getUserData(passport_no):
    # Find the document in the database based on the passport number
    data = models.HealthPermitForm.find_one({'passport_no': passport_no})
    if not data:
        return jsonify({'error': 'Request not found'}), 404

    # Convert ObjectId to string
    if '_id' in data:
        data['_id'] = str(data['_id'])

    # Format dates to 'YYYY-MM-DD' for JSON response
    if 'date_of_joining' in data:
        if data['date_of_joining'] and isinstance(data['date_of_joining'], datetime):
            data['date_of_joining'] = data['date_of_joining'].strftime('%Y-%m-%d')
    if 'passport_exp_date' in data:
        if data['passport_exp_date'] and isinstance(data['passport_exp_date'], datetime):
            data['passport_exp_date'] = data['passport_exp_date'].strftime('%Y-%m-%d')

    # Return the data as JSON
    return jsonify(data), 200


@app.route('/update/<string:passport_no>', methods=['POST'])
def update_request(passport_no):
    try:
        # Parse JSON data from the request body
        update_data = request.get_json()

        if not update_data:
            return jsonify({"error": "No data provided"}), 400

        # Remove 'passport_no' from the update data if present
        update_data.pop('passport_no', None)

        # Perform the update in the database
        result = models.HealthPermitForm.update_one(
            {'passport_no': passport_no},
            {'$set': update_data}
        )

        # Check if the update was successful
        if result.modified_count > 0:
            return jsonify({
                "message": "Update successful",
                "updated_fields": update_data,
                "passport_no": passport_no
            }), 200
        else:
            return jsonify({
                "message": "No document found with the provided passport_no, or no changes were made",
                "passport_no": passport_no
            }), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/delete/<string:passport_no>', methods=['DELETE'])
def delete_request(passport_no):
    models.HealthPermitForm.delete_one({'passport_no': passport_no})
    return jsonify({"message": "Request deleted successfully"}), 200


@app.route("/customerService")
def customerService():
    return render_template("index.html")  # Serve the chatbot HTML


# Chatbot API endpoint
# main chatbot route

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_input = request.json.get("message", "").strip()
    user_id = request.json.get("user_id", "")

    if not user_id:
        return jsonify({"response": "User ID is required."})

    if user_id not in permit_data:
        permit_data[user_id] = {"state": "start", "form": {}, "current_field": None}

    state = permit_data[user_id]["state"]

    if is_greeting(user_input):
        if user_input.lower() == "menu":
            response = (
                "Welcome to the Medical Permit Chatbot! Please select an option:\n"
                "1. Guide line\n"
                "2. Ask a Question\n"
                "3. Start Medical Permit Request"
            )
            permit_data[user_id]["state"] = "main_menu"
        elif state == "start":  
            response = (
                "Hello! I'm here to help you with medical permits. "
                "Please select an option:\n"
                "1. Guide line\n"
                "2. Ask a Question\n"
                "3. Start Medical Permit Request"
            )
            permit_data[user_id]["state"] = "main_menu"  
        else:  
            response = (
                "Hello! How can I assist you today? "
                "Type 'menu' to return to the main menu."
            )
        return jsonify({"response": response})


    if state == "start":
        response = (
            "Please select an option:\n"
            "1. Guide line\n"
            "2. Ask a Question\n"
            "3. Start Medical Permit Request"
        )
        permit_data[user_id]["state"] = "main_menu"

    elif state == "main_menu":
        if user_input == "1":  
         response = (
             "Guide Line: This chatbot helps you submit a medical permit request. "
            "Here’s the process step-by-step:\n\n"
            "1. **Provide Basic Information**: You’ll be asked to provide your name, hospital details, preferred language, and date of joining.\n"
            "2. **Provide Medical Information**: You’ll need to share details such as marital status, phone number, urgency of the request, and your doctor’s name.\n"
            "3. **Provide Personal Information**: This includes your passport number and its expiry date.\n"
            "4. **Upload Required Documents**: You’ll need to upload the following files:\n"
            "   - **Identification Documents** (e.g., ID or passport)\n"
            "   - **Medical Documents** (e.g., medical reports or certificates)\n"
            "   - **Authorization Letter** (if applicable)\n"
            "5. **Confirm and Submit**: Once all details and documents are uploaded, you’ll review the information and confirm submission.\n\n"
            "Type 'menu' to return to the main menu or '3' to start the process now."
         )
         permit_data[user_id]["state"] = "guide_line"


        elif user_input == "2":  
            response = "Feel free to ask your question. I will do my best to assist you."
            permit_data[user_id]["state"] = "question_answer"

        elif user_input == "3":  
            response = "Great! Let’s start your medical permit request. Please provide your Full Name."
            permit_data[user_id]["state"] = "basic_info"
            permit_data[user_id]["current_field"] = "Patient Name"
            
        elif user_input.lower() == "menu":
            response = (
                "Welcome to the Medical Permit Chatbot! Please select an option:\n"
                "1. Guide line\n"
                "2. Ask a Question\n"
                "3. Start Medical Permit Request"
            )
            permit_data[user_id]["state"] = "main_menu"
        else:
            response = "Invalid option. Please select 1, 2, or 3."


    elif state == "guide_line":
        if user_input.lower() == "menu":
            response = (
                "Welcome to the Medical Permit Chatbot! Please select an option:\n"
                "1. Guide line\n"
                "2. Ask a Question\n"
                "3. Start Medical Permit Request"
            )
            permit_data[user_id]["state"] = "main_menu"
        elif user_input == "3":
            response = "Great! Let’s start your medical permit request. Please provide your Full Name."
            permit_data[user_id]["state"] = "basic_info"
            permit_data[user_id]["current_field"] = "Patient Name"
        else:
            response = "Invalid input. Type 'menu' to return to the main menu or '3' to start the permit request process."




    elif state == "question_answer":
     if user_input.lower() == "menu":
         response = (
            "Welcome to the Medical Permit Chatbot! Please select an option:\n"
            "1. Guide line\n"
            "2. Ask a Question\n"
            "3. Start Medical Permit Request"
        )
         permit_data[user_id]["state"] = "main_menu"
     else:
        #  faq_response = get_faq_response(user_input)
        
        #  if "I'm sorry" in faq_response:
        gpt_prompt = (
            f"Answer the user's query based on the context of medical permits:\n\n"
            f"User Query: {user_input}\n\nAnswer:"
        )
        gpt_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant specializing in medical permits."},
                {"role": "user", "content": gpt_prompt},
            ],
            max_tokens=150,
            temperature=0.5,
        )
        faq_response = gpt_response["choices"][0]["message"]["content"].strip()

        response = f"{faq_response}\n\nFeel free to ask another question or type 'menu' to return to the main menu."

    elif state == "basic_info":
      current_field = permit_data[user_id]["current_field"]
      form = permit_data[user_id]["form"]
      if is_question(user_input):
        # faq_response = get_faq_response(user_input)
        # if "I'm sorry" in faq_response:
        response = get_dynamic_response(user_input, current_field)
        # else:
        #     response = faq_response
        response += f"\n\nAfter resolving your query, please continue by providing your {current_field}."
        permit_data[user_id]["state"] = "basic_info"
      else:    
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
            if not validate_date(user_input):
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
     current_field = permit_data[user_id]["current_field"]
     form = permit_data[user_id]["form"]
     if is_question(user_input):
        # faq_response = get_faq_response(user_input)
        # if "I'm sorry" in faq_response:
        response = get_dynamic_response(user_input, current_field)
        # else:
        #     response = faq_response
        response += f"\n\nAfter resolving your query, please continue by providing your {current_field}."
        permit_data[user_id]["state"] = "medical_info"
     
     else: 

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
     current_field = permit_data[user_id]["current_field"]
     form = permit_data[user_id]["form"]
     if is_question(user_input):
        # faq_response = get_faq_response(user_input)
        # if "I'm sorry" in faq_response:
        response = get_dynamic_response(user_input, current_field)
        # else:
        #     response = faq_response
        response += f"\n\nAfter resolving your query, please continue by providing your {current_field}."
        permit_data[user_id]["state"] = "personal_info"
     
     else: 

        if current_field == "Passport Number":
            form["Passport Number"] = user_input
            response = "Enter your Passport Expiry Date (yyyy/mm/dd)."
            permit_data[user_id]["current_field"] = "Passport Expiry Date"
        elif current_field == "Passport Expiry Date":
            if not validate_date(user_input):
                response = "Invalid date format. Please provide the Passport Expiry Date in yyyy/mm/dd format."
            else:
                form["Passport Expiry Date"] = user_input
                response = "Please upload your Identification Documents."
                permit_data[user_id]["state"] = "documents"
                permit_data[user_id]["current_field"] = "Identification Documents"

    elif state == "documents":
        current_field = permit_data[user_id]["current_field"]
        form = permit_data[user_id]["form"]
        if is_question(user_input):
        #     faq_response = get_faq_response(user_input)
        #     if "I'm sorry" in faq_response:
            response = get_dynamic_response(user_input, current_field)
            # else:
            #     response = faq_response
            response += f"\n\nAfter resolving your query, please continue by providing your {current_field}."
            permit_data[user_id]["state"] = "documents"
        
        else: 

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
        if is_question(user_input):
            # faq_response = get_faq_response(user_input)
            # if "I'm sorry" in faq_response:
            response = get_dynamic_response(user_input, current_field)
            # else:
            #     response = faq_response
            response += f"\n\nAfter resolving your query, please continue by providing your {current_field}."
            permit_data[user_id]["state"] = "confirmation"
        
        else: 
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
        response = "Something went wrong. Please try again."
        permit_data[user_id]["state"] = "start"

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
    # socketio.run(app, port=9095)
    socketio.run(app, port=9095, allow_unsafe_werkzeug=True)