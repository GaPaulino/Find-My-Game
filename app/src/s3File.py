import boto3
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def upload_file(bucket_name, file_path, object_name=None):

    # Se o nome no S3 não for especificado, usa o nome do arquivo local (convertido para parquet)
    if object_name is None:
        object_name = file_path.replace('.json', '.parquet')
    
    parquet_file = convert_to_parquet(file_path)

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

    try:
        print(f"Enviando {parquet_file} para o bucket {bucket_name}...")
        s3_client.upload_file(parquet_file, bucket_name, object_name)
        
        # Limpa o arquivo JSON original (opcional)
        os.remove(file_path)
        print("Upload concluído com sucesso! 🚀")
        return True
    except FileNotFoundError:
        print("Erro: O arquivo local não foi encontrado.")
        return False
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        return False


def convert_to_parquet(file_path):
    try:
        df = pd.read_json(file_path)
        parquet_file = file_path.replace('.json', '.parquet')
        df.to_parquet(parquet_file, index=False)
        print("Arquivo convertido para Parquet com sucesso!")
        return parquet_file
    except Exception as e:
        raise Exception("Erro ao converter para Parquet") from e
    

# Execução
if __name__ == "__main__":
    nome_arquivo = 'jogos_extraidos.json'
    nome_bucket = os.getenv('BUCKET_NAME')
    
    upload_file(nome_bucket, nome_arquivo)