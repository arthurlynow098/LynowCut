from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path
import queue
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile

from PIL import Image, ImageOps
from PySide6.QtCore import QEasingCurve, QObject, QPoint, Property, QPropertyAnimation, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QFileDialog, QFrame, QGraphicsOpacityEffect,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QSlider, QSpacerItem, QVBoxLayout, QWidget,
)

from .engine import Cancelled, IMAGES, Options, Result, binary, process, resource


INK = '#191814'
INK_2 = '#25231d'
CREAM = '#F8F0E3'
PAPER = '#FFF9F0'
PAPER_2 = '#F0E3D0'
ORANGE = '#DE4B1E'
ORANGE_DARK = '#B73613'
PEACH = '#F5C29E'
MUTED = '#756E63'
GREEN = '#26764C'
RED = '#B73C32'


def size(value: int) -> str:
    return f'{value / 1_000_000:.2f} MB' if value >= 1_000_000 else f'{value / 1000:.1f} KB'


def button(text: str, class_name: str = 'secondary') -> QPushButton:
    item = QPushButton(text)
    item.setProperty('class', class_name)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    return item


class WorkerEvents(QObject):
    event = Signal(tuple)


class DropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('dropzone')
        self.setAcceptDrops(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        plus = QLabel('+')
        plus.setObjectName('plus')
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plus)
        words = QVBoxLayout()
        title = QLabel('Solte os arquivos aqui ou escolha do computador')
        title.setObjectName('dropTitle')
        words.addWidget(title)
        subtitle = QLabel('Fotos, vídeos, Word, PDF, PowerPoint, Excel e muito mais')
        subtitle.setObjectName('dropSubtitle')
        words.addWidget(subtitle)
        layout.addLayout(words, 1)
        self.count = QLabel('NENHUM ARQUIVO')
        self.count.setObjectName('dropCount')
        layout.addWidget(self.count)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.files_dropped.emit([])
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setProperty('dragging', True); self.style().unpolish(self); self.style().polish(self)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setProperty('dragging', False); self.style().unpolish(self); self.style().polish(self)

    def dropEvent(self, event):
        self.setProperty('dragging', False); self.style().unpolish(self); self.style().polish(self)
        self.files_dropped.emit([Path(url.toLocalFile()) for url in event.mimeData().urls()])
        event.acceptProposedAction()


