import sys
import pandas as pd
import re
import requests
import os
import io
import numpy as np
from keras.models import Model
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,QHBoxLayout,QSpacerItem,QSizePolicy,QTextEdit,QToolButton, QTableWidget, QTableWidgetItem
# from keras.applications.vgg19 import VGG19
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
#import h5py
import cv2
import os
from keras.applications.vgg16 import VGG16, preprocess_input
from scipy.spatial.distance import cosine
import json

def load_local_settings():
    with open('../local.settings.json') as f:
        data = json.load(f)
    return data["Values"]
local_settings = load_local_settings()

container_path=f'{local_settings["GacetaStorageUrl"]}/{local_settings["GacetaContainerName"]}/'
archivo="assets/csv/ImgBepensa.csv"
urldoc=container_path+archivo

# Enviar solicitud HTTP y obtener la respuesta
response2 = requests.get(urldoc)

# Verificar si la solicitud fue exitosa
if response2.status_code == 200:
    # Obtener contenido de la respuesta
    contenido2 = response2.content
    contenido2_csv = io.StringIO(contenido2.decode('utf-8'))
    dataframe2 = pd.read_csv(contenido2_csv)
#df=pd.read_csv(contenido)

bepensa_logos_subfolder = "assets/logos/"

### Cargar el modelo VGG16
global vgg16
vgg16 = VGG16(weights='imagenet', include_top=True, pooling='max', input_shape=(224, 224, 3))
## Configurar el modelo VGG16
global basemodel
basemodel = Model(inputs=vgg16.input, outputs=vgg16.get_layer('fc2').output)

def get_feature_vector(img):
                
    global basemodel
    img1 = cv2.resize(img, (224, 224))
    feature_vector = basemodel.predict(img1.reshape(1, 224, 224, 3))
    return feature_vector

# global basemodelvgg19
# vgg19 = VGG19(weights='imagenet', include_top=True, pooling='max', input_shape=(224, 224, 3))

# basemodelvgg19 = Model(inputs=vgg19.input, outputs=vgg19.get_layer('fc2').output)
# ##### generar vector modelo vgg16
# def get_feature_vector19(img):
                
#     global basemodelvgg19
#     img1 = cv2.resize(img, (224, 224))
#     feature_vector = basemodelvgg19.predict(img1.reshape(1, 224, 224, 3))
#     return feature_vector
LS_Vgg=[]

def calculate_similarity(vector1, vector2):
    vector1_1d = vector1.flatten()
    vector2_1d = vector2.flatten()
    return (1 - cosine(vector1_1d, vector2_1d))

for img in dataframe2["Imagenes"]:
    print (img)
    url=container_path+bepensa_logos_subfolder+img
    response = requests.get(url)

    # Verificar si la solicitud fue exitosa
    if response.status_code == 200:
        # Obtener contenido de la respuesta
        contenido = response.content
        # Convertir el contenido a un array de bytes
        nparr = np.frombuffer(contenido, np.uint8)
        
        # Decodificar el array de bytes como una imagen utilizando OpenCV
        imagen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    ##### generar vector modelo vgg16
    f1=get_feature_vector(imagen)
    # f2=get_feature_vector19(imagen)
    # x={
    #     "Imagen":img,
    #     "Vector16":f1,
    #     "Vector19":f2
    # }
    x={
        "Imagen":img,
        "Vector16":f1
    }
    LS_Vgg.append(x)

def Compararimg(logo,task_id,porcentaje,tiposimi): 
    url3=container_path+'data/' + task_id + '/logos/' + logo
    response3 = requests.get(url3)
    # Verificar si la solicitud fue exitosa
    if response3.status_code == 200:
        # Obtener contenido de la respuesta
        contenido3 = response3.content
        # Convertir el contenido a un array de bytes
        nparr3 = np.frombuffer(contenido3, np.uint8)
        
        # Decodificar el array de bytes como una imagen utilizando OpenCV
        v1 = cv2.imdecode(nparr3, cv2.IMREAD_COLOR)
        f1=get_feature_vector(v1)
        # f2=get_feature_vector19(v1)

    dis16_ls=[]
    # dis19_ls=[]
    # disfi_ls=[]
    names_ls=[]
    for i in range(len(LS_Vgg)):
        x=LS_Vgg[i]
        namei=x.get("Imagen")
        v16=x.get("Vector16")
        # v19=x.get("Vector19")
        distv16=round(calculate_similarity(f1,v16)*100,1)
        # distv19=round(calculate_similarity(f2,v19)*100,1)
        dis16_ls.append(distv16)
        # dis19_ls.append(distv19)
        names_ls.append(namei)

        # if distv16>distv19:
        #     disfinal=distv16
        #     disfi_ls.append(disfinal)
        # else: 
        #     disfinal=distv19
        #     disfi_ls.append(disfinal)

    df_magenesaux=pd.DataFrame() 
    df_magenesaux["logotipo"]=names_ls
    # df_magenesaux["Similitud_VGG16"]=dis16_ls
    # df_magenesaux["Similitud_VGG19"]=dis19_ls
    df_magenesaux["Similitud_Final"]=dis16_ls
    df_magenesaux=df_magenesaux.sort_values(by=tiposimi, ascending=False)

    porcentaje=int(porcentaje)
    # if tiposimi=="Similitud_VGG16":
    #     df_magenesaux=df_magenesaux[df_magenesaux.Similitud_VGG16 >= porcentaje ]
    # if tiposimi=="Similitud_VGG19":
    #     df_magenesaux=df_magenesaux[df_magenesaux.Similitud_VGG19 >= porcentaje ]
    # if tiposimi=="Similitud_Final":
    #     df_magenesaux=df_magenesaux[df_magenesaux.Similitud_Final >= porcentaje ]

    df_magenesaux=df_magenesaux[df_magenesaux.Similitud_Final >= porcentaje ]

    lista_similitudeimg = []
    for _, row in df_magenesaux.iterrows():
        similitude = {}
        for column in df_magenesaux.columns:
            similitude[column] = row[column]
        lista_similitudeimg.append(similitude)
    return(lista_similitudeimg)
