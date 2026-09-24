import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "dados", "banco.db")

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT UNIQUE NOT NULL,
            razao_social TEXT,
            uf TEXT DEFAULT 'SP',
            certificado TEXT,
            senha TEXT,
            ambiente TEXT DEFAULT 'Produção',
            ult_nsu TEXT DEFAULT '000000000000000',
            ultima_consulta TEXT,
            bloqueado_ate TEXT
        )
        """)
        colunas = {row[1] for row in c.execute("PRAGMA table_info(empresas)").fetchall()}
        if "ultima_consulta" not in colunas:
            c.execute("ALTER TABLE empresas ADD COLUMN ultima_consulta TEXT")
        if "bloqueado_ate" not in colunas:
            c.execute("ALTER TABLE empresas ADD COLUMN bloqueado_ate TEXT")
        c.execute("""
        CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT UNIQUE,
            cnpj_emitente TEXT,
            cnpj_destinatario TEXT,
            numero TEXT,
            serie TEXT,
            tipo TEXT,
            data_emissao TEXT,
            valor REAL,
            xml_path TEXT,
            pdf_path TEXT,
            nsu TEXT
        )
        """)

def salvar_empresa(cnpj, razao, uf, certificado, senha, ambiente):
    with conn() as c:
        c.execute("""
        INSERT INTO empresas(cnpj, razao_social, uf, certificado, senha, ambiente)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(cnpj) DO UPDATE SET
            razao_social=excluded.razao_social,
            uf=excluded.uf,
            certificado=excluded.certificado,
            senha=excluded.senha,
            ambiente=excluded.ambiente
        """, (cnpj, razao, uf, certificado, senha, ambiente))

def listar_empresas():
    with conn() as c:
        return [dict(x) for x in c.execute("SELECT * FROM empresas ORDER BY razao_social").fetchall()]

def obter_empresa(id_empresa):
    with conn() as c:
        r = c.execute("SELECT * FROM empresas WHERE id=?", (id_empresa,)).fetchone()
        return dict(r) if r else None

def atualizar_nsu(id_empresa, nsu, momento_iso):
    with conn() as c:
        c.execute(
            "UPDATE empresas SET ult_nsu=?, ultima_consulta=?, bloqueado_ate=NULL WHERE id=?",
            (nsu, momento_iso, id_empresa),
        )

def registrar_bloqueio(id_empresa, momento_iso, bloqueado_ate_iso):
    with conn() as c:
        c.execute(
            "UPDATE empresas SET ultima_consulta=?, bloqueado_ate=? WHERE id=?",
            (momento_iso, bloqueado_ate_iso, id_empresa),
        )

def salvar_documento(chave, cnpj_emitente, cnpj_destinatario, numero, serie, tipo,
                     data_emissao, valor, xml_path, pdf_path, nsu):
    with conn() as c:
        c.execute("""
        INSERT INTO documentos
        (chave, cnpj_emitente, cnpj_destinatario, numero, serie, tipo,
         data_emissao, valor, xml_path, pdf_path, nsu)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(chave) DO UPDATE SET
            xml_path=excluded.xml_path,
            nsu=excluded.nsu
        """, (
            chave, cnpj_emitente, cnpj_destinatario, numero, serie, tipo,
            data_emissao, valor, xml_path, pdf_path, nsu
        ))

def listar_documentos():
    with conn() as c:
        return [dict(x) for x in c.execute(
            "SELECT * FROM documentos ORDER BY id DESC"
        ).fetchall()]
