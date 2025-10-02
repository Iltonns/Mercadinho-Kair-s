# ==============================================================================
# 1. IMPORTS E CONFIGURAÇÃO
# ==============================================================================
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import re

DB_NAME = 'loja.db'

# ==============================================================================
# 2. CLASSES DE MODELO (Representação de Dados)
# ==============================================================================
class User(UserMixin):
    """Modelo de Usuário para Flask-Login."""
    def __init__(self, id, username, password_hash=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return str(self.id)

    def verify_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash."""
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

class Produto:
    def __init__(self, id, nome, preco, quantidade, codigo_barras=None):
        self.id = id
        self.nome = nome
        self.preco = preco
        self.quantidade = quantidade
        self.codigo_barras = codigo_barras
        
    def to_dict(self):
        """Retorna o objeto Produto como um dicionário."""
        return {
            'id': self.id,
            'nome': self.nome,
            'preco': self.preco,
            'quantidade': self.quantidade,
            'codigo_barras': self.codigo_barras
        }

class Cliente:
    def __init__(self, id, nome, telefone=None, email=None, cpf_cnpj=None, endereco=None):
        self.id = id
        self.nome = nome
        self.telefone = telefone
        self.email = email
        self.cpf_cnpj = cpf_cnpj
        self.endereco = endereco

    def to_dict(self):
        """Retorna o objeto Cliente como um dicionário."""
        return {
            'id': self.id,
            'nome': self.nome,
            'telefone': self.telefone,
            'email': self.email,
            'cpf_cnpj': self.cpf_cnpj,
            'endereco': self.endereco
        }

# ==============================================================================
# 3. CONEXÃO E SETUP DO BANCO DE DADOS
# ==============================================================================
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn

def setup_database():
    """Cria tabelas se não existirem."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabela Usuarios (para autenticação)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            );
        """)
        
        # Tabela Produtos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL,
                codigo_barras TEXT UNIQUE
            );
        """)

        # Tabela Clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                cpf_cnpj TEXT UNIQUE,
                endereco TEXT
            );
        """)

        # Tabela Vendas (Transações)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                data_venda TEXT NOT NULL,
                total REAL NOT NULL,
                forma_pagamento TEXT NOT NULL,
                valor_pago REAL NOT NULL,
                troco REAL NOT NULL,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            );
        """)

        # Tabela ItensVendidos (Detalhes da Venda)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_vendidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venda_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL,
                FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos_pesaveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                preco_por_kg REAL NOT NULL,
                codigo_personalizado TEXT UNIQUE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE CASCADE
            );
        """)
        
        # Tabela Produtos Pesáveis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos_pesaveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                preco_por_kg REAL NOT NULL,
                codigo_personalizado TEXT UNIQUE,
                FOREIGN KEY (produto_id) REFERENCES produtos (id) ON DELETE CASCADE
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL,
                codigo_barras TEXT UNIQUE
            );
        """)
        
        conn.commit()
        print("Banco de dados configurado com sucesso.")  # Log de sucesso
        return True
    except Exception as e:
        print(f"Erro ao configurar o banco de dados: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ==============================================================================
# 4. FUNÇÕES DE AUTENTICAÇÃO (User)
# ==============================================================================
def add_user(username, password):
    """Adiciona um novo usuário ao banco de dados."""
    if not username or not password:
        return False, "Nome de usuário e senha são obrigatórios."
        
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verifica se o usuário já existe
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Nome de usuário já existe."

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)", 
            (username, password_hash)
        )
        conn.commit()
        return True, "Usuário cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Nome de usuário já existe."
    except Exception as e:
        print(f"Erro ao adicionar usuário: {e}")
        return False, "Erro interno ao cadastrar usuário."
    finally:
        if conn:
            conn.close()

def get_user_by_username(username):
    """Busca usuário pelo nome de usuário."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['password_hash'])
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário por nome: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_by_id(user_id):
    """Busca usuário pelo ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash FROM usuarios WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['password_hash'])
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário por ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

# ==============================================================================
# 5. FUNÇÕES DE VALIDAÇÃO
# ==============================================================================
def validar_preco(preco_str):
    """Valida se a string é um preço válido e retorna o float."""
    try:
        preco_float = float(str(preco_str).replace(',', '.'))
        if preco_float >= 0:
            return True, round(preco_float, 2)
        return False, 0.0
    except ValueError:
        return False, 0.0

