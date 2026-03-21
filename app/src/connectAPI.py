"""
- Conectar com Rotas da API
- Rodar um Post para capturar lista de jogos
- Enviar para o S3 (por enquanto, um json aqui)
"""
import requests
import json

CLIENT_ID = 'w2n89xbc7o7ler04xlphjmg413928s'
ACCESS_TOKEN = 'eg6ode4x95t13wuwd9gbfrl1bv9rwu'

def buscar_jogos():
    url = 'https://api.igdb.com/v4/games'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'Content-Type': 'text/plain'
    }

    body = 'fields *; where id = 115;'
    req = requests.post(url,headers=headers,data=body)

    if req.status_code == 200:
        dados = req.json()
        
        # 3. Gerando o JSON no VS Code
        with open('jogos_extraidos.json', 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        
        print("Sucesso! Arquivo 'jogos_extraidos.json' gerado.")
    else:
        print(f"Erro: {req.status_code}")
        print(req.text)
buscar_jogos()