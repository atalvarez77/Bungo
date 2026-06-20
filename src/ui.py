import sys
import os
import json
import romkan
import re
import pykakasi.kanji
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, 
                             QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QCheckBox, QFrame, QScrollArea, 
                             QLayout, QDockWidget, QListWidget)
from PyQt6.QtCore import Qt, QTimer, QRect, QSize, QPoint
from PyQt6.QtGui import QPainter, QColor

if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    pykakasi.kanji.DEFAULT_KANWADICT = os.path.join(bundle_dir, 'pykakasi', 'data', 'kanwadict4.db')

base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from engine import BungoEngine
except ImportError:
    # Fallback for packaged environment
    sys.path.append(os.path.join(base_dir, 'src'))
    from engine import BungoEngine

# --- THEME CONSTANTS ---
BG_COLOR = "#18181A"         
PANEL_COLOR = "#222226"      
ACCENT_COLOR = "#E8AD5A"     
ACCENT_HOVER = "#F5C37A"     
TEXT_MAIN = "#F2F2F2"        

# Grammar Color Key
POS_COLORS = {
    '助動詞': '#B39DDB',  
    '動詞': '#4DA8DA',    
    '助詞': '#E8AD5A',    
    '名詞': '#EE6C4D',    
    '代名詞': '#EE6C4D',  
    '形容詞': '#81C784',  
    '形状詞': '#81C784',  
}

POS_TRANSLATOR = {
    '名詞': 'Noun', '代名詞': 'Pronoun', '動詞': 'Verb', '形容詞': 'Adjective',
    '形状詞': 'Na-Adjective', '副詞': 'Adverb', '助詞': 'Particle', 
    '助動詞': 'Aux/Copula', '連体詞': 'Pre-noun Adj', '接続詞': 'Conjunction', 
    '感動詞': 'Interjection', '記号': 'Punctuation', '補助記号': 'Punctuation', 
    '空白': 'Whitespace', '接尾辞': 'Suffix', '接頭辞': 'Prefix'
}

HISTORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'history.json'))

# --- STYLESHEET ---
GLOBAL_STYLE = f"""
    QMainWindow, QScrollArea, QStackedWidget {{ background-color: {BG_COLOR}; border: none; }}
    QWidget {{ background-color: {BG_COLOR}; color: {TEXT_MAIN}; font-family: system-ui, sans-serif; }}
    
    QPushButton.primary {{
        background-color: {ACCENT_COLOR}; color: #121212;
        border-radius: 20px; border: 1px solid {ACCENT_COLOR}; 
        font-weight: bold; font-size: 16px; padding: 10px 20px;
    }}
    QPushButton.primary:hover {{ background-color: {ACCENT_HOVER}; border: 1px solid {ACCENT_HOVER}; }}
    
    QPushButton.icon {{
        background-color: transparent; color: {TEXT_MAIN};
        border-radius: 15px; border: 1px solid #444;
        font-size: 18px; padding: 5px 10px;
    }}
    QPushButton.icon:hover {{ background-color: #333; border: 1px solid {ACCENT_COLOR}; color: {ACCENT_COLOR}; }}
    
    QTextEdit {{
        background-color: {PANEL_COLOR}; border: 2px solid #333;
        border-radius: 10px; padding: 15px; font-size: 24px; color: {TEXT_MAIN};
    }}
    QTextEdit:focus {{ border: 2px solid {ACCENT_COLOR}; }}
    
    QCheckBox {{ font-size: 14px; font-weight: bold; color: #AAA; }}
    QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 2px solid #555; }}
    QCheckBox::indicator:checked {{ background-color: {ACCENT_COLOR}; border: 2px solid {ACCENT_COLOR}; }}
    
    QFrame#InfoPopup {{
        background-color: {PANEL_COLOR}; border: 1px solid {ACCENT_COLOR};
        border-radius: 8px; padding: 15px;
    }}
    
    QListWidget {{
        background-color: {PANEL_COLOR}; border: none; color: {TEXT_MAIN};
        font-size: 16px; padding: 10px;
    }}
    QListWidget::item {{ padding: 10px; border-bottom: 1px solid #333; }}
    QListWidget::item:hover {{ background-color: #333; }}
"""

