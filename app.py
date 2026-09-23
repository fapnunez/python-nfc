import os
import socket
from datetime import date

from flask import Flask, flash, get_flashed_messages, redirect, render_template, request, send_file, url_for

from banco import (
    atualizar_nsu,
    init_db,
    listar_documentos,
    listar_empresas,
    salvar_documento,
    salvar_empresa,
)
from certificado import validar_certificado_bytes
from danfe_pdf import gerar_danfe_pdf
from sefaz_sp import consultar_nfe_distribuicao
from xml_parser import parse_xml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
XML_DIR = os.path.join(BASE_DIR, "dados", "xml")
PDF_DIR = os.path.join(BASE_DIR, "dados", "pdf")
CERT_DIR = os.path.join(BASE_DIR, "dados", "certificados")
os.makedirs(XML_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(CERT_DIR, exist_ok=True)
CERT_EXTENSOES = (".pfx", ".p12")

app = Flask(__name__, template_folder="templates")
app.secret_key = "nfc-secret-key"
init_db()


def mascara_cnpj(cnpj: str) -> str:
    c = "".join(ch for ch in str(cnpj or "") if ch.isdigit())
    if len(c) == 14:
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
    return c


@app.route("/")
def dashboard():
    empresas = listar_empresas()
    docs = listar_documentos()
    return render_template(
        "dashboard.html",
        title="NF-e Manager — São Paulo",
        active="Dashboard",
        empresas=len(empresas),
        documentos=len(docs),
        xmls=sum(1 for d in docs if d.get("xml_path")),
    )


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/empresas", methods=["GET", "POST"])
def empresas():
    if request.method == "POST":
        cnpj = request.form.get("cnpj", "").strip()
        razao = request.form.get("razao", "").strip()
        uf = request.form.get("uf", "SP")
        senha = request.form.get("senha", "")
        ambiente = request.form.get("ambiente", "Produção")
        digits = "".join(ch for ch in cnpj if ch.isdigit())
        arquivo = request.files.get("certificado_arquivo")

        if len(digits) != 14:
            flash("Informe um CNPJ com 14 dígitos.", "error")
            return redirect(url_for("empresas"))

        existente = next((e for e in listar_empresas() if e["cnpj"] == digits), None)

        if arquivo and arquivo.filename:
            ext = os.path.splitext(arquivo.filename)[1].lower()
            if ext not in CERT_EXTENSOES:
                flash("Envie um certificado nos formatos .pfx ou .p12.", "error")
                return redirect(url_for("empresas"))
            dados_cert = arquivo.read()
            if not validar_certificado_bytes(dados_cert, senha):
                flash("Não foi possível abrir o certificado com a senha informada.", "error")
                return redirect(url_for("empresas"))
            certificado = os.path.join(CERT_DIR, f"{digits}{ext}")
            with open(certificado, "wb") as f:
                f.write(dados_cert)
        elif existente:
            certificado = existente["certificado"]
            if not os.path.isfile(certificado):
                flash("Certificado não encontrado no servidor. Envie o arquivo novamente.", "error")
                return redirect(url_for("empresas"))
            with open(certificado, "rb") as f:
                dados_cert_existente = f.read()
            if not validar_certificado_bytes(dados_cert_existente, senha):
                flash("Não foi possível abrir o certificado com a senha informada.", "error")
                return redirect(url_for("empresas"))
        else:
            flash("Selecione o arquivo do certificado A1 (.pfx/.p12).", "error")
            return redirect(url_for("empresas"))

        salvar_empresa(digits, razao, uf, certificado, senha, ambiente)
        flash("Empresa cadastrada/atualizada com sucesso.", "success")
        return redirect(url_for("empresas"))

    empresas_list = listar_empresas()
    return render_template(
        "empresas.html",
        title="Empresas / CNPJs",
        active="Empresas / CNPJs",
        empresas=empresas_list,
        mascara_cnpj=mascara_cnpj,
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/consultar", methods=["GET", "POST"])
def consultar():
    empresas_list = listar_empresas()
    if request.method == "POST":
        emp_id = request.form.get("empresa_id")
        inicio = request.form.get("inicio")
        fim = request.form.get("fim")
        if not emp_id:
            flash("Selecione a empresa.", "error")
            return redirect(url_for("consultar"))
        emp = next((e for e in empresas_list if str(e["id"]) == str(emp_id)), None)
        if not emp:
            flash("Empresa inválida.", "error")
            return redirect(url_for("consultar"))
        try:
            inicio_date = date.fromisoformat(inicio) if inicio else date.today()
            fim_date = date.fromisoformat(fim) if fim else date.today()
        except ValueError:
            flash("Datas inválidas.", "error")
            return redirect(url_for("consultar"))

        if inicio_date > fim_date:
            flash("A data inicial não pode ser maior que a final.", "error")
            return redirect(url_for("consultar"))

        try:
            resultado = consultar_nfe_distribuicao(
                cnpj=emp["cnpj"],
                certificado=emp["certificado"],
                senha=emp["senha"],
                ambiente=emp["ambiente"],
                ultimo_nsu=emp["ult_nsu"] or "000000000000000",
            )
            qtd = 0
            for item in resultado.get("documentos", []):
                info = parse_xml(item["xml"])
                nome = f"{info.get('chave') or item['nsu']}.xml"
                caminho = os.path.join(XML_DIR, nome)
                with open(caminho, "wb") as f:
                    f.write(item["xml"])
                salvar_documento(
                    chave=info.get("chave"),
                    cnpj_emitente=info.get("cnpj_emitente"),
                    cnpj_destinatario=info.get("cnpj_destinatario"),
                    numero=info.get("numero"),
                    serie=info.get("serie"),
                    tipo=info.get("tipo", "NF-e"),
                    data_emissao=info.get("data_emissao"),
                    valor=info.get("valor"),
                    xml_path=caminho,
                    pdf_path=None,
                    nsu=item["nsu"],
                )
                qtd += 1
            atualizar_nsu(emp["id"], resultado["ult_nsu"])
            flash(f"Consulta concluída. Documentos baixados: {qtd}. NSU atual: {resultado['ult_nsu']}", "success")
        except Exception as ex:
            flash(f"Erro na consulta: {ex}", "error")
        return redirect(url_for("consultar"))

    return render_template(
        "consultar.html",
        title="Consultar SEFAZ",
        active="Consultar SEFAZ",
        empresas=empresas_list,
        today=date.today().isoformat(),
        mascara_cnpj=mascara_cnpj,
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/importar", methods=["GET", "POST"])
def importar_xml():
    if request.method == "POST":
        uploaded = request.files.getlist("xml_files")
        ok = 0
        for arq in uploaded:
            if not arq or arq.filename == "":
                continue
            try:
                conteudo = arq.read()
                info = parse_xml(conteudo)
                chave = info.get("chave")
                nome = f"{chave or os.path.splitext(arq.filename)[0]}.xml"
                caminho = os.path.join(XML_DIR, nome)
                with open(caminho, "wb") as f:
                    f.write(conteudo)
                salvar_documento(
                    chave=chave,
                    cnpj_emitente=info.get("cnpj_emitente"),
                    cnpj_destinatario=info.get("cnpj_destinatario"),
                    numero=info.get("numero"),
                    serie=info.get("serie"),
                    tipo=info.get("tipo", "NF-e/NFC-e"),
                    data_emissao=info.get("data_emissao"),
                    valor=info.get("valor"),
                    xml_path=caminho,
                    pdf_path=None,
                    nsu=None,
                )
                ok += 1
            except Exception:
                continue
        flash(f"{ok} XML(s) importado(s) com sucesso.", "success")
        return redirect(url_for("importar_xml"))

    return render_template(
        "importar.html",
        title="Importar XML",
        active="Importar XML",
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/xml_para_pdf", methods=["GET", "POST"])
def xml_para_pdf():
    docs = [d for d in listar_documentos() if d.get("xml_path") and os.path.isfile(d["xml_path"])]
    if request.method == "POST":
        doc_id = request.form.get("doc_id")
        if not doc_id:
            flash("Selecione um XML.", "error")
            return redirect(url_for("xml_para_pdf"))
        doc = next((d for d in docs if str(d["id"]) == str(doc_id)), None)
        if not doc:
            flash("XML inválido.", "error")
            return redirect(url_for("xml_para_pdf"))
        try:
            gerar_danfe_pdf(doc["xml_path"], PDF_DIR)
            flash("PDF gerado com sucesso.", "success")
            return redirect(url_for("documentos"))
        except Exception as ex:
            flash(f"Erro ao gerar PDF: {ex}", "error")
            return redirect(url_for("xml_para_pdf"))

    return render_template(
        "xml_para_pdf.html",
        title="XML → PDF",
        active="XML → PDF",
        docs=docs,
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/documentos")
def documentos():
    docs = listar_documentos()
    return render_template(
        "documentos.html",
        title="Documentos",
        active="Documentos",
        docs=docs,
        url_for=url_for,
        messages=get_flashed_messages(with_categories=True),
    )


@app.route("/download/xml/<int:doc_id>")
def download_xml(doc_id):
    for d in listar_documentos():
        if d["id"] == doc_id and d.get("xml_path") and os.path.isfile(d["xml_path"]):
            return send_file(d["xml_path"], mimetype="application/xml", as_attachment=True, download_name=os.path.basename(d["xml_path"]))
    return "Arquivo XML não encontrado.", 404


@app.route("/download/pdf/<int:doc_id>")
def download_pdf(doc_id):
    for d in listar_documentos():
        if d["id"] == doc_id and d.get("xml_path") and os.path.isfile(d["xml_path"]):
            pdf_path = os.path.join(PDF_DIR, f"{os.path.splitext(os.path.basename(d['xml_path']))[0]}.pdf")
            if not os.path.isfile(pdf_path):
                return "PDF ainda não gerado.", 404
            return send_file(pdf_path, mimetype="application/pdf", as_attachment=True, download_name=os.path.basename(pdf_path))
    return "Arquivo PDF não encontrado.", 404


@app.route("/gerar_pdf/<int:doc_id>")
def gerar_pdf_externo(doc_id):
    for d in listar_documentos():
        if d["id"] == doc_id and d.get("xml_path") and os.path.isfile(d["xml_path"]):
            try:
                gerar_danfe_pdf(d["xml_path"], PDF_DIR)
                return redirect(url_for("download_pdf", doc_id=doc_id))
            except Exception as ex:
                return f"Erro ao gerar PDF: {ex}", 500
    return "XML não encontrado.", 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5003"))
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    print(f"NF-e Manager iniciado na porta {port}")
    print(f"Acesso local:  http://127.0.0.1:{port}")
    print(f"Acesso na rede: http://{local_ip}:{port}")
    from waitress import serve

    serve(app, host="0.0.0.0", port=port)
