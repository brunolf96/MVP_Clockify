from datetime import datetime

from database import insert_entry

class TimerManager:
    def __init__(self):
        self.running = False
        self.start_time = None
        self.project = None
        self.description = None

    def start(self, project, description=""):
        if self.running:
            raise Exception("Timer já está em execução")

        self.running = True
        self.start_time = datetime.now()
        self.project = project
        self.description = description

        print(f"Temporizador iniciado: {project} às {self.start_time}")

    def stop(self):
        if not self.running:
            raise Exception("Nenhum timer em execução")

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        self._save_entry(end_time, duration)

        print(f"Temporizador parado: duração {duration/60:.2f} minutos")

        self.running = False
        self.start_time = None
        self.project = None
        self.description = None

    def _save_entry(self, end_time, duration):
        insert_entry(
            self.project,
            self.description,
            self.start_time.isoformat(),
            end_time.isoformat(),
            int(duration)
        )