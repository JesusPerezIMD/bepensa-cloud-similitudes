import logging
import json
import os
from typing import List
from typing import Any
from dataclasses import dataclass
from fuzzywuzzy import fuzz
from fuzzywuzzy.fuzz import token_set_ratio
import pandas as pd
import requests
import io
import Levenshtein
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_local_settings():
    with open('../local.settings.json') as f:
        data = json.load(f)
    return data["Values"]
local_settings = load_local_settings()

# URL de la imagen
container_path=f'{local_settings["GacetaStorageUrl"]}/{local_settings["GacetaContainerName"]}/'
archivo="assets/csv/data.csv"
url=container_path+archivo

# Enviar solicitud HTTP y obtener la respuesta
response = requests.get(url)

# Verificar si la solicitud fue exitosa
if response.status_code == 200:
    # Obtener contenido de la respuesta
    contenido = response.content
    contenido_csv = io.StringIO(contenido.decode('utf-8'))
    dataframe = pd.read_csv(contenido_csv)
#df=pd.read_csv(contenido)



def buscar(dataframe, query, porcentaje):
    texto1=query
    #################     
    texto1=texto1.upper()
    data = dataframe
    data['Denominación']=data['Denominación'].str.upper()
    data['Denominación_Translate']=data['Denominación_Translate'].str.upper()
    Dempre=data.Denominación.to_list()
    DempreI=data.Denominación_Translate.to_list()
    DistanciaL=[]
    DistanciaL2=[]
    def fuzzytex(tex1,tex2):
        similitud = fuzz.token_set_ratio(tex1, tex2)
        return similitud
    def ComTexto(tex1,tex2):
        distancia = Levenshtein.distance(tex1, tex2)
        porcentaje_similitud = 100 - (distancia / max(len(tex1), len(tex2))) * 100
        return porcentaje_similitud
    def contenidoen(texto,BText):
        palabras = list(filter(lambda palabra: len(palabra) > 3, (palabra.strip(".,?!") for palabra in texto.split())))
        if len(palabras) !=0:

            largo=len(palabras)
            #print(palabras)
            Sim=0
            for palabra in palabras:
                posicion = BText.find(palabra)
                if posicion >= 0:
                    Sim=Sim+1
                    #print(f"La palabra '{palabra}' está en la posición {posicion} del texto")
                #else:
                    #print(f"La palabra '{palabra}' no se encuentra en el texto")
            psim=(Sim/largo)*100
        else:
            psim=0
        return psim

    for i in range(len(Dempre)):
        dist=ComTexto(texto1,Dempre[i])
        dist2=ComTexto(texto1,DempreI[i])
        dfuz1=fuzzytex(texto1,Dempre[i])
        dfuz2=fuzzytex(texto1,DempreI[i])
        dcon1=contenidoen(texto1,Dempre[i])
        dcon2=contenidoen(texto1,DempreI[i])
        #print(dist)
        #print(dist2)
        disfin=max(dist,dist2)
        disfuzzy=max(dfuz1,dfuz2)
        dconfin=max(dcon1,dcon2)
        
        if disfin < dconfin:
            if disfuzzy<dconfin:
                DistanciaL.append(dconfin)
                DistanciaL2.append("Similitud_Contenido")
            else: 
                DistanciaL.append(disfuzzy)
                DistanciaL2.append("Similitud_Fuzzy")
        else:
            if disfuzzy<disfin:
                DistanciaL.append(disfin)
                DistanciaL2.append("Similitud_Levenshtein")
            else:
                DistanciaL.append(disfuzzy)
                DistanciaL2.append("Similitud_Fuzzy")
                




    datafinal=data
    datafinal['Porcentaje_Similitud']=DistanciaL
    datafinal['Tipo_de_similitud']=DistanciaL2
    #datafinal['Similitud Coseno']=DistanciaC   
    datafinal=datafinal.sort_values(by=['Porcentaje_Similitud'], ascending=False)
    porcentaje=int(porcentaje)
    datafinal=datafinal[datafinal.Porcentaje_Similitud >= porcentaje ]

    #Definir Tabla 
    df=datafinal
    # Suponiendo que tiene un DataFrame llamado 'df'
    # Cree una instancia de QTableWidget
    lista_similitude = []
    for _, row in df.iterrows():
        similitude = {}
        for column in df.columns:
            similitude[column] = row[column]
        lista_similitude.append(similitude)
    
    return(lista_similitude)

def ScoreSimilitudTxt(obj):
    objAux = SimilitudTXTRequest(obj.get('task_id'), obj.get('data'))
    largo=len(objAux.data)
    ls_final=[]
    dataframe

    try:
        for i in range(largo):
            dts=objAux.data[i]
            name=dts.get("brand_name")
            clase=dts.get("brand_class")
            similitude=buscar(dataframe,name,50)
            elemento = {
                "brand_name": name,
                "brand_class": clase,
                "image_url": dts.get("image_url"),  # Añadir página a los datos de la respuesta
                "similitud_TxT": similitude
            }
            ls_final.append(elemento)
        
        response= {
            "status": "OK",
            "message": "",
            "task_id": objAux.task_id,
            "data": ls_final
        }
    except ValueError as e:
                
                response= {
                "status": "Error",
                "message": e,
                "task_id": " ",
                "data": " "
                }

    return response

@dataclass
class SimilitudTXTDataRequest:
    brand_name: str
    brand_class: str
    page: int

@dataclass
class SimilitudTXTRequest:
    task_id: str
    data: List[SimilitudTXTDataRequest]
