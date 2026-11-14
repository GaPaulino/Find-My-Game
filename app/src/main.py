"""
- Conectar com Rotas da API
- Rodar um Post para capturar lista de jogos
- Enviar para o S3
- AWS Lambda Handler
"""
import requests
import json
import os
import tempfile
from dotenv import load_dotenv
from s3File import upload_file
from genres import GenreMapper
from datetime import datetime

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
BUCKET_NAME = os.getenv('BUCKET_NAME')

def buscar_jogos(limit=100):
    """
    Busca jogos da API IGDB e faz upload para o S3.
    
    Args:
        limit (int): Número de jogos a buscar. Padrão: 100
        
    Returns:
        tuple: (dados, caminho_arquivo) em caso de sucesso, (None, None) em caso de erro
    """
    url = 'https://api.igdb.com/v4/games'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'text/plain'
    }
    
    body = f"fields 'name', 'summary', 'genres', 'total_rating'; limit {limit};"
    req = requests.post(url, headers=headers, data=body)

    if req.status_code == 200:
        dados = req.json()
        dados_with_genres = GenreMapper().add_to_games(dados)
        
        # Usar /tmp para arquivos temporários no Lambda
        temp_dir = tempfile.gettempdir()
        arquivo_path = os.path.join(temp_dir, f'jogos_extraidos_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        with open(arquivo_path, 'w', encoding='utf-8') as f:
            json.dump(dados_with_genres, f, ensure_ascii=False, indent=4)
        
        print(f"Arquivo '{arquivo_path}' gerado com sucesso.")
        return dados_with_genres, arquivo_path
    else:
        print(f"Erro na API: {req.status_code}")
        print(req.text)
        return None, None


def lambda_handler(event, context):
    """
    AWS Lambda Handler
    
    Args:
        event (dict): Evento do Lambda (pode conter parâmetros)
        context (object): Contexto do Lambda
        
    Returns:
        dict: Resposta com statusCode e body
    """
    try:
        # Extrair parâmetros opcionais do event
        limit = event.get('limit', 100) if event else 100
        
        print(f"Iniciando busca de {limit} jogos...")
        
        # Buscar jogos
        dados, arquivo_path = buscar_jogos(limit=limit)
        
        if dados is None:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Falha ao buscar jogos da API IGDB'
                })
            }
        
        # Enviar para S3
        try:
            if not upload_file(BUCKET_NAME, arquivo_path):
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Falha ao fazer upload para o S3 (veja os logs)'
                    })
                }

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Sucesso! Jogos extraídos e enviados para S3.',
                    'jogos_carregados': len(dados),
                    'bucket': BUCKET_NAME
                })
            }
        except Exception as e:
            print(f"Erro ao fazer upload: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Erro ao fazer upload para S3: {str(e)}'
                })
            }
            
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Erro inesperado: {str(e)}'
            })
        }


# Para testes locais (será ignorado pelo Lambda)
if __name__ == "__main__":
    test_event = {'limit': 100}
    test_context = None
    response = lambda_handler(test_event, test_context)
    print(json.dumps(response, indent=2))