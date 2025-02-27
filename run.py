import requests
import os
from flask import Flask, redirect, request, jsonify, render_template
from flask_socketio import SocketIO
import models as models
import datetime
from flask_cors import CORS
# from datetime import datetime
import random
import re
import mimetypes
from flask import Flask, request, jsonify
import boto3
import bcrypt
import jwt

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


# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv('your_aws_access_key')
AWS_SECRET_KEY = os.getenv('your_aws_secret_key')
AWS_BUCKET_NAME = os.getenv('your_s3_bucket_name')
AWS_REGION = os.getenv('your_aws_region')

def upload_to_s3(file, bucket_name, file_name):
    """
    Uploads a file to an S3 bucket and returns the file's public URL.
    """
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )

               # Guess the ContentType from the file name
        import mimetypes
        content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

        s3.upload_fileobj(
            Fileobj=file,
            Bucket=bucket_name,
            Key=file_name,
            ExtraArgs={
                'ACL': 'public-read',  # Make the file publicly readable
                'ContentType': content_type  # Set the correct Content-Type
            }
        )

        file_url = f"https://{bucket_name}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
        return file_url
    except Exception as e:
        raise RuntimeError(f"Error uploading to S3: {e}")

        

# Convert Arabic/Persian numerals to English numerals
def convert_to_english_numerals(input_string):
    if not isinstance(input_string, str):  # Ensure it's a string
        input_string = str(input_string)
    
    arabic_to_english = str.maketrans(
        '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹',
        '01234567890123456789'
    )
    return input_string.translate(arabic_to_english)

# get ref status 
@app.route('/getStatus', methods=['GET'])
def get_status():
    """
    API to retrieve the status based on the reference ID (refID).
    """
    try:
        # Get refID from query parameters
        ref_id = request.args.get('refID')

         # Convert Arabic/Persian numerals to English numerals
        ref_id = convert_to_english_numerals(ref_id)

        if not ref_id:
            return jsonify({"error": "Reference ID (refID) is required"}), 400

        # Query the database for the record with the given refID
        record = models.HealthPermitForm.find_one({"reference_number": ref_id}, {"_id": 0})

        if not record:
            return jsonify({"error": "No record found with the provided refID"}), 404

        # Check if the status is "rejected" and include the reject reason if available
        response = {"status": record["status"]}
        if record["status"].lower() == "rejected":
            response["rejectReason"] = record.get("rejectReason", "No reject reason provided")

        # Return the response
        return jsonify(response)

        # Return the status
        # return jsonify({"status": record["status"]})

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": "An error occurred while retrieving the status", "details": str(e)}), 500


@app.route('/checkData', methods=['GET'])
def checkData():
    """
    API to retrieve the status based on the reference ID (refID) and passport number.
    """
    try:
        # Get refID and passport_no from query parameters
        ref_id = request.args.get('refID')

        # Convert Arabic/Persian numerals to English numerals
        ref_id = convert_to_english_numerals(ref_id)
        
        passport_no = request.args.get('passport_no')

        # Standardize the provided passport number to English numerals
        standardized_passport_no = convert_to_english_numerals(passport_no)

        # Fetch the record matching the refID
        record = models.HealthPermitForm.find_one(
            {"reference_number": ref_id},
        )

        if not record:
            return jsonify({"error": "No record found with the provided refID and passport number"}), 404

        # Standardize the passport number in the record
        record_passport_no = convert_to_english_numerals(record["passport_no"])

        # Compare the standardized passport numbers
        if standardized_passport_no != record_passport_no:
            return jsonify({"error": "No record found with the provided refID and passport number"}), 404

        # Check if the status is "rejected" and include the reject reason if available
        response = {"status": record["status"]}
        if record["status"].lower() == "rejected":
            response["rejectReason"] = record.get("rejectReason", "No reject reason provided")

        # Return the response
        return jsonify(response)

    except Exception as e:
        print({"error": str(e)})
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


@app.route('/existPhoneOld', methods=['GET'])
def check_phone_existenceOld():
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


