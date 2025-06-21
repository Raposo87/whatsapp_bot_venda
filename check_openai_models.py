# check_openai_models.py
import openai
import os
import sys

# Adiciona o diretório raiz do projeto ao sys.path para importar as settings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.config import settings

# Configura sua chave de API
openai.api_key = settings.OPENAI_API_KEY

try:
    print("Verificando modelos disponíveis para a sua chave de API...")
    # Esta é a nova forma de listar modelos na v1 da biblioteca OpenAI
    # Use 'client.models.list()' se você estiver instanciando o cliente OpenAI como:
    # client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    # models = client.models.list()
    
    # Se você está usando o estilo mais antigo (openai.api_key), a linha abaixo está correta:
    models = openai.models.list() 
    
    print("\nModelos acessíveis:")
    found_any_gpt = False
    for model in models.data:
        # Filtra por modelos GPT para facilitar a visualização e exclui embeddings ou modelos de imagem
        if "gpt" in model.id and "embedding" not in model.id and "image" not in model.id: 
            print(f"- {model.id}")
            found_any_gpt = True
    
    if not found_any_gpt:
        print("Nenhum modelo GPT encontrado para sua chave. Isso é incomum.")
        print("Certifique-se de que sua conta está ativa e tem permissões.")

except openai.AuthenticationError:
    print("Erro de autenticação: Sua chave de API pode estar incorreta ou inválida.")
    print("Verifique sua OPENAI_API_KEY no arquivo .env.")
except openai.APITimeoutError:
    print("Erro de timeout da API. A solicitação demorou muito. Tente novamente.")
except openai.APIConnectionError as e:
    print(f"Erro de conexão com a API: {e}. Verifique sua conexão de internet.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")