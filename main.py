import json
from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
import cv2
import mysql.connector
from keras.models import load_model
import datetime
import io
from PIL import Image
import requests

from mysql.connector import Error
import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.uploader import upload
from cloudinary.utils import cloudinary_url


app = Flask(__name__)

# Load Model
model = load_model('E:/NgodinG/Python/kuliah/semes4/ppl/Train/mobilenetv2_1.00_224-Chicken Disease-95.91.h5')

cloudinary.config(
    cloud_name = "dqjhykebs",
    api_key = "662587477953516",
    api_secret = "vfv7KxeXed6i9CuOu4odEZLYLOo"
)
# Function to preprocess the image
def preprocess_image(image):
    # Preprocess the image (resize, convert to RGB, etc.)
    # You may need to adjust this based on your model's input requirements
    image = cv2.resize(image, (224, 224))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = image.astype(np.float32) / 255.0
    return image


def get_class_name(predicted_class):
    # Karena kita menggunakan generator yang menghasilkan one-hot encoding,
    # mari kita gunakan np.argmax untuk mendapatkan kelas dengan nilai probabilitas tertinggi
    if predicted_class == 1:
        return "Coccidiosis"
    elif predicted_class == 0:
        return "Healthy"
    elif predicted_class == 2:
        return "New Castle Disease"
    elif predicted_class == 3:
        return "Salmonella"
    else:
        return "Undifined"


# Function to save prediction to MySQL database
def save_to_database(class_name, image_url, user_id):
    # Connect to MySQL database
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chicheck"
    )
    cursor = connection.cursor()
    # Insert prediction into database table
    if class_name == "Healthy":  # Healthy
        description = "Ayam dalam keadaan sehat"
        solution = "-"
    elif class_name == "Salmonella":  # Salmonella
        description = "Penyebab: Bakteri Salmonella spp. Penularan: Feses yang terkontaminasi, kontak dengan hewan yang terinfeksi, telur yang terkontaminasi."
        solution = ""
    elif class_name == "New Castle Disease":  # New Castle Disease
        description = "Penyebab: Virus Avian Paramyxovirus serotype 1 (APMV-1). Penularan: Kontak langsung dengan hewan yang terinfeksi, aerosol (percikan air liur), feses. Gejala: Batuk, bersin, sesak napas, tremor, sayap terkulai, diare, kematian mendadak."
        solution = "Pengobatan: Tidak ada, hanya pengobatan suportif. Pencegahan: Vaksinasi, sanitasi kandang yang baik, biosecurity yang ketat."
    elif class_name == "Coccidiosis":  # Coccidiosis
        description = "Penyebab: Parasit protozoa Eimeria spp. Penularan: Oosista (telur parasit) yang terkontaminasi di tanah, air, atau makanan. Gejala: Diare berdarah, lemas, nafsu makan menurun, penurunan produksi telur."
        solution = "Pengobatan: Anticoccidial (obat anti-parasit), elektrolit, vitamin. Pencegahan: Sanitasi kandang yang baik, koksiidiostat (obat pencegah) dalam pakan."
    else:
        description = "Prediksi tidak diketahui"
        solution = "Prediksi tidak diketahui"

    cursor.execute("INSERT INTO predictions (penyakit, deskripsi, solusi, img_url, user_id) VALUES (%s, %s, %s, %s, %s)", (class_name, description, solution, image_url, user_id))
    connection.commit()
    # Close connection
    cursor.close()
    connection.close()




@app.route('/predict', methods=['POST'])
def predict():
    # Terima gambar dari permintaan POST
    image_file = request.files['image']
    user_id = request.form.get('user_id')

    time_now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    original_file_name = 'original_image' + '_' + time_now + '.jpg'
    
    # Baca gambar dan ubah menjadi array numpy
    img = cv2.imdecode(np.fromstring(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
    
    # Preprocessing gambar sesuai dengan kebutuhan model
    # (misalnya, ubah ukuran gambar, normalisasi, dll.)
    img = preprocess_image(img)
    
    # Lakukan prediksi menggunakan model
    predictions = model.predict(np.expand_dims(img, axis=0))
    
    # Ambil label kelas prediksi
    predicted_class = np.argmax(predictions)
    
    # Konversi label kelas menjadi kelas sebenarnya (misalnya, dari angka menjadi nama penyakit)
    class_name = get_class_name(predicted_class)
    print(class_name)
    

    image = Image.open(image_file)
    with io.BytesIO() as output:
        image.save(output, format="JPEG")
        image_bytes = output.getvalue()

    # Unggah gambar ke Cloudinary
    processed_file_name = 'processed_images/process_image' + '_' + time_now + '.jpg'
    # upload_result = upload(image_bytes, folder="predictions", public_id=processed_file_name)

    # Get URL of the uploaded image
    # image_url, _ = cloudinary_url(upload_result['public_id'], format=upload_result['format'])

    upload_response = cloudinary.uploader.upload(image_bytes, folder="predictions", public_id=processed_file_name)
    image_url = upload_response['secure_url']



    save_to_database(class_name, image_url, user_id)

    message = {
        'user_id': user_id,
        'status': 200,
        'message': 'OK',
        'hasil': class_name, 
        'processed_image': image_url
    }

    # url = "http://127.0.0.1:8000/predict"
    # r = requests.post(url, json=json.dumps(message))

    return jsonify(message)

if __name__ == '__main__':
    app.run()
