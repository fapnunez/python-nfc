import base64
import gzip
import os
import xml.etree.ElementTree as ET

from requests_pkcs12 import Pkcs12Adapter
import requests

PROD_URL = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
HOM_URL = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

NS = {
    "soap": "http://www.w3.org/2003/05/soap-envelope",
    "nfe": "http://www.portalfiscal.inf.br/nfe"
}

def _montar_envelope(cnpj, ultimo_nsu, tp_amb):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
 <soap12:Body>
  <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
   <nfeDadosMsg>
    <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
     <tpAmb>{tp_amb}</tpAmb>
     <cUFAutor>35</cUFAutor>
     <CNPJ>{cnpj}</CNPJ>
     <distNSU>
      <ultNSU>{ultimo_nsu}</ultNSU>
     </distNSU>
    </distDFeInt>
   </nfeDadosMsg>
  </nfeDistDFeInteresse>
 </soap12:Body>
</soap12:Envelope>"""

def _decodificar_doczip(valor):
    raw = base64.b64decode(valor)
    try:
        return gzip.decompress(raw)
    except Exception:
        return raw

def consultar_nfe_distribuicao(cnpj, certificado, senha, ambiente="Produção",
                               ultimo_nsu="000000000000000"):
    if not os.path.isfile(certificado):
        raise FileNotFoundError("Certificado A1 não encontrado.")

    tp_amb = "1" if ambiente == "Produção" else "2"
    url = PROD_URL if tp_amb == "1" else HOM_URL

    session = requests.Session()
    session.mount(
        "https://",
        Pkcs12Adapter(
            pkcs12_filename=certificado,
            pkcs12_password=senha
        )
    )

    envelope = _montar_envelope(cnpj, ultimo_nsu, tp_amb)

    resposta = session.post(
        url,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "application/soap+xml; charset=utf-8",
            "Accept": "application/soap+xml, text/xml"
        },
        timeout=90,
        verify=True
    )
    resposta.raise_for_status()

    root = ET.fromstring(resposta.content)

    cstat = root.find(".//nfe:cStat", NS)
    xmotivo = root.find(".//nfe:xMotivo", NS)
    cstat_text = cstat.text if cstat is not None else ""
    motivo = xmotivo.text if xmotivo is not None else ""

    if cstat_text not in ("138", "137"):
        raise RuntimeError(f"SEFAZ retornou cStat={cstat_text}: {motivo}")

    ult = root.find(".//nfe:ultNSU", NS)
    ult_nsu = ult.text if ult is not None else ultimo_nsu

    documentos = []
    for doczip in root.findall(".//nfe:docZip", NS):
        nsu = doczip.attrib.get("NSU", "")
        schema = doczip.attrib.get("schema", "")
        xml = _decodificar_doczip(doczip.text or "")
        documentos.append({
            "nsu": nsu,
            "schema": schema,
            "xml": xml
        })

    return {
        "ult_nsu": ult_nsu,
        "max_nsu": root.findtext(".//nfe:maxNSU", default=ultimo_nsu, namespaces=NS),
        "documentos": documentos,
        "cstat": cstat_text,
        "motivo": motivo
    }
