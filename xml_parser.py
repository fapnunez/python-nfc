import xml.etree.ElementTree as ET

NS = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def txt(node, path, default=""):
    x = node.find(path, NS)
    return x.text.strip() if x is not None and x.text else default

def parse_xml(conteudo):
    root = ET.fromstring(conteudo)
    inf = root.find(".//nfe:infNFe", NS)
    if inf is None:
        raise ValueError("XML não contém infNFe.")

    chave = inf.attrib.get("Id", "").replace("NFe", "")
    ide = inf.find("nfe:ide", NS)
    emit = inf.find("nfe:emit", NS)
    dest = inf.find("nfe:dest", NS)
    total = inf.find("nfe:total/nfe:ICMSTot", NS)

    modelo = txt(ide, "nfe:mod") if ide is not None else ""
    tipo = "NFC-e" if modelo == "65" else "NF-e"

    return {
        "chave": chave,
        "tipo": tipo,
        "cnpj_emitente": txt(emit, "nfe:CNPJ") if emit is not None else "",
        "cnpj_destinatario": txt(dest, "nfe:CNPJ") if dest is not None else "",
        "numero": txt(ide, "nfe:nNF") if ide is not None else "",
        "serie": txt(ide, "nfe:serie") if ide is not None else "",
        "data_emissao": txt(ide, "nfe:dhEmi") or txt(ide, "nfe:dEmi"),
        "valor": float(txt(total, "nfe:vNF", "0") or 0) if total is not None else 0.0,
    }
