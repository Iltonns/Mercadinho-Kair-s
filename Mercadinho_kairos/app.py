# ==============================================================================
# 1. IMPORTS
# ==============================================================================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
import Mercadinho_kairos.logica_banco as db
import re
import os
import io
import pandas as pd
import copy
from Imports ReportLab para PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ==============================================================================
# 2. CONFIGURAÇÃO INICIAL
# ==============================================================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_super_segura_aqui_2024')

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "warning"

# ==============================================================================
# 3. FUNÇÕES ESSENCIAIS DO FLASK-LOGIN
# ==============================================================================
@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário a partir do ID."""
    try:
        return db.get_user_by_id(int(user_id))
    except (ValueError, TypeError):
        return None

# ==============================================================================
# 4. FUNÇÕES AUXILIARES DE SEGURANÇA E VALIDAÇÃO
# ==============================================================================
def sanitizar_input(texto):
    """Remove caracteres perigosos e tags HTML."""
    if not texto: return ""
    texto = re.sub(r'<[^>]*>', '', texto)
    return texto.strip()

def validar_email(email):
    """Valida formato de email."""
    if not email: return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==============================================================================
# 5. ROTAS DE AUTENTICAÇÃO
# ==============================================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Você já está logado!', 'info')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            username = sanitizar_input(request.form.get('username', ''))
            password = request.form.get('password', '')
            usuario = db.get_user_by_username(username)

            if usuario and usuario.verify_password(password):
                login_user(usuario)
                session['usuario_nome'] = usuario.username
                flash(f'Bem-vindo, {usuario.username}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Usuário ou senha inválidos.', 'danger')
        except Exception as e:
            print(f"Erro durante o login: {e}")  # Log de erro
            flash('Erro durante o login. Tente novamente.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    session.clear()
    flash(f'Até logo, {username}! Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            username = sanitizar_input(request.form.get('username', ''))
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if password != confirm_password:
                flash('As senhas não coincidem.', 'danger')
                return render_template('cadastro.html')
                
            sucesso, mensagem = db.add_user(username, password)
            
            if sucesso:
                flash('Usuário criado com sucesso! Por favor, faça login.', 'success')
                return redirect(url_for('login'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro durante o cadastro: {e}")  # Log de erro
            flash('Erro durante o cadastro. Tente novamente.', 'danger')
    return render_template('cadastro.html')

# ==============================================================================
# 6. ROTAS PRINCIPAIS
# ==============================================================================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        estatisticas = db.get_estatisticas_gerais()
        produtos_recentes = db.listar_produtos()[:5]
        
        return render_template('dashboard.html', 
                             estatisticas=estatisticas,
                             produtos_recentes=produtos_recentes)
    except Exception as e:
        print(f"Erro ao carregar dashboard: {e}")  # Log de erro
        flash('Erro ao carregar dashboard.', 'danger')
        return redirect(url_for('produtos'))

# ==============================================================================
# 7. ROTA DE RELATÓRIOS (MOVIDA PARA CIMA PARA EVITAR ERRO DE IMPORTAÇÃO)
# ==============================================================================
@app.route('/relatorios')
@login_required
def relatorios():
    """Página principal de relatórios"""
    try:
        # Dados básicos
        estoque = db.listar_produtos()
        vendas = db.get_relatorio_vendas_detalhado()
        
        # Calcular estatísticas
        total_produtos = len(estoque)
        produtos_sem_estoque = len([p for p in estoque if p.get('quantidade', 0) <= 0])
        produtos_estoque_baixo = len([p for p in estoque if 0 < p.get('quantidade', 0) <= 5])
        
        # Calcular valor total do estoque
        valor_estoque = sum(p.get('preco', 0) * p.get('quantidade', 0) for p in estoque)
        
        # Calcular estatísticas de vendas
        total_vendas_valor = 0
        vendas_agrupadas = {}
        for venda in vendas:
            venda_id = venda.get('id')
            if venda_id and venda_id not in vendas_agrupadas:
                vendas_agrupadas[venda_id] = venda.get('total', 0)
        
        total_vendas_valor = sum(vendas_agrupadas.values())
        total_transacoes = len(vendas_agrupadas)
        total_itens_vendidos = sum(venda.get('quantidade', 0) for venda in vendas)
        
        # Movimentações (simuladas a partir das vendas)
        movimentacoes = []
        for venda in vendas[:50]:  # Limitar para performance
            if venda.get('produto_nome'):
                movimentacoes.append({
                    'produto_nome': venda.get('produto_nome'),
                    'quantidade': venda.get('quantidade', 0),
                    'data_venda': venda.get('data_venda'),
                    'tipo': 'saida'
                })
        
        estatisticas = {
            'total_produtos': total_produtos,
            'produtos_sem_estoque': produtos_sem_estoque,
            'produtos_estoque_baixo': produtos_estoque_baixo,
            'valor_estoque': valor_estoque,
            'total_vendas_valor': total_vendas_valor,
            'total_transacoes': total_transacoes,
            'total_itens_vendidos': total_itens_vendidos
        }
        
        return render_template('relatorios.html',
                            estoque=estoque,
                            vendas=vendas,
                            movimentacoes=movimentacoes,
                            estatisticas=estatisticas,
                            produtos_sem_estoque=produtos_sem_estoque,
                            hoje=datetime.now().strftime('%Y-%m-%d'))
                            
    except Exception as e:
        print(f"Erro ao carregar relatórios: {e}")
        import traceback
        traceback.print_exc()
        # GARANTE CONTEXTO SEGURO PARA O TEMPLATE
        return render_template('relatorios.html',
                            estoque=[],
                            vendas=[],
                            movimentacoes=[],
                            estatisticas={
                                'total_produtos': 0, 
                                'produtos_estoque_baixo': 0, 
                                'valor_estoque': 0.0,
                                'total_vendas_valor': 0.0,
                                'total_transacoes': 0,
                                'total_itens_vendidos': 0
                            },
                            produtos_sem_estoque=0,
                            hoje=datetime.now().strftime('%Y-%m-%d')) # Deve ser fornecido

@app.route('/relatorios/filtrar', methods=['POST'])
@login_required
def filtrar_relatorios():
    """Filtrar relatórios por data - VERSÃO MAIS ROBUSTA"""
    try:
        data_inicio = request.json.get('data_inicio')
        data_fim = request.json.get('data_fim')
        tipo_relatorio = request.json.get('tipo_relatorio', 'completo')
        
        print(f"DEBUG FILTRO: {data_inicio} até {data_fim}, tipo: {tipo_relatorio}")
        
        # Validar datas
        if data_inicio and data_fim and data_inicio > data_fim:
            return jsonify({
                'success': False,
                'error': 'Data início não pode ser maior que data fim'
            }), 400
        
        # Obter dados do banco
        estoque_filtrado = db.listar_produtos()
        
        # Buscar vendas com filtro de data
        vendas_filtradas = []
        if data_inicio and data_fim:
            try:
                vendas_filtradas = db.get_vendas_por_periodo(data_inicio, data_fim)
            except Exception as e:
                print(f"Erro ao buscar vendas por período: {e}")
                vendas_filtradas = []
        else:
            # Se não há filtro de data, buscar todas as vendas
            try:
                vendas_filtradas = db.get_relatorio_vendas_detalhado()
            except Exception as e:
                print(f"Erro ao buscar todas as vendas: {e}")
                vendas_filtradas = []
        
        # Aplicar filtro por tipo de relatório
        if tipo_relatorio == 'estoque':
            vendas_filtradas = []
        elif tipo_relatorio == 'vendas':
            # Manter apenas vendas (já está assim)
            pass
        elif tipo_relatorio == 'movimentacoes':
            # Para movimentações, podemos manter um subconjunto
            pass
        
        # Recalcular estatísticas com tratamento de erro
        try:
            total_produtos = len(estoque_filtrado)
            produtos_sem_estoque = len([p for p in estoque_filtrado if p.get('quantidade', 0) <= 0])
            produtos_estoque_baixo = len([p for p in estoque_filtrado if 0 < p.get('quantidade', 0) <= 5])
            valor_estoque = sum(p.get('preco', 0) * p.get('quantidade', 0) for p in estoque_filtrado)
            
            # Calcular estatísticas de vendas
            total_vendas_valor = 0
            vendas_agrupadas = {}
            for venda in vendas_filtradas:
                venda_id = venda.get('id')
                if venda_id and venda_id not in vendas_agrupadas:
                    vendas_agrupadas[venda_id] = float(venda.get('total', 0))
            
            total_vendas_valor = sum(vendas_agrupadas.values())
            total_transacoes = len(vendas_agrupadas)
            total_itens_vendidos = sum(venda.get('quantidade', 0) for venda in vendas_filtradas)
            
        except Exception as e:
            print(f"Erro ao calcular estatísticas: {e}")
            total_produtos = 0
            produtos_sem_estoque = 0
            produtos_estoque_baixo = 0
            valor_estoque = 0
            total_vendas_valor = 0
            total_transacoes = 0
            total_itens_vendidos = 0
        
        # Preparar movimentações
        movimentacoes_filtradas = []
        try:
            for venda in vendas_filtradas[:100]:  # Limitar para performance
                if venda.get('produto_nome'):
                    movimentacoes_filtradas.append({
                        'produto_nome': venda.get('produto_nome'),
                        'quantidade': venda.get('quantidade', 0),
                        'data_venda': venda.get('data_venda'),
                        'venda_id': venda.get('id'),
                        'tipo': 'saida'
                    })
        except Exception as e:
            print(f"Erro ao preparar movimentações: {e}")
        
        estatisticas = {
            'total_produtos': total_produtos,
            'produtos_sem_estoque': produtos_sem_estoque,
            'produtos_estoque_baixo': produtos_estoque_baixo,
            'valor_estoque': valor_estoque,
            'total_vendas_valor': total_vendas_valor,
            'total_transacoes': total_transacoes,
            'total_itens_vendidos': total_itens_vendidos
        }
        
        print(f"DEBUG: Retornando {len(estoque_filtrado)} produtos, {len(vendas_filtradas)} vendas")
        
        return jsonify({
            'success': True,
            'estoque': estoque_filtrado,
            'vendas': vendas_filtradas,
            'movimentacoes': movimentacoes_filtradas,
            'estatisticas': estatisticas,
            'produtos_sem_estoque': produtos_sem_estoque
        })
        
    except Exception as e:
        print(f"ERRO CRÍTICO AO FILTRAR RELATÓRIOS: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Erro interno do servidor: {str(e)}'
        }), 500
        
        
# ==============================================================================
# 8. ROTAS DE PRODUTOS E BUSCA
# ==============================================================================
@app.route('/produtos')
def produtos():
    try:
        lista_produtos = db.listar_produtos()
        
        # Calcular estatísticas para o template
        total_produtos = len(lista_produtos)
        produtos_com_estoque = len([p for p in lista_produtos if p.get('quantidade', 0) > 0])
        produtos_estoque_baixo = len([p for p in lista_produtos if 0 < p.get('quantidade', 0) <= 5])
        produtos_sem_estoque = len([p for p in lista_produtos if p.get('quantidade', 0) == 0])
        
        # Calcular valor total do estoque
        valor_total_estoque = sum(p.get('preco', 0) * p.get('quantidade', 0) for p in lista_produtos)
        
        # Contar produtos recentes (últimos 7 dias)
        produtos_recentes_count = len([p for p in lista_produtos 
                                     if p.get('data_criacao') 
                                     and (datetime.now() - p.get('data_criacao')).days <= 7])
        
        return render_template('produtos.html', 
                             produtos=lista_produtos,
                             produtos_com_estoque=produtos_com_estoque,
                             produtos_estoque_baixo=produtos_estoque_baixo,
                             produtos_sem_estoque=produtos_sem_estoque,
                             valor_total_estoque=valor_total_estoque,
                             produtos_recentes_count=produtos_recentes_count)
                             
    except Exception as e:
        print(f"Erro ao carregar produtos: {e}")
        # Retornar valores padrão em caso de erro
        return render_template('produtos.html', 
                             produtos=[],
                             produtos_com_estoque=0,
                             produtos_estoque_baixo=0,
                             produtos_sem_estoque=0,
                             valor_total_estoque=0,
                             produtos_recentes_count=0)

@app.route('/produtos/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            preco = request.form.get('preco', '')
            quantidade = request.form.get('quantidade', '')
            codigo_barras = sanitizar_input(request.form.get('codigo_barras', ''))
            
            preco_valido, preco_float = db.validar_preco(preco)
            qtd_valida, qtd_int = db.validar_quantidade(quantidade)
            
            if not nome or len(nome) < 2:
                flash('Nome do produto deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)
            if not preco_valido:
                flash('Preço inválido ou menor que zero.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)
            if not qtd_valida:
                flash('Quantidade inválida.', 'danger')
                return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

            sucesso, mensagem = db.adicionar_produto(nome, preco_float, qtd_int, codigo_barras)
            
            if sucesso:
                flash('Produto adicionado com sucesso!', 'success')
                return redirect(url_for('produtos'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro ao adicionar produto: {e}")  # Log de erro
            flash('Erro ao adicionar produto. Tente novamente.', 'danger')

    return render_template('produto_formulario.html', titulo="Adicionar Produto", produto=None)

@app.route('/produtos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    produto_existente = db.buscar_produto_por_id(id)
    if not produto_existente:
        flash('Produto não encontrado.', 'danger')
        return redirect(url_for('produtos'))

    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            preco = request.form.get('preco', '')
            quantidade = request.form.get('quantidade', '')
            codigo_barras = sanitizar_input(request.form.get('codigo_barras', ''))
            
            preco_valido, preco_float = db.validar_preco(preco)
            qtd_valida, qtd_int = db.validar_quantidade(quantidade)
            
            if not nome or len(nome) < 2:
                flash('Nome do produto deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)
            if not preco_valido:
                flash('Preço inválido ou menor que zero.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)
            if not qtd_valida:
                flash('Quantidade inválida.', 'danger')
                return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

            sucesso, mensagem = db.atualizar_produto(id, nome, preco_float, qtd_int, codigo_barras)
            
            if sucesso:
                flash('Produto atualizado com sucesso!', 'success')
                return redirect(url_for('produtos'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro ao atualizar produto: {e}")  # Log de erro
            flash('Erro ao atualizar produto. Tente novamente.', 'danger')

    return render_template('produto_formulario.html', titulo="Editar Produto", produto=produto_existente)

@app.route('/produtos/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto(id):
    try:
        sucesso, mensagem = db.excluir_produto(id)
        
        if sucesso:
            flash('Produto excluído com sucesso!', 'success')
        else:
            flash(mensagem, 'danger')
            
    except Exception as e:
        print(f"Erro ao excluir produto: {e}")  # Log de erro
        flash('Erro ao excluir produto.', 'danger')
    
    return redirect(url_for('produtos'))

@app.route('/buscar_produto_estoque', methods=['POST'])
@login_required
def buscar_produto_estoque():
    """Busca de produtos para o estoque (usa busca flexível/código)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados inválidos'})
        
        termo = sanitizar_input(data.get('codigo', ''))
        
        produto_exato = db.buscar_produto_por_codigo(termo)
        
        if produto_exato:
            return jsonify({
                'success': True,
                'produto': produto_exato
            })
        else:
            return jsonify({'success': False, 'message': 'Produto não encontrado'})
            
    except Exception as e:
        print(f"Erro na busca de produto no estoque: {e}")  # Log de erro
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@app.route('/buscar_produto_caixa', methods=['POST'])
@login_required
def buscar_produto_caixa():
    """Busca de produtos para o caixa: retorna lista de matches (código exato ou nome parcial)."""
    try:
        data = request.get_json()
        
        # CORREÇÃO: Garante que 'data' é um dicionário, evitando AttributeError se for None
        if not isinstance(data, dict):
            data = {} 

        # O termo é buscado do campo 'codigo' que o front-end envia
        termo = sanitizar_input(data.get('codigo', ''))

        if not termo:
            return jsonify({'success': False, 'message': 'Código ou nome do produto é obrigatório'})

        # Esta função já faz a busca parcial por nome e código de barras, conforme solicitado.
        produtos_lista = db.buscar_produtos_por_nome(termo) 
        
        if produtos_lista:
            return jsonify({
                'success': True,
                'produtos': produtos_lista
            })
        else:
            # Garante que o front-end recebe uma resposta clara
            return jsonify({'success': False, 'message': 'Produto não encontrado', 'produtos': []})
            
    except Exception as e:
        print(f"Erro na busca ao produto no caixa: {e}")
        # Adiciona o status 500 para ser capturado pelo front-end com um erro
        return jsonify({'success': False, 'message': 'Erro interno do servidor', 'produtos': []}), 500
    