@app.route('/existPhone', methods=['GET'])
def check_phone_existence():
    """
    API to check if a specific passport exists in the database.
    Passport can be in English numerals or Arabic/Persian numerals.
    """

    # Get the email from query parameters
    phone = request.args.get('phone')

    if not phone:
        return jsonify({"error": "passport parameter is required"}), 400

    try:
        # Convert the input passport number to English numerals
        standardized_phone = convert_to_english_numerals(phone)
            # Remove any spaces in the phone number
        standardized_phone = standardized_phone.replace(" ", "")
        # Ensure the phone number starts with a '+' character
        if not standardized_phone.startswith('+'):
            standardized_phone = f'+{standardized_phone}'

        # Fetch the record from the database
        # Fetch only `passport_no` and `_id` fields from the database
        phone_records = list(models.HealthPermitForm.find(
            {"phone_number": {"$exists": True}},  # Filter to include only documents with `phone_number`
            {"phone_number": 1, "_id": 1}  # Projection to include only `phone_number` and `_id`
        ))

        # Convert each record's `passport_no` to English numerals for comparison
        def is_phone_exist(records, standardized_phone):
            for record in records:
                db_passport = convert_to_english_numerals(record["phone_number"])
                if db_passport == standardized_phone:
                    return True
            return False

        phone_exists = is_phone_exist(phone_records, standardized_phone)

        # Return the result as a JSON response
        return jsonify({"exists": phone_exists})
    except Exception as e:
        # Handle any database or application errors
        return jsonify({"error": str(e)}), 500


