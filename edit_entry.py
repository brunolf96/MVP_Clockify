from database import update_entry
from reports import get_all_entries_with_id
from utils import format_seconds

def run_editor():
    entries = get_all_entries_with_id()

    for e in entries:
        print(e)

    entry_id = int(input("\nID da entrada para editar: "))

    project = input("Novo projeto: ")
    description = input("Nova descrição: ")
    start = input("Novo start_time (ISO): ")
    end = input("Novo end_time (ISO): ")
    duration = int(input("Duração em segundos: "))

    update_entry(entry_id, project, description, start, end, duration)

    print("Entrada atualizada com sucesso!")