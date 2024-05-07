import tensorflow as tf
import cv2
from io import BytesIO
import keras
import keras_cv
import numpy as np
import mysql.connector
from mysql.connector import Error
import datetime
import cloudinary
import cloudinary.uploader
import cloudinary.api

def load_model(model_path):
    with keras.utils.custom_object_scope({"YOLOV8Detector": keras_cv.models.YOLOV8Detector}):
        model = tf.keras.models.load_model(model_path, compile=False)
    return model



# Inisialisasi Cloudinary
cloudinary.config(
    cloud_name = "dqjhykebs",
    api_key = "662587477953516",
    api_secret = "vfv7KxeXed6i9CuOu4odEZLYLOo"
)

def upload_image_to_cloudinary(blob_name, image):
    # Unggah gambar ke Cloudinary
    result = cloudinary.uploader.upload(image, public_id=blob_name)
    return result['secure_url']
    

def read_image_from_cloudinary(blob_name):
    # Baca gambar dari Cloudinary
    result = cloudinary.api.resource(blob_name)
    img = result['secure_url']
    # Kemudian Anda dapat menggunakan image_url untuk membaca gambar dari URL
    return img

def get_prediction(image, model):
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = tf.image.resize(image, (256, 256))
    image = tf.expand_dims(image, axis=0)
    predictions = model.predict(image)
    return predictions


def draw_prediction(image, model):
    # compute class mapping
    class_ids = ["salmo", 'cocci', 'healthy', 'ncd',]
    class_mapping = dict(zip(range(len(class_ids)), class_ids))
    color_list = [(231, 76, 60), (52, 152, 219), (39, 231, 96), (243, 156, 18)]
    # get original image
    original_image = image

    # original_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
    width = original_image.shape[1]
    height = original_image.shape[0]

    # get scaled image
    scale_width = width / 256
    scale_height = height / 256

    # get predictions
    predictions = get_prediction(image, model)

    # get boxes, confindences and classes
    num_detections = int(predictions['num_detections'][0])
    classes = predictions['classes'][0]
    confindences = predictions['confidence'][0]
    boxes = predictions['boxes'][0]
    results = []

    for i in range(num_detections):
        class_id = int(classes[i])
        x, y, w, h = boxes[i]
        x1 = int(x * scale_width)
        y1 = int(y * scale_height)
        w = int(w * scale_width)
        h = int(h * scale_height)
        x2 = x1 + w
        y2 = y1 + h
        # check if box is out of bounds
        if x1 < 0:
            x1 = int(0 + width*0.05)
        if y1 < 0:
            y1 = int(0 + height*0.05)
        if x2 > width:
            x2 = int(width - width*0.05)
        if y2 > height:
            y2 = int(height - height*0.05)

        cv2.rectangle(original_image, (x1, y1),(x2, y2), color_list[class_id], 1)

        linewidth = min(int((x2-x1)*0.2), int((y2-y1)*0.2))
        cv2.line(original_image, (x1, y1),(x1+linewidth, y1), color_list[class_id], 4)
        cv2.line(original_image, (x1, y1),(x1, y1+linewidth), color_list[class_id], 4)
        cv2.line(original_image, (x2, y1),(x2-linewidth, y1), color_list[class_id], 4)
        cv2.line(original_image, (x2, y1),(x2, y1+linewidth), color_list[class_id], 4)

        cv2.line(original_image, (x1, y2),(x1+linewidth, y2), color_list[class_id], 4)
        cv2.line(original_image, (x1, y2),(x1, y2-linewidth), color_list[class_id], 4)
        cv2.line(original_image, (x2, y2),(x2-linewidth, y2), color_list[class_id], 4)
        cv2.line(original_image, (x2, y2),(x2, y2-linewidth), color_list[class_id], 4)
        results.append({
            'class': class_id,
            'confidence': str(confindences[i]),
            'boxes': [str(x1), str(y1), str(x2), str(y2)]
        })

    # save image
    # cv2.imwrite('prediction.jpg',original_image)
    return results, original_image

        
def save_to_database(prediction):
    # Connect to MySQL database
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="chicheck"
    )
    cursor = connection.cursor()
    # Insert prediction into database table
    if prediction == 0:  # Healthy
        description = "Ayam dalam keadaan sehat"
        solution = "-"
    elif prediction == 1:  # Salmonella
        description = "Penyebab: Bakteri Salmonella spp. Penularan: Feses yang terkontaminasi, kontak dengan hewan yang terinfeksi, telur yang terkontaminasi."
        solution = ""
    elif prediction == 2:  # New Castle Disease
        description = "Penyebab: Virus Avian Paramyxovirus serotype 1 (APMV-1). Penularan: Kontak langsung dengan hewan yang terinfeksi, aerosol (percikan air liur), feses. Gejala: Batuk, bersin, sesak napas, tremor, sayap terkulai, diare, kematian mendadak."
        solution = "Pengobatan: Tidak ada, hanya pengobatan suportif. Pencegahan: Vaksinasi, sanitasi kandang yang baik, biosecurity yang ketat."
    elif prediction == 3:  # Coccidiosis
        description = "Penyebab: Parasit protozoa Eimeria spp. Penularan: Oosista (telur parasit) yang terkontaminasi di tanah, air, atau makanan. Gejala: Diare berdarah, lemas, nafsu makan menurun, penurunan produksi telur."
        solution = "Pengobatan: Anticoccidial (obat anti-parasit), elektrolit, vitamin. Pencegahan: Sanitasi kandang yang baik, koksiidiostat (obat pencegah) dalam pakan."
    else:
        description = "Prediksi tidak diketahui"
        solution = "Prediksi tidak diketahui"

    cursor.execute("INSERT INTO predictions (penyakit, deskripsi, solusi, img_url, probability) VALUES (%s, %s, %s, %s)", (prediction, description, solusion, processed_image_url))
    connection.commit()
    # Close connection
    cursor.close()
    connection.close()

