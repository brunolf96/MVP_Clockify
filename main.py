#from database import init_db
#from timer_manager import TimerManager
#import time

#init_db()

#timer = TimerManager()

## Simulação de uso
#timer.start("Projeto A", "Desenvolvimento inicial")

#time.sleep(5)  # simula trabalho

#timer.stop()

from database import init_db
from reports import print_report, project_summary

init_db()

print_report()
project_summary()