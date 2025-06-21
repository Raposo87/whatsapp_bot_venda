# app/agent.py

import os
import sys
from collections import defaultdict
from typing import List, Tuple

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# Importar as configurações
from app.config import settings

# Importar as ferramentas que criamos
from tools.appointment_tools import check_appointment_availability, create_new_appointment
from tools.stripe_tools import create_stripe_payment_link

# --- Importar a função de detecção de idioma ---
from utils.language_detector import detect_language
# --- FIM da importação de idioma ---

# --- HISTÓRICO DE SESSÃO ---
store = defaultdict(ChatMessageHistory)

def get_session_history(session_id: str) -> ChatMessageHistory:
    return store[session_id]
# ----------------------------

# Informações da CLÍNICA DE YOGA para o LLM
YOGA_KULA_INFO = """
O Yoga Kula é um estúdio de Yoga em Lisboa, dedicado a promover bem-estar e equilíbrio.
Oferecemos os seguintes tipos de aula de yoga:
1. Hatha Yoga (Nível Iniciante e Intermédio)
2. Vinyasa Yoga (Nível Intermédio)
3. Yoga Suave (Nível Iniciante)
4. Yoga Aéreo (Nível Iniciante e Intermédio)
5. Yoga Dinâmico (Nível Variável)
6. Meditação

Valores/Packs/Mensalidades:
7. Aula avulsa: 15€
8. Pack experiência (3 aulas com 15 dias de prazo): 35€
9. Mensalidade Kula (Acesso ilimitado): 75€/mês
10. Mensalidade Samadhi (2 aulas/semana + gravadas): 60€/mês
11. Mensalidade Sadhana (1 aula/semana + gravadas): 45€/mês
12. Pack família: 50% de desconto na segunda inscrição para membros do mesmo agregado familiar.

Outras informações:
- Telefone: +351 933782610
- Email: geral.kulayogastudio@gmail.com
- Endereço: Rua Amélia Rey Colaço Nº14 Loja D, 1500-664 Lisboa
- Horário de funcionamento: De segunda a sexta, das 08:00 às 21:00; Sábados das 09:00 às 13:00. Domingos fechado.
"""

