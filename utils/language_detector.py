# utils/language_detector.py

from langdetect import detect, DetectorFactory

# Garante que a detecção seja consistente
DetectorFactory.seed = 0

def detect_language(text: str) -> str:
    """
    Detecta o idioma de um dado texto.
    Retorna 'pt' para português, 'en' para inglês, ou 'unknown' se não conseguir detectar.
    """
    try:
        lang = detect(text)
        if lang == 'pt':
            return 'pt'
        elif lang == 'en':
            return 'en'
        else:
            return 'other' # Para outros idiomas que você não queira especificar
    except Exception:
        # Pode ocorrer erro se o texto for muito curto ou sem conteúdo
        return 'unknown'

if __name__ == '__main__':
    print(f"'Olá, como posso ajudar?' -> {detect_language('Olá, como posso ajudar?')}")
    print(f"'Hello, how can I help you?' -> {detect_language('Hello, how can I help you?')}")
    print(f"'This is a test.' -> {detect_language('This is a test.')}")
    print(f"'Isso é um teste.' -> {detect_language('Isso é um teste.')}")
    print(f"'' -> {detect_language('')}") # Texto vazio
    print(f"'abc' -> {detect_language('abc')}") # Texto muito curto