class FileCard(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, path: Path):
        super().__init__()
        self.index = index
        self.setObjectName('fileCard')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 14, 12)
        icon = QLabel(path.suffix[1:5].upper() or 'FILE')
        icon.setObjectName('fileIcon')
        icon.setFixedSize(44, 40)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        words = QVBoxLayout(); words.setSpacing(2)
        self.name = QLabel(path.name); self.name.setObjectName('fileName')
        self.name.setToolTip(path.name)
        self.meta = QLabel(f'{size(path.stat().st_size)}  •  aguardando sua ação'); self.meta.setObjectName('fileMeta')
        words.addWidget(self.name); words.addWidget(self.meta); layout.addLayout(words, 1)
        self.badge = QLabel('NA FILA'); self.badge.setObjectName('badge')
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter); self.badge.setFixedWidth(94)
        layout.addWidget(self.badge)
        self.progress = QFrame(); self.progress.setObjectName('cardProgress'); self.progress.setFixedHeight(2); self.progress.setFixedWidth(0)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignBottom)

    def mousePressEvent(self, event):
        self.clicked.emit(self.index)
        super().mousePressEvent(event)

    def state(self, name: str, meta: str | None = None):
        if meta: self.meta.setText(meta)
        self.badge.setText(name)
        self.setProperty('state', name.lower().replace(' ', '-'))
        self.style().unpolish(self); self.style().polish(self)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('LynowCut · Menos peso. Mais espaço.')
        self.setMinimumSize(1120, 760)
        self.resize(1320, 870)
        self.setWindowIcon(QIcon(str(resource('assets/lynowcut.ico'))))
        self.paths: list[Path] = []
        self.results: list[Result | str | None] = []
        self.cards: list[FileCard] = []
        self.selected = None
        self.events: queue.Queue = queue.Queue()
        self.signal = WorkerEvents(); self.signal.event.connect(self.handle_event)
        self.cancel_event = threading.Event(); self.busy = False; self.closing = False
        self.action = 'Comprimir'; self.mode = 'Porcentagem'; self.format = 'WebP'; self.reduction = 70
        self.destination = str(Path.home() / 'Downloads' / 'LynowCut')
        self.build(); self.check_ffmpeg()
        self.timer = QTimer(self); self.timer.timeout.connect(self.poll); self.timer.start(90)

    def label(self, value, class_name='', parent=None):
        item = QLabel(value, parent)
        if class_name: item.setObjectName(class_name)
        return item

    def build(self):
        root = QWidget(); root.setObjectName('root'); self.setCentralWidget(root)
        shell = QHBoxLayout(root); shell.setContentsMargins(0, 0, 0, 0); shell.setSpacing(0)
        shell.addWidget(self.build_sidebar())
        main = QWidget(); main.setObjectName('main'); shell.addWidget(main, 1)
        layout = QVBoxLayout(main); layout.setContentsMargins(36, 27, 36, 20); layout.setSpacing(13)
        layout.addLayout(self.build_header())
        self.dropzone = DropZone(); self.dropzone.files_dropped.connect(self.receive_files)
        layout.addWidget(self.dropzone)
        queue_head = QHBoxLayout(); queue_head.addWidget(self.label('Sua fila', 'sectionTitle'))
        queue_head.addStretch(); clear = button('Limpar fila', 'quiet'); clear.clicked.connect(self.clear); queue_head.addWidget(clear)
        layout.addLayout(queue_head)
        self.queue = QScrollArea(); self.queue.setObjectName('queue'); self.queue.setWidgetResizable(True); self.queue.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.queue_body = QWidget(); self.queue_layout = QVBoxLayout(self.queue_body); self.queue_layout.setContentsMargins(9, 9, 9, 9); self.queue_layout.setSpacing(7)
        self.empty = self.label('Nenhum arquivo por aqui ainda.\nEscolha algo pesado e veja a diferença.', 'empty')
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter); self.queue_layout.addWidget(self.empty); self.queue_layout.addStretch()
        self.queue.setWidget(self.queue_body); layout.addWidget(self.queue, 1)
        layout.addWidget(self.build_controls())
        layout.addLayout(self.build_footer())

    def build_sidebar(self):
        side = QFrame(); side.setObjectName('sidebar'); side.setFixedWidth(270)
        box = QVBoxLayout(side); box.setContentsMargins(20, 26, 20, 24); box.setSpacing(7)
        box.addWidget(self.label('LYNOW  /  CREATIVE TOOLS', 'sideEyebrow'))
        pix = QPixmap(str(resource('assets/mascot-ui.png'))).scaled(194, 194, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        logo = QLabel(); logo.setPixmap(pix); logo.setFixedSize(194, 194); logo.setObjectName('logo'); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(logo, alignment=Qt.AlignmentFlag.AlignHCenter)
        box.addWidget(self.label('LynowCut', 'brand'))
        box.addWidget(self.label('MENOS PESO. MAIS ESPAÇO.', 'tagline'))
        box.addSpacing(20)
        self.nav = {}
        for title, note, action in [('Comprimir', 'Imagens e documentos', 'Comprimir'), ('Extrair áudio', 'Vídeo para MP3', 'Extrair áudio'), ('Criar ZIP', 'Compactação sem perdas', 'Criar ZIP')]:
            nav = button(f'{title}\n{note}', 'nav'); nav.setMinimumHeight(58); nav.setCheckable(True); nav.setChecked(action == 'Comprimir')
            nav.clicked.connect(lambda checked=False, value=action: self.set_action(value)); box.addWidget(nav); self.nav[action] = nav
        box.addStretch(1)
        formats = button('Formatos e saídas  →', 'sideQuiet'); formats.clicked.connect(self.show_formats); box.addWidget(formats)
        self.media = button('Verificando recursos de mídia…', 'media'); self.media.clicked.connect(self.install_ffmpeg); box.addWidget(self.media)
        box.addWidget(self.label('•  PROCESSAMENTO LOCAL E PRIVADO', 'privacy'))
        return side

    def build_header(self):
        row = QHBoxLayout(); text = QVBoxLayout(); text.setSpacing(2)
        self.eyebrow = self.label('COMPRESSÃO INTELIGENTE', 'eyebrow'); text.addWidget(self.eyebrow)
        self.title = self.label('Transforme arquivos pesados\nem resultados leves.', 'title'); text.addWidget(self.title)
        self.subtitle = self.label('Escolha a qualidade. O LynowCut cuida do tamanho e preserva o original.', 'subtitle'); text.addWidget(self.subtitle)
        row.addLayout(text, 1)
        pill = QFrame(); pill.setObjectName('savedPill'); pill.setFixedSize(150, 74); p = QVBoxLayout(pill); p.setContentsMargins(17, 11, 17, 10)
        self.saved_value = self.label('0 KB', 'savedValue'); p.addWidget(self.saved_value); p.addWidget(self.label('ESPAÇO RECUPERADO', 'savedLabel'))
        row.addWidget(pill, alignment=Qt.AlignmentFlag.AlignTop); return row

    def chip_group(self, values, current, callback, object_name='chip'):
        holder = QWidget(); row = QHBoxLayout(holder); row.setContentsMargins(0, 0, 0, 0); row.setSpacing(5); group = QButtonGroup(holder); group.setExclusive(True)
        for value in values:
            item = button(value, object_name); item.setCheckable(True); item.setChecked(value == current); item.clicked.connect(lambda checked=False, v=value: callback(v)); group.addButton(item); row.addWidget(item)
        return holder

    def build_controls(self):
        panel = QFrame(); panel.setObjectName('controls'); layout = QVBoxLayout(panel); layout.setContentsMargins(19, 15, 19, 15); layout.setSpacing(11)
        first = QHBoxLayout(); first.setSpacing(24)
        target = QVBoxLayout(); target.addWidget(self.label('OBJETIVO', 'controlLabel')); target.addWidget(self.chip_group(['Porcentagem', 'Tamanho máximo'], self.mode, self.set_mode))
        first.addLayout(target, 2)
        image = QVBoxLayout(); image.addWidget(self.label('SAÍDA DE IMAGEM', 'controlLabel')); image.addWidget(self.chip_group(['WebP', 'JPEG', 'PNG', 'AVIF'], self.format, self.set_format))
        first.addLayout(image, 2)
        quality = QVBoxLayout(); quality.addWidget(self.label('PERFIL DE QUALIDADE', 'controlLabel')); quality.addWidget(self.chip_group(['Leve', 'Equilibrado', 'Máximo'], 'Equilibrado', self.set_preset))
        first.addLayout(quality, 2)
        layout.addLayout(first)
        second = QHBoxLayout(); second.setSpacing(10)
        self.target_text = self.label('REDUZIR 70%', 'targetText'); second.addWidget(self.target_text)
        self.slider = QSlider(Qt.Orientation.Horizontal); self.slider.setObjectName('slider'); self.slider.setRange(1, 95); self.slider.setValue(70); self.slider.valueChanged.connect(self.slider_changed); second.addWidget(self.slider, 1)
        self.max_mb = QLineEdit('10'); self.max_mb.setObjectName('number'); self.max_mb.setFixedWidth(66); self.max_mb.setAlignment(Qt.AlignmentFlag.AlignCenter); second.addWidget(self.max_mb)
        second.addWidget(self.label('MB', 'unit')); layout.addLayout(second)
        third = QHBoxLayout(); self.metadata = button('✓  Remover metadados', 'toggle'); self.metadata.setCheckable(True); self.metadata.setChecked(True); third.addWidget(self.metadata)
        self.resize = button('✓  Ajustar resolução para atingir a meta', 'toggle'); self.resize.setCheckable(True); self.resize.setChecked(True); third.addWidget(self.resize)
        advanced = button('Recorte de mídia', 'quiet'); advanced.clicked.connect(self.show_advanced); third.addWidget(advanced); third.addStretch()
        self.folder = button('Pasta de saída  ·  Downloads/LynowCut', 'destination'); self.folder.clicked.connect(self.choose_folder); third.addWidget(self.folder); layout.addLayout(third)
        examples = QHBoxLayout(); examples.setSpacing(7)
        examples.addWidget(self.label('SAÍDAS RECOMENDADAS', 'examplesLabel'))
        for icon, title, note in [('WEBP', 'Fotos para web', 'menor peso'), ('PDF', 'Documentos', 'compacto'), ('MP4', 'Vídeos', 'compatível'), ('MP3', 'Áudio', 'extraído')]:
            examples.addWidget(self.example_card(icon, title, note))
        examples.addStretch(); layout.addLayout(examples)
        return panel

    def example_card(self, icon, title, note):
        card = QFrame(); card.setObjectName('exampleCard'); row = QHBoxLayout(card); row.setContentsMargins(8, 5, 9, 5); row.setSpacing(6)
        badge = self.label(icon, 'exampleBadge'); badge.setAlignment(Qt.AlignmentFlag.AlignCenter); row.addWidget(badge)
        words = QVBoxLayout(); words.setSpacing(0); words.addWidget(self.label(title, 'exampleTitle')); words.addWidget(self.label(note, 'exampleNote')); row.addLayout(words)
        return card

    def build_footer(self):
        row = QHBoxLayout(); self.go = button('COMPRIMIR AGORA  →', 'primary'); self.go.setMinimumHeight(48); self.go.clicked.connect(self.start); row.addWidget(self.go)
        self.cancel = button('Cancelar', 'secondary'); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.stop); row.addWidget(self.cancel)
        row.addStretch(); compare = button('Comparar', 'quiet'); compare.clicked.connect(self.compare); row.addWidget(compare)
        report = button('Exportar CSV', 'quiet'); report.clicked.connect(self.export); row.addWidget(report)
        self.status = self.label('PRONTO PARA COMEÇAR', 'status'); row.addWidget(self.status); return row

    def set_action(self, action):
        self.action = action
        for name, item in self.nav.items(): item.setChecked(name == action)
        texts = {
            'Comprimir': ('COMPRESSÃO INTELIGENTE', 'Transforme arquivos pesados\nem resultados leves.', 'COMPRIMIR AGORA  →'),
            'Extrair áudio': ('EXTRAÇÃO DE ÁUDIO', 'Fique só com o som.\nDeixe o resto para trás.', 'EXTRAIR ÁUDIO  →'),
            'Criar ZIP': ('COMPACTAÇÃO SEM PERDAS', 'Organize seus arquivos\nsem alterar o conteúdo.', 'CRIAR ZIP  →'),
        }[action]
        self.eyebrow.setText(texts[0]); self.title.setText(texts[1]); self.go.setText(texts[2])
        if action == 'Extrair áudio':
            try: binary('ffmpeg'); binary('ffprobe')
            except RuntimeError: self.status.setText('INSTALE OS RECURSOS DE MÍDIA NA LATERAL')

    def set_mode(self, mode): self.mode = mode
    def set_format(self, value): self.format = value
    def set_preset(self, value):
        data = {'Leve': (35, '65'), 'Equilibrado': (70, '35'), 'Máximo': (88, '18')}[value]
        self.slider.setValue(data[0]); self.quality = data[1]
    def slider_changed(self, value): self.reduction = value; self.target_text.setText(f'REDUZIR {value}%')

    def receive_files(self, paths):
        if self.busy: return
        if not paths:
            names, _ = QFileDialog.getOpenFileNames(self, 'Escolha arquivos para processar')
            paths = [Path(name) for name in names]
        for path in paths:
            if path.is_file() and path not in self.paths:
                self.paths.append(path); self.add_card(path)
        self.dropzone.count.setText(f'{len(self.paths)} ARQUIVO(S)')

    def add_card(self, path):
        if self.empty.isVisible(): self.empty.hide()
        card = FileCard(len(self.cards), path); card.clicked.connect(self.select)
        self.queue_layout.insertWidget(max(0, self.queue_layout.count() - 1), card); self.cards.append(card)
        effect = QGraphicsOpacityEffect(card); card.setGraphicsEffect(effect); animation = QPropertyAnimation(effect, b'opacity', card); animation.setDuration(260); animation.setStartValue(0.0); animation.setEndValue(1.0); animation.setEasingCurve(QEasingCurve.Type.OutCubic); animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def select(self, index):
        self.selected = index
        for item, card in enumerate(self.cards): card.setProperty('selected', item == index); card.style().unpolish(card); card.style().polish(card)
        if index < len(self.results) and self.results[index] is not None: self.details()

    def clear(self):
        if self.busy: return
        for card in self.cards: card.deleteLater()
        self.paths.clear(); self.results.clear(); self.cards.clear(); self.selected = None; self.empty.show(); self.dropzone.count.setText('NENHUM ARQUIVO'); self.saved_value.setText('0 KB')

    def choose_folder(self):
        value = QFileDialog.getExistingDirectory(self, 'Escolha a pasta de saída', self.destination)
        if value:
            self.destination = value; self.folder.setText(f'Pasta de saída  ·  {Path(value).name}')

    def show_advanced(self):
        dialog = QDialog(self); dialog.setWindowTitle('Recorte de mídia'); dialog.setObjectName('dialog'); dialog.setMinimumWidth(430)
        box = QVBoxLayout(dialog); box.addWidget(self.label('Recorte de vídeo ou áudio', 'dialogTitle'))
        box.addWidget(self.label('Use em segundos. Duração vazia mantém o arquivo até o final.', 'dialogText'))
        self.start_field = QLineEdit(getattr(self, 'start_value', '0')); self.start_field.setPlaceholderText('Início (segundos)'); self.start_field.setObjectName('input')
        self.duration_field = QLineEdit(getattr(self, 'duration_value', '')); self.duration_field.setPlaceholderText('Duração (segundos)'); self.duration_field.setObjectName('input')
        box.addWidget(self.start_field); box.addWidget(self.duration_field); save = button('Salvar recorte', 'primary'); save.clicked.connect(lambda: (setattr(self, 'start_value', self.start_field.text()), setattr(self, 'duration_value', self.duration_field.text()), dialog.accept())); box.addWidget(save)
        dialog.exec()

    def build_options(self):
        number = lambda text: float(text.strip().replace(',', '.'))
        quality = int(getattr(self, 'quality', '35'))
        return Options(reduction=self.reduction, max_mb=number(self.max_mb.text()) if self.mode == 'Tamanho máximo' else None,
                       image_format=self.format, min_quality=quality, remove_metadata=self.metadata.isChecked(), action=self.action,
                       start=number(getattr(self, 'start_value', '0')), duration=number(self.duration_value) if getattr(self, 'duration_value', '').strip() else None,
                       resize_to_target=self.resize.isChecked())

    def start(self):
        if self.busy or not self.paths:
            if not self.paths: self.status.setText('ADICIONE AO MENOS UM ARQUIVO')
            return
        try:
            options = self.build_options(); options.target(1000); folder = Path(self.destination).expanduser().resolve()
        except (ValueError, OSError) as error:
            QMessageBox.critical(self, 'Confira as configurações', str(error)); return
        self.busy = True; self.results = [None] * len(self.paths); self.cancel_event.clear(); self.go.setEnabled(False); self.cancel.setEnabled(True); self.status.setText('PROCESSANDO…')
        threading.Thread(target=self.worker, args=(list(self.paths), folder, options), daemon=True).start()

    def worker(self, paths, folder, options):
        try:
            for index, path in enumerate(paths):
                if self.cancel_event.is_set(): break
                self.events.put(('active', index))
                try: self.events.put(('result', index, process(path, folder, options, self.cancel_event, lambda message: self.events.put(('status', index, message)))))
                except Cancelled: self.events.put(('error', index, 'Cancelado')); break
                except Exception as error: self.events.put(('error', index, str(error)))
        finally: self.events.put(('done',))

    def poll(self):
        try:
            while True: self.handle_event(self.events.get_nowait())
        except queue.Empty: pass

    def handle_event(self, event):
        kind = event[0]
        if kind == 'active': self.cards[event[1]].state('PROCESSANDO', 'O tigre está reduzindo o peso…')
        elif kind == 'status': self.cards[event[1]].meta.setText(event[2])
        elif kind == 'result': self.show_result(event[1], event[2])
        elif kind == 'error': self.show_error(event[1], event[2])
        elif kind == 'done': self.finish()
        elif kind == 'ffmpeg_installed': self.media.setEnabled(True); self.check_ffmpeg(); self.status.setText('RECURSOS DE MÍDIA PRONTOS')
        elif kind == 'ffmpeg_error': self.media.setEnabled(True); self.check_ffmpeg(); QMessageBox.critical(self, 'Falha na instalação', event[1])

    def show_result(self, index, result):
        self.results[index] = result
        if not result.output:
            self.cards[index].state('SEM GANHO', 'O arquivo já está muito comprimido. Tente o perfil Máximo ou uma meta menor.')
            return
        reduction = max(0, (1 - result.after / result.before) * 100)
        detail = 'texto preservado' if 'estruturalmente' in result.note else 'versão visual compacta'
        self.cards[index].state('CONCLUÍDO' if result.status == 'Meta atingida' else result.status.upper(), f'{size(result.before)}  →  {size(result.after)}  •  {reduction:.0f}% menor  •  {detail}')

    def show_error(self, index, error): self.results[index] = error; self.cards[index].state('ERRO', error)
    def finish(self):
        self.busy = False; self.go.setEnabled(True); self.cancel.setEnabled(False); saved = sum(item.saved for item in self.results if isinstance(item, Result)); self.animate_saved(saved); self.status.setText('FINALIZADO · ORIGINAIS PRESERVADOS')
        if self.closing: self.close()
    def animate_saved(self, goal):
        step = {'n': 0}
        timer = QTimer(self)
        def tick():
            step['n'] += 1; portion = 1 - (1 - min(step['n'], 16) / 16) ** 3; self.saved_value.setText(size(int(goal * portion)))
            if step['n'] >= 16: timer.stop()
        timer.timeout.connect(tick); timer.start(28)

    def stop(self): self.cancel_event.set(); self.status.setText('CANCELANDO COM SEGURANÇA…')
    def details(self):
        if self.selected is None or self.selected >= len(self.results): return
        value = self.results[self.selected]
        if isinstance(value, Result): QMessageBox.information(self, value.status, f'{value.note}\n\nOriginal: {size(value.before)}\nResultado: {size(value.after)}\nMeta: {size(value.target)}\n\nSaída: {value.output or "Nenhuma cópia criada"}')
        elif isinstance(value, str): QMessageBox.critical(self, 'Não foi possível processar', value)

    def compare(self):
        if self.selected is None or not isinstance(self.results[self.selected] if self.selected < len(self.results) else None, Result): QMessageBox.information(self, 'Comparar', 'Selecione uma imagem concluída.'); return
        result = self.results[self.selected]
        if not result.output or Path(result.source).suffix.lower() not in IMAGES: QMessageBox.information(self, 'Comparar', 'A comparação é disponível para imagens.'); return
        dialog = QDialog(self); dialog.setWindowTitle('Antes e depois'); dialog.resize(950, 590); box = QHBoxLayout(dialog)
        for path, caption in ((result.source, 'ORIGINAL'), (result.output, 'RESULTADO')):
            column = QVBoxLayout(); title = self.label(caption, 'eyebrow'); title.setAlignment(Qt.AlignmentFlag.AlignCenter); column.addWidget(title)
            with Image.open(path) as opened:
                preview = ImageOps.exif_transpose(opened).convert('RGBA'); preview.thumbnail((430, 470), Image.Resampling.LANCZOS); data = preview.tobytes('raw', 'RGBA')
            image = QImage(data, preview.width, preview.height, QImage.Format.Format_RGBA8888); label = QLabel(); label.setPixmap(QPixmap.fromImage(image)); label.setAlignment(Qt.AlignmentFlag.AlignCenter); label.setObjectName('preview'); column.addWidget(label, 1); box.addLayout(column)
        dialog.exec()

    def export(self):
        items = [item for item in self.results if isinstance(item, Result)]
        if not items: QMessageBox.information(self, 'Relatório', 'Processe ao menos um arquivo antes de exportar.'); return
        path, _ = QFileDialog.getSaveFileName(self, 'Salvar relatório', 'LynowCut-relatorio.csv', 'CSV (*.csv)')
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';'); writer.writerow(['Arquivo', 'Saída', 'Bytes original', 'Bytes resultado', 'Bytes meta', 'Status', 'Observação'])
                for item in items: writer.writerow([item.source, item.output or '', item.before, item.after, item.target, item.status, item.note])
            self.status.setText('RELATÓRIO CSV SALVO')
        except OSError as error: QMessageBox.critical(self, 'Relatório', str(error))

    def show_formats(self):
        dialog = QDialog(self); dialog.setWindowTitle('Formatos e exemplos de saída'); dialog.resize(760, 560); dialog.setObjectName('dialog'); box = QVBoxLayout(dialog)
        box.addWidget(self.label('Escolha a saída certa para cada arquivo.', 'dialogTitle'))
        data = [('Fotos para internet', 'JPG/PNG/HEIC → WebP ou AVIF · menor peso para sites e WhatsApp'), ('Fotos para compartilhar', 'PNG/WebP → JPEG · compatível com qualquer celular'), ('Documentos leves', 'DOCX, PPTX, XLSX, ODT e EPUB → mesmo formato, com imagens internas otimizadas'), ('PDF para enviar', 'PDF → PDF otimizado, mantendo texto pesquisável'), ('Vídeo leve', 'MOV/MKV/AVI/WMV → MP4 H.264/AAC'), ('Áudio separado', 'MP4/MOV/AVI/WAV/FLAC → MP3'), ('Arquivo organizado', 'Qualquer arquivo → ZIP sem perdas')]
        for title, body in data:
            card = QFrame(); card.setObjectName('formatCard'); row = QVBoxLayout(card); row.addWidget(self.label(title, 'formatTitle')); row.addWidget(self.label(body, 'formatText')); box.addWidget(card)
        dialog.exec()

    def check_ffmpeg(self):
        try: binary('ffmpeg'); binary('ffprobe'); self.media.setText('●  Áudio e vídeo prontos'); self.media.setProperty('ready', True)
        except RuntimeError: self.media.setText('↓  Instalar áudio e vídeo')
        self.media.style().unpolish(self.media); self.media.style().polish(self.media)

    def install_ffmpeg(self):
        try: binary('ffmpeg'); binary('ffprobe'); QMessageBox.information(self, 'Recursos de mídia', 'Tudo já está pronto.'); return
        except RuntimeError: pass
        if QMessageBox.question(self, 'Ativar áudio e vídeo', 'Baixar aproximadamente 110 MB? Os arquivos ficam somente na pasta do LynowCut.') != QMessageBox.StandardButton.Yes: return
        self.media.setText('Baixando recursos…'); self.media.setEnabled(False); threading.Thread(target=self._install_ffmpeg_worker, daemon=True).start()

    def _install_ffmpeg_worker(self):
        try:
            root = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]; target = root / 'bin'; target.mkdir(parents=True, exist_ok=True)
            url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
            with tempfile.TemporaryDirectory(prefix='lynowcut-ffmpeg-') as temp:
                archive = Path(temp) / 'ffmpeg.zip'; urllib.request.urlretrieve(url, archive); expected = urllib.request.urlopen(url + '.sha256', timeout=30).read().decode('ascii').split()[0]
                digest = hashlib.sha256()
                with archive.open('rb') as downloaded:
                    while chunk := downloaded.read(1024 * 1024): digest.update(chunk)
                if digest.hexdigest() != expected: raise RuntimeError('A verificação de segurança do download falhou.')
                with zipfile.ZipFile(archive) as package:
                    files = {Path(member).name.lower(): member for member in package.namelist() if Path(member).name.lower() in {'ffmpeg.exe', 'ffprobe.exe'} and '/bin/' in member.replace('\\', '/').lower()}
                    if len(files) != 2: raise RuntimeError('Pacote de mídia inválido.')
                    for name, member in files.items():
                        with package.open(member) as source, (target / name).open('wb') as output: shutil.copyfileobj(source, output)
            self.events.put(('ffmpeg_installed',))
        except Exception as error: self.events.put(('ffmpeg_error', str(error)))

    def closeEvent(self, event):
        if self.busy: self.closing = True; self.stop(); event.ignore()
        else: event.accept()


