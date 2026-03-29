"""
- Conectar com Rotas da API
- Rodar um Post para capturar lista de jogos
- Enviar para o S3 (por enquanto, um json aqui)
"""
import requests
import json
import boto3
import os
from dotenv import load_dotenv
from s3File import upload_file
from genres import add_genres_to_games

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

def buscar_jogos():
    url = 'https://api.igdb.com/v4/games'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'text/plain'
    }
    #TODO: Deixar o body dinamico, para pegar mais ou menos campos, ou mais ou menos jogos.
    body = "fields 'name', 'summary', 'genres', 'total_rating'; limit 100;"
    req = requests.post(url,headers=headers,data=body)

    if req.status_code == 200:
        dados = req.json()
        dados_with_genres = add_genres_to_games(dados)
        
        # 3. Gerando o JSON no VS Code
        with open('app/src/data/jogos_extraidos.json', 'w', encoding='utf-8') as f:
            json.dump(dados_with_genres, f, ensure_ascii=False, indent=4)
        print("Sucesso! Arquivo 'jogos_extraidos.json' gerado.")
        
        # Enviar para S3
        bucket_name = os.getenv('BUCKET_NAME')
        upload_file(bucket_name, 'app/src/data/jogos_extraidos.json')
    else:
        print(f"Erro: {req.status_code}")
        print(req.text)
buscar_jogos()