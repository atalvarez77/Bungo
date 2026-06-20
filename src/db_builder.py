import sqlite3
import os
from lxml import etree

def build_database():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xml_path = os.path.join(base_dir, 'data', 'raw', 'JMdict_e.xml')
    db_path = os.path.join(base_dir, 'data', 'bungo_dictionary.db')

    print(f"Looking for XML at: {xml_path}")

    if not os.path.exists(xml_path):
        print("Error: JMdict_e.xml not found at the expected path.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('PRAGMA synchronous = OFF')
    cursor.execute('PRAGMA journal_mode = MEMORY')
    
    # 1. Rebuild our tables with relational integrity
    cursor.execute('DROP TABLE IF EXISTS entries')
    cursor.execute('DROP TABLE IF EXISTS senses')
    cursor.execute('DROP TABLE IF EXISTS glosses')
    
    cursor.execute('CREATE TABLE entries (id INTEGER PRIMARY KEY, kanji TEXT, kana TEXT)')
    cursor.execute('CREATE TABLE senses (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER, pos TEXT, sense_info TEXT)')
    cursor.execute('CREATE TABLE glosses (sense_id INTEGER, gloss TEXT)')
    
    # Create indexes immediately to speed up Pass 3 lookups significantly
    cursor.execute('CREATE INDEX idx_entries_kanji ON entries(kanji)')
    cursor.execute('CREATE INDEX idx_entries_kana ON entries(kana)')
    cursor.execute('CREATE INDEX idx_senses_entry ON senses(entry_id)')
    cursor.execute('CREATE INDEX idx_glosses_sense ON glosses(sense_id)')
    
    print("Parsing XML into relational schema... this may take a moment.")
    
    try:
        context = etree.iterparse(xml_path, events=('end',), tag='entry')
        for event, elem in context:
            kanji = elem.findtext('.//keb')
            kana = elem.findtext('.//reb')
            
            cursor.execute('INSERT INTO entries (kanji, kana) VALUES (?, ?)', (kanji, kana))
            entry_id = cursor.lastrowid
            
            for sense in elem.findall('.//sense'):
                # Extract all <pos> tags and join them as a comma-separated string (e.g. "&pn;,&adj;")
                pos_list = [p.text for p in sense.findall('.//pos') if p.text]
                pos_str = ",".join(pos_list) if pos_list else None
                
                # Extract specific usage contextual labels
                s_inf = sense.findtext('.//s_inf')
                
                cursor.execute(
                    'INSERT INTO senses (entry_id, pos, sense_info) VALUES (?, ?, ?)', 
                    (entry_id, pos_str, s_inf)
                )
                sense_id = cursor.lastrowid
                
                # Fetch ALL english gloss meanings for this exact sense block
                for gloss_node in sense.findall('.//gloss'):
                    if gloss_node.text:
                        cursor.execute(
                            'INSERT INTO glosses (sense_id, gloss) VALUES (?, ?)', 
                            (sense_id, gloss_node.text)
                        )
            
            elem.clear()
        
        conn.commit()
        print(f"Success! Relational database created at: {db_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    build_database()