@app.route('/existPassportOld', methods=['GET'])
def check_passport_existenceOld():
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
        print("error", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/existPassport', methods=['GET'])
def check_passport_existence():
    """
    API to check if a specific passport exists in the database.
    Passport can be in English numerals or Arabic/Persian numerals.
    """
    # Get the passport from query parameters
    passport = request.args.get('passport')

    if not passport:
        return jsonify({"error": "passport parameter is required"}), 400

    try:
        # Convert the input passport number to English numerals
        standardized_passport = convert_to_english_numerals(passport)

        # Fetch the record from the database
        # Fetch only `passport_no` and `_id` fields from the database
        passport_records = models.HealthPermitForm.find(
            {},  # Empty filter to fetch all documents
            {"passport_no": 1, "_id": 1}  # Projection to include only `passport_no` and `_id`
        )

        # Convert each record's `passport_no` to English numerals for comparison
        def is_passport_exist(records, standardized_passport):
            for record in records:
                db_passport = convert_to_english_numerals(record["passport_no"])
                if db_passport == standardized_passport:
                    return True
            return False

        passport_exists = is_passport_exist(passport_records, standardized_passport)

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


@app.route('/saveNewRecord', methods=['POST'])
def saveNewRecord():
    """
    API to save data to MongoDB.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid input. Please provide JSON data."}), 400

       
        # Generate a unique reference number
        def generate_unique_reference():
            while True:
                reference_number = f"HP-{random.randint(10000000, 99999999)}"  # 8-digit number
                existing_entry = models.HealthPermitForm.find_one({"reference_number": reference_number})
                if not existing_entry:
                    return reference_number

        # Assign the generated reference number
        # data['reference_number'] = generate_unique_reference()

        # Add timestamps
        now = datetime.datetime.utcnow()
        data['created_at'] = now
        data['updated_at'] = now

        # Set default status
        data['status'] = 'pending'

        # Insert the data into MongoDB
        result = models.HealthPermitForm.insert_one(data)

        return jsonify({
            "success": True,
            "message": "Data saved successfully",
            "reference_number": data['reference_number'],  # Return the generated reference number
            "id": str(result.inserted_id)  # Return the inserted document's ID
        }), 201

    except Exception as e:
        print({"error": str(e)})
        return jsonify({
            "success": False,
            "message": "Something went wrong, Please start the process again",
            "error": str(e)}), 500
    

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
            'hospital', 'medical_doc', 'authorization_letter', 'visaAssistant'
        ]
        missing_fields = [field for field in required_fields if field not in data]

        # if missing_fields:
        #     return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Validate patient_name as an object with 'first' and 'last' keys
        # Validate and merge patient_name
        # if not isinstance(data.get('patient_name'), dict) or 'first' not in data['patient_name']:
        #     return jsonify({"error": "Invalid patient_name. Must be an object with 'first' and optionally 'last' keys."}), 400

        # Merge first and last name into a single string
        # Merge first and last name into a single string, handling None values
        first_name = (data['patient_name'].get('first') or '').strip()
        last_name = (data['patient_name'].get('last') or '').strip()
        data['patient_name'] = f"{first_name} {last_name}".strip()


        def is_valid_file(url, valid_types):
            # Extract MIME type based on the file extension
            mime_type, _ = mimetypes.guess_type(url)
            return mime_type in valid_types if mime_type else False

        # Define valid MIME types
        image_types = ['image/jpeg', 'image/png', 'application/pdf']
        file_types = ['application/pdf']



        # Extract URLs for file fields
        data['medical_doc'] = extract_url(data.get('medical_doc', ''))
        data['authorization_letter'] = extract_url(data.get('authorization_letter', ''))

        # Extract fields
        medical_doc_url = data.get('medical_doc', '')
        authorization_letter_url = data.get('authorization_letter', '')

        # Validate medical_doc
        if not medical_doc_url or not is_valid_file(medical_doc_url, image_types):
            return jsonify({"success": False, "fileError": "Medical doc must be a valid file or image"}), 400

        # Validate authorization_letter
        if not authorization_letter_url or not is_valid_file(authorization_letter_url, image_types):
            return jsonify({"success": False, "fileError": "Referral letter must be a valid file or image"}), 400



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
        now = datetime.datetime.utcnow()
        data['created_at'] = now
        data['updated_at'] = now

        # Set default status
        data['status'] = 'pending'

        # Insert the data into MongoDB
        result = models.HealthPermitForm.insert_one(data)

        return jsonify({
            "success": True,
            "message": "Data saved successfully",
            "reference_number": data['reference_number'],  # Return the generated reference number
            "id": str(result.inserted_id)  # Return the inserted document's ID
        }), 201

    except Exception as e:
        print({"error": str(e)})
        return jsonify({
            "success": False,
            "message": "Something went wrong, Please start the process again",
            "error": str(e)}), 500



@app.route('/updateData/<string:reference_number>', methods=['PUT'])
def update_datafile(reference_number):
    """
    API to update fields in MongoDB and upload a file to an S3 bucket.
    """
    try:
        # Parse JSON data and file from the request
        update_data = request.form.to_dict()
        file_medical_doc = request.files.get('medical_doc')
        file_authorization_letter = request.files.get('authorization_letter')

        # if not update_data and not (file_medical_doc or file_authorization_letter):
        #     return jsonify({"error": "Invalid input. Please provide data or a file."}), 400

        # Check if the entry exists in the database
        existing_entry = models.HealthPermitForm.find_one({"reference_number": reference_number})
        if not existing_entry:
            return jsonify({"error": "Data not found."}), 404

        # Exclude reference_number and passport_number from the update data
        update_data.pop('reference_number', None)
        update_data.pop('passport_number', None)

        # Rename fields to match the required format
        rename_fields = {
            "patientName": "patient_name",
            "phoneNumber": "phone_number",
            "emailAddress": "email_address",
           "passportNo" : "passport_no",
           "referenceNumber" : "reference_number",
        }
        
        for old_key, new_key in rename_fields.items():
            if old_key in update_data:
                update_data[new_key] = update_data.pop(old_key)

        # Add the updated_at timestamp
        update_data['updated_at'] = datetime.datetime.utcnow()

        if file_medical_doc or file_authorization_letter:
            # Handle file uploads to S3
            for file, key in [(file_medical_doc, 'medical_doc'), (file_authorization_letter, 'authorization_letter')]:
                if file:
                    # Generate a unique filename based on current datetime
                    current_datetime = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
                    file_extension = file.filename.split('.')[-1]
                    file_name = f"{current_datetime}.{file_extension}"

                    try:
                        # Upload the file to S3
                        file_url = upload_to_s3(file, AWS_BUCKET_NAME, file_name)
                        update_data[key] = file_url  # Add the S3 URL to the update data
                    except Exception as e:
                        return jsonify({"error": f"Failed to upload {key} to S3: {e}"}), 500

        # Update the record in MongoDB
        result = models.HealthPermitForm.update_one(
            {"reference_number": reference_number},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            return jsonify({
                "success": True,
                "message": "Data updated successfully",
                "file_url": update_data.get('medical_doc')
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No changes made to the record"
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
     


@app.route('/updateDatawithoutFile/<string:passport_no>', methods=['PUT'])
def update_datawithoutFile(passport_no):
    """
    API to update fields in MongoDB, excluding passport_no and passport_number.
    """
    try:
        # Parse JSON data from the request
        update_data = request.get_json()

        if not update_data:
            return jsonify({"error": "Invalid input. Please provide JSON data."}), 400

        # Ensure passport_no exists in the database
        existing_entry = models.HealthPermitForm.find_one({"passport_no": passport_no})
        if not existing_entry:
            return jsonify({"error": "Reference number not found."}), 404

        # Exclude reference_number and passport_number from the update data
        if 'reference_number' in update_data:
            del update_data['reference_number']
        if 'passport_number' in update_data:
            del update_data['passport_number']

        # Add the updated_at timestamp
        update_data['updated_at'] = datetime.datetime.utcnow()

        # Update the record in MongoDB
        result = models.HealthPermitForm.update_one(
            {"passport_no": passport_no},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            return jsonify({
                "success": True,
                "message": "Data updated successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "No changes made to the record"
            }), 200

    except Exception as e:
        print({"error": str(e)})
        return jsonify({
            "success": False,
            "message": "Something went wrong, Please try again",
            "error": str(e)
        }), 500



@app.route('/saveDataMB', methods=['POST'])
def save_data_MB():
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
            'hospital', 'medical_doc', 'authorization_letter', 'visaAssistant'
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
        # data['medical_doc'] = extract_url(data.get('medical_doc', ''))
        # data['identification_doc'] = extract_url(data.get('identification_doc', ''))
        # data['authorization_letter'] = extract_url(data.get('authorization_letter', ''))




        # Generate a unique reference number
        def generate_unique_reference():
            while True:
                reference_number = f"HP-{random.randint(10000000, 99999999)}"  # 8-digit number
                existing_entry = models.HealthPermitForm.find_one({"reference_number": reference_number})
                if not existing_entry:
                    return reference_number

        # Assign the generated reference number
        data["reference_number"] = generate_unique_reference()

        # Add timestamps
        now = datetime.datetime.utcnow()
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


@app.route("/ipAddress")
def ipAddress():
    client_ip = get_client_ip()
    if client_ip == "127.0.0.1":  # Localhost testing case
        return "Localhost detected. Use a real IP to test location."
    location = get_location_by_ip(client_ip)
    return f"Detected IP Address: {client_ip} <br> Location: {location}"


@app.route('/getAllUsersData', methods=['GET'])
def read_requests():
    requests = list(models.HealthPermitForm.find({}, {'_id': 0}))  # Exclude MongoDB ObjectID
    return jsonify(requests), 200



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
        if data['date_of_joining'] and isinstance(data['date_of_joining'], datetime.datetime):
            data['date_of_joining'] = data['date_of_joining'].strftime('%Y-%m-%d')
    if 'passport_exp_date' in data:
        if data['passport_exp_date'] and isinstance(data['passport_exp_date'], datetime.datetime):
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

        # Check if 'rejectReason' is part of the update data
        if 'rejectReason' in update_data:
            # Update or insert the `rejectReason`
            reject_reason = update_data.pop('rejectReason')  # Extract the rejectReason value
            update_data['rejectReason'] = reject_reason  # Ensure rejectReason is updated or added

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


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()

    # Extract required fields (adjust as needed)
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email, and password are required'}), 400

    # Check if the owner already exists
    if models.Owner.find_one({'email': email}):
        return jsonify({'error': 'Owner already registered'}), 400

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Create the owner record
    owner = {
        'username': username,
        'email': email,
        'password': hashed_password,
        'created_at': datetime.datetime.utcnow()
    }

    models.Owner.insert_one(owner)
    return jsonify({'message': 'Signup successful'}), 201

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Find the owner by email
    owner = models.Owner.find_one({'email': email})
    if not owner:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Verify the password
    if not bcrypt.checkpw(password.encode('utf-8'), owner['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Generate a JWT token that expires in 24 hours
    token = jwt.encode({
        'user_id': str(owner['_id']),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token}), 200


# Chatbot API endpoint
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