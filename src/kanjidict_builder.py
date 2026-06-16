# src/kanjidict_builder.py
import sqlite3
import xml.etree.ElementTree as ET
import os

# Paths (Adjust if your structure is different)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'bungo_dictionary.db')
XML_PATH = os.path.join(BASE_DIR, 'data', 'raw', 'kanjidic2.xml')

def build_kanji_table():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create the new Kanji table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS kanji_meta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kanji TEXT UNIQUE,
        onyomi TEXT,
        kunyomi TEXT,
        meaning TEXT
    )
    ''')
    
    # Clear existing data if you run the script multiple times
    cursor.execute('DELETE FROM kanji_meta')

    print(f"Parsing {XML_PATH} (This may take a few seconds)...")
    
    context = ET.iterparse(XML_PATH, events=('end',))
    count = 0
    
    for event, elem in context:
        if elem.tag == 'character':
            literal = elem.findtext('literal')
            
            onyomi_list = []
            kunyomi_list = []
            meaning_list = []
            
            rmgroup = elem.find('.//rmgroup')
            if rmgroup is not None:
                # Extract Readings
                for reading in rmgroup.findall('reading'):
                    r_type = reading.get('r_type')
                    if r_type == 'ja_on':
                        onyomi_list.append(reading.text)
                    elif r_type == 'ja_kun':
                        kunyomi_list.append(reading.text)
                
                # Extract Meanings (Only English meanings lack the m_lang attribute in Kanjidic2)
                for meaning in rmgroup.findall('meaning'):
                    if not meaning.get('m_lang'):
                        meaning_list.append(meaning.text)
                        
            # Only insert if we have a valid Kanji with meanings
            if literal and meaning_list:
                cursor.execute('''
                INSERT OR IGNORE INTO kanji_meta (kanji, onyomi, kunyomi, meaning)
                VALUES (?, ?, ?, ?)
                ''', (
                    literal,
                    "、".join(onyomi_list), # Join with Japanese comma
                    "、".join(kunyomi_list),
                    ", ".join(meaning_list)
                ))
                count += 1
                
            # Clear element from memory to keep RAM usage incredibly low
            elem.clear()

    # Create an index for lightning-fast lookups
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_kanji ON kanji_meta(kanji)')
    
    conn.commit()
    conn.close()
    print(f"Successfully inserted {count} Kanji into the database!")

if __name__ == "__main__":
    if not os.path.exists(XML_PATH):
        print(f"Error: Could not find {XML_PATH}")
    else:
        build_kanji_table()