STYLE = f'''
* {{ font-family: Inter, "Segoe UI"; color: {INK}; }}
QWidget#root, QWidget#main {{ background: {CREAM}; }}
QFrame#sidebar {{ background: {INK}; }}
QLabel#sideEyebrow {{ color: #AAA294; font-size: 10px; font-weight: 700; letter-spacing: 1px; }}
QLabel#logo {{ background: #DB4A1D; border-radius: 20px; }}
QLabel#brand {{ color: #FFF8EA; font-size: 29px; font-weight: 800; margin-top: 7px; }}
QLabel#tagline {{ color: #F17A4B; font-size: 10px; font-weight: 800; letter-spacing: 1px; }}
QPushButton {{ border: 0; font-weight: 650; padding: 9px 13px; }}
QPushButton[class="nav"] {{ background: transparent; color: #F9F1E4; text-align: left; border-radius: 14px; font-size: 12px; }}
QPushButton[class="nav"]:hover {{ background: {INK_2}; }} QPushButton[class="nav"]:checked {{ background: {ORANGE}; }}
QPushButton[class="sideQuiet"] {{ color: #C1B7A8; background: transparent; text-align: left; }}
QPushButton[class="media"] {{ color: #F39A70; background: {INK_2}; text-align: left; border-radius: 11px; }} QPushButton[class="media"][ready="true"] {{ color: #8BDA9E; }}
QLabel#privacy {{ color: #817A70; font-size: 9px; font-weight: 700; margin: 7px; }}
QLabel#eyebrow {{ color: {ORANGE}; font-size: 10px; font-weight: 800; letter-spacing: 1px; }}
QLabel#title {{ color: {INK}; font-size: 31px; font-weight: 800; line-height: 1.12; }} QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QFrame#savedPill {{ background: {INK}; border-radius: 20px; }} QLabel#savedValue {{ color: #FFF8EA; font-size: 23px; font-weight: 800; }} QLabel#savedLabel {{ color: #F17A4B; font-size: 9px; font-weight: 800; }}
QFrame#dropzone {{ background: {ORANGE}; border-radius: 20px; }} QFrame#dropzone[dragging="true"] {{ background: {ORANGE_DARK}; }} QLabel#plus {{ color: {ORANGE}; background: #FFF8EC; border-radius: 26px; font-size: 28px; font-weight: 500; min-width: 52px; min-height: 52px; }} QLabel#dropTitle {{ color: white; font-size: 15px; font-weight: 750; }} QLabel#dropSubtitle {{ color: #FFE4D1; font-size: 10px; }} QLabel#dropCount {{ color: #FFE4D1; font-size: 10px; font-weight: 800; }}
QLabel#sectionTitle {{ font-size: 16px; font-weight: 800; }} QScrollArea#queue {{ background: {PAPER}; border: 0; border-radius: 18px; }} QScrollArea#queue > QWidget > QWidget {{ background: {PAPER}; }} QLabel#empty {{ color: #A59989; font-size: 13px; padding: 44px; }}
QFrame#fileCard {{ background: #F9EEDC; border: 1px solid transparent; border-radius: 14px; }} QFrame#fileCard[selected="true"] {{ border: 2px solid {ORANGE}; }} QFrame#fileCard[state="concluído"] {{ background: #E5F2E7; }} QFrame#fileCard[state="erro"] {{ background: #F9E1DB; }}
QLabel#fileIcon {{ background: {PAPER_2}; color: {ORANGE}; border-radius: 10px; font-size: 9px; font-weight: 800; }} QLabel#fileName {{ font-size: 11px; font-weight: 750; }} QLabel#fileMeta {{ color: {MUTED}; font-size: 10px; }} QLabel#badge {{ color: {MUTED}; background: {PAPER_2}; border-radius: 11px; font-size: 9px; font-weight: 800; padding: 7px; }}
QFrame#controls {{ background: {PAPER}; border-radius: 18px; }} QLabel#controlLabel {{ color: {MUTED}; font-size: 9px; font-weight: 800; letter-spacing: .8px; }} QPushButton[class="chip"] {{ background: {PAPER_2}; color: {INK}; border-radius: 9px; min-height: 18px; }} QPushButton[class="chip"]:checked {{ background: {ORANGE}; color: white; }}
QLabel#targetText {{ font-size: 10px; font-weight: 800; }} QSlider#slider::groove:horizontal {{ background: {PAPER_2}; height: 5px; border-radius: 2px; }} QSlider#slider::sub-page:horizontal {{ background: {ORANGE}; border-radius: 2px; }} QSlider#slider::handle:horizontal {{ background: {ORANGE}; width: 16px; margin: -6px 0; border-radius: 8px; }} QLineEdit#number, QLineEdit#input {{ background: {PAPER_2}; border: 0; border-radius: 9px; padding: 8px; }} QLabel#unit {{ color: {MUTED}; font-size: 9px; font-weight: 800; }}
QPushButton[class="toggle"] {{ background: transparent; color: {MUTED}; padding: 6px 0; }} QPushButton[class="toggle"]:checked {{ color: {ORANGE}; }} QPushButton[class="destination"] {{ background: {PAPER_2}; border-radius: 9px; color: {INK}; }} QLabel#examplesLabel {{ color: {MUTED}; font-size: 9px; font-weight: 800; }} QFrame#exampleCard {{ background: #F9EEDC; border-radius: 9px; }} QLabel#exampleBadge {{ color: {ORANGE}; background: #F2DDC7; border-radius: 6px; font-size: 8px; font-weight: 800; padding: 4px; }} QLabel#exampleTitle {{ font-size: 9px; font-weight: 750; }} QLabel#exampleNote {{ color: {MUTED}; font-size: 8px; }}
QPushButton[class="primary"] {{ background: {ORANGE}; color: white; border-radius: 14px; padding: 12px 17px; }} QPushButton[class="primary"]:hover {{ background: {ORANGE_DARK}; }} QPushButton[class="secondary"] {{ background: {PAPER_2}; color: {MUTED}; border-radius: 12px; }} QPushButton[class="quiet"] {{ background: transparent; color: {MUTED}; }} QPushButton[class="quiet"]:hover {{ background: {PAPER_2}; border-radius: 9px; }} QPushButton:disabled {{ color: #B9AA98; background: #EEE2D0; }} QLabel#status {{ color: {MUTED}; font-size: 9px; font-weight: 800; }}
QDialog {{ background: {CREAM}; }} QLabel#dialogTitle {{ font-size: 23px; font-weight: 800; }} QLabel#dialogText, QLabel#formatText {{ color: {MUTED}; font-size: 11px; }} QFrame#formatCard {{ background: {PAPER}; border-radius: 12px; padding: 4px; }} QLabel#formatTitle {{ color: {ORANGE}; font-size: 11px; font-weight: 800; }} QLabel#preview {{ background: {PAPER}; border-radius: 16px; }}
'''


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    font_id = QFontDatabase.addApplicationFont(str(resource('assets/fonts/Inter.ttf')))
    family = QFontDatabase.applicationFontFamilies(font_id)[0] if font_id >= 0 else 'Segoe UI'
    app.setFont(QFont(family, 10)); app.setStyleSheet(STYLE)
    window = MainWindow(); window.show(); app.exec()