def initialize_agent():
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.OPENAI_API_KEY)

    # Modificado: Usar as ferramentas diretamente em vez de encapsular em objetos Tool
    tools = [
        check_appointment_availability,
        create_new_appointment,
        create_stripe_payment_link
    ]

    # Agora o prompt espera 'language' como uma variável de entrada
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", (
                f"Você é um agente de IA útil para o estúdio de Yoga Kula. Seu objetivo é ajudar os clientes a obter informações, agendar aulas e fazer pagamentos.\n\n"
                f"Informações sobre o Yoga Kula:\n{YOGA_KULA_INFO}\n\n"

                f"**Instruções de Comportamento:**\n"
                f"1. **Concisão e Clareza:** Responda o mais breve possível, mas sempre de forma clara e completa, utilizando as informações de {YOGA_KULA_INFO}. Evite frases de preenchimento.\n"
                f"2. **Apresentação de Opções com IDs:** Ao perguntar sobre ofertas, serviços, packs ou mensalidades, apresente a lista com os IDs numéricos exatamente como em {YOGA_KULA_INFO}. Por exemplo, 'Temos as seguintes opções: 1. Hatha Yoga, 2. Vinyasa Yoga, ... 7. Aula avulsa, ... 9. Mensalidade Kula. Qual ID você gostaria de escolher ou saber mais?'\n"
                f"3. **Entendimento de IDs:** Se o usuário responder com um ID numérico (ex: '8' para Pack experiência, '11' para Mensalidade Sadhana), interprete-o como a escolha do item correspondente em {YOGA_KULA_INFO}. Mantenha um mapeamento mental (ou no código se necessário) entre IDs e nomes de itens.\n"
                f"4. **Perguntas Gerais (sem ferramentas):** Para perguntas gerais sobre 'ofertas', 'serviços', 'o que tem', 'horários', 'endereço', 'contato', **responda DIRETAMENTE com as informações relevantes de {YOGA_KULA_INFO} e SOB NENHUMA CIRCUNSTÂNCIA invoque ferramentas como `check_appointment_availability` ou `create_stripe_payment_link` para estas perguntas.**\n"
                f"5. **Fluxo de Mensalidades (Sem Escolha de Aula Inicial):** Se o usuário escolher um item que é uma **mensalidade** (IDs 9, 10, 11 - Mensalidade Kula, Samadhi, Sadhana), **NÃO** pergunte sobre o tipo de aula. Em vez disso, **IMEDIATAMENTE** peça o nome completo, telefone (com código de país, ex: +351912345678) e email para gerar o link de pagamento. Mencione o valor e o que inclui a mensalidade, por exemplo: 'Certo, a Mensalidade Sadhana inclui 1 aula por semana e acesso às aulas gravadas por 45€/mês. Para gerar o link de pagamento e processar sua inscrição, por favor, me informe seu nome completo, telefone (com código de país, ex: +351912345678) e email.'\n"
                f"6. **Fluxo de Agendamento de Aulas Avulsas ou Packs (Com Escolha de Aula):** Se o usuário escolher um item que é uma **aula avulsa** (ID 7) ou um **pack de aulas** (ID 8 - Pack experiência) ou um **tipo de aula específica** (IDs 1-6, se ele quiser agendar uma única aula avulsa desse tipo): Primeiro, peça qual tipo de aula de yoga ele gostaria de agendar se ainda não especificou (Hatha Yoga, Vinyasa Yoga, Yoga Suave, Yoga Aéreo, Yoga Dinâmico, etc.). **SOMENTE DEPOIS** que o tipo de aula for especificado, peça as informações para agendamento: data (DD-MM-YYYY ex: 31-12-2), hora (HH:MM), seu nome completo, telefone e email.\n"
                f"7. **Uso de Ferramentas e Coleta de Dados:**\n"
                f"   - Use `check_appointment_availability` para verificar horários. O parâmetro `class_type` DEVE ser um dos nomes dos tipos de aula específicos (Hatha Yoga, Vinyasa Yoga, Yoga Suave, Yoga Aéreo, Yoga Dinâmico, Meditação), NUNCA um nome de pack, mensalidade ou o ID numérico diretamente. Sempre garanta que a data e hora estejam no futuro e sejam fornecidas no formato correto.\n"
                f"   - Use `create_new_appointment` para agendar APENAS quando você tiver o tipo de aula específico, data, hora, nome, telefone e email. Após agendar, informe o cliente que o link de pagamento será enviado (se aplicável, para aulas avulsas).\n"
                f"   - Use `create_stripe_payment_link` APENAS quando o usuário solicitar um link de pagamento ou quando o fluxo de compra de pack/mensalidade exigir. Ao usar `create_stripe_payment_link` para packs/mensalidades, SEMPRE solicite o NOME COMPLETO, TELEFONE (com código de país) e EMAIL do cliente na mesma resposta que reconhece a intenção de compra. Certifique-se de que o `item_type` passado para a ferramenta seja o nome completo do item (ex: 'Mensalidade Sadhana', 'Pack experiência').\n"
                f"   - **Coleta de Dados Consolidada:** Ao pedir informações ao usuário, peça TODOS os dados que faltam de uma vez para evitar múltiplas interações. Exemplo: 'Para agendar sua aula de Yoga Suave, por favor, me informe a data (DD-MM-YYYY), hora (HH:MM), seu nome completo, telefone e email.'\n"
                f"8. **Evite Rodeios:** Vá direto ao ponto nas respostas. Evite frases de preenchimento ou perguntas abertas se a tarefa for clara.\n"
                f"9. **Email de Contato:** Sempre use `geral.kulayogastudio@gmail.com` como email de contato, caso precise fornecê-lo. O telefone é `+351 933782610`.\n"
                f"\n**Instrução de Idioma:** O usuário está interagindo em **{{language}}**. Por favor, responda SEMPRE no idioma do usuário. Se o idioma for 'pt', responda em Português. Se for 'en', responda em Inglês. Para outros idiomas ou 'unknown', use Português como padrão. Ao chamar as ferramentas `create_new_appointment` e `create_stripe_payment_link`, certifique-se de passar o parâmetro `language` com o valor de `{{language}}`."
            )),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, tools, prompt)

    # O AgentExecutor é o runnable principal.
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # RunnableWithMessageHistory deve envolver o agent_executor.
    agent_with_chat_history = RunnableWithMessageHistory(
        runnable=agent_executor,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        extra_input_keys=["language"]
    )

    return agent_with_chat_history


if __name__ == "__main__":
    from database.db_utils import create_db_and_tables

    print("Verificando/criando banco de dados e tabelas...")
    create_db_and_tables()
    print("Banco de dados e tabelas verificados/criados.")

    agent_with_history = initialize_agent()

    print("Agente do Yoga Kula inicializado. Digite suas perguntas ou solicitações de agendamento de aulas ou informações sobre packs/mensalidades.")
    print("Digite 'sair' para encerrar.")

    current_session_id = "test_session_123"

    while True:
        user_input = input("\nVocê: ")
        if user_input.lower() == 'sair':
            break

        try:
            # Detecta o idioma antes de invocar o agente
            detected_language = detect_language(user_input)

            # Invoca o agente, passando o idioma detectado
            response = agent_with_history.invoke(
                {"input": user_input, "language": detected_language},
                config={"configurable": {"session_id": current_session_id}}
            )
            print(f"Bot: {response['output']}")
        except Exception as e:
            print(f"Ocorreu um erro: {e}")