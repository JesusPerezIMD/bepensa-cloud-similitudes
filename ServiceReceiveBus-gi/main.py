from google.cloud import pubsub_v1
import json
import logging
import os
import requests
from FunctionExtractSimilitud.SimExtractXML import process_xml_and_compute_similarity

def load_local_settings():
    with open('../local.settings.json') as f:
        data = json.load(f)
    return data["Values"]
local_settings = load_local_settings()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '../service-account-key.json'

def main(project_id, subscription_id):
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    def callback(message):
        message_data = message.data.decode('utf-8')
        data = json.loads(message_data)

        # Proceso del mensaje
        task_id = data.get('task_id', None)
        print(f"Task ID: {task_id}")
        email = data.get('email', None)
        print(f"Email: {email}")
        if task_id is None or email is None:
            logging.error("task_id or email is not found in the message")
            return

        try:
            # Procesar el XML y calcular la similitud
            result = process_xml_and_compute_similarity(task_id)
            print("Process similarity successfully.")
            email_subject = "Notificación - Gaceta IMPI"
            email_body = f'Se realizó el cálculo de similitudes, para ver los resultados haga clic en el siguiente botón<br><br><a href="{local_settings["GacetaAppUrl"]}?uuid={task_id}" style="color: #fff; background-color: #008CBA;text-decoration: none; padding: 10px 15px; border-radius: 4px;">Ver Reporte</a><br><br><br>'
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            email_subject = "Error en Procesamiento - Gaceta IMPI"
            email_body = f'Ocurrió un error al procesar el archivo: {e}'

        # Define el cuerpo JSON para la solicitud de la API
        body = {
            "to": [email],
            "subject": email_subject,
            "body": email_body
        }

        # Enviar una solicitud POST a la API
        response = requests.post(f'{local_settings["BConnectApiUrl"]}/Email/SendEmail', json=body)

        # Verificar la respuesta
        if response.status_code == 200:
            logging.info("Email sent successfully.")
            print("Email sent successfully.")
        else:
            logging.error(f"Failed to send email. Status code: {response.status_code}. Response: {response.text}")

        message.ack()

    future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        future.result()
    except KeyboardInterrupt:
        future.cancel()

main("mindful-audio-410619", "my-subscription")