def validar_quantidade(quantidade_str):
    """Valida se a string é uma quantidade inteira válida."""
    try:
        qtd_int = int(quantidade_str)
        if qtd_int >= 0:
            return True, qtd_int
        return False, 0
    except ValueError:
        return False, 0

# ==============================================================================
# 6. FUNÇÕES DE PRODUTOS
# ==============================================================================
def adicionar_produto(nome, preco, quantidade, codigo_barras, preco_por_kg=None):
    """Adiciona um novo produto ao banco de dados, incluindo o preço por KG se for produto pesável."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insere produto na tabela 'produtos'
        cursor.execute(
            "INSERT INTO produtos (nome, preco, quantidade, codigo_barras) VALUES (?, ?, ?, ?)",
            (nome, preco, quantidade, codigo_barras if codigo_barras else None)
        )
        produto_id = cursor.lastrowid
        
        # Se o produto tem preço por KG, insere na tabela 'produtos_pesaveis'
        if preco_por_kg:
            cursor.execute(
                "INSERT INTO produtos_pesaveis (produto_id, preco_por_kg) VALUES (?, ?)",
                (produto_id, preco_por_kg)
            )

        conn.commit()
        return True, "Produto adicionado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Código de barras já existe."
    except Exception as e:
        print(f"Erro ao adicionar produto: {e}")
        return False, f"Erro ao adicionar produto: {e}"
    finally:
        if conn:
            conn.close()

def atualizar_produto(id, nome, preco, quantidade, codigo_barras):
    """Atualiza um produto existente."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE produtos SET nome=?, preco=?, quantidade=?, codigo_barras=? WHERE id=?",
            (nome, preco, quantidade, codigo_barras if codigo_barras else None, id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Produto atualizado com sucesso."
        else:
            return False, "Produto não encontrado."
    except sqlite3.IntegrityError:
        return False, "Código de barras já existe ou duplicado."
    except Exception as e:
        print(f"Erro ao atualizar produto: {e}")
        return False, f"Erro ao atualizar produto: {e}"
    finally:
        if conn:
            conn.close()

def excluir_produto(id):
    """Exclui um produto."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM produtos WHERE id=?", (id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return True, "Produto excluído com sucesso."
        else:
            return False, "Produto não encontrado."
    except Exception as e:
        print(f"Erro ao excluir produto: {e}")
        return False, f"Erro ao excluir produto: {e}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    """Lista todos os produtos."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos ORDER BY nome ASC")
        produtos_data = cursor.fetchall()
        
        produtos_lista = [
            Produto(
                id=p['id'],
                nome=p['nome'],
                preco=p['preco'],
                quantidade=p['quantidade'],
                codigo_barras=p['codigo_barras']
            ).to_dict() for p in produtos_data
        ]
        return produtos_lista
    except Exception as e:
        print(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def buscar_produto_por_id(id):
    """Busca um produto pelo ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
        p = cursor.fetchone()
        
        if p:
            return Produto(
                id=p['id'],
                nome=p['nome'],
                preco=p['preco'],
                quantidade=p['quantidade'],
                codigo_barras=p['codigo_barras']
            ).to_dict()
        return None
    except Exception as e:
        print(f"Erro ao buscar produto por ID: {e}")
        return None
    finally:
        if conn:
            conn.close()


def buscar_produto_por_codigo(termo):
    """Busca produto por código de barras (exato) ou código personalizado (exato)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Primeiro tenta buscar por Código de Barras exato
        cursor.execute("SELECT * FROM produtos WHERE codigo_barras = ?", (termo,))
        p = cursor.fetchone()
        
        if p:
            return {
                'id': p['id'],
                'nome': p['nome'],
                'preco': p['preco'],
                'quantidade': p['quantidade'],
                'codigo_barras': p['codigo_barras'],
                'pesavel': False
            }

        # 2. Tenta buscar por Código Personalizado de produto pesável
        # OBS: A função buscar_produto_pesavel_por_codigo deve estar definida e funcional.
        produto_pesavel = buscar_produto_pesavel_por_codigo(termo)
        if produto_pesavel:
            return produto_pesavel

        # 3. Tenta buscar por ID (se for numérico)
        if termo.isdigit():
            cursor.execute("SELECT * FROM produtos WHERE id = ?", (termo,))
            p = cursor.fetchone()
            if p:
                return {
                    'id': p['id'],
                    'nome': p['nome'],
                    'preco': p['preco'],
                    'quantidade': p['quantidade'],
                    'codigo_barras': p['codigo_barras'],
                    'pesavel': False
                }
                
        return None
    except Exception as e:
        # Se um erro de banco de dados ocorrer aqui, ele é capturado e logado.
        print(f"Erro na busca de produto por código: {e}")
        return None
    finally:
        if conn:
            conn.close()
            

def buscar_produtos_por_nome(termo):
    """Busca produtos por nome parcial ou código de barras parcial/exato (retorna lista)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Busca por nome OU código de barras
        termo_like = f'%{termo}%'
        cursor.execute("""
            SELECT * FROM produtos 
            WHERE nome LIKE ? OR codigo_barras LIKE ?
            ORDER BY nome ASC
        """, (termo_like, termo_like))
        
        produtos_data = cursor.fetchall()
        
        produtos_lista = [
            Produto(
                id=p['id'],
                nome=p['nome'],
                preco=p['preco'],
                quantidade=p['quantidade'],
                codigo_barras=p['codigo_barras']
            ).to_dict() for p in produtos_data
        ]
        return produtos_lista
    except Exception as e:
        print(f"Erro na busca de produtos por nome: {e}")
        return []
    finally:
        if conn:
            conn.close()
            

# ==============================================================================
# 7. FUNÇÕES PARA PRODUTOS PESÁVEIS
# ==============================================================================

def adicionar_produto_pesavel(produto_id, preco_por_kg, codigo_personalizado):
    """Adiciona um produto à lista de produtos pesáveis."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Inserir produto pesável na tabela 'produtos_pesaveis'
        cursor.execute("""
            INSERT INTO produtos_pesaveis (produto_id, preco_por_kg, codigo_personalizado) 
            VALUES (?, ?, ?)
        """, (produto_id, preco_por_kg, codigo_personalizado))

        conn.commit()
        return True, "Produto pesável adicionado com sucesso."
    except sqlite3.IntegrityError:
        return False, "Código personalizado já existe."
    except Exception as e:
        return False, f"Erro ao adicionar produto pesável: {e}"
    finally:
        if conn:
            conn.close()


def buscar_produto_pesavel_por_codigo(codigo):
    """Busca produto pesável pelo código personalizado."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pp.*, p.nome, p.quantidade 
            FROM produtos_pesaveis pp
            JOIN produtos p ON pp.produto_id = p.id
            WHERE pp.codigo_personalizado = ?
        """, (codigo,))
        
        produto = cursor.fetchone()
        if produto:
            return {
                'id': produto['produto_id'],
                'nome': produto['nome'],
                'preco_por_kg': produto['preco_por_kg'],
                'codigo_personalizado': produto['codigo_personalizado'],
                'quantidade': produto['quantidade'],
                'pesavel': True
            }
        return None
    except Exception as e:
        print(f"Erro ao buscar produto pesável: {e}")
        return None
    finally:
        if conn:
            conn.close()