@app.route('/caixa/buscar_auto', methods=['POST'])
@login_required
def buscar_produto_auto():
    """Busca automática de produtos para o caixa"""
    try:
        dados = request.get_json()
        codigo = dados.get('codigo', '').strip()
        
        if not codigo:
            return jsonify({'success': False, 'message': 'Código vazio'})
        
        # Buscar produto por código de barras
        produto = db.buscar_produto_por_codigo(codigo)
        if produto:
            # Verificar se é pesável
            if produto.get('pesavel'):
                return jsonify({
                    'success': True,
                    'pesavel': True,
                    'produto': produto
                })
            else:
                return jsonify({
                    'success': True,
                    'adicionar_carrinho': True,
                    'produto': produto,
                    'quantidade': 1
                })
        
        # Buscar por código personalizado
        produto = db.buscar_produto_por_codigo_personalizado(codigo)
        if produto:
            if produto.get('pesavel'):
                return jsonify({
                    'success': True,
                    'pesavel': True,
                    'produto': produto
                })
            else:
                return jsonify({
                    'success': True,
                    'adicionar_carrinho': True,
                    'produto': produto,
                    'quantidade': 1
                })
        
        # Buscar por nome (parcial)
        produtos = db.buscar_produtos_por_nome(codigo)
        if produtos:
            return jsonify({
                'success': True,
                'produtos': produtos[:10],  # Limitar a 10 resultados
                'message': f'Encontrados {len(produtos)} produtos'
            })
        
        return jsonify({
            'success': False,
            'message': 'Produto não encontrado'
        })
        
    except Exception as e:
        print(f"Erro na busca automática: {e}")
        return jsonify({
            'success': False,
            'message': 'Erro interno na busca'
        })

 
