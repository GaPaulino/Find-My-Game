import pandas as pd
import os


def add_genres_to_games(dados_with_genres):
    """
    Adiciona nomes dos gêneros aos jogos baseado em ID de gênero.
    
    Args:
        dados_with_genres (list): Lista de jogos com IDs de gêneros
        
    Returns:
        list: Lista de jogos com nomes de gêneros
    """
    # Determinar o caminho do arquivo de gêneros (compatível com Lambda)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    genres_file = os.path.join(current_dir, 'data', 'list_genres.json')
    
    if not os.path.exists(genres_file):
        print(f"Aviso: Arquivo de gêneros não encontrado em {genres_file}")
        return dados_with_genres
    
    list_generos = pd.read_json(genres_file)
    
    for jogo in dados_with_genres:
        generos_jogo = []
        for genero_id in jogo.get('genres', []):
            genero_nome = list_generos.loc[list_generos['id'] == genero_id, 'name']
            if not genero_nome.empty:
                generos_jogo.append(genero_nome.values[0])
        jogo['genres'] = generos_jogo
    
    return dados_with_genres
    