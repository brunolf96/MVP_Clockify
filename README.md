# MVP_Clockify

Work time tracker desktop inspirado no Clockify.

## Objetivo

Este projeto permite controlar tempo de trabalho por projeto no computador usando uma interface desktop simples e armazenamento local SQLite. A ideia é criar um app que rode sem instalação adicional para o usuário final quando empacotado.

## Funcionalidades atuais

- Iniciar e parar temporizador por projeto
- Registro manual de entradas
- Editar e excluir entradas
- Filtrar histórico por projeto e por período
- Salvar entradas no banco `tracker.db`
- Visualizar histórico em tabela
- Gerar relatório em tela
- Ver resumo de horas por projeto
- Exportar histórico para CSV

## Como rodar

1. Ative seu ambiente Python.
2. Instale dependências:

```bash
pip install -r requirements.txt
```

3. Execute o aplicativo:

```bash
python app.py
```

## Empacotar como aplicativo sem instalação

Para distribuir sem exigir que o usuário instale Python ou dependências:

1. Instale o PyInstaller:

```bash
pip install pyinstaller
```

2. Gere um executável:

```bash
python -m PyInstaller --onefile --windowed app.py
```

3. O binário resultante estará em `dist/app` no Linux/macOS ou `dist/app.exe` no Windows.

> Esse executável pode ser copiado para outra máquina e executado sem instalar o projeto, desde que exista suporte ao binário no sistema.

## Próximos passos de desenvolvimento

- Adicionar relatórios por período personalizado
- Incluir tags, clientes e projetos fixos
- Permitir exportar para JSON e Excel
- Salvar timer em execução entre reinícios
- Adicionar gráficos de tempo gasto por projeto

## Estrutura do projeto

- `app.py` — interface desktop principal
- `timer_manager.py` — lógica de controle do cronômetro
- `database.py` — inicialização do SQLite e funções de atualização
- `reports.py` — geração de relatórios e exportação
- `utils.py` — utilitários de formatação
