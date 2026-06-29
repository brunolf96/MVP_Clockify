import sys
from datetime import date, datetime

from PySide6.QtCore import QTimer, Qt, QDate, QDateTime
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QComboBox, QLineEdit, QLabel, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog, QHeaderView,
    QDialog, QDialogButtonBox, QDateEdit, QDateTimeEdit, QCheckBox,
    QMenu, QListWidget, QListWidgetItem, QPlainTextEdit
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
from preferences import (
    DEFAULT_VISIBLE_COLUMNS,
    load_visible_columns,
    save_visible_columns,
    load_tags,
    save_tags,
)


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


class TagManagerDialog(QDialog):
    def __init__(self, tags, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar tags")
        self.setMinimumWidth(420)

        self.tags = list(tags or [])

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Adicionar nova tag")

        self.add_tag_btn = QPushButton("Adicionar")
        self.add_tag_btn.clicked.connect(self.add_tag)

        self.tag_list = QListWidget()
        self.tag_list.setSelectionMode(QListWidget.SingleSelection)
        self.refresh_tag_list()

        self.remove_tag_btn = QPushButton("Remover selecionada")
        self.remove_tag_btn.clicked.connect(self.remove_selected_tag)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.tag_input)
        button_layout.addWidget(self.add_tag_btn)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.tag_list)
        layout.addWidget(self.remove_tag_btn)

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_button = dialog_buttons.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = dialog_buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if ok_button:
            ok_button.setText("Salvar")
        if cancel_button:
            cancel_button.setText("Cancelar")
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)

        layout.addWidget(dialog_buttons)
        self.setLayout(layout)

    def refresh_tag_list(self):
        self.tag_list.clear()
        for tag in self.tags:
            item = QListWidgetItem(tag)
            self.tag_list.addItem(item)

    def add_tag(self):
        tag = self.tag_input.text().strip()
        if not tag:
            return
        if tag not in self.tags:
            self.tags.append(tag)
            self.refresh_tag_list()
        self.tag_input.clear()

    def remove_selected_tag(self):
        selected_items = self.tag_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            tag = item.text()
            if tag in self.tags:
                self.tags.remove(tag)
        self.refresh_tag_list()

    def get_tags(self):
        return list(self.tags)


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
        self.visible_columns = load_visible_columns()
        self.tags = load_tags()
        self.updating_table = False

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

        self.clear_project_btn = QPushButton("Limpar projeto")
        self.clear_project_btn.clicked.connect(self.clear_project_input)

        self.tag_buttons_widget = QWidget()
        self.tag_buttons_layout = QHBoxLayout(self.tag_buttons_widget)
        self.tag_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_buttons_layout.setSpacing(4)
        self.update_tag_buttons()

        self.manage_tags_btn = QPushButton("Gerenciar tags")
        self.manage_tags_btn.clicked.connect(self.open_manage_tags_dialog)

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
        self.history_table.setSelectionBehavior(QTableWidget.SelectItems)
        self.history_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.history_table.setEditTriggers(
            QTableWidget.DoubleClicked |
            QTableWidget.SelectedClicked |
            QTableWidget.EditKeyPressed
        )
        self.history_table.setSortingEnabled(True)
        self.history_table.setFocusPolicy(Qt.StrongFocus)
        self.history_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_table.customContextMenuRequested.connect(self.show_history_table_context_menu)
        self.history_table.itemSelectionChanged.connect(self.on_entry_selected)
        self.history_table.itemChanged.connect(self.on_history_item_changed)

        self.summary_label = QLabel("Total: 00:00:00")
        self.summary_label.setAlignment(Qt.AlignRight)

        self.column_preferences_group = QWidget()
        self.column_preferences_layout = QVBoxLayout(self.column_preferences_group)
        self.column_preferences_layout.setContentsMargins(0, 0, 0, 0)
        self.column_preferences_layout.addWidget(QLabel("Colunas visíveis:"))

        self.column_checkboxes = {}
        for column_name in ["Data", "Início", "Fim", "Projeto", "Descrição", "Duração"]:
            checkbox = QCheckBox(column_name)
            checkbox.setChecked(column_name in self.visible_columns)
            checkbox.toggled.connect(self.apply_column_visibility)
            self.column_checkboxes[column_name] = checkbox
            self.column_preferences_layout.addWidget(checkbox)

        self.column_preferences_button = QPushButton("Preferências de colunas")
        self.column_preferences_button.clicked.connect(self.toggle_column_preferences)
        self.update_table_columns()

        form_layout.addWidget(self.project_input)
        form_layout.addWidget(self.clear_project_btn)
        form_layout.addWidget(self.tag_buttons_widget)
        form_layout.addWidget(self.manage_tags_btn)
        form_layout.addWidget(self.desc_input)
        form_layout.addWidget(self.elapsed_label)
        form_layout.addWidget(self.today_label)
        form_layout.addWidget(self.status_label)
        form_layout.addLayout(buttons_layout)
        form_layout.addLayout(action_layout)

        history_layout.addLayout(filter_layout)
        history_layout.addWidget(self.column_preferences_button)
        history_layout.addWidget(self.column_preferences_group)
        self.column_preferences_group.hide()
        history_layout.addWidget(self.history_table)
        history_layout.addWidget(self.summary_label)

        top_layout.addLayout(form_layout, 1)
        top_layout.addLayout(history_layout, 2)

        layout.addLayout(top_layout)
        self.setLayout(layout)

        self.setStyleSheet(
            "QPushButton {"
            " background-color: #1565C0;"
            " color: white;"
            " border: 1px solid #0D47A1;"
            " border-radius: 6px;"
            " padding: 6px 12px;"
            " font-weight: 600;"
            "}" 
            "QPushButton:hover {"
            " background-color: #1976D2;"
            "}" 
            "QPushButton:pressed {"
            " background-color: #0D47A1;"
            "}" 
            "QPushButton:disabled {"
            " background-color: #90A4AE;"
            " color: #ECEFF1;"
            " border-color: #78909C;"
            "}"
        )

        self.refresh_history()
        self.refresh_buttons()

    def refresh_buttons(self):
        self.start_btn.setEnabled(not self.timer.running)
        self.stop_btn.setEnabled(self.timer.running)

    def update_tag_buttons(self):
        while self.tag_buttons_layout.count():
            item = self.tag_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for tag in self.tags:
            button = QPushButton(tag)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked, value=tag: self._apply_tag_to_project(value))
            self.tag_buttons_layout.addWidget(button)

        self.tag_buttons_layout.addStretch()

    def _apply_tag_to_project(self, tag: str):
        self.project_input.setEditText(tag)
        self.project_input.setFocus()

    def clear_project_input(self):
        self.project_input.setEditText("")
        self.project_input.setFocus()

    def _get_column_index(self, column_name: str):
        for index in range(self.history_table.columnCount()):
            item = self.history_table.horizontalHeaderItem(index)
            if item is not None and item.text() == column_name:
                return index
        return None

    def _get_cell_text(self, row: int, column_name: str):
        index = self._get_column_index(column_name)
        if index is None:
            return ""
        item = self.history_table.item(row, index)
        return item.text() if item is not None else ""

    def _find_entry_by_id(self, entry_id: int):
        return next((entry for entry in self.current_entries if entry[0] == entry_id), None)

    def _parse_datetime(self, date_text: str, time_text: str):
        if not date_text or not time_text:
            raise ValueError("Data e hora são obrigatórias")
        return datetime.fromisoformat(f"{date_text}T{time_text}")

    def _set_row_error_state(self, row_index: int, error: bool):
        color = QColor("#ffcdd2") if error else QColor("white")
        for col in range(self.history_table.columnCount()):
            item = self.history_table.item(row_index, col)
            if item is not None:
                item.setBackground(color)

    def _validate_history_row(self, row_index: int) -> bool:
        data_text = self._get_cell_text(row_index, "Data")
        start_text = self._get_cell_text(row_index, "Início")
        end_text = self._get_cell_text(row_index, "Fim")

        if not data_text or not start_text or not end_text:
            self._set_row_error_state(row_index, False)
            return True

        try:
            start_dt = self._parse_datetime(data_text, start_text)
            end_dt = self._parse_datetime(data_text, end_text)
        except ValueError:
            self._set_row_error_state(row_index, True)
            return False

        if end_dt <= start_dt:
            self._set_row_error_state(row_index, True)
            return False

        for other_row in range(self.history_table.rowCount()):
            if other_row == row_index:
                continue

            other_data = self._get_cell_text(other_row, "Data")
            other_start = self._get_cell_text(other_row, "Início")
            other_end = self._get_cell_text(other_row, "Fim")
            if not other_data or not other_start or not other_end:
                continue

            try:
                other_start_dt = self._parse_datetime(other_data, other_start)
                other_end_dt = self._parse_datetime(other_data, other_end)
            except ValueError:
                continue

            if start_dt < other_end_dt and end_dt > other_start_dt:
                self._set_row_error_state(row_index, True)
                return False

        self._set_row_error_state(row_index, False)
        return True

    def _restore_history_cell(self, row: int, col: int, original_entry):
        column_name = None
        header_item = self.history_table.horizontalHeaderItem(col)
        if header_item is not None:
            column_name = header_item.text()

        if column_name is None:
            return

        if column_name == "Projeto":
            text = original_entry[1] or ""
        elif column_name == "Descrição":
            text = original_entry[2] or ""
        elif column_name == "Data":
            text = original_entry[3].split("T")[0]
        elif column_name == "Início":
            text = original_entry[3].split("T")[1]
        elif column_name == "Fim":
            text = original_entry[4].split("T")[1] if original_entry[4] else ""
        elif column_name == "Duração":
            text = format_seconds(original_entry[5] or 0)
        else:
            text = self._get_cell_text(row, column_name)

        self.updating_table = True
        try:
            item = self.history_table.item(row, col)
            if item is None:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
            else:
                item.setText(text)
            self.history_table.setItem(row, col, item)
            self.history_table.setCurrentCell(row, col)
            self.history_table.setFocus()
        finally:
            self.updating_table = False

    def on_history_item_changed(self, item):
        if self.updating_table:
            return

        row = item.row()
        col = item.column()
        if col == 0:
            return

        id_item = self.history_table.item(row, 0)
        if id_item is None:
            return

        try:
            entry_id = int(id_item.text())
        except ValueError:
            return

        original_entry = self._find_entry_by_id(entry_id)
        if original_entry is None:
            return

        project = self._get_cell_text(row, "Projeto") or original_entry[1]
        desc = self._get_cell_text(row, "Descrição") or original_entry[2] or ""

        if self._get_column_index("Data") is not None:
            date_text = self._get_cell_text(row, "Data") or original_entry[3].split("T")[0]
        else:
            date_text = original_entry[3].split("T")[0]

        if self._get_column_index("Início") is not None:
            start_time_text = self._get_cell_text(row, "Início") or original_entry[3].split("T")[1]
        else:
            start_time_text = original_entry[3].split("T")[1]

        if self._get_column_index("Fim") is not None:
            end_time_text = self._get_cell_text(row, "Fim") or original_entry[4].split("T")[1]
        else:
            end_time_text = original_entry[4].split("T")[1] if original_entry[4] else ""

        try:
            start_dt = self._parse_datetime(date_text, start_time_text)
            end_date = date_text if self._get_column_index("Data") is not None else original_entry[4].split("T")[0]
            end_dt = self._parse_datetime(end_date, end_time_text)
        except ValueError:
            QMessageBox.warning(self, "Aviso", "Formato de data/hora inválido. Use YYYY-MM-DD e HH:MM:SS.")
            self.refresh_history()
            return

        if end_dt <= start_dt:
            QMessageBox.warning(self, "Aviso", "O horário de fim deve ser depois do início.")
            self.refresh_history()
            return

        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        duration = int((end_dt - start_dt).total_seconds())

        if not self._validate_history_row(row):
            self._restore_history_cell(row, col, original_entry)
            QMessageBox.warning(self, "Aviso", "Registro inválido ou com sobreposição de horário.")
            return

        try:
            update_entry(entry_id, project, desc, start_iso, end_iso, duration)
        except ValueError as exc:
            QMessageBox.warning(self, "Aviso", str(exc))
            self.refresh_history()
            return

        self.refresh_history()

    def open_manage_tags_dialog(self):
        dialog = TagManagerDialog(self.tags, self)
        if dialog.exec() == QDialog.Accepted:
            self.tags = dialog.get_tags()
            save_tags(self.tags)
            self.update_tag_buttons()

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
        dialog = QDialog(self)
        dialog.setWindowTitle("Relatório")
        dialog.setModal(True)
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout(dialog)
        text_view = QPlainTextEdit()
        text_view.setReadOnly(True)
        text_view.setPlainText(report)
        layout.addWidget(text_view)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_button:
            close_button.setText("Fechar")
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def show_summary(self):
        summary = build_summary_text()
        dialog = QDialog(self)
        dialog.setWindowTitle("Resumo")
        dialog.setModal(True)
        dialog.setMinimumSize(700, 500)

        layout = QVBoxLayout(dialog)
        text_view = QPlainTextEdit()
        text_view.setReadOnly(True)
        text_view.setPlainText(summary)
        layout.addWidget(text_view)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_button = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_button:
            close_button.setText("Fechar")
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec()

    def toggle_column_preferences(self):
        self.column_preferences_group.setVisible(not self.column_preferences_group.isVisible())

    def apply_column_visibility(self):
        selected_columns = [
            column_name for column_name, checkbox in self.column_checkboxes.items() if checkbox.isChecked()
        ]
        if not selected_columns:
            selected_columns = list(DEFAULT_VISIBLE_COLUMNS)
            for column_name, checkbox in self.column_checkboxes.items():
                checkbox.setChecked(column_name in selected_columns)
        self.visible_columns = selected_columns
        self.update_table_columns()
        save_visible_columns(self.visible_columns)

    def update_table_columns(self):
        column_names = ["Data", "Início", "Fim", "Projeto", "Descrição", "Duração"]
        visible_columns = [name for name in column_names if name in self.visible_columns]
        self.history_table.setColumnCount(len(visible_columns) + 1)
        self.history_table.setHorizontalHeaderLabels(["ID"] + visible_columns)
        self.history_table.setColumnHidden(0, True)

        for column_index in range(1, self.history_table.columnCount()):
            self.history_table.setColumnHidden(column_index, False)

        self.refresh_history_table_data()

    def refresh_history_table_data(self):
        self.updating_table = True
        try:
            entries = self.current_entries
            self.history_table.setRowCount(len(entries))
            total_seconds = 0

            visible_column_names = []
            for index in range(1, self.history_table.columnCount()):
                header_item = self.history_table.horizontalHeaderItem(index)
                if header_item is not None:
                    visible_column_names.append(header_item.text())

            for row_index, row in enumerate(entries):
                row_id = row[0]
                id_item = QTableWidgetItem(str(row_id))
                id_item.setTextAlignment(Qt.AlignCenter)
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                self.history_table.setItem(row_index, 0, id_item)

                for display_index, column_name in enumerate(visible_column_names, start=1):
                    source_index = None
                    if column_name == "Projeto":
                        source_index = 1
                    elif column_name == "Descrição":
                        source_index = 2
                    elif column_name in {"Data", "Início"}:
                        source_index = 3
                    elif column_name == "Fim":
                        source_index = 4
                    elif column_name == "Duração":
                        source_index = 5

                    if source_index is None:
                        continue

                    value = row[source_index]
                    cell_text = str(value or "")
                    if column_name == "Data" and value:
                        try:
                            cell_text = datetime.fromisoformat(value).strftime("%Y-%m-%d")
                        except (TypeError, ValueError):
                            cell_text = str(value or "")
                    elif column_name == "Início" and value:
                        try:
                            cell_text = datetime.fromisoformat(value).strftime("%H:%M:%S")
                        except (TypeError, ValueError):
                            cell_text = str(value or "")
                    elif column_name == "Fim" and value:
                        try:
                            cell_text = datetime.fromisoformat(value).strftime("%H:%M:%S")
                        except (TypeError, ValueError):
                            cell_text = str(value or "")
                    elif column_name == "Duração":
                        cell_text = format_seconds(value or 0)
                        total_seconds += value or 0

                    item = QTableWidgetItem(cell_text)
                    item.setTextAlignment(Qt.AlignCenter)
                    if column_name == "Duração":
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.history_table.setItem(row_index, display_index, item)

            self.summary_label.setText(f"Total: {format_seconds(total_seconds)}")
            self.update_today_label()
        finally:
            self.updating_table = False

    def show_history_table_context_menu(self, position):
        selected_items = self.history_table.selectedItems()
        if not selected_items:
            return

        menu = QMenu(self)
        copy_action = QAction("Copiar", self)
        copy_action.triggered.connect(self.copy_selected_history_cells)
        menu.addAction(copy_action)
        menu.exec(self.history_table.viewport().mapToGlobal(position))

    def copy_selected_history_cells(self):
        selected_items = self.history_table.selectedItems()
        if not selected_items:
            return

        rows = sorted({item.row() for item in selected_items})
        cols = sorted({item.column() for item in selected_items})
        lines = []
        for row in rows:
            line = []
            for col in cols:
                item = self.history_table.item(row, col)
                line.append(item.text() if item is not None else "")
            lines.append("\t".join(line))

        QApplication.clipboard().setText("\n".join(lines))

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

        self.refresh_history_table_data()

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
            try:
                insert_entry(project, desc, start, end, duration)
            except ValueError as exc:
                QMessageBox.warning(self, "Aviso", str(exc))
            else:
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
            try:
                update_entry(self.selected_entry_id, project, desc, start, end, duration)
            except ValueError as exc:
                QMessageBox.warning(self, "Aviso", str(exc))
            else:
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
