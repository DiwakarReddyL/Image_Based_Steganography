from flask import Flask, render_template, request, send_file, jsonify
from stegano import lsb
import os
from cryptography.fernet import Fernet
import base64
import io

app = Flask(__name__)

# Configure Upload Folders
UPLOAD_FOLDER = "static/uploads"
ENCODED_FOLDER = "static/encoded_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCODED_FOLDER, exist_ok=True)

# Generate a Secret AES Key (Generate Only Once)
SECRET_KEY = Fernet.generate_key().decode()  # Save this key securely

def encrypt_message(message, key):
    """Encrypt a message using AES encryption."""
    cipher = Fernet(key.encode())
    return cipher.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message, key):
    """Decrypt a message using AES decryption."""
    cipher = Fernet(key.encode())
    return cipher.decrypt(encrypted_message.encode()).decode()

@app.route("/")
def home():
    """Render the main dashboard UI."""
    return render_template("index.html", secret_key=SECRET_KEY)

@app.route("/encode", methods=["POST"])
def encode():
    """Hide encrypted text inside an image and return it as a downloadable file."""
    image = request.files.get("image")
    secret_text = request.form.get("message", "")
    user_key = request.form.get("key", "")

    if not image or not secret_text or not user_key:
        return jsonify({"error": "Please provide an image, a message, and a key."})

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)

    try:
        # Encrypt the secret message
        encrypted_message = encrypt_message(secret_text, user_key)
    except Exception as e:
        return jsonify({"error": f"Encryption failed: {str(e)}"})

    # Encode the encrypted message into the image
    try:
        encoded_image = lsb.hide(image_path, encrypted_message)
        image_io = io.BytesIO()
        encoded_image.save(image_io, format="PNG")
        image_io.seek(0)

        return send_file(
            image_io,
            mimetype="image/png",
            as_attachment=True,
            download_name="encoded_image.png"
        )
    except Exception as e:
        return jsonify({"error": f"Image encoding failed: {str(e)}"})

@app.route("/decode", methods=["POST"])
def decode():
    """Extract and decrypt the hidden message from an image."""
    image = request.files.get("image")
    decryption_key = request.form.get("key", "")

    if not image or not decryption_key:
        return jsonify({"error": "Please provide an image and a decryption key."})

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    image.save(image_path)

    try:
        encrypted_text = lsb.reveal(image_path)
        if not encrypted_text:
            return jsonify({"error": "No hidden message found in the image."})

        decrypted_text = decrypt_message(encrypted_text, decryption_key)
        return jsonify({"message": decrypted_text})
    except Exception as e:
        return jsonify({"error": f"Decoding failed: {str(e)}"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
