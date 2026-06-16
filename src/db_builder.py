import sqlite3
import os
from lxml import etree

def build_database():
    # Get absolute paths to ensure we know where things are
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path = os.path.join(base_dir, 'data', 'raw', 'JMdict_e.xml')
    db_path = os.path.join(base_dir, 'data', 'bungo_dictionary.db')

    print(f"Looking for XML at: {xml_path}")

    if not os.path.exists(xml_path):
        print("Error: JMdict_e.xml not found at the expected path.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable optimized PRAGMAs for faster inserts
    cursor.execute('PRAGMA synchronous = OFF')
    cursor.execute('PRAGMA journal_mode = MEMORY')
    
    cursor.execute('CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY, kanji TEXT, kana TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS senses (entry_id INTEGER, definition TEXT)')
    
    print("Parsing XML... this may take a moment.")
    
    try:
        context = etree.iterparse(xml_path, events=('end',), tag='entry')
        for event, elem in context:
            kanji = elem.findtext('.//keb')
            kana = elem.findtext('.//reb')
            
            cursor.execute('INSERT INTO entries (kanji, kana) VALUES (?, ?)', (kanji, kana))
            entry_id = cursor.lastrowid
            
            for sense in elem.findall('.//sense'):
                gloss = sense.findtext('.//gloss')
                if gloss:
                    cursor.execute('INSERT INTO senses (entry_id, definition) VALUES (?, ?)', (entry_id, gloss))
            
            elem.clear()
        
        conn.commit()
        print(f"Success! Database created at: {db_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    build_database()