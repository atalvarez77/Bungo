import sys
from sudachipy import dictionary, tokenizer
import pykakasi
import sqlite3
import os
import re

from rules import GrammarRuleEngine

class DictionaryService:
    def __init__(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.db_path = os.path.join(base_path, 'data', 'bungo_dictionary.db')

    def get_contextual_definition(self, word, base_kana, pos_tags, context_dict):
        """
        V2: Cleaned Dictionary Service. Fetches senses and scores them based purely 
        on POS tags, phonetics, and polarity. 
        (Collocations are now handled organically by the N-Gram Chunker).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        has_kanji = bool(re.search(r'[\u4E00-\u9FFF]', word))
        
        if has_kanji:
            query = """
            SELECT e.kana, s.pos, s.sense_info, GROUP_CONCAT(g.gloss, ', ') as sense_glosses
            FROM entries e
            JOIN senses s ON e.id = s.entry_id
            JOIN glosses g ON s.id = g.sense_id
            WHERE e.kanji = ?
            GROUP BY s.id
            """
            cursor.execute(query, (word,))
        else:
            query = """
            SELECT e.kana, s.pos, s.sense_info, GROUP_CONCAT(g.gloss, ', ') as sense_glosses
            FROM entries e
            JOIN senses s ON e.id = s.entry_id
            JOIN glosses g ON s.id = g.sense_id
            WHERE e.kana = ?
            GROUP BY s.id
            """
            cursor.execute(query, (word,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        sudachi_primary = pos_tags[0] if len(pos_tags) > 0 else ""
        sudachi_secondary = pos_tags[1] if len(pos_tags) > 1 else ""

        scored_senses = []
        
        # Unpack Environment for Polarity checking
        env = context_dict.get('environment', {})
        sentence_polarity = env.get('polarity', 'positive')

        for index, (db_kana, s_pos, s_inf, sense_glosses) in enumerate(rows):
            score = 0
            s_pos_str = s_pos or ""
            s_inf_str = s_inf or ""
            score -= (index * 0.1) 
            
            # 1. Phonetic Matching
            if base_kana and db_kana and base_kana != db_kana:
                score -= 50
            else:
                score += 10

            # 2. POS Tag Matching
            if sudachi_primary == '動詞' and 'v' in s_pos_str and 'adv' not in s_pos_str:
                score += 20
            elif (sudachi_primary == '代名詞' or sudachi_secondary == '代名詞') and 'pn' in s_pos_str:
                score += 20
            elif sudachi_primary == '名詞' and 'n' in s_pos_str: 
                score += 20
            elif sudachi_primary == '形容詞' and 'adj' in s_pos_str:
                score += 20
            elif sudachi_primary == '副詞' and 'adv' in s_pos_str:
                score += 20
                
            # 3. Environmental Context Matching
            if sentence_polarity == 'negative':
                if 'negative' in s_inf_str.lower():
                    score += 15
            else:
                if 'negative' in s_inf_str.lower():
                    score -= 15
                    
            # 4. Quality Control
            if 'obs' in s_pos_str or 'arch' in s_pos_str or 'rare' in s_pos_str:
                score -= 5
                
            formatted_sense = f"[{s_inf}] {sense_glosses}" if s_inf else sense_glosses
            scored_senses.append((score, formatted_sense))

        scored_senses.sort(key=lambda x: x[0], reverse=True)
        best_def_string = " | ".join([sense[1] for sense in scored_senses])

        return best_def_string

    def get_kanji_details(self, word):
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
        if romaji_str.endswith("tsu") and text.endswith("っ"):
            romaji_str = romaji_str[:-3] + "t"
        return romaji_str
    
    def get_hiragana(self, text):
        result = self.kks.convert(text)
        return "".join([item['hira'] for item in result])

    def parse_sentence(self, text):
        raw_sentences = [s for s in re.split(r'([。！？]+)', text) if s.strip()]
        
        sentences = []
        for i in range(0, len(raw_sentences), 2):
            sentence = raw_sentences[i]
            if i + 1 < len(raw_sentences):
                sentence += raw_sentences[i+1]
            sentences.append(sentence)

        compiled_results = []
        rule_engine = GrammarRuleEngine()

        for raw_sentence in sentences:
            # 1. Sudachi creates its custom MorphemeList
            tokens = self.tokenizer_obj.tokenize(raw_sentence, self.mode)
            
            # --- THE FIX: Convert it to a standard Python list! ---
            tokens = list(tokens)
            # ------------------------------------------------------
            
            sentence_context = {
                'tense': 'present',
                'polarity': 'positive',
                'politeness': 'plain'
            }
            sentence_context['surface_words'] = [t.surface() for t in tokens]
            
            for token in tokens:
                base = token.dictionary_form()
                if base in ['ない', 'ぬ', 'ん'] or 'ません' in token.surface():
                    sentence_context['polarity'] = 'negative'
                if base == 'た' or 'ました' in token.surface():
                    sentence_context['tense'] = 'past'
                if base in ['です', 'ます'] or 'ません' in token.surface():
                    sentence_context['politeness'] = 'polite'

            skip_count = 0
            for i, token in enumerate(tokens):
                if skip_count > 0:
                    skip_count -= 1
                    continue
                
                context_dict = {
                    'tokens': tokens,
                    'index': i,
                    'environment': sentence_context
                }
                
                # ==========================================
                # V2: THE N-GRAM CHUNKER
                # ==========================================
                # Look ahead up to 4 tokens to see if they form a dictionary idiom!
                ngram_found = False
                
                # Check sizes: 4 tokens, then 3 tokens, then 2 tokens
                for n in range(4, 1, -1):
                    if i + n <= len(tokens):
                        # Construct the JMdict Lemma (e.g. 年 + を + 取る = 年を取る)
                        ngram_lemma = "".join([t.dictionary_form() for t in tokens[i:i+n]])
                        ngram_kana = self.get_hiragana(ngram_lemma)
                        
                        # Silently query the dictionary
                        ngram_def = self.dict_service.get_contextual_definition(ngram_lemma, ngram_kana, ['動詞', '名詞'], context_dict)
                        
                        if ngram_def and ngram_def != "Definition not found.":
                            # WE FOUND A VALID IDIOM! 
                            # Reconstruct the surface phrase as it appears in the sentence
                            word_surface = "".join([t.surface() for t in tokens[i:i+n]])
                            romaji = self.get_romaji(word_surface)
                            
                            # Grab just the top contextual meaning for the UI
                            top_def = ngram_def.split('|')[0].strip()
                            
                            compiled_results.append({
                                "word": word_surface,
                                "romaji": romaji,
                                "pos": "Idiom/Phrase", # Custom POS marker for the UI
                                "definition": f"[Idiom] {top_def}",
                                "kanji_data": self.dict_service.get_kanji_details(ngram_lemma)
                            })
                            
                            # Skip processing the rest of the tokens in this idiom
                            skip_count = n - 1
                            ngram_found = True
                            break
                            
                # If an idiom was caught, move entirely to the next available token!
                if ngram_found:
                    continue
                # ==========================================
                
                word = token.surface()
                base_form = token.dictionary_form()
                pos = token.part_of_speech()
                base_kana = self.get_hiragana(base_form)
                
                definition = None
                romaji = None
                
                # 1. Grammar Rules & Overrides
                slang_def = rule_engine.get_casual_contraction_explanation(token)
                if slang_def:
                    definition = slang_def
                    romaji = self.get_romaji(word)
                elif base_form == 'ない' or base_form == 'ん':
                    definition = "Negative suffix / Does not exist"
                    romaji = "nai"
                elif base_form in ['て', 'で'] and '助詞' in pos:
                    definition, skip = rule_engine.get_te_form_explanation(token, context_dict)
                    skip_count = skip 
                    
                    if skip > 0:
                        next_token = tokens[i+1]
                        word += next_token.surface() 
                        romaji = self.get_romaji(word)
                    else:
                        romaji = "te" if base_form == 'て' else "de"
                elif '助詞' in pos:
                    definition = rule_engine.get_explanation(token, context_dict)
                    romaji = rule_engine.get_romaji_override(token, context_dict)
                
                elif '助動詞' in pos:
                    definition = rule_engine.get_auxiliary_explanation(token, context_dict)
                    if not definition:
                        definition = self.dict_service.get_contextual_definition(base_form, base_kana, pos, context_dict)
                    romaji = self.get_romaji(word)
                
                elif word in rule_engine.punctuation_registry:
                    definition = rule_engine.punctuation_registry[word]
                    romaji = word

                # 2. Smart Dictionary Lookup
                if not definition:
                    definition = self.dict_service.get_contextual_definition(base_form, base_kana, pos, context_dict)
                    if not definition and re.fullmatch(r'[\u30A0-\u30FFー]+', word):
                        if not definition or definition == "Definition not found.":
                            definition = f"[Loanword] {self.get_romaji(word).capitalize()}"
                    elif not definition or definition == "Definition not found.":
                        override_lemma = rule_engine.verb_lemma_map.get(word)

                        if override_lemma:
                            definition = self.dict_service.get_contextual_definition(
                                override_lemma, 
                                override_lemma, 
                                pos, 
                                context_dict
                            )
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
    sentence = "最近、年をとってすぐ風邪を引いちゃうから、しっかり睡眠をとらなきゃ。"
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

Final Boss Tests:
昨日、先生にピアノを弾かされちゃったから、今は全然練習したくないですね。
Yesterday, because I was forced by my teacher to play the piano, I don't want to practice at all now, right?
変な音がしたから、確認するために眼鏡をかけといた。
Because I heard a strange sound, I put my glasses on in advance to check.
最近、年をとってすぐ風邪を引いちゃうから、しっかり睡眠をとらなきゃ。
Lately, because I grow old and catch colds immediately, I absolutely have to get some sleep.
"""