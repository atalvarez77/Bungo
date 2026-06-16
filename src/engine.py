import sys

from sudachipy import dictionary, tokenizer
import pykakasi
import sqlite3
import os

from rules import GrammarRuleEngine

class DictionaryService:
    def __init__(self):
        # Determine the base path based on whether we are frozen (packaged) or not
        if getattr(sys, 'frozen', False):
            # If running as an executable, the data folder is extracted here:
            base_path = sys._MEIPASS
        else:
            # If running as a script, go up one level from src/ to the root
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.db_path = os.path.join(base_path, 'data', 'bungo_dictionary.db')

    def get_definition(self, word, pos_tags):
        # Standard Dictionary Lookup
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = """
        SELECT s.definition FROM entries e 
        JOIN senses s ON e.id = s.entry_id 
        WHERE e.kanji = ? OR e.kana = ? 
        ORDER BY LENGTH(s.definition) ASC LIMIT 1
        """
        cursor.execute(query, (word, word))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else "Definition not found."
    
    def get_kanji_details(self, word):
        """
        Takes a word, extracts only the Kanji characters, and fetches their metadata.
        Returns a list of dictionaries.
        """
        # 1. Use regex to extract ONLY Kanji characters from the word (ignores kana)
        import re
        kanji_chars = re.findall(r'[\u4e00-\u9faf]', word)
        
        if not kanji_chars:
            return [] # No Kanji in this word

        results = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for kanji in kanji_chars:
            cursor.execute('''
                SELECT onyomi, kunyomi, meaning 
                FROM kanji_meta 
                WHERE kanji = ?
            ''', (kanji,))
            
            row = cursor.fetchone()
            if row:
                results.append({
                    'kanji': kanji,
                    'onyomi': row[0] or "-",
                    'kunyomi': row[1] or "-",
                    'meaning': row[2] or "Unknown"
                })
                
        conn.close()
        return results

class BungoEngine:
    def __init__(self):
        self.tokenizer_obj = dictionary.Dictionary().create()
        self.kks = pykakasi.kakasi()
        self.mode = tokenizer.Tokenizer.SplitMode.C
        self.dict_service = DictionaryService()

    def get_romaji(self, text):
        result = self.kks.convert(text)
        return "".join([item['hepburn'] for item in result])

    def parse_sentence(self, text):
        tokens = self.tokenizer_obj.tokenize(text, self.mode)
        results = []
        rule_engine = GrammarRuleEngine()
        
        for i, token in enumerate(tokens):
            context = {
                'tokens': tokens,
                'index': i
            }
            
            word = token.surface()
            base_form = token.dictionary_form()
            pos = token.part_of_speech()
            definition = None
            romaji = None
            
            # Attempt rule-based definition first for particles
            if '助詞' in pos:
                definition = rule_engine.get_explanation(token, context)
                romaji = rule_engine.get_romaji_override(token, context)
            # Verb-Math Rules for auxiliary verb suffixes
            elif '助動詞' in pos:
                definition = rule_engine.get_auxiliary_explanation(token, context)
                romaji = self.get_romaji(word)
            # Punctuation Handling
            elif word in rule_engine.punctuation_registry:
                definition = rule_engine.punctuation_registry[word]
                romaji = word

            # If no rule found (not a particle, aux verb, or punctuation), 
            # fall back to dictionary database and romaji conversion
            if not definition:
                definition = self.dict_service.get_definition(base_form, pos)
            if not romaji:
                romaji = self.get_romaji(word)
                
            results.append({
                "word": word,
                "romaji": romaji,
                "pos": pos,
                "definition": definition,
                "kanji_data": self.dict_service.get_kanji_details(base_form)
            })
        return results
    
    

# Verification
if __name__ == "__main__":
    engine = BungoEngine()
    sentence = "昨日、千円しかないから、私さえ駅から図書館まで道を歩きましたよ。図書館へ行くと、明日の試験があると先生が言いましたね。だから、五分で終わる本こそ読みたかったが、彼には少し難しいか。"
    data = engine.parse_sentence(sentence)
    for item in data:
        print(f"Word: {item['word']} | Romaji: {item['romaji']} | Def: {item['definition']}")

""" TEST SENTENCES
1. 食べませんでした"
2. 彼は学校に行きます。
3. 私は図書館で勉強しますが、明日には試験があります。
4. 空を飛ぶ
5. 先生にその難しい質問を聞く。
5. 公園を歩くのが好きだと、彼も言いました。
6. 昨日、千円しかないから、私さえ駅から図書館まで道を歩きましたよ。図書館へ行くと、明日の試験があると先生が言いましたね。だから、五分で終わる本こそ読みたかったが、彼には少し難しいか。

"""