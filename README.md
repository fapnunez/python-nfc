# NF-e Manager SP

Aplicação Flask para:

- cadastrar CNPJs;
- selecionar certificado digital A1 `.pfx`/`.p12`;
- consultar NF-e destinadas ao CNPJ via NFeDistribuicaoDFe;
- armazenar XMLs em disco;
- importar XMLs manualmente;
- evitar duplicidade pela chave;
- gerar PDF auxiliar/DANFE a partir do XML.

## Instalação

Windows:

```bat
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Executar localmente:

```bat
python app.py
```

## Deploy em VPS Linux

Use o Gunicorn e mantenha a porta fornecida pelo provedor:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python -m gunicorn --bind 0.0.0.0:${PORT:-5003} --access-logfile - --error-logfile - --capture-output app:app
```

Teste o processo diretamente no próprio VPS:

```bash
curl http://127.0.0.1:${PORT:-5003}/health
```

O retorno esperado é `{"status":"ok"}`. Se esse teste falhar, o problema está no processo, na porta ou no ambiente virtual; se funcionar e o navegador continuar com 502, o problema está na configuração do proxy reverso.

## Certificado

O usuário informa o caminho do certificado A1 na tela:

```text
C:\Certificados\empresa.pfx
```

O certificado não é copiado para o projeto.

## Atenção sobre NF-e x NFC-e

A consulta `NFeDistribuicaoDFe` é o mecanismo utilizado para documentos de interesse do CNPJ, especialmente NF-e.

A NFC-e tem características próprias. A SEFAZ-SP disponibiliza o Sistema de Apoio à Escrituração da NFC-e para listagem/download de NFC-e emitidas por um CNPJ. Isso não deve ser confundido com "todas as NFC-e recebidas contra um CNPJ".

Por isso esta primeira versão permite importar NFC-e XML e gerar PDF, enquanto a consulta automática de NF-e contra o CNPJ usa a Distribuição DF-e.

## Segurança

Esta versão guarda a senha do certificado no SQLite para simplificar o protótipo. Para produção, recomenda-se trocar isso por Windows Credential Manager/DPAPI ou outro armazenamento seguro.

## Observação fiscal

O PDF gerado é uma representação auxiliar baseada no XML. Para uso fiscal, preserve sempre o XML autorizado original.
