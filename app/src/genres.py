import pandas as pd


def add_genres_to_games(dados_with_genres):
    list_generos = pd.read_json('app/src/data/list_genres.json')
    for jogo in dados_with_genres:
        generos_jogo = []
        for genero_id in jogo.get('genres', []):
            genero_nome = list_generos.loc[list_generos['id'] == genero_id, 'name']
            if not genero_nome.empty:
                generos_jogo.append(genero_nome.values[0])
        jogo['genres'] = generos_jogo
    return dados_with_genres
    