def format_definition_to_html(raw_definition):
    if not raw_definition or raw_definition == "Definition not found.":
        return "<span style='color: #8A8A8E; font-style: italic;'>Definition not found.</span>"

    senses = [sense.strip() for sense in raw_definition.split('|')]
    formatted_senses = []
    
    for i, sense in enumerate(senses):
        # Format Context Badges [...] -> Accent Color, Bold
        sense = re.sub(
            r'\[(.*?)\]', 
            f'<span style="color: {ACCENT_COLOR}; font-weight: bold; font-size: 13px;">[\\1]</span>', 
            sense
        )
        # Format Nuance Notes (...) -> Gray, Italic
        sense = re.sub(
            r'\((.*?)\)', 
            r'<span style="color: #8A8A8E; font-style: italic;">(\1)</span>', 
            sense
        )
        # Number list if multiple definitions exist
        if len(senses) > 1:
            formatted_senses.append(f"<span style='color: #8A8A8E; font-weight: bold;'>{i+1}.</span> {sense}")
        else:
            formatted_senses.append(sense)

    return "<br><br>".join(formatted_senses)

class CenteredFlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=10):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item): self.itemList.append(item)
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index): return self.itemList.pop(index) if 0 <= index < len(self.itemList) else None
    def expandingDirections(self): return Qt.Orientation.Horizontal
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self.doLayout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList: size = size.expandedTo(item.minimumSize())
        return size + QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())

    def doLayout(self, rect, testOnly):
        x, y, lineHeight = rect.x(), rect.y(), 0
        rows, current_row, row_width = [], [], 0

        for item in self.itemList:
            spaceX, spaceY = self.spacing(), self.spacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                rows.append((current_row, row_width - spaceX, lineHeight))
                x, y, lineHeight = rect.x(), y + lineHeight + spaceY, 0
                nextX = x + item.sizeHint().width() + spaceX
                current_row, row_width = [], 0
            current_row.append(item)
            row_width += item.sizeHint().width() + spaceX
            x, lineHeight = nextX, max(lineHeight, item.sizeHint().height())
        if current_row: rows.append((current_row, row_width - spaceX, lineHeight))

        y = rect.y()
        for row, r_width, r_height in rows:
            offset_x = rect.x() + (rect.width() - r_width) // 2
            x = offset_x
            for item in row:
                if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                x += item.sizeHint().width() + self.spacing()
            y += r_height + self.spacing()
        return y - rect.y()

class LoadingOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        layout = QVBoxLayout(self)
        self.label = QLabel("Initializing Engine...", self)
        self.label.setStyleSheet(f"color: {ACCENT_COLOR}; font-size: 20px; font-weight: bold; background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.messages = ["Slicing Tokens...", "Applying Verb Math...", "Querying JMdict...", "Parsing Kanji..."]
        self.msg_idx = 0
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_text)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(10, 10, 12, 220))

    def start(self):
        self.msg_idx = 0; self.label.setText(self.messages[0]); self.show(); self.raise_(); self.timer.start(350)

    def stop(self): self.timer.stop(); self.hide()
    def update_text(self): self.msg_idx = (self.msg_idx + 1) % len(self.messages); self.label.setText(self.messages[self.msg_idx])

class TokenBlock(QFrame):
    def __init__(self, data, popup_callback):
        super().__init__()
        self.data = data
        self.popup_callback = popup_callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        pos_tuple = data['pos'] if isinstance(data['pos'], (list, tuple)) else [data['pos']]
        self.color = "#888888" 
        for key_pos, col in POS_COLORS.items():
            if any(key_pos in p for p in pos_tuple):
                self.color = col
                break

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 2)
        layout.setSpacing(2)
        
        self.lbl_word = QLabel(data['word'])
        self.lbl_word.setStyleSheet("font-size: 22px; font-weight: bold; color: white; background: transparent;")
        self.lbl_word.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_romaji = QLabel(data['romaji'])
        self.lbl_romaji.setStyleSheet("font-size: 12px; color: #999; background: transparent;")
        self.lbl_romaji.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lbl_word)
        layout.addWidget(self.lbl_romaji)
        self.setLayout(layout)
        
        self.setStyleSheet(f"""
            TokenBlock {{ background-color: {PANEL_COLOR}; border-bottom: 3px solid {self.color}; border-radius: 4px; }}
            TokenBlock:hover {{ background-color: #333333; border-bottom: 5px solid {self.color}; }}
        """)

    def mousePressEvent(self, event):
        self.popup_callback(self.data, self.color)

