import os
import logging
import io
import uuid
import json
from google.cloud import pubsub_v1
from azure.storage.blob import BlobServiceClient
import requests

# Functions for Blob Storage
def upload_to_blob_storage(connection_string, container_name, task_id, blob_name, file):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container_name, f"data/{task_id}/{blob_name}")
    
    blob_client.upload_blob(file, overwrite=True)

def send_message_to_pubsub(project_id, topic_id, message_body):
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    message_bytes = message_body.encode('utf-8')
    future = publisher.publish(topic_path, message_bytes)
    return future.result()

def load_local_settings():
    with open('../local.settings.json') as f:
        data = json.load(f)
    return data["Values"]
local_settings = load_local_settings()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '../service-account-key.json'

def main(request):
    storage_connection_string = local_settings["AzureWebJobsStorage"]
    container_name = local_settings["GacetaContainerName"]
    task_id = str(uuid.uuid4())
    blob_name = f"{task_id}.xml"

    email = request.form.get('email')
    if email is None:
        return 'Please provide email in the request form data.', 400
    
    file = request.files.get('file')
    if file is None:
        return 'Please provide file data in the request form data.', 400
    
    upload_to_blob_storage(storage_connection_string, container_name, task_id, blob_name, file.stream.read())

    project_id = "mindful-audio-410619"
    topic_id = "topic-example"

    message = {"task_id": task_id, "email": email}
    message_body = json.dumps(message)

    # Sending the message to Azure Service Bus
    send_message_to_pubsub(project_id, topic_id, message_body)

    final_response = {
        "status": "OK",
        "message": "COMPLETE",
        "task_id": task_id
    }

    return json.dumps(final_response, ensure_ascii=False), 200, {'Content-Type': 'application/json'}