def listar_produtos_pesaveis():
    """Lista todos os produtos pesáveis (função que o app.py está procurando)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifique se o produto está na tabela 'produtos_pesaveis' e se o preço por KG está acima de zero
        cursor.execute("""
            SELECT pp.*, p.nome, p.quantidade, p.preco
            FROM produtos_pesaveis pp
            JOIN produtos p ON pp.produto_id = p.id
            WHERE pp.preco_por_kg > 0  -- Garante que o preço por KG é válido
            ORDER BY p.nome
        """)
        
        produtos = cursor.fetchall()
        return [dict(produto) for produto in produtos]
    except Exception as e:
        print(f"Erro ao listar produtos pesáveis: {e}")
        return []
    finally:
        if conn:
            conn.close()


def listar_produtos_para_associar():
    """Lista produtos na tabela 'produtos' que AINDA NÃO SÃO pesáveis."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                p.id, 
                p.nome, 
                p.preco
            FROM produtos p
            LEFT JOIN produtos_pesaveis pp ON p.id = pp.produto_id
            WHERE pp.produto_id IS NULL  -- Garante que o produto não foi associado
            ORDER BY p.nome
        """)
        produtos_data = cursor.fetchall()

        produtos = []
        for row in produtos_data:
            produtos.append({
                'id': row['id'], 
                'nome': row['nome'], 
                'preco': row['preco']
            })
        return produtos
    except Exception as e:
        print(f"Erro ao listar produtos para associação: {e}")
        return []
    finally:
        if conn:
            conn.close()


def excluir_produto_pesavel(id_pesavel):
    """Remove a associação do produto pesável."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produtos_pesaveis WHERE id=?", (id_pesavel,))
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Produto pesável excluído com sucesso."
        return False, "Associação de produto pesável não encontrada."
    except Exception as e:
        print(f"Erro ao excluir produto pesável: {e}")
        return False, f"Erro ao excluir produto pesável: {e}"
    finally:
        if conn:
            conn.close()

