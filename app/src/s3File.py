import boto3
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

def upload_file(bucket_name, file_path, object_name=None, remove_after_upload=True):
    """
    Faz upload de um arquivo para o S3, convertendo para Parquet.
    
    Args:
        bucket_name (str): Nome do bucket S3
        file_path (str): Caminho do arquivo local
        object_name (str): Nome do objeto no S3. Se None, usa o nome do arquivo
        remove_after_upload (bool): Remove o arquivo local após upload. Padrão: True
        
    Returns:
        bool: True se sucesso, False se erro
    """
    if object_name is None:
        object_name = os.path.basename(file_path).replace('.json', '.parquet')
    
    try:
        parquet_file = convert_to_parquet(file_path)

        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

        print(f"Enviando {parquet_file} para o bucket {bucket_name}...")
        s3_client.upload_file(parquet_file, bucket_name, object_name)
        
        # Limpa os arquivos temporários
        if remove_after_upload:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(parquet_file):
                os.remove(parquet_file)
        
        print("Upload concluído com sucesso! 🚀")
        return True
    except FileNotFoundError as e:
        print(f"Erro: O arquivo local não foi encontrado. {str(e)}")
        return False
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {str(e)}")
        return False


def convert_to_parquet(file_path):
    """
    Converte um arquivo JSON para Parquet.
    
    Args:
        file_path (str): Caminho do arquivo JSON
        
    Returns:
        str: Caminho do arquivo Parquet gerado
        
    Raises:
        Exception: Se houver erro na conversão
    """
    try:
        df = pd.read_json(file_path)
        parquet_file = file_path.replace('.json', '.parquet')
        df.to_parquet(parquet_file, index=False)
        print("Arquivo convertido para Parquet com sucesso!")
        return parquet_file
    except Exception as e:
        raise Exception("Erro ao converter para Parquet") from e


# Execução local (será ignorada pelo Lambda)
if __name__ == "__main__":
    nome_arquivo = 'jogos_extraidos.json'
    nome_bucket = os.getenv('BUCKET_NAME')
    
    if os.path.exists(nome_arquivo):
        upload_file(nome_bucket, nome_arquivo)
    else:
        print(f"Arquivo {nome_arquivo} não encontrado.")