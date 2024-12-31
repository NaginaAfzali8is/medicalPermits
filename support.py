import openai
import json
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import Flask, request, jsonify
# from sentence_transformers import SentenceTransformer, util
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv('api_key'),  # This is the default and can be omitted
)


ALLOWED_EXTENSIONS = {"pdf", "jpg", "png"} 
# Helper function to check allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Set your OpenAI API key
openai.api_key = os.getenv('api_key')

# Helper function to validate date format
def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# Helper function to get the response from gpt 
def get_dynamic_response(user_input, current_field=None):
    """
    Generate a dynamic response using GPT for unmatched queries.
    """
    gpt_prompt = (
        f"Provide an appropriate response to the user's query based on the context of medical permits.\n\n"
        f"User Query: {user_input}\n\n"
        f"{f'Field: {current_field}' if current_field else ''}\n\nAnswer:"
    )
    # gpt_response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=[
    #         {"role": "system", "content": "You are an assistant specializing in medical permits and general inquiries."},
    #         {"role": "user", "content": gpt_prompt},
    #     ],
    #     max_tokens=150,
    #     temperature=0.5,
    # )
    # return gpt_response["choices"][0]["message"]["content"].strip()
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",  # Specify the model you are using
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": gpt_prompt}  # Replace `user_input` with the actual input
    #     ]
    # )
    gpt_response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an assistant specializing in medical permits and general inquiries."},
            {"role": "user", "content": gpt_prompt},
            ],
            model="gpt-4o",
        )

    # Access the response text
    # reply = response.choices[0].message.content
    return gpt_response.choices[0].message.content

def is_greeting(user_input):
    greetings = ["hi", "hello", "hey", "how are you", "good morning", "good evening"]
    return any(greet in user_input.lower() for greet in greetings)

def is_question(user_input):
    question_keywords = ["why", "what", "how", "when", "who", "where"]
    return any(word in user_input.lower() for word in question_keywords) or "?" in user_input

# Context-based explanations for form fields
context_explanations = {
    "Patient Name": "Your full name is required to identify you and link your details with your request.",
    "Hospital Name": "The hospital name is required to verify your treatment location and to coordinate with the medical authorities or committees reviewing your request.",
    "Preferred Language": "Your preferred language is needed to ensure we communicate with you effectively and provide documents in your language.",
    "Date of Joining": "The date of joining helps us verify when your treatment process or referral began.",
    "Marital Status": "Please specify your marital status. For example, you can answer 'single', 'married', 'divorced', or 'widowed'.",
    "Phone Number": "Your phone number is needed to contact you for updates and notifications about your request.",
    "Urgent Need": "Knowing whether your request is urgent helps us prioritize cases that require immediate attention.",
    "Doctor Name": "The name of your doctor is required to verify your medical history and coordinate with the medical authority.",
    "Passport Number": "Your passport number is necessary for identity verification and processing international treatment requests.",
    "Passport Expiry Date": "The expiry date of your passport ensures your travel documents are valid for the duration of the process.",
    "Identification Documents": "Identification documents, such as a passport or national ID, are required to verify your identity and process your application.",
    "Medical Documents": "Medical documents, including reports or referrals, are necessary to evaluate your medical condition and support your permit request.",
    "Authorization Letter": "An authorization letter is required if someone else is submitting the application on your behalf or to confirm permissions related to your case.",
    "confirmation": "This is the final stage where you review all the information you have provided, confirm its accuracy, and submit your request. You can also edit any section before submission."
}