class InputScreen(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50) 

        top_bar = QHBoxLayout()
        title = QLabel("Bungo (文語)")
        title.setStyleSheet("font-size: 28px; font-weight: 900; color: #FFFFFF;")
        
        self.app.furigana_toggle.setParent(self) 
        btn_history = QPushButton("🕒 History")
        btn_history.setProperty("class", "icon")
        btn_history.clicked.connect(self.app.toggle_history)

        top_bar.addWidget(title); top_bar.addStretch()
        top_bar.addWidget(self.app.furigana_toggle)
        top_bar.addWidget(btn_history)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter Japanese, Kana, or Romaji (e.g., watashi wa)...")
        self.text_input.setFixedHeight(200) 

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 14px;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter); self.error_label.hide()

        self.btn_translate = QPushButton("Translate!")
        self.btn_translate.setProperty("class", "primary")
        self.btn_translate.setFixedWidth(200)
        self.btn_translate.clicked.connect(self.handle_click)
        
        btn_layout = QHBoxLayout(); btn_layout.addWidget(self.btn_translate)

        layout.addLayout(top_bar); layout.addSpacing(20)
        layout.addWidget(self.text_input); layout.addSpacing(10)
        layout.addWidget(self.error_label); layout.addLayout(btn_layout)
        self.setLayout(layout)

    def handle_click(self):
        raw_text = self.text_input.toPlainText().strip()
        if not raw_text:
            self.error_label.setText("Please enter some text to begin."); self.error_label.show()
            return
        self.error_label.hide() 
        processed_text = romkan.to_hiragana(raw_text).replace(" ", "").replace(" ", "")
        if raw_text != processed_text: self.text_input.setPlainText(processed_text)
        self.app.process_text(processed_text)

