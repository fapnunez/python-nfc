import os
import xml.etree.ElementTree as ET
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def t(node, path, default=""):
    x = node.find(path, NS)
    return x.text if x is not None and x.text else default

def gerar_danfe_pdf(xml_path, pasta_pdf):
    with open(xml_path, "rb") as f:
        root = ET.fromstring(f.read())

    inf = root.find(".//nfe:infNFe", NS)
    ide = inf.find("nfe:ide", NS)
    emit = inf.find("nfe:emit", NS)
    dest = inf.find("nfe:dest", NS)
    total = inf.find("nfe:total/nfe:ICMSTot", NS)

    chave = inf.attrib.get("Id", "").replace("NFe", "")
    numero = t(ide, "nfe:nNF")
    serie = t(ide, "nfe:serie")
    emissao = t(ide, "nfe:dhEmi") or t(ide, "nfe:dEmi")
    valor = t(total, "nfe:vNF", "0")
    nome_emit = t(emit, "nfe:xNome")
    cnpj_emit = t(emit, "nfe:CNPJ")
    nome_dest = t(dest, "nfe:xNome")
    cnpj_dest = t(dest, "nfe:CNPJ")

    os.makedirs(pasta_pdf, exist_ok=True)
    saida = os.path.join(pasta_pdf, f"{chave or numero}.pdf")

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Title"], fontSize=14, leading=16)
    normal = ParagraphStyle("normal2", parent=styles["Normal"], fontSize=8, leading=10)

    doc = SimpleDocTemplate(
        saida, pagesize=A4,
        rightMargin=10*mm, leftMargin=10*mm,
        topMargin=10*mm, bottomMargin=10*mm
    )

    story = [
        Paragraph("DANFE — DOCUMENTO AUXILIAR DA NF-e", titulo),
        Spacer(1, 4*mm)
    ]

    dados = [
        ["Emitente", nome_emit, "CNPJ", cnpj_emit],
        ["Destinatário", nome_dest, "CNPJ", cnpj_dest],
        ["Número", numero, "Série", serie],
        ["Emissão", emissao, "Valor NF", f"R$ {valor}"],
        ["Chave de acesso", chave, "", ""],
    ]

    tabela = Table(dados, colWidths=[28*mm, 78*mm, 28*mm, 56*mm])
    tabela.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tabela)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("<b>Produtos / Serviços</b>", styles["Heading3"]))

    linhas = [["Item", "Descrição", "Qtd", "V. Unit.", "V. Total"]]
    for i, det in enumerate(root.findall(".//nfe:det", NS), 1):
        prod = det.find("nfe:prod", NS)
        if prod is None:
            continue
        linhas.append([
            str(i),
            t(prod, "nfe:xProd"),
            t(prod, "nfe:qCom"),
            t(prod, "nfe:vUnCom"),
            t(prod, "nfe:vProd")
        ])

    tabela_prod = Table(linhas, colWidths=[12*mm, 86*mm, 24*mm, 30*mm, 30*mm], repeatRows=1)
    tabela_prod.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 7),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tabela_prod)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        f"<b>Chave de acesso:</b> {chave}<br/>"
        "Documento gerado a partir do XML da NF-e. "
        "Este PDF é uma representação auxiliar e não substitui o XML fiscal.",
        normal
    ))

    doc.build(story)
    return saida