# Rota para listagem e gerenciamento de Produtos Pesáveis
@app.route('/produtos_pesaveis')
@login_required
def produtos_pesaveis():
    produtos = db.listar_produtos_pesaveis()
    return render_template('produtos_pesaveis.html', produtos=produtos)

# Rota para o formulário de adição de Produto Pesável
@app.route('/produtos_pesaveis/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_produto_pesavel():
    if request.method == 'POST':
        try:
            produto_id = request.form.get('produto_id')
            codigo_personalizado = request.form.get('codigo_personalizado')

            # 1. Buscar o produto base para obter o preco (que é o preco_por_kg)
            produto_base = db.buscar_produto_por_id(produto_id)
            if not produto_base:
                flash("Erro: Produto base não encontrado.", 'danger')
                return redirect(url_for('adicionar_produto_pesavel'))
            
            preco_por_kg = produto_base['preco']
            
            # CORREÇÃO CRÍTICA: Passar os três argumentos que a função espera.
            sucesso, mensagem = db.adicionar_produto_pesavel(produto_id, preco_por_kg, codigo_personalizado)
            
            if sucesso:
                flash(mensagem, 'success')
                return redirect(url_for('produtos_pesaveis'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro ao adicionar produto pesável: {e}")
            flash('Erro interno ao processar a associação.', 'danger')
            
        # Garante que a lista de produtos é carregada novamente em caso de erro
        produtos_base = db.listar_produtos_para_associar()
        return render_template('produto_pesavel_formulario.html', produtos_base=produtos_base)
    
    # GET: Listar produtos base para associação
    produtos_base = db.listar_produtos_para_associar()
    return render_template('produto_pesavel_formulario.html', produtos_base=produtos_base)


# Rota para exclusão de Produto Pesável
@app.route('/produtos_pesaveis/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_produto_pesavel(id):
    sucesso, mensagem = db.excluir_produto_pesavel(id)
    if sucesso:
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'danger')
    return redirect(url_for('produtos_pesaveis'))
      

# ==============================================================================
# 9. ROTAS DE CLIENTES
# ==============================================================================
@app.route('/clientes')
@login_required
def clientes():
    try:
        lista_clientes = db.listar_clientes()
        return render_template('clientes.html', clientes=lista_clientes)
    except Exception as e:
        print(f"Erro ao carregar clientes: {e}")  # Log de erro
        flash('Erro ao carregar clientes.', 'danger')
        return render_template('clientes.html', clientes=[])

@app.route('/clientes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            telefone = sanitizar_input(request.form.get('telefone', ''))
            email = sanitizar_input(request.form.get('email', ''))
            cpf_cnpj = sanitizar_input(request.form.get('cpf_cnpj', ''))
            endereco = sanitizar_input(request.form.get('endereco', ''))
            
            if not nome or len(nome) < 2:
                flash('Nome do cliente deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)
                
            if email and not validar_email(email):
                flash('Email inválido.', 'danger')
                return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

            sucesso, mensagem = db.adicionar_cliente(nome, telefone, email, cpf_cnpj, endereco)
            
            if sucesso:
                flash('Cliente adicionado com sucesso!', 'success')
                return redirect(url_for('clientes'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro ao adicionar cliente: {e}")  # Log de erro
            flash('Erro ao adicionar cliente. Tente novamente.', 'danger')

    return render_template('cliente_formulario.html', titulo="Adicionar Cliente", cliente=None)

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente_existente = db.buscar_cliente_por_id(id)
    if not cliente_existente:
        flash('Cliente não encontrado.', 'danger')
        return redirect(url_for('clientes'))

    if request.method == 'POST':
        try:
            nome = sanitizar_input(request.form.get('nome', ''))
            telefone = sanitizar_input(request.form.get('telefone', ''))
            email = sanitizar_input(request.form.get('email', ''))
            cpf_cnpj = sanitizar_input(request.form.get('cpf_cnpj', ''))
            endereco = sanitizar_input(request.form.get('endereco', ''))
            
            if not nome or len(nome) < 2:
                flash('Nome do cliente deve ter pelo menos 2 caracteres.', 'danger')
                return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)
                
            if email and not validar_email(email):
                flash('Email inválido.', 'danger')
                return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

            sucesso, mensagem = db.atualizar_cliente(id, nome, telefone, email, cpf_cnpj, endereco)
            
            if sucesso:
                flash('Cliente atualizado com sucesso!', 'success')
                return redirect(url_for('clientes'))
            else:
                flash(mensagem, 'danger')
        except Exception as e:
            print(f"Erro ao atualizar cliente: {e}")  # Log de erro
            flash('Erro ao atualizar cliente. Tente novamente.', 'danger')

    return render_template('cliente_formulario.html', titulo="Editar Cliente", cliente=cliente_existente)

@app.route('/clientes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    try:
        sucesso, mensagem = db.excluir_cliente(id)
        
        if sucesso:
            flash('Cliente excluído com sucesso!', 'success')
        else:
            flash(mensagem, 'danger')
            
    except Exception as e:
        print(f"Erro ao excluir cliente: {e}")  # Log de erro
        flash('Erro ao excluir cliente.', 'danger')
    
    return redirect(url_for('clientes'))

# ==============================================================================
# 10. ROTAS DE VENDAS E CAIXA
# ==============================================================================
@app.route('/vendas')
@login_required
def vendas():
    """Histórico de vendas (com clientes para filtros)"""
    try:
        # A lista completa e original
        vendas_historico = db.get_relatorio_vendas_detalhado()
        clientes = db.listar_clientes()
        
        print(f"DEBUG: {len(vendas_historico)} vendas recuperadas do DB.")  # Log de debug
        
        # PASSO CRÍTICO DE CÓPIA: Crie uma cópia profunda antes de filtrar/iterar
        historico_copia = copy.deepcopy(vendas_historico)

        # Filtra a cópia, removendo qualquer coisa que não seja um dict válido
        vendas_historico_filtrado = [
            item for item in historico_copia 
            if isinstance(item, dict) and item.get('id') is not None
        ]
        
        total_vendas_valor = 0.0
        vendas_agrupadas_para_calculo = {}

        # Usa a lista FILTRADA
        for venda_item in vendas_historico_filtrado:
            venda_id = venda_item.get('id')
            if venda_id not in vendas_agrupadas_para_calculo:
                # O problema estava aqui, mas agora a lista é segura
                vendas_agrupadas_para_calculo[venda_id] = venda_item.get('total', 0.0)

        total_vendas_valor = sum(vendas_agrupadas_para_calculo.values())

        # Retorna a lista ORIGINAL para o template (pois ele precisa dos registros)
        return render_template('vendas.html', 
                             vendas=vendas_historico, # A lista original/filtrada para exibição
                             clientes=clientes,
                             total_vendas_valor=total_vendas_valor)
                             
    except Exception as e:
        print(f"ERRO AO CARREGAR HISTÓRICO DE VENDAS: {e}")
        import traceback
        traceback.print_exc()  # Traceback completo para debug
        try:
             clientes = db.listar_clientes()
        except:
             clientes = []
             
        # Retorna com valores seguros
        return render_template('vendas.html', vendas=[], clientes=clientes, total_vendas_valor=0.0) # GARANTE CONTEXTO SEGURO
@app.route('/caixa')
@login_required
def caixa():
    """PDV - Ponto de Venda CORRIGIDO"""
    try:
        produtos_disponiveis = db.listar_produtos()
        clientes_cadastrados = db.listar_clientes()
        
        # Filtrar apenas produtos com estoque positivo
        produtos_com_estoque = [p for p in produtos_disponiveis if p.get('quantidade', 0) > 0]
        
        print(f"DEBUG CAIXA: {len(produtos_com_estoque)} produtos com estoque carregados")
        
        return render_template('caixa.html', 
                             produtos=produtos_com_estoque, 
                             clientes=clientes_cadastrados)
    except Exception as e:
        print(f"Erro ao carregar caixa: {e}")
        flash('Erro ao carregar caixa.', 'danger')
        return render_template('caixa.html', produtos=[], clientes=[])

@app.route('/caixa/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    """Finalizar venda via AJAX - VERSÃO CORRIGIDA"""
    try:
        # Verifica se é JSON
        if request.is_json:
            dados = request.get_json()
        else:
            # Fallback para form data
            dados = request.form.to_dict()
            # Converte itens do carrinho se necessário
            if 'itens' in dados:
                import json
                dados['itens'] = json.loads(dados['itens'])
        
        print(f"DEBUG: Dados recebidos para venda: {dados}")
        
        if not dados or 'itens' not in dados or not dados['itens']:
            return jsonify({'success': False, 'message': 'Carrinho vazio'}), 400
        
        itens_carrinho = dados.get('itens', [])
        total_venda = float(dados.get('total', 0))
        
        forma_pagamento = dados.get('forma_pagamento', 'dinheiro')
        valor_pago = float(dados.get('valor_pago', total_venda))
        troco = float(dados.get('troco', 0))

        # Converte cliente_id para None se estiver vazio
        cliente_id = dados.get('cliente_id')
        if cliente_id == '' or cliente_id == 'null' or not cliente_id:
            cliente_id = None
        elif cliente_id:
            cliente_id = int(cliente_id)
        
        print(f"DEBUG: Registrando venda - Itens: {len(itens_carrinho)}, Total: {total_venda}")
        
        venda_id, mensagem = db.registrar_venda_completa(
            cliente_id=cliente_id,
            itens_carrinho=itens_carrinho,
            total=total_venda,
            forma_pagamento=forma_pagamento,
            valor_pago=valor_pago,
            troco=troco
        )
        
        if venda_id:
            return jsonify({
                'success': True,
                'message': 'Venda finalizada com sucesso!',
                'venda_id': venda_id
            })
        else:
            return jsonify({'success': False, 'message': mensagem}), 400
            
    except Exception as e:
        print(f"Erro ao finalizar venda: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

            
@app.route('/debug/vendas-detalhado')
@login_required
def debug_vendas_detalhado():
    """Debug detalhado das vendas"""
    try:
        vendas = db.get_relatorio_vendas_detalhado()
        
        # Analisar estrutura dos dados
        analise = {
            'total_registros': len(vendas),
            'primeiros_3_registros': vendas[:3] if vendas else [],
            'tipos_de_dados': [type(v) for v in vendas[:5]],
            'campos_do_primeiro': list(vendas[0].keys()) if vendas else []
        }
        
        return jsonify(analise)
        
    except Exception as e:
        print(f"Erro no debug de vendas: {e}")  # Log de erro
        return jsonify({'error': str(e)}), 500    

@app.route('/vendas/excluir/<int:venda_id>', methods=['POST'])
@login_required
def excluir_venda(venda_id):
    """Excluir venda e restaurar o estoque dos produtos vendidos"""
    try:
        sucesso, mensagem = db.excluir_venda(venda_id)
        
        if sucesso:
            flash(mensagem, 'success')
        else:
            flash(f"Falha ao excluir venda: {mensagem}", 'danger')
        
        return redirect(url_for('vendas'))
    except Exception as e:
        print(f"Erro ao excluir venda: {e}")  # Log de erro
        flash(f'Erro interno ao excluir venda: {e}', 'danger')
        return redirect(url_for('vendas'))

@app.route('/api/detalhes_venda/<int:venda_id>')
@login_required
def api_detalhes_venda(venda_id):
    """API para buscar detalhes completos de uma venda (usada no modal em vendas.html)"""
    try:
        detalhes = db.get_venda_detalhada_por_id(venda_id)
        if detalhes:
            return jsonify(detalhes)
        else:
            return jsonify({'erro': 'Venda não encontrada'}), 404
    except Exception as e:
        print(f"Erro na API de detalhes de venda: {e}")  # Log de erro
        return jsonify({'erro': 'Erro interno do servidor'}), 500
    
@app.route('/vendas_filtradas', methods=['POST'])
@login_required
def vendas_filtradas():
    """Filtrar vendas por data e cliente"""
    try:
        data_inicio = request.json.get('data_inicio')
        data_fim = request.json.get('data_fim')
        cliente_id = request.json.get('cliente_id')

        # Obter todas as vendas primeiro
        todas_vendas = db.get_relatorio_vendas_detalhado()
        
        # Aplicar filtros
        vendas_filtradas = []
        for venda in todas_vendas:
            # Filtro por data
            data_venda = venda.get('data_venda', '')
            if data_inicio and data_venda:
                if data_venda.split(' ')[0] < data_inicio:
                    continue
            if data_fim and data_venda:
                if data_venda.split(' ')[0] > data_fim:
                    continue
            
            # Filtro por cliente
            if cliente_id and str(cliente_id) != '':
                venda_cliente_id = venda.get('cliente_id')
                if venda_cliente_id and str(venda_cliente_id) != str(cliente_id):
                    continue
            
            vendas_filtradas.append(venda)

        # Calcular total
        vendas_agrupadas = {}
        for venda in vendas_filtradas:
            venda_id = venda.get('id')
            if venda_id not in vendas_agrupadas:
                vendas_agrupadas[venda_id] = venda.get('total', 0.0)
        
        total_vendas_valor = sum(vendas_agrupadas.values())

        return jsonify({
            'success': True,
            'vendas': vendas_filtradas,
            'total_vendas_valor': total_vendas_valor,
            'total_registros': len(vendas_filtradas)
        })
    except Exception as e:
        print(f"Erro ao filtrar vendas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'vendas': [],
            'total_vendas_valor': 0,
            'total_registros': 0
        }), 500
 

@app.route('/recibo/<int:venda_id>')
@login_required
def recibo(venda_id):
    """Gera um PDF de recibo simples para a venda"""
    venda = db.get_venda_detalhada_por_id(venda_id)
    if not venda:
        flash("Venda não encontrada para gerar recibo.", 'danger')
        return redirect(url_for('vendas'))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph("RECIBO DE VENDA", styles['Title']))
    elements.append(Paragraph(f"Venda #**{venda_id}** | Data: **{venda['data_venda']}**", styles['Normal']))
    elements.append(Paragraph(f"Cliente: **{venda['cliente_nome'] or 'Cliente Avulso'}**", styles['Normal']))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Itens Vendidos:", styles['Heading2']))
    data = [['Produto', 'Qtd', 'Preço Unit.', 'Subtotal']]
    total_recalculado = 0
    for item in venda['itens']:
        subtotal = item['quantidade'] * item['preco_unitario']
        data.append([
            item['produto_nome'],
            str(item['quantidade']),
            f"R$ {item['preco_unitario']:.2f}",
            f"R$ {subtotal:.2f}"
        ])
        total_recalculado += subtotal
    
    data.append([Paragraph('**TOTAL DA VENDA**', styles['Heading4']), '', '', Paragraph(f'**R$ {total_recalculado:.2f}**', styles['Heading4'])])

    table = Table(data, colWidths=[200, 50, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("Resumo do Pagamento:", styles['Heading3']))
    elements.append(Paragraph(f"Forma de Pagamento: **{venda['forma_pagamento']}**", styles['Normal']))
    if venda.get('forma_pagamento') == 'Dinheiro':
        elements.append(Paragraph(f"Valor Recebido: **R$ {venda['valor_pago']:.2f}**", styles['Normal']))
        elements.append(Paragraph(f"Troco: **R$ {venda['troco']:.2f}**", styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'recibo_venda_{venda_id}.pdf'
    )

# ==============================================================================
# 11. ROTAS DE EXPORTAÇÃO
# ==============================================================================
@app.route('/exportar_excel')
@login_required
def exportar_excel():
    """Exportar relatórios para Excel - Produtos e Vendas"""
    try:
        produtos = db.listar_produtos()
        vendas = db.get_relatorio_vendas_detalhado()
        
        df_produtos = pd.DataFrame(produtos)
        df_vendas = pd.DataFrame(vendas)
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_produtos.to_excel(writer, sheet_name='Produtos', index=False)
            df_vendas.to_excel(writer, sheet_name='Vendas', index=False)
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'relatorio_loja_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        print(f"Erro ao exportar Excel: {e}")  # Log de erro
        flash(f'Erro ao exportar Excel: {str(e)}', 'error')
        return redirect('/relatorios')

@app.route('/exportar_pdf')
@login_required
def exportar_pdf():
    """Exportar relatórios para PDF - Produtos e Vendas"""
    try:
        produtos = db.listar_produtos()
        vendas = db.get_relatorio_vendas_detalhado()
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph("Relatório da Loja - Mercadinho Kayrós", styles['Title']))
        elements.append(Paragraph(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        if produtos:
            elements.append(Paragraph("Produtos em Estoque", styles['Heading2']))
            data = [['ID', 'Nome', 'Preço', 'Quantidade', 'Código']]
            for produto in produtos:
                data.append([
                    str(produto['id']),
                    produto['nome'],
                    f"R$ {produto['preco']:.2f}",
                    str(produto['quantidade']),
                    produto.get('codigo_barras', 'N/A')
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
        
        if vendas:
            elements.append(Paragraph("Histórico de Vendas", styles['Heading2']))
            vendas_agrupadas_total = {}
            for v in vendas:
                if v['id'] not in vendas_agrupadas_total:
                    vendas_agrupadas_total[v['id']] = {
                        'data': v['data_venda'],
                        'cliente': v['cliente_nome'] or 'Avulso',
                        'total': v['total'],
                        'pagamento': v['forma_pagamento']
                    }
            
            data = [['ID', 'Data', 'Cliente', 'Pagamento', 'Total']]
            for id, v in vendas_agrupadas_total.items():
                data.append([
                    str(id),
                    v['data'],
                    v['cliente'],
                    v['pagamento'],
                    f"R$ {v['total']:.2f}"
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'relatorio_loja_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"Erro ao exportar PDF: {e}")  # Log de erro
        flash(f'Erro ao exportar PDF: {str(e)}', 'error')
        return redirect('/relatorios')

# ==============================================================================
# 12. BLOCO DE EXECUÇÃO
# ==============================================================================
if __name__ == '__main__':
    @app.context_processor
    def inject_template_vars():
        return {
            'current_year': datetime.utcnow().year,
            'current_user': current_user
        }
        
    if db.setup_database():
        print("✅ Banco de dados configurado com sucesso!")
    else:
        print("❌ Erro ao configurar banco de dados!")
    
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    
    app.run(host=host, port=port, debug=debug_mode)