import google.generativeai as genai
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

# Configure sua API Key do Google AI Studio
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def gerar_embedding(texto):
    # Usamos o modelo 'embedding-001', que é otimizado para isso
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=texto,
        task_type="retrieval_document"
    )
    return result['embedding']

def calcular_similaridade(v1, v2):
    # A fórmula do cosseno mede o ângulo entre os vetores
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

# --- NOSSO EXPERIMENTO ---
print("🧠 Gerando inteligência...")

frase_1 = "Um jogo de RPG de turno com temática medieval e dragões."
frase_2 = "Um simulador de corrida com carros esportivos em pistas reais."
frase_3 = "Um jogo de aventura em um mundo de fantasia com cavaleiros e magia."

v1 = gerar_embedding(frase_1)
v2 = gerar_embedding(frase_2)
v3 = gerar_embedding(frase_3)

print(f"\n📊 Comparando Frase 1 e Frase 2 (RPG vs Corrida): {calcular_similaridade(v1, v2):.4f}")
print(f"📊 Comparando Frase 1 e Frase 3 (RPG vs Aventura): {calcular_similaridade(v1, v3):.4f}")
print(f"📊 Comparando Frase 2 e Frase 3 (Corrida vs Aventura): {calcular_similaridade(v2, v3):.4f}")