class ParseScreen(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.app = parent_app
        self.current_popup = None
        self.furigana_labels = [] 
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        self.main_layout = QVBoxLayout(content_widget)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.setContentsMargins(40, 20, 40, 40)
        scroll.setWidget(content_widget)
        
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.addWidget(scroll)

        top_bar = QHBoxLayout()
        btn_edit = QPushButton("✏️ Edit")
        btn_edit.setProperty("class", "icon"); btn_edit.clicked.connect(self.app.show_input_screen)
        btn_new = QPushButton("🔄 New")
        btn_new.setProperty("class", "icon"); btn_new.clicked.connect(self.handle_new)
        btn_history = QPushButton("🕒 History")
        btn_history.setProperty("class", "icon"); btn_history.clicked.connect(self.app.toggle_history)
        
        top_bar.addWidget(btn_edit); top_bar.addWidget(btn_new); top_bar.addStretch()
        self.toggle_container = QVBoxLayout() 
        top_bar.addLayout(self.toggle_container)
        top_bar.addWidget(btn_history)
        self.main_layout.addLayout(top_bar)
        
        self.sentence_container = QWidget()
        self.sentence_layout = CenteredFlowLayout(self.sentence_container, spacing=2)
        self.main_layout.addSpacing(20)
        self.main_layout.addWidget(self.sentence_container)
        
        key_layout = QHBoxLayout()
        key_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for label, color in [("Verb", "#4DA8DA"), ("Particle", "#E8AD5A"), ("Noun", "#EE6C4D"), ("Adj", "#81C784"), ("Aux/Copula", "#B39DDB")]:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; margin: 0px 10px;")
            key_layout.addWidget(lbl)
        self.main_layout.addSpacing(10)
        self.main_layout.addLayout(key_layout)

        blocks_container = QWidget()
        self.flow_layout = CenteredFlowLayout(blocks_container)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(blocks_container)
        
        self.info_panel = QFrame()
        self.info_panel.setObjectName("InfoPopup")
        self.info_layout = QVBoxLayout(self.info_panel)
        
        # Word info section
        self.lbl_info_word = QLabel()
        self.lbl_info_def = QLabel()
        self.lbl_info_pos = QLabel()
        self.lbl_info_word.setStyleSheet("font-size: 24px; font-weight: bold; background: transparent;")
        self.lbl_info_def.setStyleSheet("font-size: 16px; color: white; background: transparent;")
        self.lbl_info_def.setWordWrap(True)
        self.lbl_info_pos.setStyleSheet(f"font-size: 14px; color: {ACCENT_COLOR}; font-style: italic; font-weight: bold; background: transparent;")
        
        self.info_layout.addWidget(self.lbl_info_word)
        self.info_layout.addWidget(self.lbl_info_pos)
        self.info_layout.addWidget(self.lbl_info_def)
        
        # New Kanji Breakdown Container
        self.kanji_container = QWidget()
        self.kanji_container.setStyleSheet("background: transparent;")
        self.kanji_layout = QVBoxLayout(self.kanji_container)
        self.kanji_layout.setContentsMargins(0, 10, 0, 0)
        self.info_layout.addWidget(self.kanji_container)
        
        self.info_panel.hide()
        self.main_layout.addWidget(self.info_panel)

        self.lbl_literal = QLabel()
        self.lbl_literal.setStyleSheet("font-size: 18px; color: #FFF; line-height: 1.5;")
        self.lbl_literal.setWordWrap(True)
        self.lbl_literal.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addSpacing(30)
        self.main_layout.addWidget(self.lbl_literal)
        self.main_layout.addStretch()

    def handle_new(self):
        self.app.input_screen.text_input.clear()
        self.app.show_input_screen()

    def toggle_furigana_view(self, is_checked):
        for lbl in self.furigana_labels: lbl.setVisible(is_checked)

    def build_ui(self, parsed_data):
        for i in reversed(range(self.sentence_layout.count())): 
            self.sentence_layout.itemAt(i).widget().setParent(None)
        for i in reversed(range(self.flow_layout.count())): 
            self.flow_layout.itemAt(i).widget().setParent(None)
            
        self.info_panel.hide(); self.current_popup = None; self.furigana_labels.clear()
        
        literal_parts = []
        show_furigana = self.app.furigana_toggle.isChecked()

        for data in parsed_data:
            word = data['word']
            pos_tuple = data['pos'] if isinstance(data['pos'], (list, tuple)) else [data['pos']]
            
            word_widget = QWidget()
            vbox = QVBoxLayout(word_widget)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)
            vbox.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
            
            lbl_kanji = QLabel(word)
            lbl_kanji.setStyleSheet("font-size: 32px; color: white; background: transparent;")
            lbl_kanji.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl_kana = QLabel("")
            lbl_kana.setStyleSheet(f"font-size: 14px; color: {ACCENT_COLOR}; background: transparent; font-weight: bold;")
            lbl_kana.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if re.search(r'[\u4e00-\u9faf]', word):
                lbl_kana.setText(romkan.to_hiragana(data['romaji']))
                self.furigana_labels.append(lbl_kana)
                lbl_kana.setVisible(show_furigana)
            else:
                lbl_kana.setVisible(False) 
                
            vbox.addWidget(lbl_kana)
            vbox.addWidget(lbl_kanji)
            self.sentence_layout.addWidget(word_widget)

            block = TokenBlock(data, self.toggle_info_popup)
            self.flow_layout.addWidget(block)
            
            full_def = data['definition'] or "Unknown"
            is_grammar = any(p in pos_tuple for p in ['助詞', '助動詞'])
            is_punct = any(p in pos_tuple for p in ['記号', '補助記号'])
            
            if is_punct:
                literal_parts.append(word)
            else:
                # 1. Isolate ONLY the first definition before the '|' separator
                first_sense = full_def.split('|')[0].strip()
                
                if is_grammar:
                    # Look for our new [...] context badges first
                    match = re.match(r'\[(.*?)\]', first_sense)
                    if match:
                        # Extract text inside brackets, removing extra info like "(Casual)"
                        short_def = match.group(1).split('(')[0].strip()
                    else:
                        # Fallback for old colon-based rules (e.g., "Topic marker: ...")
                        short_def = first_sense.split(':')[0].split('(')[0].strip()
                        
                    literal_parts.append(f"({short_def})")
                else:
                    # For normal words, use Regex to strip out all [...] and (...) context notes
                    clean_def = re.sub(r'\[.*?\]', '', first_sense)
                    clean_def = re.sub(r'\(.*?\)', '', clean_def)
                    
                    # Take only the very first English word/phrase before a comma
                    short_def = clean_def.split(',')[0].strip()
                    literal_parts.append(short_def.capitalize())

        # Combine into the final literal sentence string
        raw_literal = " ".join(literal_parts)
        raw_literal = re.sub(r'\s+([。、！？.!,?])', r'\1', raw_literal)
        raw_literal = re.sub(r"\s+'s", "'s", raw_literal) 
        self.lbl_literal.setText(f'"{raw_literal}"')

    def toggle_info_popup(self, data, color):
        if self.current_popup == data['word'] and not self.info_panel.isHidden():
            self.info_panel.hide(); return
            
        self.current_popup = data['word']
        self.info_panel.setStyleSheet(f"QFrame#InfoPopup {{ background-color: {PANEL_COLOR}; border: 1px solid {color}; border-radius: 8px; padding: 15px; }}")
        
        pos_list = data['pos'] if isinstance(data['pos'], (list, tuple)) else [data['pos']]
        english_pos = []
        for p in pos_list:
            if p in POS_TRANSLATOR:
                english_pos.append(POS_TRANSLATOR[p])
        pos_display = " - ".join(english_pos) if english_pos else " - ".join(pos_list)
        
        self.lbl_info_word.setText(f"{data['word']}  <span style='color:#888; font-size:16px;'>[{data['romaji']}]</span>")
        self.lbl_info_pos.setText(pos_display)
        
        if any(p in pos_list for p in ['記号', '補助記号']):
            self.lbl_info_def.setText("Punctuation")
        else:
            raw_def = data['definition']
            rich_def = format_definition_to_html(raw_def)
            
            self.lbl_info_def.setTextFormat(Qt.TextFormat.RichText)
            self.lbl_info_def.setText(rich_def)
            
        # --- DYNAMIC KANJI BREAKDOWN ---
        for i in reversed(range(self.kanji_layout.count())):
            self.kanji_layout.itemAt(i).widget().setParent(None)
            
        if 'kanji_data' in data and data['kanji_data']:
            for k_data in data['kanji_data']:
                lbl_kanji_row = QLabel(
                    f"<b style='font-size: 20px; color: {ACCENT_COLOR};'>{k_data['kanji']}</b> : {k_data['meaning']}<br>"
                    f"<span style='font-size: 12px; color: #aaa;'><b>On:</b> {k_data['onyomi']} | <b>Kun:</b> {k_data['kunyomi']}</span>"
                )
                lbl_kanji_row.setStyleSheet("background: transparent; color: white; padding-top: 10px; border-top: 1px solid #444;")
                lbl_kanji_row.setWordWrap(True)
                self.kanji_layout.addWidget(lbl_kanji_row)
                
        self.info_panel.show()

class BungoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bungo (文語)")
        self.resize(900, 650) 
        self.engine = BungoEngine()

        self.furigana_toggle = QCheckBox("Furigana")
        self.furigana_toggle.setChecked(True)
        self.furigana_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.furigana_toggle.toggled.connect(self.handle_furigana_toggle)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.input_screen = InputScreen(self)
        self.parse_screen = ParseScreen(self)

        self.stack.addWidget(self.input_screen)
        self.stack.addWidget(self.parse_screen)

        self.overlay = LoadingOverlay(self)
        
        self.history_dock = QDockWidget("Translation History", self)
        self.history_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.load_history_item)
        self.history_dock.setWidget(self.history_list)
        self.history_dock.setStyleSheet(f"""
            QDockWidget {{ color: {ACCENT_COLOR}; font-weight: bold; font-size: 14px; }}
            QDockWidget::title {{ background: {PANEL_COLOR}; padding-left: 10px; padding-top: 5px; }}
        """)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
        self.history_dock.hide()
        
        self.load_history()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay'): self.overlay.resize(self.size())

    def toggle_history(self):
        self.history_dock.setVisible(not self.history_dock.isVisible())

    def load_history_item(self, item):
        self.process_text(item.text(), add_to_history=False)

    def handle_furigana_toggle(self, is_checked):
        self.parse_screen.toggle_furigana_view(is_checked)

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    saved_history = json.load(f)
                    for item in saved_history:
                        self.history_list.addItem(item)
            except Exception as e:
                print(f"Could not load history: {e}")

    def save_history(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        history_items = [self.history_list.item(i).text() for i in range(self.history_list.count())]
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_items, f, ensure_ascii=False, indent=2)

    def process_text(self, text, add_to_history=True):
        if add_to_history:
            existing_items = self.history_list.findItems(text, Qt.MatchFlag.MatchExactly)
            for item in existing_items:
                self.history_list.takeItem(self.history_list.row(item))
            self.history_list.insertItem(0, text)
            if self.history_list.count() > 50:
                self.history_list.takeItem(50)
            self.save_history()
            
        self.overlay.start()
        QTimer.singleShot(100, lambda: self.execute_engine(text))

    def execute_engine(self, text):
        parsed_data = self.engine.parse_sentence(text)
        self.parse_screen.build_ui(parsed_data)
        QTimer.singleShot(800, self.finish_processing)

    def finish_processing(self):
        self.overlay.stop()
        self.parse_screen.toggle_container.addWidget(self.furigana_toggle) 
        self.stack.setCurrentIndex(1)

    def show_input_screen(self):
        self.input_screen.layout().itemAt(0).layout().insertWidget(2, self.furigana_toggle) 
        self.stack.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_STYLE)
    window = BungoApp()
    window.show()
    sys.exit(app.exec())