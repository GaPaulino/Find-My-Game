import logging
import boto3
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
logger = logging.getLogger(__name__)


def _create_s3_client():
    """Cria o cliente S3.

    Se as chaves estiverem no ambiente (dev local, via .env) elas são usadas.
    Caso contrário o boto3 usa a cadeia padrão de credenciais, que no Lambda
    é a IAM role da função (sem chaves no código).
    """
    key = os.getenv('AWS_ACCESS_KEY_ID')
    secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    region = os.getenv('AWS_REGION')
    if key and secret:
        return boto3.client('s3', aws_access_key_id=key,
                            aws_secret_access_key=secret, region_name=region)
    return boto3.client('s3', region_name=region)

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

        s3_client = _create_s3_client()

        logger.info("Enviando %s para o bucket %s...", parquet_file, bucket_name)
        s3_client.upload_file(parquet_file, bucket_name, object_name)
        
        # Limpa os arquivos temporários
        if remove_after_upload:
            if os.path.exists(file_path):
                os.remove(file_path)
            if os.path.exists(parquet_file):
                os.remove(parquet_file)
        
        logger.info("Upload concluído com sucesso!")
        return True
    except FileNotFoundError:
        logger.exception("O arquivo local não foi encontrado")
        return False
    except Exception:
        logger.exception("Erro inesperado no upload")
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
        logger.info("Arquivo convertido para Parquet com sucesso!")
        return parquet_file
    except Exception as e:
        raise Exception("Erro ao converter para Parquet") from e


# Execução local (será ignorada pelo Lambda)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    nome_arquivo = 'jogos_extraidos.json'
    nome_bucket = os.getenv('BUCKET_NAME')
    
    if os.path.exists(nome_arquivo):
        upload_file(nome_bucket, nome_arquivo)
    else:
        logger.error("Arquivo %s não encontrado.", nome_arquivo)