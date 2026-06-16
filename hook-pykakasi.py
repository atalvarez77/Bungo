import os
import sys

def get_pykakasi_data_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, 'pykakasi', 'data')
    return None

# We inject this into the pykakasi config at runtime
import pykakasi.kanji
pykakasi.kanji.DEFAULT_KANWADICT = os.path.join(get_pykakasi_data_path(), 'kanwadict4.db')