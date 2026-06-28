import sys
from datetime import date, datetime

from PySide6.QtCore import QTimer, Qt, QDate, QDateTime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QComboBox, QLineEdit, QLabel, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView,
    QDialog, QDialogButtonBox, QDateEdit, QDateTimeEdit
)

from database import (
    init_db,
    insert_entry,
    delete_entry,
    fetch_entries,
    fetch_projects,
    update_entry
)
from reports import (
    build_report_text,
    build_summary_text,
    export_entries_to_csv,
)
from timer_manager import TimerManager
from utils import format_seconds


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry=None):
        super().__init__(parent)
        self.setWindowTitle("Editar entrada" if entry else "Novo registro manual")
        self.setMinimumWidth(480)

        self.project_input = QLineEdit()
        self.desc_input = QLineEdit()
        self.start_input = QDateTimeEdit()
        self.start_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.start_input.setCalendarPopup(True)

        self.end_input = QDateTimeEdit()
        self.end_input.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.end_input.setCalendarPopup(True)

        self.project_input.setPlaceholderText("Projeto")
        self.desc_input.setPlaceholderText("Descrição (opcional)")

        if entry:
            self.entry_id = entry[0]
            self.project_input.setText(entry[1] or "")
            self.desc_input.setText(entry[2] or "")
            self.start_input.setDateTime(QDateTime(datetime.fromisoformat(entry[3])))
            self.end_input.setDateTime(QDateTime(datetime.fromisoformat(entry[4])))
        else:
            current = QDateTime.currentDateTime()
            self.start_input.setDateTime(current)
            self.end_input.setDateTime(current)

        form_layout = QFormLayout()
        form_layout.addRow("Projeto:", self.project_input)
        form_layout.addRow("Descrição:", self.desc_input)
        form_layout.addRow("Início:", self.start_input)
        form_layout.addRow("Fim:", self.end_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button:
            save_button.setText("Salvar")
        if cancel_button:
            cancel_button.setText("Cancelar")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)

    def accept(self):
        if not self.project_input.text().strip():
            QMessageBox.warning(self, "Aviso", "O projeto é obrigatório.")
            return

        start = self.start_input.dateTime().toPython()
        end = self.end_input.dateTime().toPython()
        if end <= start:
            QMessageBox.warning(self, "Aviso", "A data de término deve ser depois do início.")
            return

        super().accept()

    def get_data(self):
        start_dt = self.start_input.dateTime().toPython()
        end_dt = self.end_input.dateTime().toPython()
        duration = int((end_dt - start_dt).total_seconds())

        return (
            self.project_input.text().strip(),
            self.desc_input.text().strip(),
            start_dt.isoformat(),
            end_dt.isoformat(),
            duration
        )


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Gerenciador de tempo")
        self.setGeometry(100, 100, 1100, 620)

        self.timer = TimerManager()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_elapsed_label)

        self.selected_entry_id = None
        self.current_entries = []

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        form_layout = QVBoxLayout()
        history_layout = QVBoxLayout()

        self.project_input = QComboBox()
        self.project_input.setEditable(True)
        self.project_input.setInsertPolicy(QComboBox.NoInsert)
        self.load_project_list()

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Descrição (opcional)")

        self.status_label = QLabel("Status: parado")
        self.elapsed_label = QLabel("Tempo: 00:00:00")
        self.today_label = QLabel("Hoje: 00:00:00")

        self.start_btn = QPushButton("Iniciar")
        self.stop_btn = QPushButton("Parar")
        self.report_btn = QPushButton("Relatório")
        self.summary_btn = QPushButton("Resumo")
        self.refresh_btn = QPushButton("Atualizar")

        self.start_btn.clicked.connect(self.start_timer)
        self.stop_btn.clicked.connect(self.stop_timer)
        self.report_btn.clicked.connect(self.show_report)
        self.summary_btn.clicked.connect(self.show_summary)
        self.refresh_btn.clicked.connect(self.refresh_history)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addWidget(self.report_btn)
        buttons_layout.addWidget(self.summary_btn)
        buttons_layout.addWidget(self.refresh_btn)

        self.manual_btn = QPushButton("Registro manual")
        self.edit_btn = QPushButton("Editar")
        self.delete_btn = QPushButton("Excluir")
        self.export_btn = QPushButton("Exportar CSV")

        self.manual_btn.clicked.connect(self.create_manual_entry)
        self.edit_btn.clicked.connect(self.edit_selected_entry)
        self.delete_btn.clicked.connect(self.delete_selected_entry)
        self.export_btn.clicked.connect(self.export_csv)

        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.manual_btn)
        action_layout.addWidget(self.edit_btn)
        action_layout.addWidget(self.delete_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.export_btn)

        self.filter_project_input = QLineEdit()
        self.filter_project_input.setPlaceholderText("Filtrar por projeto")

        self.filter_mode_combo = QComboBox()
        self.filter_mode_combo.addItems(["Exato", "Parcial"])
        self.filter_mode_combo.setCurrentText("Exato")

        self.filter_start_date = QDateEdit(calendarPopup=True)
        self.filter_start_date.setDisplayFormat("dd/MM/yyyy")
        self.filter_start_date.setDate(QDate(2000, 1, 1))

        self.filter_end_date = QDateEdit(calendarPopup=True)
        self.filter_end_date.setDisplayFormat("dd/MM/yyyy")
        self.filter_end_date.setDate(QDate.currentDate())

        self.filter_btn = QPushButton("Filtrar")
        self.clear_filter_btn = QPushButton("Limpar")
        self.filter_btn.clicked.connect(self.refresh_history)
        self.clear_filter_btn.clicked.connect(self.clear_filters)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Projeto:"))
        filter_layout.addWidget(self.filter_project_input)
        filter_layout.addWidget(QLabel("Modo:"))
        filter_layout.addWidget(self.filter_mode_combo)
        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.filter_start_date)
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.filter_end_date)
        filter_layout.addWidget(self.filter_btn)
        filter_layout.addWidget(self.clear_filter_btn)

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels([
            "ID", "Projeto", "Descrição", "Início", "Fim", "Duração"
        ])
        self.history_table.setColumnHidden(0, True)
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSortingEnabled(True)
        self.history_table.itemSelectionChanged.connect(self.on_entry_selected)

        self.summary_label = QLabel("Total: 00:00:00")
        self.summary_label.setAlignment(Qt.AlignRight)

        form_layout.addWidget(self.project_input)
        form_layout.addWidget(self.desc_input)
        form_layout.addWidget(self.elapsed_label)
        form_layout.addWidget(self.today_label)
        form_layout.addWidget(self.status_label)
        form_layout.addLayout(buttons_layout)
        form_layout.addLayout(action_layout)

        history_layout.addLayout(filter_layout)
        history_layout.addWidget(self.history_table)
        history_layout.addWidget(self.summary_label)

        top_layout.addLayout(form_layout, 1)
        top_layout.addLayout(history_layout, 2)

        layout.addLayout(top_layout)
        self.setLayout(layout)

        self.refresh_history()
        self.refresh_buttons()

    def refresh_buttons(self):
        self.start_btn.setEnabled(not self.timer.running)
        self.stop_btn.setEnabled(self.timer.running)

    def load_project_list(self):
        current_text = self.project_input.currentText() if self.project_input.count() else ""
        self.project_input.clear()
        self.project_input.addItems(fetch_projects())
        if current_text:
            self.project_input.setEditText(current_text)

    def update_today_label(self):
        today = date.today().isoformat()
        entries = fetch_entries(None, today, today)
        total_seconds = sum(row[5] or 0 for row in entries)

        if self.timer.running and self.timer.start_time and self.timer.start_time.date() == date.today():
            total_seconds += int((datetime.now() - self.timer.start_time).total_seconds())

        self.today_label.setText(f"Hoje: {format_seconds(total_seconds)}")

    def start_timer(self):
        project = self.project_input.currentText().strip()
        desc = self.desc_input.text().strip()

        if not project:
            self.status_label.setText("Digite um projeto!")
            return

        try:
            self.timer.start(project, desc)
            self.status_label.setText(f"Rodando: {project}")
            self.update_timer.start(1000)
        except Exception as e:
            self.status_label.setText(str(e))
        finally:
            self.refresh_buttons()
            self.update_elapsed_label()

    def stop_timer(self):
        try:
            self.timer.stop()
            self.status_label.setText("Status: parado")
            self.update_timer.stop()
            self.refresh_history()
        except Exception as e:
            self.status_label.setText(str(e))
        finally:
            self.refresh_buttons()
            self.update_elapsed_label()

    def show_report(self):
        report = build_report_text()
        QMessageBox.information(self, "Relatório", report)

    def show_summary(self):
        summary = build_summary_text()
        QMessageBox.information(self, "Resumo", summary)

    def refresh_history(self):
        self.load_project_list()
        project_filter = self.filter_project_input.text().strip() or None
        start_date = self.filter_start_date.date().toString(Qt.ISODate)
        end_date = self.filter_end_date.date().toString(Qt.ISODate)
        match_mode = "partial" if self.filter_mode_combo.currentText() == "Parcial" else "exact"

        entries = fetch_entries(project_filter, start_date, end_date, match_mode=match_mode)
        self.current_entries = entries
        self.selected_entry_id = None
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

        self.history_table.setRowCount(len(entries))
        total_seconds = 0

        for row_index, row in enumerate(entries):
            row_id = row[0]
            id_item = QTableWidgetItem(str(row_id))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(row_index, 0, id_item)

            for column_index, value in enumerate(row[1:], start=1):
                cell_text = str(value or "")
                if column_index in (3, 4) and value:
                    try:
                        cell_text = datetime.fromisoformat(value).strftime("%Y-%m-%d | %H:%M:%S")
                    except (TypeError, ValueError):
                        cell_text = str(value or "")
                elif column_index == 5:
                    cell_text = format_seconds(value or 0)
                    total_seconds += value or 0
                item = QTableWidgetItem(cell_text)
                item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row_index, column_index, item)

        self.summary_label.setText(f"Total: {format_seconds(total_seconds)}")
        self.update_today_label()

    def clear_filters(self):
        self.filter_project_input.clear()
        self.filter_mode_combo.setCurrentText("Exato")
        self.filter_start_date.setDate(QDate(2000, 1, 1))
        self.filter_end_date.setDate(QDate.currentDate())
        self.refresh_history()

    def on_entry_selected(self):
        selected_row = self.history_table.currentRow()
        if selected_row >= 0:
            id_item = self.history_table.item(selected_row, 0)
            if id_item is not None:
                self.selected_entry_id = int(id_item.text())
                self.edit_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
                return

        self.selected_entry_id = None
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)

    def create_manual_entry(self):
        dialog = EntryDialog(self)
        if dialog.exec() == QDialog.Accepted:
            project, desc, start, end, duration = dialog.get_data()
            insert_entry(project, desc, start, end, duration)
            self.refresh_history()

    def edit_selected_entry(self):
        if not self.selected_entry_id:
            return

        entry = next((item for item in self.current_entries if item[0] == self.selected_entry_id), None)
        if entry is None:
            return

        dialog = EntryDialog(self, entry)
        if dialog.exec() == QDialog.Accepted:
            project, desc, start, end, duration = dialog.get_data()
            update_entry(self.selected_entry_id, project, desc, start, end, duration)
            self.refresh_history()

    def delete_selected_entry(self):
        if not self.selected_entry_id:
            return

        confirm = QMessageBox.question(
            self,
            "Excluir entrada",
            "Tem certeza que deseja excluir a entrada selecionada?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            delete_entry(self.selected_entry_id)
            self.refresh_history()

    def update_elapsed_label(self):
        if self.timer.running and self.timer.start_time:
            elapsed = int((datetime.now() - self.timer.start_time).total_seconds())
            self.elapsed_label.setText(f"Tempo: {format_seconds(elapsed)}")
        else:
            self.elapsed_label.setText("Tempo: 00:00:00")
        self.update_today_label()

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório CSV", "", "Arquivos CSV (*.csv)"
        )
        if not path:
            return

        try:
            export_entries_to_csv(path, self.current_entries)
            QMessageBox.information(self, "Exportar", f"Arquivo salvo em: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível exportar: {e}")


if __name__ == "__main__":
    init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
