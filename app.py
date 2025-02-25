from flask import Flask, render_template, request, send_file, jsonify
from stegano import lsb
import os
from cryptography.fernet import Fernet
import base64
import io

app = Flask(__name__)

# Configure Upload Folder
UPLOAD_FOLDER = "static/uploads"
ENCODED_FOLDER = "static/encoded_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCODED_FOLDER, exist_ok=True)

# Generate a secret AES key (only generate once & save securely)
def generate_key():
    return base64.urlsafe_b64encode(os.urandom(32))  # Generates a random AES key

SECRET_KEY = generate_key().decode()  # Save this key securely

def encrypt_message(message, key):
    """ Encrypt message using AES """
    cipher = Fernet(key.encode())
    return cipher.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message, key):
    """ Decrypt message using AES """
    cipher = Fernet(key.encode())
    return cipher.decrypt(encrypted_message.encode()).decode()

@app.route("/")
def home():
    return render_template("index.html", secret_key=SECRET_KEY)

@app.route("/encode", methods=["POST"])
def encode():
    """ Hide encrypted text inside an image & return as downloadable file """
    if "image" not in request.files or request.files["image"].filename == "":
        return jsonify({"error": "No image uploaded"})

    image = request.files["image"]
    secret_text = request.form["message"]
    user_key = request.form["key"]

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    encoded_image_path = os.path.join(ENCODED_FOLDER, "encoded_" + image.filename)

    image.save(image_path)  # Save uploaded image

    try:
        # Encrypt the secret text using the user-provided key
        encrypted_message = encrypt_message(secret_text, user_key)
    except:
        return jsonify({"error": "Invalid encryption key!"})

    # Encode encrypted text into the image
    encoded_image = lsb.hide(image_path, encrypted_message)
    
    # Save the encoded image in memory for direct download
    image_io = io.BytesIO()
    encoded_image.save(image_io, format="PNG")
    image_io.seek(0)

    return send_file(
        image_io,
        mimetype="image/png",
        as_attachment=True,
        download_name="encoded_image.png"
    )

@app.route("/decode", methods=["POST"])
def decode():
    """ Extract and decrypt hidden text from an image """
    if "image" not in request.files or request.files["image"].filename == "":
        return jsonify({"error": "No image uploaded"})

    image = request.files["image"]
    decryption_key = request.form["key"]

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)  # Save uploaded image

    try:
        # Extract the hidden message
        encrypted_text = lsb.reveal(image_path)
        # Decrypt the message using the provided key
        decrypted_text = decrypt_message(encrypted_text, decryption_key)
        return jsonify({"message": decrypted_text})
    except:
        return jsonify({"error": "Invalid key or no hidden message found!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Dynamic Port Support for Render
    app.run(host="0.0.0.0", port=port, debug=True)
