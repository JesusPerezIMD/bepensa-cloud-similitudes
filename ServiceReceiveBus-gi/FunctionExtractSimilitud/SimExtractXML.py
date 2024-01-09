import os
import io
import json
from azure.storage.blob import BlobServiceClient
from xml.etree import ElementTree as ET
from PIL import Image
import hashlib
import requests
from typing import List, Any
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .SimTxT import ScoreSimilitudTxt
from .SimIMG import Compararimg

@dataclass
class SimilitudTXTDataRequest:
    brand_name: str
    brand_class: str
    page: int

@dataclass
class SimilitudTXTRequest:
    task_id: str
    data: List[SimilitudTXTDataRequest]

def load_local_settings():
    with open('../local.settings.json') as f:
        data = json.load(f)
    return data["Values"]
local_settings = load_local_settings()

def extract_data_from_xml(xml_content):
    data_list = []
    root = ET.fromstring(xml_content)
    logo_number = 1  # Inicializar el número de logo

    for ficha in root.findall(".//ficha"):
        brand_name = ""
        brand_class = ""
        image_url = {}

        for campo in ficha.findall(".//campo"):
            clave = campo.find("clave").text.strip()
            valor = campo.find("valor").text.strip()

            if clave == "Denominación":
                if valor == "null":
                    # Asignar un nombre de imagen predeterminado con número incrementado
                    brand_name = f"logo{logo_number}"
                    logo_number += 1
                else:
                    brand_name = valor
            elif clave == "Clase":
                brand_class = valor
            elif clave == "Imagen":
                image_url = valor

        data_list.append({
            'brand_name': brand_name,
            'brand_class': brand_class,
            'image_url': image_url
        })

    return data_list

def upload_to_blob_storage(connection_string, container_name, task_id, blob_name, data):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_name = f"data/{task_id}/api/{blob_name}"
    blob_client = blob_service_client.get_blob_client(container_name, blob_name)
    data_as_bytes = io.BytesIO(json.dumps(data, ensure_ascii=False).encode())
    blob_client.upload_blob(data_as_bytes.getvalue(), blob_type="BlockBlob", overwrite=True)

def download_from_blob_storage(connection_string, container_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container_name, f"tasks/{blob_name}")

    stream = blob_client.download_blob().readall()
    return stream

def process_xml_and_compute_similarity(task_id: str) -> dict:
    # Check if task_id and email are provided
    if not task_id:
        raise ValueError("Please provide both task_id")

    # Define your connection string and blob container name here
    connection_string = local_settings["AzureWebJobsStorage"]
    container_name = local_settings["GacetaContainerName"]
    blob_name = f"{task_id}.xml"

    # Download the PDF
    xml_bytes = download_from_blob_storage(connection_string, container_name, blob_name)
    xml_content = xml_bytes.decode('utf-8')

    data_brands = extract_data_from_xml(xml_content)
    image_hashes = set()
    i = 0
    image_dict = {}
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    for entry in data_brands:
        brand_name = entry['brand_name']
        brand_class = entry['brand_class']
        image_url = entry['image_url']

        # Check if the image URL is not empty
        if image_url:
            # Use requests to download the image
            response = requests.get(image_url)
            if response.status_code == 200:
                # Read image data and generate a unique image name
                image_data = response.content
                sha256 = hashlib.sha256()
                sha256.update(image_data)
                hash = sha256.hexdigest()
                if hash not in image_hashes:
                    image_stream = io.BytesIO(image_data)
                    image = Image.open(image_stream)
                    if image.mode in ("RGBA", "P"):
                        image = image.convert("RGB")
                    image_stream = io.BytesIO()
                    image.save(image_stream, format='JPEG')
                    image_stream.seek(0)
                    image_name = f"logo{i}.jpg"
                    image_dict[i] = {'logo': image_name, 'brand_name': brand_name, 'image_url': image_url}
                    img_blob_name = f"data/{task_id}/logos/{image_name}"
                    img_blob_client = blob_service_client.get_blob_client(container_name, img_blob_name)
                    img_blob_client.upload_blob(image_stream.getvalue(), overwrite=True)
                    i += 1
                    image_hashes.add(hash)

    text_data = {
        "task_id": task_id, 
        "data": data_brands
    }
    image_data = {
        "task_id": task_id, 
        "data": [{"logo": value['logo'], "brand_name": value['brand_name'], "image_url": value['image_url']} for value in image_dict.values()]  # Aquí añadimos el número de la página
    }

    upload_to_blob_storage(connection_string, container_name, task_id, "brands_request.json", text_data)
    upload_to_blob_storage(connection_string, container_name, task_id, "logos_request.json", image_data)

    # Similitud de texto
    brands_response = ScoreSimilitudTxt(text_data)
    upload_to_blob_storage(connection_string, container_name, task_id, "brands_response.json", brands_response)

    # Similitud de imágenes
    logos_response = []
    for img_data in image_data['data']:
        name = img_data['logo']
        denomination = img_data['brand_name']
        url = img_data['image_url']  # Recuerda que hemos añadido la página a image_data['data']

        similitudes = Compararimg(name, task_id, 50, "Similitud_Final")

        logos_response.append({
            'logo': name,
            'brand_name': denomination,
            'image_url' : url,
            'similitud_IMG': similitudes
        })

    logos_response_data = {
        'status': 'OK',
        'message': '',
        'task_id': task_id,
        'data': logos_response  # Ahora logos_response también tiene la información de la página
    }

    upload_to_blob_storage(connection_string, container_name, task_id, "logos_response.json", logos_response_data)

    similitud_response = {
        "status": "OK",
        "message": "",
        "task_id": task_id,
        "data_brands": brands_response['data'],
        "data_logos": logos_response
    }

    upload_to_blob_storage(connection_string, container_name, task_id, "Similitud.json", similitud_response)

    return similitud_response