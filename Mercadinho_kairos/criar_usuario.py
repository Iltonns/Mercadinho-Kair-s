#!/usr/bin/env python3
"""
Script para criar o primeiro usuário administrativo no sistema.
Execute este script uma vez para criar o usuário inicial.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from logica_banco import add_user, setup_database

def criar_primeiro_usuario():
    """Cria o primeiro usuário administrativo."""
    print("=" * 50)
    print("CRIAÇÃO DO PRIMEIRO USUÁRIO")
    print("=" * 50)
    
    # Garante que o banco de dados está configurado
    if not setup_database():
        print("❌ Erro ao configurar o banco de dados!")
        return False
    
    print("\nPor favor, insira os dados para o primeiro usuário:")
    
    while True:
        username = input("Nome de usuário (mínimo 3 caracteres): ").strip()
        if len(username) >= 3:
            break
        print("❌ Nome de usuário deve ter pelo menos 3 caracteres. Tente novamente.")
    
    while True:
        password = input("Senha (mínimo 6 caracteres): ").strip()
        if len(password) >= 6:
            break
        print("❌ Senha deve ter pelo menos 6 caracteres. Tente novamente.")
    
    # Confirmação da senha
    confirm_password = input("Confirme a senha: ").strip()
    if password != confirm_password:
        print("❌ As senhas não coincidem!")
        return False
    
    print(f"\nCriando usuário '{username}'...")
    
    sucesso, mensagem = add_user(username, password)
    
    if sucesso:
        print("✅ " + mensagem)
        print("\n" + "=" * 50)
        print("USUÁRIO CRIADO COM SUCESSO!")
        print("=" * 50)
        print(f"Usuário: {username}")
        print("Agora você pode:")
        print("1. Executar a aplicação Flask")
        print("2. Fazer login com este usuário")
        print("3. Apagar este script (criar_usuario.py) se desejar")
        return True
    else:
        print("❌ " + mensagem)
        return False

if __name__ == '__main__':
    try:
        criar_primeiro_usuario()
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")