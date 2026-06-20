import sys

from sudachipy import dictionary, tokenizer
import pykakasi
import sqlite3
import os

from rules import GrammarRuleEngine

class DictionaryService:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.db_path = os.path.join(base_path, 'data', 'bungo_dictionary.db')

    def get_contextual_definition(self, word, base_kana, pos_tags, sentence_context):
        """
        Fetches all senses for a word and scores them based on phonetic matching, 
        Sudachi POS tags, and global sentence context to return ONE best definition.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # We now fetch e.kana to filter out wrong Kanji readings!
        query = """
        SELECT e.kana, s.pos, s.sense_info, GROUP_CONCAT(g.gloss, ', ') as definitions
        FROM entries e
        JOIN senses s ON e.id = s.entry_id
        JOIN glosses g ON s.id = g.sense_id
        WHERE e.kanji = ? OR e.kana = ?
        GROUP BY s.id
        """
        cursor.execute(query, (word, word))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # Extract Sudachi POS hierarchy
        sudachi_primary = pos_tags[0] if len(pos_tags) > 0 else ""
        sudachi_secondary = pos_tags[1] if len(pos_tags) > 1 else ""

        best_score = -999
        best_def = rows[0][3] # Fallback to the first definition if nothing scores well

        for index, (db_kana, s_pos, s_inf, definitions) in enumerate(rows):
            score = 0
            s_pos_str = s_pos or ""
            s_inf_str = s_inf or ""
            score -= (index * 0.1) # Slightly demote lower-ranked senses to prefer top results, but not too heavily
            
            
            # --- 1. Phonetic Matching ---
            # Solves the "彼" (kare vs are) issue. If the dictionary kana doesn't match our target, heavily penalize it.
            if base_kana and db_kana and base_kana != db_kana:
                score -= 50
            else:
                score += 10 # Matches the phonetic reading!

            # --- 2. POS Tag Matching ---
            # Cross-referencing Sudachi output with JMdict XML tags
            if sudachi_primary == '動詞' and 'v' in s_pos_str and 'adv' not in s_pos_str:
                score += 20
            elif (sudachi_primary == '代名詞' or sudachi_secondary == '代名詞') and 'pn' in s_pos_str:
                score += 20
            elif sudachi_primary == '名詞' and 'n' in s_pos_str: # <--- FIXED: Allow suru-verbs to act as nouns!
                score += 20
            elif sudachi_primary == '形容詞' and 'adj' in s_pos_str:
                score += 20
            elif sudachi_primary == '副詞' and 'adv' in s_pos_str:
                score += 20

            # --- Collocation / Look-Behind Bonus ---
            # If the definition explicitly mentions a Japanese word or English concept 
            # found elsewhere in the sentence, give it a massive contextual bonus!
            
            # (Requires passing the raw token surfaces into sentence_context beforehand)
            sentence_words = sentence_context.get('surface_words', [])
            
            # e.g., if "電話" is in the sentence, and the definition has "phone" or "telephone"
            if '電話' in sentence_words and ('phone' in definitions.lower() or 'telephone' in definitions.lower()):
                score += 50
                
            # e.g., if "時間" is in the sentence, and the definition has "time"
            if '時間' in sentence_words and ('time' in definitions.lower() or 'accurate' in definitions.lower()):
                score += 50
                
            # --- 3. Environmental Context Matching ---
            if sentence_context.get('polarity') == 'negative':
                if 'negative' in s_inf_str.lower():
                    score += 15 # Perfect environmental match
            else:
                if 'negative' in s_inf_str.lower():
                    score -= 15 # Penalize negative definitions in a positive sentence!
                    
            # --- 4. Quality Control ---
            if 'obs' in s_pos_str or 'arch' in s_pos_str or 'rare' in s_pos_str:
                score -= 5 # Demote obsolete/archaic terms
                
            # --- 5. Update Winner ---
            if score > best_score:
                best_score = score
                # Clean up the output string, keeping context notes if they exist
                best_def = f"[{s_inf}] {definitions}" if s_inf else definitions

        return best_def

    def get_kanji_details(self, word):
        # (Keep your existing get_kanji_details code exactly as is)
        import re
        kanji_chars = re.findall(r'[\u4e00-\u9faf]', word)
        
        if not kanji_chars:
            return []

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
        romaji_str = "".join([item['hepburn'] for item in result])
        
        # --- THE SMALL つ FIX ---
        if romaji_str.endswith("tsu") and text.endswith("っ"):
            romaji_str = romaji_str[:-3] + "t"
            
        return romaji_str
    
    def get_hiragana(self, text):
        result = self.kks.convert(text)
        return "".join([item['hira'] for item in result])

    def parse_sentence(self, text):
        import re
        # Phase 1: Sentence Splitting (Preprocessing)
        # Splits text on Japanese periods, question marks, and exclamation points
        raw_sentences = [s for s in re.split(r'([。！？]+)', text) if s.strip()]
        
        # Re-attach the punctuation to the sentence
        sentences = []
        for i in range(0, len(raw_sentences), 2):
            sentence = raw_sentences[i]
            if i + 1 < len(raw_sentences):
                sentence += raw_sentences[i+1]
            sentences.append(sentence)

        compiled_results = []
        rule_engine = GrammarRuleEngine()

        for raw_sentence in sentences:
            tokens = self.tokenizer_obj.tokenize(raw_sentence, self.mode)
            
            # --- Pass 1: Global Context Aggregation ---
            # Default state
            sentence_context = {
                'tense': 'present',
                'polarity': 'positive',
                'politeness': 'plain'
            }
            sentence_context['surface_words'] = [t.surface() for t in tokens]
            
            # Scan tokens to establish the environment
            for token in tokens:
                base = token.dictionary_form()
                pos = token.part_of_speech()
                
                # Basic logic to flag negative or past tense sentences
                if base in ['ない', 'ぬ', 'ん'] or 'ません' in token.surface():
                    sentence_context['polarity'] = 'negative'
                if base == 'た' or 'ました' in token.surface():
                    sentence_context['tense'] = 'past'
                if base in ['です', 'ます'] or 'ません' in token.surface():
                    sentence_context['politeness'] = 'polite'

            # --- Pass 2 & 3: Definition and Rule Loop ---
            skip_count = 0
            for i, token in enumerate(tokens):
                # If a previous rule absorbed this token, skip it entirely!
                if skip_count > 0:
                    skip_count -= 1
                    continue
                
                context_dict = {
                    'tokens': tokens,
                    'index': i,
                    'environment': sentence_context
                }
                
                word = token.surface()
                base_form = token.dictionary_form()
                pos = token.part_of_speech()
                base_kana = self.get_hiragana(base_form)
                
                definition = None
                romaji = None
                
                # 1. Grammar Rules & Overrides
                if base_form == 'ない' or base_form == 'ん':
                    definition = "Negative suffix / Does not exist"
                    romaji = "nai"
                elif rule_engine.get_casual_contraction_explanation(token):
                    definition = rule_engine.get_casual_contraction_explanation(token)
                elif base_form in ['て', 'で'] and '助詞' in pos:
                    # Unpack our new tuple
                    definition, skip = rule_engine.get_te_form_explanation(token, context_dict)
                    skip_count = skip 
                    
                    if skip > 0:
                        # Mathematically bundle the auxiliary verb to the particle for the UI
                        next_token = tokens[i+1]
                        word += next_token.surface() # e.g., "て" + "いる" = "ている"
                        romaji = self.get_romaji(word)
                    else:
                        romaji = "te" if base_form == 'て' else "de"
                elif '助詞' in pos:
                    definition = rule_engine.get_explanation(token, context_dict)
                    romaji = rule_engine.get_romaji_override(token, context_dict)
                
                elif '助動詞' in pos:
                    definition = rule_engine.get_auxiliary_explanation(token, context_dict)
                    if not definition:
                        definition = self.dict_service.get_contextual_definition(base_form, base_kana, pos, sentence_context)
                    romaji = self.get_romaji(word)
                
                elif word in rule_engine.punctuation_registry:
                    definition = rule_engine.punctuation_registry[word]
                    romaji = word

                # 2. Smart Dictionary Lookup
                if not definition:
                    definition = self.dict_service.get_contextual_definition(base_form, base_kana, pos, sentence_context)
                    if not definition:
                        definition = "Definition not found."
                        
                if not romaji:
                    romaji = self.get_romaji(word)
                    
                compiled_results.append({
                    "word": word,
                    "romaji": romaji,
                    "pos": pos,
                    "definition": definition,
                    "kanji_data": self.dict_service.get_kanji_details(base_form)
                })
                
        return compiled_results

# Verification
if __name__ == "__main__":
    engine = BungoEngine()
    sentence = "ごめん、お母さんのケーキ、全部食べちゃった！"
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

T1 今日は全然時間がないから、水しか飲みません。
T2 この時計はとても高いですが、時間がよく合います。
T3 先生には、私からもう一度だけ電話をかけます。

て-Test: 
私はケーキを食べている。
明日テストがあるから、漢字を書いておきます。
お母さんのケーキを全部食べてしまった。
朝起きて、コーヒーを飲みます。

Casual Test:
ごめん、お母さんのケーキ、全部食べちゃった！
"""