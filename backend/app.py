from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes and all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Configure the Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-pro')
chat_session = model.start_chat(history=[])

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Send the message to Gemini and get the response
        response = chat_session.send_message(user_message)
        
        return jsonify({
            "reply": response.text,
            "success": True
        })
    except Exception as e:
        print(f"Error processing message: {str(e)}")  # Add debug output
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

# Add a simple test endpoint
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({"message": "Backend server is running!", "success": True})

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')