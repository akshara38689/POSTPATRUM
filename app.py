import os
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize Gemini API Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Gemini Model
model = "gemini-2.0-flash"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json["message"]

    # Chatbot prompt
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=user_input)])
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=2,
        top_p=0.95,
        top_k=40,
        max_output_tokens=8192,
        response_mime_type="text/plain",
    )

    # Get Response from Gemini
    response = ""
    for chunk in client.models.generate_content_stream(model=model, contents=contents, config=generate_content_config):
        response += chunk.text

    return jsonify({"response": response})


if __name__ == "__main__":
    app.run(debug=True)