# ==============================================================================
# 8. FUNÇÕES DE CLIENTES
# ==============================================================================
def listar_clientes():
    """Lista todos os clientes."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes ORDER BY nome ASC")
        clientes_data = cursor.fetchall()
        
        clientes_lista = [
            Cliente(
                id=c['id'],
                nome=c['nome'],
                telefone=c['telefone'],
                email=c['email'],
                cpf_cnpj=c['cpf_cnpj'],
                endereco=c['endereco']
            ).to_dict() for c in clientes_data
        ]
        return clientes_lista
    except Exception as e:
        print(f"Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()
            
def buscar_cliente_por_id(id):
    """Busca um cliente pelo ID."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (id,))
        c = cursor.fetchone()
        
        if c:
            return Cliente(
                id=c['id'],
                nome=c['nome'],
                telefone=c['telefone'],
                email=c['email'],
                cpf_cnpj=c['cpf_cnpj'],
                endereco=c['endereco']
            ).to_dict()
        return None
    except Exception as e:
        print(f"Erro ao buscar cliente por ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def adicionar_cliente(nome, telefone, email, cpf_cnpj, endereco):
    """Adiciona um novo cliente ao banco de dados."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Evitar CPF/CNPJ duplicado (se fornecido)
        if cpf_cnpj:
            cursor.execute("SELECT id FROM clientes WHERE cpf_cnpj = ?", (cpf_cnpj,))
            if cursor.fetchone():
                return False, "CPF/CNPJ já cadastrado."

        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, cpf_cnpj, endereco) VALUES (?, ?, ?, ?, ?)",
            (nome, telefone, email, cpf_cnpj, endereco)
        )
        conn.commit()
        return True, "Cliente adicionado com sucesso."
    except Exception as e:
        print(f"Erro ao adicionar cliente: {e}")
        return False, f"Erro ao adicionar cliente: {e}"
    finally:
        if conn:
            conn.close()

def atualizar_cliente(id, nome, telefone, email, cpf_cnpj, endereco):
    """Atualiza um cliente existente."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Evitar CPF/CNPJ duplicado por outro cliente
        if cpf_cnpj:
            cursor.execute("SELECT id FROM clientes WHERE cpf_cnpj = ? AND id != ?", (cpf_cnpj, id))
            if cursor.fetchone():
                return False, "CPF/CNPJ já cadastrado para outro cliente."
                
        cursor.execute(
            "UPDATE clientes SET nome=?, telefone=?, email=?, cpf_cnpj=?, endereco=? WHERE id=?",
            (nome, telefone, email, cpf_cnpj, endereco, id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            return True, "Cliente atualizado com sucesso."
        else:
            return False, "Cliente não encontrado."
    except Exception as e:
        print(f"Erro ao atualizar cliente: {e}")
        return False, f"Erro ao atualizar cliente: {e}"
    finally:
        if conn:
            conn.close()

def excluir_cliente(id):
    """Exclui um cliente (Não implementa verificação de vendas para manter a simplicidade)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM clientes WHERE id=?", (id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return True, "Cliente excluído com sucesso."
        else:
            return False, "Cliente não encontrado."
    except Exception as e:
        print(f"Erro ao excluir cliente: {e}")
        return False, f"Erro ao excluir cliente: {e}"
    finally:
        if conn:
            conn.close()

# ==============================================================================
# 9. FUNÇÕES DE VENDAS (PDV)
# ==============================================================================
def registrar_venda_completa(self, cliente_id, itens_carrinho, total, forma_pagamento, valor_pago, troco):
    """Registrar venda completa no banco de dados"""
    try:
        # 1. Registrar a venda principal
        query_venda = """
        INSERT INTO vendas (cliente_id, total, forma_pagamento, valor_pago, troco, data_venda)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """
        self.cursor.execute(query_venda, (cliente_id, total, forma_pagamento, valor_pago, troco))
        venda_id = self.cursor.lastrowid
        
        # 2. Registrar os itens da venda
        query_item = """
        INSERT INTO itens_venda (venda_id, produto_id, quantidade, preco_unitario, subtotal)
        VALUES (?, ?, ?, ?, ?)
        """
        
        # 3. Atualizar estoque
        query_estoque = "UPDATE produtos SET estoque = estoque - ? WHERE id = ?"
        
        for item in itens_carrinho:
            produto_id = item.get('id')
            quantidade = item.get('quantidade', 1)
            preco_unitario = item.get('preco', 0)
            subtotal = quantidade * preco_unitario
            
            # Registrar item
            self.cursor.execute(query_item, (venda_id, produto_id, quantidade, preco_unitario, subtotal))
            
            # Atualizar estoque
            self.cursor.execute(query_estoque, (quantidade, produto_id))
        
        self.conn.commit()
        print(f"DEBUG: Venda #{venda_id} registrada com sucesso!")
        return 1, "Venda registrada com sucesso (Placeholder)."
        
    except Exception as e:
        self.conn.rollback()
        print(f"ERRO AO REGISTRAR VENDA: {e}")
        return None, f"Erro ao registrar venda: {str(e)}"

def excluir_venda(venda_id):
    """Exclui uma venda e reverte o estoque dos produtos envolvidos."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Obter detalhes dos itens vendidos para reverter o estoque
        cursor.execute(
            "SELECT produto_id, quantidade FROM itens_vendidos WHERE venda_id = ?", 
            (venda_id,)
        )
        itens = cursor.fetchall()
        
        if not itens:
            cursor.execute("SELECT id FROM vendas WHERE id = ?", (venda_id,))
            if not cursor.fetchone():
                return False, "Venda não encontrada."

        # 2. Reverter o Estoque
        for item in itens:
            cursor.execute(
                "UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?",
                (item['quantidade'], item['produto_id'])
            )

        # 3. Excluir Itens Vendidos (ON DELETE CASCADE deveria cuidar disso, mas fazemos manualmente para garantir)
        cursor.execute("DELETE FROM itens_vendidos WHERE venda_id = ?", (venda_id,))
        
        # 4. Excluir Venda (Cabeçalho)
        cursor.execute("DELETE FROM vendas WHERE id = ?", (venda_id,))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return False, "Venda não encontrada após as tentativas de reversão."

        conn.commit()
        return True, f"Venda #{venda_id} excluída e estoque restaurado com sucesso."
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ ERRO ao excluir venda: {e}")  # DEBUG
        return False, f"Erro durante a exclusão da venda: {e}"
    finally:
        if conn:
            conn.close()

def get_venda_detalhada_por_id(venda_id):
    """Retorna todos os detalhes de uma venda, incluindo cliente e itens."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Buscar Cabeçalho da Venda e Cliente
        cursor.execute("""
            SELECT 
                v.id, v.data_venda, v.total, v.forma_pagamento, v.valor_pago, v.troco,
                c.nome AS cliente_nome
            FROM vendas v
            LEFT JOIN clientes c ON v.cliente_id = c.id
            WHERE v.id = ?
        """, (venda_id,))
        venda_data = cursor.fetchone()
        
        if not venda_data:
            return None

        venda = dict(venda_data)
        
        # 2. Buscar Itens Vendidos
        cursor.execute("""
            SELECT 
                iv.quantidade, iv.preco_unitario, 
                p.nome AS produto_nome, p.codigo_barras
            FROM itens_vendidos iv
            JOIN produtos p ON iv.produto_id = p.id
            WHERE iv.venda_id = ?
        """, (venda_id,))
        
        itens_data = cursor.fetchall()
        venda['itens'] = [dict(item) for item in itens_data]
        
        return venda
        
    except Exception as e:
        print(f"Erro ao buscar venda detalhada: {e}")
        return None
    finally:
        if conn:
            conn.close()
            
def get_vendas_por_periodo(data_inicio=None, data_fim=None):
    """Buscar vendas por período"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT 
            v.id as venda_id, v.data_venda, v.total, v.forma_pagamento, v.valor_pago, v.troco,
            c.nome as cliente_nome, c.id as cliente_id,
            iv.produto_id, p.nome as produto_nome, p.codigo_barras,
            iv.quantidade, iv.preco_unitario
        FROM vendas v
        LEFT JOIN clientes c ON v.cliente_id = c.id
        JOIN itens_vendidos iv ON v.id = iv.venda_id
        JOIN produtos p ON iv.produto_id = p.id
        WHERE 1=1
        """
        
        params = []
        
        if data_inicio:
            query += " AND DATE(v.data_venda) >= ?"
            params.append(data_inicio)
        
        if data_fim:
            query += " AND DATE(v.data_venda) <= ?"
            params.append(data_fim)
        
        query += " ORDER BY v.data_venda DESC, v.id DESC"
        
        cursor.execute(query, params)
        resultados = cursor.fetchall()
        
        vendas = []
        for row in resultados:
            vendas.append(dict(row))
        
        print(f"DEBUG: {len(vendas)} vendas no período {data_inicio} a {data_fim}")
        return vendas
        
    except Exception as e:
        print(f"Erro ao buscar vendas por período: {e}")
        return []
    finally:
        if conn:
            conn.close()            

# ==============================================================================
# 10. FUNÇÕES DE RELATÓRIOS E ESTATÍSTICAS
# ==============================================================================
def get_relatorio_vendas_detalhado():
    """Retorna o histórico detalhado de vendas (um registro por item vendido)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # QUERY COMPLETAMENTE REVISADA
        cursor.execute("""
            SELECT
                v.id as venda_id,
                v.data_venda,
                v.total as venda_total,
                v.forma_pagamento,
                v.valor_pago,
                v.troco,
                c.nome AS cliente_nome,
                iv.quantidade,
                iv.preco_unitario,
                p.nome AS produto_nome,
                p.codigo_barras,
                p.id as produto_id
            FROM vendas v
            JOIN itens_vendidos iv ON v.id = iv.venda_id
            JOIN produtos p ON iv.produto_id = p.id
            LEFT JOIN clientes c ON v.cliente_id = c.id
            ORDER BY v.data_venda DESC, v.id DESC
        """)
        
        vendas_data = cursor.fetchall()
        
        vendas_lista = []
        for row in vendas_data:
            # CONVERSÃO SEGURA para dicionário
            if hasattr(row, '_asdict'):  # Para SQLAlchemy-like objects
                venda_dict = row._asdict()
            elif hasattr(row, 'keys'):   # Para sqlite3.Row objects
                venda_dict = dict(zip(row.keys(), row))
            else:
                # Fallback seguro
                venda_dict = {
                    'id': row[0] if len(row) > 0 else 0,
                    'data_venda': row[1] if len(row) > 1 else '',
                    'total': row[2] if len(row) > 2 else 0.0,
                    'forma_pagamento': row[3] if len(row) > 3 else '',
                    'valor_pago': row[4] if len(row) > 4 else 0.0,
                    'troco': row[5] if len(row) > 5 else 0.0,
                    'cliente_nome': row[6] if len(row) > 6 else 'N/A',
                    'quantidade': row[7] if len(row) > 7 else 0,
                    'preco_unitario': row[8] if len(row) > 8 else 0.0,
                    'produto_nome': row[9] if len(row) > 9 else '',
                    'codigo_barras': row[10] if len(row) > 10 else '',
                    'produto_id': row[11] if len(row) > 11 else 0
                }
            
            # Estrutura padronizada (tratamento de None para cliente_nome)
            venda_item = {
                'id': venda_dict.get('venda_id') or venda_dict.get('id', 0),
                'data_venda': venda_dict.get('data_venda', ''),
                'total': float(venda_dict.get('venda_total') or venda_dict.get('total', 0.0)),
                'forma_pagamento': venda_dict.get('forma_pagamento', ''),
                'valor_pago': float(venda_dict.get('valor_pago', 0.0)),
                'troco': float(venda_dict.get('troco', 0.0)),
                'cliente_nome': venda_dict.get('cliente_nome') or 'N/A',
                'quantidade': int(venda_dict.get('quantidade', 0)),
                'preco_unitario': float(venda_dict.get('preco_unitario', 0.0)),
                'produto_nome': venda_dict.get('produto_nome', ''),
                'codigo_barras': venda_dict.get('codigo_barras', ''),
                'produto_id': venda_dict.get('produto_id', 0)
            }
            
            vendas_lista.append(venda_item)
            
        print(f"✅ DEBUG: Retornando {len(vendas_lista)} registros de vendas")  # DEBUG
        return vendas_lista
        
    except Exception as e:
        print(f"❌ ERRO CRÍTICO em get_relatorio_vendas_detalhado: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            conn.close()

def get_relatorio_estoque():
    """Retorna todos os produtos (para relatórios gerais de estoque)."""
    return listar_produtos()

def get_relatorio_movimentacao_estoque():
    """Retorna as últimas 100 movimentações de estoque (simulado via Itens Vendidos)."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                iv.quantidade,
                v.data_venda,
                p.nome AS produto_nome,
                'SAÍDA' AS tipo_movimentacao
            FROM itens_vendidos iv
            JOIN vendas v ON iv.venda_id = v.id
            JOIN produtos p ON iv.produto_id = p.id
            ORDER BY v.data_venda DESC
            LIMIT 100
        """)
        
        movimentacoes_data = cursor.fetchall()
        
        return [dict(m) for m in movimentacoes_data]
        
    except Exception as e:
        print(f"Erro ao obter relatório de movimentação: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_estatisticas_gerais():
    """
    CORRIGIDO: Coleta e retorna estatísticas gerais para o Dashboard.
    Assegura que os valores padrão são 0 em caso de tabelas vazias.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Usando SUM(coluna) para obter o valor total, coalesce(SUM(coluna), 0) garante 0 se não houver registros
        cursor.execute("SELECT COALESCE(SUM(preco * quantidade), 0) FROM produtos")
        valor_estoque = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id) FROM produtos")
        total_produtos = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(id) FROM clientes")
        total_clientes = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COALESCE(SUM(total), 0) FROM vendas")
        total_vendas_valor = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(id) FROM vendas")
        total_transacoes = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(id) FROM produtos WHERE quantidade <= 10") # Produtos com estoque baixo/esgotado
        produtos_estoque_baixo = cursor.fetchone()[0] or 0

        # Tenta a consulta com tabela itens_vendidos. Se falhar (e a tabela existir), retorna 0.
        try:
             cursor.execute("SELECT COALESCE(SUM(quantidade), 0) FROM itens_vendidos")
             total_itens_vendidos = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
             total_itens_vendidos = 0 # Tabela não existe ou outro erro, assumir 0.
        
        return {
            'valor_estoque': round(valor_estoque, 2),
            'total_produtos': total_produtos,
            'total_clientes': total_clientes,
            'total_vendas_valor': round(total_vendas_valor, 2),
            'total_transacoes': total_transacoes,
            'produtos_estoque_baixo': produtos_estoque_baixo,
            'total_itens_vendidos': total_itens_vendidos,
        }
        
    except Exception as e:
        # Se falhar aqui, o problema é mais profundo (conexão ou outras tabelas)
        print(f"FATAL: Erro ao obter estatísticas gerais: {e}")
        return {
            'valor_estoque': 0.0,
            'total_produtos': 0,
            'total_clientes': 0,
            'total_vendas_valor': 0.0,
            'total_transacoes': 0,
            'produtos_estoque_baixo': 0,
            'total_itens_vendidos': 0,
        }
    finally:
        if conn:
            conn.close()
            
# ==============================================================================
# 11. BLOCO DE EXECUÇÃO
# ==============================================================================
if __name__ == '__main__':
    if setup_database():
        print("Banco de dados configurado (tabelas criadas ou já existentes).")
    else:
        print("Erro na configuração do banco de dados.")