from cryptography.hazmat.primitives.serialization import pkcs12

def validar_certificado_bytes(dados, senha):
    try:
        pkcs12.load_key_and_certificates(
            dados,
            senha.encode("utf-8") if senha else None
        )
        return True
    except Exception:
        return False

def validar_certificado(caminho, senha):
    try:
        with open(caminho, "rb") as f:
            dados = f.read()
        return validar_certificado_bytes(dados, senha)
    except Exception:
        return False
