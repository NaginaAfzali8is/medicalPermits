from flask import Flask, request
import requests

app = Flask(__name__)

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

@app.route("/")
def home():
    client_ip = get_client_ip()
    if client_ip == "127.0.0.1":  # Localhost testing case
        return "Localhost detected. Use a real IP to test location."
    location = get_location_by_ip(client_ip)
    return f"Detected IP Address: {client_ip} <br> Location: {location}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
