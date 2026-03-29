import pandas as pd

def read_pq_file():
    df = pd.read_parquet("app/src/data/jogos_extraidos.parquet")
    print(df.head())

read_pq_file()