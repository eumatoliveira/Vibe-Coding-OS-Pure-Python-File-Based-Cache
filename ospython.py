#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
=================================================
 PTPY Mini OS - v1.5 (Versão Corrigida)
=================================================

Este é um projeto abrangente que simula um ambiente de desktop
completo usando apenas a biblioteca padrão do Python (Tkinter).

Funcionalidades Principais:
- Tela de Login obrigatória.
- Ambiente de Desktop com Ícones.
- Barra de Tarefas para gerenciamento de janelas.
- Sistema de Arquivos "Sandbox" (tudo dentro de ./minios_root).
- Lixeira com funcionalidade de restauração.
- Engine de Módulos (CRUD, Login) e Variáveis Globais.
- Sistema de Notificação.
- Persistência de Estado (salva o estado da engine em JSON).
- Ciclo de Reiniciar e Desligar.

Aplicativos Pré-instalados:
- PTPY Code (Simulador de VS Code com abas e explorador).
- Terminal (REPL Python com acesso à engine + Comandos de Automação).
- Explorador de Arquivos (visualizador/gerenciador de arquivos).
- Lixeira (visualiza e restaura arquivos deletados).
- Painel de Controle (visualiza módulos e variáveis).
- Navegador Web (Simulado - abre o browser real).

Autor: [Seu Nome/Gemini]
Versão: 1.5 (Correção de bugs críticos de indentação e lógica)
"""

# ----------------------------------------
# Importações
# (Limpas e organizadas)
# ----------------------------------------
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox, scrolledtext
import os
import shutil
import json
import datetime
import uuid
import sys
import io
import webbrowser
import re # Usado no PTPY Code para syntax highlighting

# ----------------------------------------
# CAMADA 1: A ENGINE DO "SISTEMA OPERACIONAL"
# (Sem código Tkinter aqui. Apenas lógica pura.)
# ----------------------------------------
class MiniOS_Engine:
    """
    Representa o "Kernel" do MiniOS.
    Gerencia o estado, arquivos, módulos e persistência.
    Tudo é "sandboxed" dentro do diretório root_path.
    """
    def __init__(self, root_path="./minios_root"):
        """
        Inicializa a engine, define os caminhos e carrega o estado.
        """
        self.root_path = os.path.abspath(root_path)
        self.trash_path = os.path.join(self.root_path, ".trash")
        self.state_file = os.path.join(self.root_path, ".state.json")
        
        self.modules = {}
        self.variables = {}
        self.users = []
        self.trash_index = {} # {uuid: {original_path, deleted_at}}
        
        self._setup_environment()
        self._load_state()
        self._register_default_modules()

    def _setup_environment(self):
        """
        Cria os diretórios necessários (root, trash) se não existirem.
        """
        os.makedirs(self.root_path, exist_ok=True)
        os.makedirs(self.trash_path, exist_ok=True)

    def _register_default_modules(self):
        """
        Registra módulos padrão como 'login' e um CRUD de exemplo.
        """
        if "login" not in self.modules:
            self.create_login_module()
        if "tasks" not in self.modules:
            self.create_crud_module("tasks", ["description", "status"])
            
        # Adiciona um usuário admin padrão se não houver usuários
        if not self.users:
            self.modules["login"]["register"]("admin@ptpy.os", "admin")
            print("Nenhum usuário encontrado. Criado usuário padrão: admin@ptpy.os / admin")

    def _load_state(self):
        """
        Carrega o estado salvo (variáveis, dados de CRUD, lixeira) do
        arquivo JSON.
        """
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                self.variables = state.get("variables", {})
                self.trash_index = state.get("trash_index", {})
                self.users = state.get("users", [])
                
                # Carrega dados dos CRUDs
                crud_data = state.get("crud_data", {})
                for module_name, data in crud_data.items():
                    # Recria o CRUD antes de carregar os dados
                    if module_name not in self.modules and module_name == "tasks":
                         self.create_crud_module("tasks", ["description", "status"])
                    
                    if module_name in self.modules and "_data_list" in self.modules[module_name]:
                        self.modules[module_name]["_data_list"] = data
                        
        except (FileNotFoundError, json.JSONDecodeError):
            print("Nenhum estado salvo encontrado ou arquivo corrompido. Começando novo estado.")
            self.variables = {"version": "1.5", "system_name": "PTPY Mini OS"}
            self.trash_index = {}
            self.users = []

    def save_state(self):
        """
        Salva o estado atual (variáveis, dados de CRUD, lixeira) em
        um arquivo JSON.
        """
        crud_data = {}
        for name, module in self.modules.items():
            if "_data_list" in module:
                crud_data[name] = module["_data_list"]
                
        state = {
            "variables": self.variables,
            "trash_index": self.trash_index,
            "users": self.users,
            "crud_data": crud_data
        }
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=4)

    def _get_full_path(self, relative_path):
        """
        Converte um caminho relativo (do app) para um caminho absoluto
        no sistema de arquivos real, garantindo que esteja dentro do
        root_path.
        """
        if relative_path == ".":
            return self.root_path
            
        # Limpa o caminho (remove ".." etc.)
        full_path = os.path.abspath(os.path.join(self.root_path, relative_path))
        
        # Verificação de segurança: impede sair do diretório root
        if not full_path.startswith(self.root_path):
            raise PermissionError("Acesso negado: Tentativa de sair do diretório raiz.")
            
        return full_path

    # --- API de Módulos ---
    def create_login_module(self):
        """
        Cria o módulo de login com funções de registro e login.
        """
        def register(email, password):
            for u in self.users:
                if u['email'] == email:
                    return False, "Email já registrado."
            self.users.append({"email": email, "password": password})
            self.save_state()
            return True, "Usuário registrado."
            
        def login(email, password):
            for u in self.users:
                if u['email'] == email and u['password'] == password:
                    return True, "Login bem-sucedido."
            return False, "Email ou senha inválidos."
            
        self.modules["login"] = {
            "register": register,
            "login": login
        }

    def create_crud_module(self, name, fields):
        """
        Factory para criar um módulo CRUD genérico (Create, Read, Update, Delete).
        """
        if name in self.modules:
            raise ValueError(f"Módulo CRUD '{name}' já existe.")
            
        _data_list = [] # Armazenamento de dados em memória
        
        def add(**kwargs):
            item = {f: kwargs.get(f) for f in fields}
            item["_id"] = str(uuid.uuid4())
            _data_list.append(item)
            self.save_state()
            return item["_id"]

        def edit(_id, **kwargs):
            for item in _data_list:
                if item["_id"] == _id:
                    for k, v in kwargs.items():
                        if k in fields:
                            item[k] = v
                    self.save_state()
                    return True
            return False

        def delete(_id):
            for i, item in enumerate(_data_list):
                if item["_id"] == _id:
                    _data_list.pop(i)
                    self.save_state()
                    return True
            return False

        def list_all():
            return _data_list
            
        def find_by(field, value):
            return [item for item in _data_list if item.get(field) == value]

        self.modules[name] = {
            "add": add,
            "edit": edit,
            "delete": delete,
            "list_all": list_all,
            "find_by": find_by,
            "_data_list": _data_list, # Referência para persistência
            "_fields": fields
        }

    # --- API de Sistema de Arquivos ---
    def list_dir(self, relative_path="."):
        """
        Lista o conteúdo de um diretório.
        Retorna (pastas, arquivos).
        """
        full_path = self._get_full_path(relative_path)
        items = os.listdir(full_path)
        folders = [i for i in items if os.path.isdir(os.path.join(full_path, i)) and i != ".trash"]
        files = [i for i in items if os.path.isfile(os.path.join(full_path, i))]
        return sorted(folders), sorted(files)

    def create_file(self, relative_path, content=""):
        """
        Cria um novo arquivo com conteúdo.
        """
        full_path = self._get_full_path(relative_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_file(self, relative_path):
        """
        Lê o conteúdo de um arquivo.
        """
        full_path = self._get_full_path(relative_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def create_folder(self, relative_path):
        """
        Cria um novo diretório.
        """
        full_path = self._get_full_path(relative_path)
        os.makedirs(full_path, exist_ok=True)

    def rename_item(self, relative_path, new_name):
        """
        Renomeia um arquivo ou pasta.
        """
        full_path = self._get_full_path(relative_path)
        new_full_path = self._get_full_path(os.path.join(os.path.dirname(relative_path), new_name))
        shutil.move(full_path, new_full_path)

    def move_item(self, relative_path, new_relative_folder):
        """
        Move um arquivo ou pasta para um novo diretório.
        """
        full_path = self._get_full_path(relative_path)
        new_full_path = self._get_full_path(os.path.join(new_relative_folder, os.path.basename(relative_path)))
        shutil.move(full_path, new_full_path)

    def delete_item(self, relative_path):
        """
        Move um item (arquivo/pasta) para a lixeira.
        """
        full_path = self._get_full_path(relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Arquivo '{relative_path}' não encontrado.")
            
        file_id = str(uuid.uuid4())
        
        # Move o arquivo para a lixeira com o nome do UUID
        shutil.move(full_path, os.path.join(self.trash_path, file_id))
        
        # Registra no índice da lixeira
        self.trash_index[file_id] = {
            "original_path": relative_path,
            "deleted_at": datetime.datetime.now().isoformat()
        }
        self.save_state()

    def get_trash_items(self):
        """
        Retorna os itens da lixeira.
        """
        return self.trash_index.items()

    def restore_item(self, file_id):
        """
        Restaura um item da lixeira para seu local original.
        """
        if file_id not in self.trash_index:
            raise FileNotFoundError("Item não encontrado na lixeira.")
            
        info = self.trash_index.pop(file_id)
        original_path = info["original_path"]
        
        # Caminhos de origem e destino
        trash_file_path = os.path.join(self.trash_path, file_id)
        restore_full_path = self._get_full_path(original_path)
        
        # Cria diretórios se necessário
        os.makedirs(os.path.dirname(restore_full_path), exist_ok=True)
        
        # Move o arquivo de volta
        shutil.move(trash_file_path, restore_full_path)
        self.save_state()

    def empty_trash(self):
        """
        Exclui permanentemente todos os itens da lixeira.
        """
        for file_id in list(self.trash_index.keys()):
            trash_file_path = os.path.join(self.trash_path, file_id)
            try:
                if os.path.isfile(trash_file_path):
                    os.remove(trash_file_path)
                elif os.path.isdir(trash_file_path):
                    shutil.rmtree(trash_file_path)
            except OSError as e:
                print(f"Erro ao deletar {file_id} da lixeira: {e}")
                
        self.trash_index.clear()
        self.save_state()


# ----------------------------------------
# CAMADA 2: COMPONENTES DA GUI
# (Classes base para Janelas, Ícones, etc.)
# ----------------------------------------

class NotificationManager:
    """
    Gerencia a exibição de notificações pop-up no canto da tela.
    """
    def __init__(self, master):
        self.master = master
        self.notifications = []

    def show(self, title, message, duration=3000):
        """
        Exibe uma notificação.
        """
        win = tk.Toplevel(self.master)
        win.overrideredirect(True) # Sem bordas
        win.attributes("-alpha", 0.9) # Transparência
        
        # Estilo
        win.config(bg="gray10", relief="solid", borderwidth=1)
        
        title_label = tk.Label(win, text=title, bg="gray10", fg="white", font=("Arial", 10, "bold"))
        title_label.pack(fill="x", padx=10, pady=(5, 0))
        
        msg_label = tk.Label(win, text=message, bg="gray10", fg="white", font=("Arial", 9))
        msg_label.pack(fill="x", padx=10, pady=(0, 10))
        
        win.update_idletasks()
        
        # Posicionamento no canto inferior direito
        screen_w = self.master.winfo_screenwidth()
        screen_h = self.master.winfo_screenheight()
        win_w = win.winfo_width()
        win_h = win.winfo_height()
        
        # Se a master (desktop) estiver escondida (na tela de login),
        # use a tela toda como referência.
        try:
            taskbar_height = self.master.taskbar.winfo_height()
        except:
            taskbar_height = 60 # Fallback
            
        x = screen_w - win_w - 20
        y = screen_h - win_h - taskbar_height
        
        # Empilha notificações
        for notif in self.notifications:
            y -= (notif.winfo_height() + 5)
            
        win.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        self.notifications.append(win)
        
        # Agenda o fechamento
        win.after(duration, lambda w=win: self.close_notification(w))

    def close_notification(self, win):
        """
        Fecha uma notificação e remove da lista.
        """
        if win in self.notifications:
            self.notifications.remove(win)
        if win.winfo_exists():
            win.destroy()


class OSWindow(tk.Toplevel):
    """
    Classe base para todas as janelas de "Aplicativos" no MiniOS.
    Gerencia o registro automático na barra de tarefas.
    """
    def __init__(self, desktop, title="Janela PTPY", geometry="500x300"):
        """
        Inicializa a janela e a registra no desktop.
        """
        super().__init__(desktop)
        self.desktop = desktop
        self.os_engine = desktop.os_engine
        
        self.title(title)
        self.geometry(geometry)
        
        # ID único para a barra de tarefas
        self.app_id = f"app_{uuid.uuid4()}"
        
        # Registra a janela
        self.desktop.taskbar.register_window(self)
        
        # Bind de eventos
        self.bind("<Destroy>", self._on_destroy)
        self.bind("<Map>", self._on_map) # Evento "mostrar/restaurar"
        self.bind("<Unmap>", self._on_unmap) # Evento "minimizar"
        
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        
        self.state = "normal"
        self.focus_set() # Traz a janela para frente

    def close_window(self):
        """
        Método customizado de fechamento que avisa a barra de tarefas
        antes de destruir a janela.
        """
        self.desktop.taskbar.unregister_window(self)
        self.destroy()

    def _on_destroy(self, event):
        """
        Handler para quando a janela é destruída.
        Garante que foi removida da barra de tarefas.
        """
        if event.widget == self:
            self.desktop.taskbar.unregister_window(self)

    def _on_map(self, event):
        """
        Handler para quando a janela é restaurada/mostrada.
        """
        self.state = "normal"
        self.desktop.taskbar.update_window_state(self)

    def _on_unmap(self, event):
        """
        Handler para quando a janela é minimizada.
        """
        self.state = "minimized"
        self.desktop.taskbar.update_window_state(self)


class Taskbar(tk.Frame):
    """
    A Barra de Tarefas na parte inferior da tela.
    Mostra o menu "Iniciar" e os botões das janelas abertas.
    """
    def __init__(self, desktop):
        """
        Inicializa a barra de tarefas.
        """
        super().__init__(desktop, bg="gray20", height=40)
        self.desktop = desktop
        self.window_buttons = {} # {app_id: button}
        
        # Botão "Iniciar"
        self.start_button = tk.Button(self, text="PTPY", bg="darkblue", fg="white", 
                                      relief="raised", command=self.show_start_menu)
        self.start_button.pack(side="left", padx=5, pady=5)
        
        # Frame para os botões das janelas
        self.buttons_frame = tk.Frame(self, bg="gray20")
        self.buttons_frame.pack(side="left", fill="x", expand=True)
        
        # Relógio (Simples)
        self.clock_label = tk.Label(self, text="", bg="gray20", fg="white", font=("Arial", 9))
        self.clock_label.pack(side="right", padx=10)
        
        self.update_clock()
        self.start_menu = None

    def update_clock(self):
        """
        Atualiza o relógio a cada segundo.
        """
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)

    def register_window(self, window: OSWindow):
        """
        Adiciona um botão para uma nova janela na barra de tarefas.
        """
        if window.app_id in self.window_buttons:
            return
            
        btn = tk.Button(self.buttons_frame, text=window.title(), 
                        bg="gray40", fg="white", relief="raised",
                        command=lambda w=window: self.toggle_window(w))
        btn.pack(side="left", padx=2, pady=5)
        
        self.window_buttons[window.app_id] = btn

    def unregister_window(self, window: OSWindow):
        """
        Remove o botão de uma janela da barra de tarefas.
        """
        btn = self.window_buttons.pop(window.app_id, None)
        if btn:
            btn.destroy()

    def update_window_state(self, window: OSWindow):
        """
        Atualiza a aparência do botão (pressionado/normal)
        baseado no estado da janela.
        """
        btn = self.window_buttons.get(window.app_id)
        if not btn:
            return
            
        if window.state == "minimized":
            btn.config(relief="sunken", bg="gray30")
        else:
            btn.config(relief="raised", bg="gray40")
            window.focus_set() # Traz para frente

    def toggle_window(self, window: OSWindow):
        """
        Minimiza a janela se estiver ativa, restaura se estiver minimizada.
        """
        if window.state == "minimized":
            window.deiconify() # Restaura
        else:
            if window.focus_get() == window:
                window.iconify() # Minimiza
            else:
                window.focus_set() # Apenas foca

    def show_start_menu(self):
        """
        Exibe o menu "Iniciar" com os aplicativos registrados.
        """
        if self.start_menu and self.start_menu.winfo_exists():
            self.start_menu.destroy()
            self.start_menu = None
            return

        self.start_menu = tk.Toplevel(self.desktop)
        self.start_menu.overrideredirect(True)
        self.start_menu.config(bg="gray30", relief="raised", borderwidth=1)
        
        # Lista de apps
        for app_name in self.desktop.app_registry:
            btn = tk.Button(self.start_menu, text=app_name, 
                            bg="gray40", fg="white", relief="flat", anchor="w",
                            command=lambda name=app_name: self.launch_app_from_menu(name))
            btn.pack(fill="x", padx=5, pady=2)
            
        # --- BOTÕES DE REINICIAR E DESLIGAR ---
        tk.Frame(self.start_menu, height=1, bg="gray50").pack(fill="x", padx=5, pady=5)
        
        # Botão Reiniciar
        restart_btn = tk.Button(self.start_menu, text="Reiniciar", 
                                 bg="orange", fg="black", relief="flat", anchor="w",
                                 command=self.desktop.on_restart)
        restart_btn.pack(fill="x", padx=5, pady=2)
        
        # Botão de desligar
        shutdown_btn = tk.Button(self.start_menu, text="Desligar (Salvar)", 
                                 bg="red", fg="white", relief="flat", anchor="w",
                                 command=self.desktop.on_shutdown)
        shutdown_btn.pack(fill="x", padx=5, pady=2)
        
        # Posicionamento
        self.start_menu.update_idletasks()
        w = self.start_menu.winfo_width()
        h = self.start_menu.winfo_height()
        y = self.desktop.winfo_height() - h - self.winfo_height()
        self.start_menu.geometry(f"{w}x{h}+5+{y}")
        self.start_menu.focus_set()
        
        # Fecha se clicar fora
        self.start_menu.bind("<FocusOut>", lambda e: self.start_menu.destroy() if self.start_menu.winfo_exists() else None)

    def launch_app_from_menu(self, app_name):
        """
        Lança um app e fecha o menu.
        """
        if self.start_menu:
            self.start_menu.destroy()
            self.start_menu = None
        self.desktop.launch_app(app_name)


class DesktopIcon(tk.Frame):
    """
    Um ícone clicável na área de trabalho.
    """
    def __init__(self, master, text, icon_char="🗎", **kwargs):
        """
        Inicializa o ícone.
        """
        super().__init__(master, bg=master.cget('bg'), **kwargs)
        
        self.app_name = text
        self.callback = None
        
        # Ícone (usando um caractere emoji/unicode simples)
        self.icon_label = tk.Label(self, text=icon_char, bg=self.cget('bg'), 
                                   fg="white", font=("Arial", 24))
        self.icon_label.pack()
        
        # Texto
        self.text_label = tk.Label(self, text=text, bg=self.cget('bg'), 
                                   fg="white", font=("Arial", 9))
        self.text_label.pack()
        
        # Eventos de clique
        self.bind("<Double-Button-1>", self._on_double_click)
        self.icon_label.bind("<Double-Button-1>", self._on_double_click)
        self.text_label.bind("<Double-Button-1>", self._on_double_click)
        
        # Eventos de clique simples (para seleção)
        self.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.text_label.bind("<Button-1>", self._on_click)

    def on_double_click(self, callback):
        """
        Define a função a ser chamada no clique duplo.
        """
        self.callback = callback

    def _on_double_click(self, event):
        """
        Handler interno de clique duplo.
        """
        if self.callback:
            self.callback()

    def _on_click(self, event):
        """
        Handler de clique simples (seleção).
        """
        # Des-seleciona todos os outros
        for widget in self.master.winfo_children():
            if isinstance(widget, DesktopIcon):
                widget.config(bg=self.master.cget('bg'))
                widget.icon_label.config(bg=self.master.cget('bg'))
                widget.text_label.config(bg=self.master.cget('bg'))
                
        # Seleciona este
        self.config(bg="blue")
        self.icon_label.config(bg="blue")
        self.text_label.config(bg="blue")


# ----------------------------------------
# CAMADA 3: OS APLICATIVOS
# (Herdeiros de OSWindow)
# ----------------------------------------

class TerminalApp(OSWindow):
    """
    Aplicativo de Terminal.
    Um REPL Python que pode interagir com a 'os_engine'.
    (Suporta multi-linhas com Ctrl+Enter)
    """
    def __init__(self, desktop):
        super().__init__(desktop, title="Terminal", geometry="600x400")
        
        self.terminal_env = {} # Escopo persistente do terminal
        self.command_history = []
        self.history_index = -1
        
        # Área de texto
        self.output = scrolledtext.ScrolledText(self, bg="black", fg="lime green", 
                                                font=("Consolas", 11), insertbackground="white")
        self.output.pack(expand=True, fill="both")
        self.output.insert(tk.END, "Bem-vindo ao Terminal PTPY.\n")
        self.output.insert(tk.END, "Use 'help' para ver os comandos de automação.\n")
        self.output.insert(tk.END, "Digite seu código (multi-linha) e pressione [Ctrl+Enter] para executar.\n\n")
        self.output.config(state="disabled")
        
        # Input
        self.input_frame = tk.Frame(self, bg="black")
        self.input_frame.pack(fill="x")
        
        self.prompt_label = tk.Label(self.input_frame, text=">", bg="black", 
                                     fg="lime green", font=("Consolas", 11))
        self.prompt_label.pack(side="left", padx=5, anchor="n")
        
        # Substituído 'Entry' por 'Text' para multi-linhas
        self.input_cmd = tk.Text(self.input_frame, bg="black", fg="lime green", 
                                  insertbackground="white", relief="flat", 
                                  font=("Consolas", 11), height=5) # 5 linhas de altura
        self.input_cmd.pack(fill="x", expand=True, padx=(0, 5), pady=5)
        
        # MUDANÇA DE BIND: Ctrl+Enter para executar
        self.input_cmd.bind("<Control-Return>", self.executar_comando)
        self.input_cmd.bind("<Control-Enter>", self.executar_comando) # Alias para alguns teclados
        
        # Bind de histórico
        self.input_cmd.bind("<Up>", self.history_up)
        self.input_cmd.bind("<Down>", self.history_down)
        
        self.input_cmd.focus()
        
        # Focar no input ao clicar na janela
        self.output.bind("<1>", lambda e: self.input_cmd.focus())

    def escrever_output(self, texto, tag=None):
        """
        Escreve texto na área de output.
        """
        self.output.config(state="normal")
        if tag:
            self.output.insert(tk.END, str(texto) + "\n", tag)
        else:
            self.output.insert(tk.END, str(texto) + "\n")
        self.output.see(tk.END) # Auto-scroll
        self.output.config(state="disabled")

    def get_global_scope(self):
        """ Helper para criar o escopo global para execução. """
        return {
            "os_engine": self.os_engine,
            **self.os_engine.variables,
            **self.os_engine.modules
        }

    def run_automation_command(self, command, arg):
        """
        Verifica e executa comandos de automação customizados.
        Retorna True se o comando foi tratado, False caso contrário.
        """
        if command == "help":
            self.escrever_output("Comandos de Automação PTPY:")
            self.escrever_output("  open <app>      - Abre um aplicativo (ex: open Terminal)")
            self.escrever_output("  notify <msg>    - Mostra uma notificação (ex: notify Olá)")
            self.escrever_output("  run <script.py> - Executa um script .py do sandbox")
            self.escrever_output("  trash <file>    - Move um arquivo para a lixeira")
            self.escrever_output("  restore <file>  - Restaura um arquivo da lixeira")
            self.escrever_output("  help            - Mostra esta ajuda")
            self.escrever_output("Qualquer outro comando será executado como Python.")
            return True

        if command == "open":
            if not arg:
                self.escrever_output("Erro: Especifique um app. (Ex: open Terminal)")
                return True
            
            # Procura o app (case-insensitive)
            app_name_found = None
            for reg_name in self.desktop.app_registry.keys():
                if reg_name.lower() == arg.lower():
                    app_name_found = reg_name
                    break
            
            if app_name_found:
                self.desktop.launch_app(app_name_found)
                self.escrever_output(f"Abrindo '{app_name_found}'...")
            else:
                self.escrever_output(f"Erro: App '{arg}' não encontrado.")
            return True

        if command == "notify":
            if not arg:
                self.escrever_output("Erro: Especifique uma mensagem. (Ex: notify Olá)")
                return True
            self.desktop.show_notification("Terminal", arg)
            self.escrever_output("Notificação enviada.")
            return True

        if command == "run":
            if not arg:
                self.escrever_output("Erro: Especifique um script. (Ex: run meu_script.py)")
                return True
            try:
                # Lê o script do sandbox
                script_content = self.os_engine.read_file(arg)
                
                # Executa o script
                self.escrever_output(f"Executando script '{arg}'...")
                # Usamos os mesmos escopos do REPL para consistência
                exec(script_content, self.get_global_scope(), self.terminal_env)
                self.escrever_output(f"Script '{arg}' finalizado.")
            except FileNotFoundError:
                self.escrever_output(f"Erro: Script '{arg}' não encontrado.")
            except Exception as e:
                self.escrever_output(f"Erro ao executar script: {e}")
            return True

        if command == "trash":
            if not arg:
                self.escrever_output("Erro: Especifique um arquivo. (Ex: trash meu_arquivo.txt)")
                return True
            try:
                self.os_engine.delete_item(arg)
                self.escrever_output(f"Arquivo '{arg}' movido para a Lixeira.")
                self.desktop.show_notification("Lixeira", f"'{arg}' movido para a Lixeira.")
            except Exception as e:
                self.escrever_output(f"Erro: {e}")
            return True

        if command == "restore":
            if not arg:
                self.escrever_output("Erro: Especifique o nome do arquivo. (Ex: restore meu_arquivo.txt)")
                return True

            item_id_to_restore = None
            # Procura o item na lixeira pelo nome base
            # Restaura o primeiro (ou mais recente) que encontrar
            for item_id, info in self.os_engine.get_trash_items():
                if os.path.basename(info["original_path"]) == arg:
                    item_id_to_restore = item_id
                    break 
            
            if item_id_to_restore:
                try:
                    self.os_engine.restore_item(item_id_to_restore)
                    self.escrever_output(f"Arquivo '{arg}' restaurado.")
                    self.desktop.show_notification("Lixeira", f"'{arg}' restaurado.")
                except Exception as e:
                    self.escrever_output(f"Erro ao restaurar: {e}")
            else:
                self.escrever_output(f"Erro: Arquivo '{arg}' não encontrado na Lixeira.")
            return True
        
        # Se nenhum comando correspondeu
        return False

    def executar_comando(self, event):
        """
        Executa o comando digitado (com Ctrl+Enter).
        """
        cmd = self.input_cmd.get("1.0", tk.END) # Pega TUDO do tk.Text
        if not cmd.strip():
            return
            
        self.input_cmd.delete("1.0", tk.END) # Limpa o input
        self.escrever_output(f"> {cmd.strip()}")
        
        if not self.command_history or self.command_history[-1] != cmd:
            self.command_history.append(cmd)
        self.history_index = len(self.command_history)

        # Divide o comando para análise
        parts = cmd.strip().split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        # Tenta executar como comando de automação
        # (Nota: 'run' funciona melhor agora com multi-linhas)
        handled = self.run_automation_command(command, arg)

        if handled:
            return "break" # Impede o Tkinter de adicionar uma nova linha
        
        # Se 'handled' for False, continua para execução Python
        global_scope = self.get_global_scope()
        local_scope = self.terminal_env 

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output
        
        try:
            # Tenta compilar como expressão (eval)
            # (Se for multi-linha, eval vai falhar, caindo no 'exec')
            code = compile(cmd, '<terminal>', 'eval')
            result = eval(code, global_scope, local_scope)
            if result is not None:
                self.escrever_output(repr(result))
                
        except SyntaxError:
            # Se falhar, tenta como statement (exec) - ideal para multi-linha
            try:
                code = compile(cmd, '<terminal>', 'exec')
                exec(code, global_scope, local_scope)
            except Exception as e:
                self.escrever_output(f"Erro: {e}", "error")
        except Exception as e:
            self.escrever_output(f"Erro: {e}", "error")
            
        finally:
            # Restaura stdout e imprime qualquer output
            sys.stdout = old_stdout
            stdout_val = redirected_output.getvalue()
            if stdout_val:
                self.escrever_output(stdout_val.strip())
            redirected_output.close()
            
        return "break" # Impede o Tkinter de adicionar uma nova linha

    def history_up(self, event):
        """
        Navega para cima no histórico de comandos.
        """
        # Só funciona se o cursor estiver na primeira linha
        if self.input_cmd.index(tk.INSERT).startswith("1."):
            if self.history_index > 0:
                self.history_index -= 1
                self.input_cmd.delete("1.0", tk.END)
                self.input_cmd.insert("1.0", self.command_history[self.history_index])
                return "break" # Impede o cursor de ir para o início
        return # Deixa o cursor se mover normalmente

    def history_down(self, event):
        """
        Navega para baixo no histórico de comandos.
        """
        # Só funciona se o cursor estiver na última linha
        if self.input_cmd.index(tk.INSERT).startswith(self.input_cmd.index(tk.END + "-1c").split('.')[0]):
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.input_cmd.delete("1.0", tk.END)
                self.input_cmd.insert("1.0", self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index += 1
                self.input_cmd.delete("1.0", tk.END)
                
            return "break"
        return # Deixa o cursor se mover normalmente


# --- (INÍCIO) NOVO APP: PTPY Code (Simulador de VS Code) ---
class PTPYCodeApp(OSWindow):
    """
    Aplicativo PTPY Code (Simulador de VS Code).
    Substitui o Editor de Texto. Possui abas e explorador de arquivos.
    """
    
    # Palavras-chave básicas do Python para syntax highlighting
    PYTHON_KEYWORDS = {
        'def': 'blue', 'class': 'blue', 'self': 'orange',
        'for': 'purple', 'in': 'purple', 'while': 'purple',
        'if': 'purple', 'elif': 'purple', 'else': 'purple',
        'try': 'purple', 'except': 'purple', 'finally': 'purple',
        'return': 'purple', 'yield': 'purple', 'pass': 'purple',
        'import': 'red', 'from': 'red', 'as': 'red',
        'True': 'orange', 'False': 'orange', 'None': 'orange',
        'str': 'cyan', 'int': 'cyan', 'float': 'cyan', 'list': 'cyan', 'dict': 'cyan', 'set': 'cyan'
    }
    
    def __init__(self, desktop):
        super().__init__(desktop, title="PTPY Code", geometry="900x600")
        
        # Rastreia abas abertas: {filepath: frame_da_aba}
        self.open_tabs = {} 

        # --- Menu ---
        self.create_menu()

        # --- Layout Principal (Sidebar | Editor) ---
        self.paned_window = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        self.paned_window.pack(expand=True, fill="both")

        # --- Sidebar (Explorador de Arquivos) ---
        self.sidebar_frame = tk.Frame(self.paned_window, width=250)
        tk.Label(self.sidebar_frame, text="EXPLORADOR", font=("Arial", 10, "bold")).pack(anchor="w", padx=5)
        
        self.tree = ttk.Treeview(self.sidebar_frame, show="tree")
        self.tree_scroll = ttk.Scrollbar(self.sidebar_frame, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=self.tree_scroll.set)
        
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(expand=True, fill="both")
        
        self.paned_window.add(self.sidebar_frame, width=250)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.populate_file_tree()

        # --- Editor (Abas) ---
        self.editor_frame = tk.Frame(self.paned_window)
        self.notebook = ttk.Notebook(self.editor_frame)
        self.notebook.pack(expand=True, fill="both")
        
        self.paned_window.add(self.editor_frame)
        
        # Mapeia IDs de abas para filepaths
        self.tab_map = {}

    def create_menu(self):
        """ Cria o menu "Arquivo" (Salvar, Fechar Aba). """
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        
        file_menu.add_command(label="Salvar (Ctrl+S)", command=self.on_save)
        file_menu.add_command(label="Fechar Aba (Ctrl+W)", command=self.on_close_tab)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.close_window)
        
        # Atalhos
        self.bind_all("<Control-s>", self.on_save)
        self.bind_all("<Control-w>", self.on_close_tab)

    def populate_file_tree(self, parent_node_id="", relative_path="."):
        """ Popula o Treeview do explorador de arquivos. """
        # Limpa o nó pai
        for i in self.tree.get_children(parent_node_id):
            self.tree.delete(i)
            
        try:
            folders, files = self.os_engine.list_dir(relative_path)
            
            for folder in folders:
                node_path = os.path.join(relative_path, folder)
                node_id = self.tree.insert(parent_node_id, "end", text=f"📁 {folder}", 
                                           values=[node_path, "folder"])
                self.tree.insert(node_id, "end", text="...")
                
            for file in files:
                node_path = os.path.join(relative_path, file)
                self.tree.insert(parent_node_id, "end", text=f"🗎 {file}", 
                                 values=[node_path, "file"])
                                 
        except Exception as e:
            self.desktop.show_notification("PTPY Code", f"Erro ao ler arquivos: {e}")

    def on_tree_double_click(self, event):
        """ Abre um arquivo ao dar duplo-clique na árvore. """
        selected_iid = self.tree.focus()
        if not selected_iid:
            return
            
        item = self.tree.item(selected_iid)
        if not item["values"]:
            return
            
        filepath, item_type = item["values"]
        
        if item_type == "folder":
            # Expande/contrai pasta
            is_open = self.tree.item(selected_iid, "open")
            self.populate_file_tree(selected_iid, filepath)
            self.tree.item(selected_iid, open=not is_open) # Inverte o estado
        elif item_type == "file":
            # Abre o arquivo em uma aba
            self.open_file_in_tab(filepath)

    def open_file_in_tab(self, filepath):
        """ Abre (ou foca) um arquivo em uma nova aba do notebook. """
        
        # Se a aba já está aberta, apenas foque nela
        if filepath in self.open_tabs:
            tab_frame = self.open_tabs[filepath]
            self.notebook.select(tab_frame)
            return
        
        try:
            content = self.os_engine.read_file(filepath)
        except Exception as e:
            messagebox.showerror("Erro ao Abrir", f"Não foi possível ler o arquivo: {e}")
            return

        # Cria a aba (frame)
        tab_frame = tk.Frame(self.notebook)
        
        # Cria o editor de texto
        text_editor = scrolledtext.ScrolledText(tab_frame, undo=True, bg="#2B2B2B", fg="white", insertbackground="white")
        text_editor.pack(expand=True, fill="both")
        text_editor.insert("1.0", content)
        
        # Armazena a referência
        self.open_tabs[filepath] = tab_frame
        
        # Adiciona a aba ao notebook
        self.notebook.add(tab_frame, text=os.path.basename(filepath))
        self.notebook.select(tab_frame) # Foca na nova aba
        
        # Mapeia o ID da aba ao filepath para salvar
        self.tab_map[tab_frame._name] = filepath
        
        # Aplica syntax highlighting básico
        self.apply_syntax_highlighting(text_editor)
        text_editor.bind("<KeyRelease>", lambda e: self.apply_syntax_highlighting(e.widget))

    def on_save(self, event=None):
        """ Salva o conteúdo da aba ativa. """
        try:
            selected_tab_id = self.notebook.select()
            
            # Encontra o filepath usando o ID da aba
            filepath = self.tab_map.get(selected_tab_id)
            if not filepath:
                return # Aba não mapeada (ex: aba vazia inicial)

            # Encontra o widget de texto dentro do frame da aba
            tab_frame = self.notebook.nametowidget(selected_tab_id)
            text_widget = tab_frame.winfo_children()[0] # Assumindo que é o ScrolledText
            
            content = text_widget.get("1.0", tk.END)
            self.os_engine.create_file(filepath, content)
            self.desktop.show_notification("PTPY Code", f"Arquivo '{filepath}' salvo.")
            
        except tk.TclError:
            # Nenhuma aba aberta
            pass
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar: {e}")
            
        return "break" # Impede o evento de propagar

    def on_close_tab(self, event=None):
        """ Fecha a aba ativa. """
        try:
            selected_tab_id = self.notebook.select()
            
            # Encontra e remove o item do rastreamento
            filepath_to_remove = self.tab_map.pop(selected_tab_id, None)
            
            if filepath_to_remove:
                del self.open_tabs[filepath_to_remove]
                
            self.notebook.forget(selected_tab_id) # Fecha a aba
        except tk.TclError:
            # Nenhuma aba para fechar
            pass
            
        return "break"

    def apply_syntax_highlighting(self, text_widget):
        """ Aplica coloração de sintaxe básica em palavras-chave. """
        
        # Configura as tags de cor por widget (evita conflito entre múltiplos editores)
        if not hasattr(text_widget, "_tags_configured"):
            for color in set(self.PYTHON_KEYWORDS.values()):
                text_widget.tag_config(color, foreground=color)
            text_widget._tags_configured = True

        # Limpa tags antigas
        for tag in self.PYTHON_KEYWORDS.values():
            text_widget.tag_remove(tag, "1.0", tk.END)
            
        # Aplica novas tags
        for keyword, color in self.PYTHON_KEYWORDS.items():
            # Regex para encontrar a palavra inteira (evita colorir 'def' em 'default')
            pattern = r'\b' + re.escape(keyword) + r'\b'
            
            start_index = "1.0"
            while True:
                match = text_widget.search(pattern, start_index, stopindex=tk.END, regexp=True)
                if not match:
                    break
                
                end_index = f"{match}+{len(keyword)}c"
                text_widget.tag_add(color, match, end_index)
                start_index = end_index

# --- (FIM) NOVO APP: PTPY Code ---


class FileExplorerApp(OSWindow):
    """
    Aplicativo Explorador de Arquivos.
    Usa um Treeview para mostrar a estrutura de pastas.
    """
    def __init__(self, desktop):
        super().__init__(desktop, title="Explorador de Arquivos", geometry="700x450")
        
        self.current_path = "."
        
        # --- Toolbar ---
        toolbar = tk.Frame(self, bg="gray90")
        toolbar.pack(side="top", fill="x")
        
        tk.Button(toolbar, text="Criar Pasta", command=self.on_create_folder).pack(side="left")
        tk.Button(toolbar, text="Criar Arquivo", command=self.on_create_file).pack(side="left")

        # --- PanedWindow (Treeview | Main Panel) ---
        self.paned_window = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        self.paned_window.pack(expand=True, fill="both")

        # --- Treeview (Lado Esquerdo) ---
        self.tree_frame = tk.Frame(self.paned_window)
        self.tree = ttk.Treeview(self.tree_frame, show="tree")
        self.tree_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=self.tree_scroll.set)
        
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(expand=True, fill="both")
        
        self.paned_window.add(self.tree_frame, width=200)

        # --- Main Panel (Lado Direito - por enquanto vazio) ---
        self.main_panel = tk.Frame(self.paned_window, bg="white")
        self.main_panel_label = tk.Label(self.main_panel, text="Selecione um item", bg="white")
        self.main_panel_label.pack(pady=20)
        self.paned_window.add(self.main_panel)
        
        # --- Bindings ---
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_open)
        self.tree.bind("<Button-3>", self.on_right_click)
        
        # --- Context Menu ---
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Renomear", command=self.on_rename)
        self.context_menu.add_command(label="Deletar (Lixeira)", command=self.on_delete)
        
        # --- Populando a árvore ---
        self.populate_tree()

    def populate_tree(self, parent_node_id="", relative_path="."):
        """
        Popula (ou repopula) o Treeview com o sistema de arquivos.
        """
        # Limpa o nó pai
        for i in self.tree.get_children(parent_node_id):
            self.tree.delete(i)
            
        try:
            folders, files = self.os_engine.list_dir(relative_path)
            
            # Adiciona pastas
            for folder in folders:
                node_path = os.path.join(relative_path, folder)
                node_id = self.tree.insert(parent_node_id, "end", text=f"📁 {folder}", 
                                           values=[node_path, "folder"])
                # Adiciona um nó "dummy" para que a pasta possa ser expandida
                self.tree.insert(node_id, "end", text="...")
                
            # Adiciona arquivos
            for file in files:
                node_path = os.path.join(relative_path, file)
                self.tree.insert(parent_node_id, "end", text=f"🗎 {file}", 
                                 values=[node_path, "file"])
                                 
        except Exception as e:
            self.desktop.show_notification("Erro de Arquivo", str(e))

    def on_tree_open(self, event):
        """
        Chamado quando o usuário expande uma pasta no Treeview.
        """
        selected_iid = self.tree.focus()
        item = self.tree.item(selected_iid)
        
        if not item["values"]:
            return
            
        node_path, item_type = item["values"]
        if item_type == "folder":
            self.populate_tree(selected_iid, node_path)

    def on_right_click(self, event):
        """
        Exibe o menu de contexto ao clicar com o botão direito.
        """
        # Identifica o item clicado
        iid = self.tree.identify_row(event.y)
        if iid:
            # Seleciona o item
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            # Mostra o menu
            self.context_menu.post(event.x_root, event.y_root)
        
    def get_selected_path(self):
        """
        Helper para pegar o caminho do item selecionado.
        """
        selected_iid = self.tree.focus()
        if not selected_iid:
            return None
        item = self.tree.item(selected_iid)
        return item["values"][0] # O caminho relativo

    def on_rename(self):
        """
        Renomeia o item selecionado.
        """
        path = self.get_selected_path()
        if not path:
            return
            
        new_name = simpledialog.askstring("Renomear", "Novo nome:", initialvalue=os.path.basename(path))
        if not new_name:
            return
            
        try:
            self.os_engine.rename_item(path, new_name)
            self.desktop.show_notification("Sucesso", f"'{path}' renomeado para '{new_name}'.")
            # Recarrega a árvore (forma simples)
            self.populate_tree() 
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível renomear: {e}")

    def on_delete(self):
        """
        Move o item selecionado para a lixeira.
        """
        path = self.get_selected_path()
        if not path:
            return
            
        if messagebox.askyesno("Lixeira", f"Mover '{path}' para a Lixeira?"):
            try:
                self.os_engine.delete_item(path)
                self.desktop.show_notification("Lixeira", f"'{path}' movido para a Lixeira.")
                # Recarrega a árvore
                self.populate_tree()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível deletar: {e}")

    def on_create_folder(self):
        """
        Cria uma nova pasta no diretório raiz (simplificado).
        """
        name = simpledialog.askstring("Nova Pasta", "Nome da pasta:")
        if not name:
            return
        
        try:
            self.os_engine.create_folder(name)
            self.desktop.show_notification("Sucesso", f"Pasta '{name}' criada.")
            self.populate_tree()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar pasta: {e}")

    def on_create_file(self):
        """
        Cria um novo arquivo vazio no diretório raiz (simplificado).
        """
        name = simpledialog.askstring("Novo Arquivo", "Nome do arquivo (ex: 'novo.txt'):")
        if not name:
            return
        
        try:
            self.os_engine.create_file(name, "")
            self.desktop.show_notification("Sucesso", f"Arquivo '{name}' criado.")
            self.populate_tree()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível criar arquivo: {e}")


class TrashApp(OSWindow):
    """
    Aplicativo da Lixeira.
    Mostra os itens deletados e permite restaurá-los.
    """
    def __init__(self, desktop):
        super().__init__(desktop, title="Lixeira", geometry="600x400")
        
        # --- Toolbar ---
        toolbar = tk.Frame(self)
        toolbar.pack(side="top", fill="x")
        
        tk.Button(toolbar, text="Restaurar Item", command=self.on_restore).pack(side="left")
        tk.Button(toolbar, text="Esvaziar Lixeira", command=self.on_empty_trash).pack(side="right")
        
        # --- Treeview ---
        self.tree = ttk.Treeview(self, columns=("Original Path", "Deleted At"), show="headings")
        self.tree.heading("Original Path", text="Caminho Original")
        self.tree.heading("Deleted At", text="Data da Exclusão")
        
        self.tree.pack(expand=True, fill="both")
        
        self.populate_list()

    def populate_list(self):
        """
        Popula a lista com os itens da lixeira.
        """
        # Limpa
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Preenche
        for file_id, info in self.os_engine.get_trash_items():
            self.tree.insert("", "end", iid=file_id, 
                             values=(info["original_path"], info["deleted_at"]))

    def on_restore(self):
        """
        Restaura o item selecionado.
        """
        selected_iid = self.tree.focus()
        if not selected_iid:
            messagebox.showwarning("Seleção", "Selecione um item para restaurar.")
            return
            
        try:
            self.os_engine.restore_item(selected_iid)
            self.desktop.show_notification("Lixeira", "Item restaurado com sucesso.")
            self.populate_list() # Atualiza
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível restaurar: {e}")

    def on_empty_trash(self):
        """
        Esvazia a lixeira permanentemente.
        """
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja esvaziar a lixeira?\nEsta ação é permanente."):
            try:
                self.os_engine.empty_trash()
                self.desktop.show_notification("Lixeira", "Lixeira esvaziada.")
                self.populate_list() # Atualiza
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível esvaziar: {e}")


class ControlPanelApp(OSWindow):
    """
    Aplicativo Painel de Controle.
    Mostra módulos e variáveis do sistema.
    """
    def __init__(self, desktop):
        super().__init__(desktop, title="Painel de Controle", geometry="500x350")
        
        self.notebook = ttk.Notebook(self)
        
        # --- Aba Módulos ---
        self.modules_frame = tk.Frame(self.notebook)
        self.modules_text = scrolledtext.ScrolledText(self.modules_frame, state="disabled")
        self.modules_text.pack(expand=True, fill="both", padx=10, pady=10)
        self.notebook.add(self.modules_frame, text="Módulos")
        
        # --- Aba Variáveis ---
        self.vars_frame = tk.Frame(self.notebook)
        self.vars_text = scrolledtext.ScrolledText(self.vars_frame, state="disabled")
        self.vars_text.pack(expand=True, fill="both", padx=10, pady=10)
        self.notebook.add(self.vars_frame, text="Variáveis Globais")
        
        self.notebook.pack(expand=True, fill="both")
        
        self.refresh_data()

    def refresh_data(self):
        """
        Carrega os dados da engine nos text areas.
        """
        # --- Módulos ---
        self.modules_text.config(state="normal")
        self.modules_text.delete("1.0", tk.END)
        for name, module in self.os_engine.modules.items():
            self.modules_text.insert(tk.END, f"--- {name} ---\n", ("heading",))
            self.modules_text.insert(tk.END, f"  Funções: {list(f for f in module.keys() if not f.startswith('_'))}\n")
            if "_fields" in module:
                self.modules_text.insert(tk.END, f"  Campos (CRUD): {module['_fields']}\n")
            self.modules_text.insert(tk.END, "\n")
        self.modules_text.config(state="disabled")

        # --- Variáveis ---
        self.vars_text.config(state="normal")
        self.vars_text.delete("1.0", tk.END)
        try:
            vars_pretty = json.dumps(self.os_engine.variables, indent=4)
            self.vars_text.insert(tk.END, vars_pretty)
        except Exception as e:
            self.vars_text.insert(tk.END, f"Erro ao formatar variáveis: {e}")
        self.vars_text.config(state="disabled")


class WebBrowserApp(OSWindow):
    """
    Aplicativo Navegador Web (Simulado).
    Usa a biblioteca 'webbrowser' para abrir o navegador
    padrão do sistema real.
    """
    def __init__(self, desktop):
        super().__init__(desktop, title="Navegador Web", geometry="700x100")
        
        self.configure(bg="gray90")
        
        toolbar = tk.Frame(self, bg="gray90")
        toolbar.pack(pady=20, padx=20, fill="x")

        # Barra de Endereço
        self.address_bar = tk.Entry(toolbar, font=("Arial", 12))
        self.address_bar.pack(side="left", fill="x", expand=True, ipady=4)
        self.address_bar.insert(0, "https://www.google.com")
        
        # Botão "Ir"
        self.go_button = tk.Button(toolbar, text="Ir", command=self.on_go)
        self.go_button.pack(side="right", padx=10)
        
        # Bind <Return> (Enter) para o botão
        self.address_bar.bind("<Return>", self.on_go)
        
        # Info
        info_label = tk.Label(self, 
            text="Este navegador abrirá os sites no seu navegador real (Chrome, Firefox, etc.)",
            bg="gray90",
            font=("Arial", 9, "italic")
        )
        info_label.pack(fill="x", padx=20)


    def on_go(self, event=None):
        """
        Chamado ao clicar em "Ir" ou pressionar Enter.
        """
        url = self.address_bar.get()
        
        # Adiciona https:// se não estiver presente
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        try:
            # A mágica acontece aqui:
            webbrowser.open(url)
            
            # Avisa o usuário no MiniOS
            self.desktop.show_notification("Navegador", f"Abrindo '{url}' no seu navegador real.")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível abrir o navegador: {e}")


# ----------------------------------------
# CAMADA 4: O DESKTOP (Aplicação Principal)
# (Classe tk.Tk que une tudo)
# ----------------------------------------

class Desktop(tk.Tk):
    """
    A aplicação principal (tk.Tk).
    Representa a Área de Trabalho, Barra de Tarefas e
    gerencia o lançamento de aplicativos.
    """
    def __init__(self):
        super().__init__()
        self.title("PTPY Mini OS")
        self.geometry("1280x720")
        
        # Flag para o ciclo de reinicialização
        self.restart_flag = False
        
        # Define a imagem de fundo
        # (Um fundo azul escuro simples para não depender de arquivos)
        self.desktop_frame = tk.Frame(self, bg="#000033") # Cor do "Wallpaper"
        self.desktop_frame.pack(expand=True, fill="both")
        
        # --- Inicializa a Engine ---
        self.os_engine = MiniOS_Engine(root_path="./minios_root")
        
        # --- Inicializa Sistemas da GUI ---
        self.notification_manager = NotificationManager(self)
        self.taskbar = Taskbar(self)
        self.taskbar.pack(side="bottom", fill="x")
        
        # --- Gerenciamento de Apps ---
        self.app_registry = {} # {name: {class, icon_char}}
        self.register_default_apps()
        self.create_desktop_icons()
        
        # --- Evento de Desligamento ---
        self.protocol("WM_DELETE_WINDOW", self.on_shutdown)
        
        # Esconde o desktop para mostrar o login
        self.withdraw() 

    def show_desktop(self):
        """ Torna o desktop visível após o login. """
        self.deiconify()
        self.show_notification("PTPY Mini OS", "Login bem-sucedido. Sistema iniciado.")

    def register_default_apps(self):
        """
        Registra os aplicativos que vêm com o "OS".
        """
        self.register_app("PTPY Code", PTPYCodeApp, "💡") # NOVO APP
        self.register_app("Terminal", TerminalApp, "💻")
        # self.register_app("Editor de Texto", TextEditorApp, "📝") # Substituído pelo PTPY Code
        self.register_app("Explorador", FileExplorerApp, "📁")
        self.register_app("Lixeira", TrashApp, "🗑️")
        self.register_app("Painel de Controle", ControlPanelApp, "⚙️")
        self.register_app("Navegador Web", WebBrowserApp, "🌐") 

    def register_app(self, app_name, app_class, icon_char="🗎"):
        """
        Registra um novo "App" no sistema.
        """
        self.app_registry[app_name] = {
            "class": app_class,
            "icon_char": icon_char
        }

    def create_desktop_icons(self):
        """
        Coloca os ícones dos apps registrados na área de trabalho.
        O posicionamento é feito após a janela estar visível para garantir medidas corretas.
        """
        def place_icons():
            x_pos, y_pos = 20, 20
            max_height = self.desktop_frame.winfo_height() or self.winfo_height()
            for app_name, info in self.app_registry.items():
                icon = DesktopIcon(self.desktop_frame, text=app_name, 
                                   icon_char=info["icon_char"])
                icon.on_double_click(lambda name=app_name: self.launch_app(name))
                
                # Posicionamento em grid
                icon.place(x=x_pos, y=y_pos, width=80, height=80)
                
                y_pos += 90
                if y_pos > (max_height - 200):
                    y_pos = 20
                    x_pos += 90

        # Agenda o posicionamento após a janela estar pronta
        self.after_idle(place_icons)

    def launch_app(self, app_name):
        """
        Lança uma instância de um aplicativo.
        """
        app_info = self.app_registry.get(app_name)
        if app_info:
            try:
                # Cria a instância da classe do app
                app_info["class"](self) 
            except Exception as e:
                messagebox.showerror("Erro ao Lançar App", 
                                     f"Não foi possível abrir {app_name}: {e}")
        else:
            self.show_notification("Erro", f"Aplicativo '{app_name}' não encontrado.")

    def show_notification(self, title, message, duration=3000):
        """
        Helper para exibir notificações do sistema.
        """
        self.notification_manager.show(title, message, duration)

    def on_shutdown(self):
        """
        Executa ao fechar a janela principal.
        Salva o estado e fecha o programa.
        """
        if messagebox.askokcancel("Desligar", "Deseja salvar o estado e desligar o PTPY Mini OS?"):
            print("Salvando estado...")
            self.os_engine.save_state()
            print("PTPY Mini OS Desligado.")
            self.restart_flag = False # Garante que não vai reiniciar
            self.destroy() # Fecha a janela, terminando o mainloop

    def on_restart(self):
        """
        Executa ao clicar em Reiniciar.
        Salva o estado e ativa a flag de reinício.
        """
        if messagebox.askokcancel("Reiniciar", "Deseja salvar o estado e reiniciar o PTPY Mini OS?"):
            print("Salvando estado...")
            self.os_engine.save_state()
            print("Reiniciando PTPY Mini OS...")
            self.restart_flag = True # ATIVA A FLAG
            self.destroy() # Fecha a janela, terminando o mainloop

# ----------------------------------------
# CAMADA 5: TELA DE LOGIN (NOVO)
# ----------------------------------------

class LoginScreen(tk.Toplevel):
    """
    Janela de Login modal que aparece antes do Desktop.
    """
    def __init__(self, desktop: Desktop, engine: MiniOS_Engine):
        super().__init__(desktop)
        self.desktop = desktop
        self.engine = engine
        self.login_successful = False
        
        self.title("PTPY Mini OS - Login")
        self.geometry("350x250")
        
        # Centralizar
        self.transient(desktop)
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        # UI
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")

        tk.Label(main_frame, text="PTPY Mini OS Login", font=("Arial", 16, "bold")).pack(pady=10)

        tk.Label(main_frame, text="Email:").pack(anchor="w")
        self.email_entry = tk.Entry(main_frame, width=40)
        self.email_entry.pack(fill="x", pady=5)
        self.email_entry.insert(0, "admin@ptpy.os") # Preenche com admin

        tk.Label(main_frame, text="Senha:").pack(anchor="w")
        self.pass_entry = tk.Entry(main_frame, show="*", width=40)
        self.pass_entry.pack(fill="x", pady=5)
        self.pass_entry.insert(0, "admin") # Preenche com admin
        
        self.pass_entry.bind("<Return>", self.attempt_login)

        self.error_label = tk.Label(main_frame, text="", fg="red")
        self.error_label.pack()

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=10)

        tk.Button(button_frame, text="Login", command=self.attempt_login).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(button_frame, text="Registrar", command=self.attempt_register).pack(side="right", expand=True, fill="x", padx=5)

        # Modal
        self.protocol("WM_DELETE_WINDOW", self.on_close_login)
        self.grab_set() # Torna modal
        self.focus_set()

    def attempt_login(self, event=None):
        email = self.email_entry.get()
        password = self.pass_entry.get()
        
        success, message = self.engine.modules["login"]["login"](email, password)
        
        if success:
            self.login_successful = True
            self.destroy() # Fecha a janela de login
            self.desktop.show_desktop() # Mostra o desktop
        else:
            self.error_label.config(text=message, fg="red")
            self.pass_entry.delete(0, tk.END) # Limpa apenas a senha

    def attempt_register(self):
        email = self.email_entry.get()
        password = self.pass_entry.get()
        
        if not email or not password:
            self.error_label.config(text="Preencha email e senha para registrar.", fg="red")
            return

        success, message = self.engine.modules["login"]["register"](email, password)
        
        if success:
            self.error_label.config(text=f"Registrado! Tente fazer login.", fg="green")
        else:
            self.error_label.config(text=message, fg="red")
            
    def on_close_login(self):
        """ Se o usuário fechar a janela de login, desliga o OS. """
        if not self.login_successful:
            self.desktop.destroy() # Fecha o desktop (invisível) e encerra o app


# ----------------------------------------
# INICIALIZAÇÃO
# (Modificado para suportar o Reinício e Login)
# ----------------------------------------
def main():
    """
    Função principal que permite o looping de reinicialização.
    """
    restart = True
    while restart:
        app = Desktop() # Cria o desktop (invisível)
        
        # Cria a tela de login; o app só continua se o login for sucesso
        LoginScreen(app, app.os_engine)
        
        app.mainloop()
        
        # Após o mainloop terminar (app.destroy()),
        # verificamos a flag de reinício.
        restart = app.restart_flag

if __name__ == "__main__":
    main()