class GrammarRuleEngine:
    def __init__(self):
        # 1. The Logic Registry: Maps high-context particles to their functions
        self.logic_registry = {
            'は': self._handle_wa,
            'に': self._handle_ni,
            'で': self._handle_de,
            'が': self._handle_ga,
            'を': self._handle_wo,
            'の': self._handle_no,
            'と': self._handle_to,
            'も': self._handle_mo,
            'へ': self._handle_he,
            'か': self._handle_ka,
            'ね': self._handle_ne,
            'よ': self._handle_yo,
            'から': self._handle_kara,
            'まで': self._handle_made
        }

        # 2. The Phonetic Registry: Maps specific particles to romaji overrides
        self.romaji_overrides = {
            'は': self._romaji_wa,
            'へ': self._romaji_he
        }

        self.punctuation_registry = {
            '。': "Period: Marks the end of a sentence.",
            '、': "Comma: Separates elements within a sentence.",
            '・': "Middle Dot: Used to separate items in a list or compound words.",
            '—': "Em Dash: Indicates a break in thought or a pause.",
            '―': "Horizontal Bar: Similar to '—', used for emphasis or interruption.",
            '?': "Question Mark: Indicates a question.",
            '！': "Exclamation Mark: Indicates exclamation or strong emotion.",
            '〜': "Tilde: Indicates a range or approximation.",
            '…': "Ellipsis: Indicates an ellipsis, showing omission or trailing off."
        }

        # --- VERB LEMMA OVERRIDE MAP ---
        self.verb_lemma_map = {
            '弾かさ': '弾く',
            '書かす': '書く',
            '行か': '行く',
            '読ま': '読む',
            '飲ま': '飲む',
            'させ': 'する',
            '見': '見る',
            '食べさせ': '食べる'
        }

        # --- THE SLANG & DIALECT MAP ---
        self.contraction_map = {
            'ちゃう': "[Regret / Completion] Contraction of てしまう. (Note: In Kansai dialect, this can also mean 'wrong' / chigau).",            
            'じゃう': "[Regret / Completion (Casual)] Contraction of でしまう. Indicates a completed action, often with regret.",
            'ちまう': "[Regret / Completion (Rough)] Contraction of てしまう. Often used in masculine or rough speech.",
            'とく': "[Preparatory Action (Casual)] Contraction of ておく. Action done in advance for future readiness.",
            'どく': "[Preparatory Action (Casual)] Contraction of でおく. Action done in advance.",
            'てる': "[Continuous / State (Casual)] Contraction of ている. Indicates an ongoing action or current state.",
            'でる': "[Continuous / State (Casual)] Contraction of でいる. Indicates an ongoing action.",
            'なきゃ': "[Obligation (Casual)] Contraction of なければ. Means 'must do' or 'have to do'.",
            'なくちゃ': "[Obligation (Casual)] Contraction of なくては. Means 'must do' or 'have to do'.",
            'じゃん': "[Assertion (Casual)] Contraction of ではないか. Means 'isn't it?' or 'see?'.",
            'へん': "[Negative (Kansai Dialect)] Equivalent to standard 'nai' (ない). Indicates negation.",
            'ひん': "[Negative (Kansai Dialect)] Equivalent to standard 'nai' (ない).",
            'やん': "[Confirmation (Kansai Dialect)] Equivalent to standard 'janai' (じゃない) or 'ne' (ね).",
            'ねん': "[Explanatory/Emphasis (Kansai Dialect)] Equivalent to standard 'n da' (んだ) or 'no da' (のだ).",
            'おおきに': "[Gratitude (Kansai Dialect)] Equivalent to 'arigatou' (ありがとう). Thank you.",
            'せや': "[Agreement (Kansai Dialect)] Equivalent to standard 'sou da' (そうだ). Means 'that is so'."
        }

    # ==========================================
    # PUBLIC ROUTING METHODS (Called by Engine)
    # ==========================================

    def get_explanation(self, token, context):
        word = token.surface()
        if word in self.logic_registry:
            return self.logic_registry[word](token, context)
        
        tier_3_particles = {
            'さえ': "Emphasis particle: 'Even' (often implies an extreme case).",
            'こそ': "Emphasis particle: 'For sure' / 'This specifically' (strong focus).",
            'しか': "Limitation particle: 'Only / Nothing but' (Always paired with a negative verb).",
            'だけ': "Limitation particle: 'Only / Just' (Expresses exclusivity).",
            'など': "Listing particle: 'Et cetera / And so on' (Implies an incomplete list).",
            'ばかり': "Quantity particle: 'Nothing but / Only / Just finished doing'.",
            'くらい': "Approximation particle: 'About / Approximately / To the extent that'.",
            'ぐらい': "Approximation particle: 'About / Approximately / To the extent that'."
        }
        
        if word in tier_3_particles:
            return tier_3_particles[word]
        return None

    def get_te_form_explanation(self, token, context):
        tokens = context['tokens']
        i = context['index']
        
        if i + 1 < len(tokens):
            next_token = tokens[i+1]
            next_base = next_token.dictionary_form()
            
            if next_base in ['いる', '居る', 'います', 'いた']:
                return "[Continuous / State of Being] Indicates an ongoing action or current state.", 1
            elif next_base in ['おく', '置く', 'おきます', 'おいた']:
                return "[Preparatory Action] Action done in advance for future readiness.", 1
            elif next_base in ['しまう', '仕舞う', 'ちゃう', 'しまった']:
                return "[Regret / Completion] Completed action, often with a sense of regret or finality.", 1
            elif next_base in ['みる', '見る', 'みます', 'みた']:
                return "[Trial Action] Trying something out to see what happens.", 1
            elif next_base in ['あげる', 'くれる', 'もらう', '頂く']:
                return "[Benefactive Favor] Action done as a favor for someone.", 1

        return "[Conjunction] 'And then' / Connects clauses or sequential actions.", 0
    
    def get_casual_contraction_explanation(self, token):
        base = token.dictionary_form()
        surface = token.surface()
        
        explanation = self.contraction_map.get(base)
        if not explanation:
            explanation = self.contraction_map.get(surface)
            
        return explanation
    
    def get_romaji_override(self, token, context):
        word = token.surface()
        if word in self.romaji_overrides:
            return self.romaji_overrides[word](token, context)
        return None
    
    def get_auxiliary_explanation(self, token, context):
        aux_explanation = None
        base_form = token.dictionary_form()
        surface_form = token.surface()
        
        aux_math = {
            'ます': "Polite suffix",
            'た': "Casual Past tense suffix",
            'ない': "Formal Negative suffix",
            'ん': "Negative suffix",
            'たい': "Desire suffix (Want to do)",
            'せる': "Causative suffix (Make/Let do)",
            'れる': "Passive/Potential suffix (Able to do / Done to)",
            'だ': "Copula (State of being)",
            'です': "Polite Copula, state of being",
            'う': "Volitional suffix (Let's do / Probably)"
        }

        if base_form in ['れる', 'られる']:
            tokens = context['tokens']
            current_index = context['index']
            
            for j in range(current_index - 1, max(-1, current_index - 6), -1):
                prev_token = tokens[j]
                prev_base = prev_token.dictionary_form()
                prev_pos = prev_token.part_of_speech()
                
                if prev_base in ['。', '、', '！', '？']:
                    break
                if '助詞' in prev_pos:
                    if prev_base == 'に':
                        return "[Passive] Indicates the action is done TO the subject (marked by 'ni')."
                    elif prev_base == 'が':
                        return "[Potential] Indicates the ABILITY to perform the action."
            return "[Passive / Potential] Can indicate the action is done TO the subject (Passive), the subject has the ABILITY to do it (Potential), or formal respect." 
        elif base_form in ['せる', 'させる']:
            return "[Causative] Indicates making, forcing, or allowing someone to do an action." 
        elif base_form in ['たい', 'たがる']:
            return "[Desire] Expresses the speaker's want or desire to perform the action."
        elif base_form in ['そうだ', 'そうです', 'そう']:
            return "[Appearance / Hearsay] Indicates that something 'looks like' or 'is said to be' a certain way."
        elif base_form in ['ぬ', 'ず']:
            return "[Negative (Formal)] Classical/Written form of 'nai'. Indicates negation."
        
        aux_explanation = aux_math.get(base_form)
        if not aux_explanation:
            aux_explanation = aux_math.get(surface_form, "Auxiliary verb suffix")
        return aux_explanation

    # ==========================================
    # PRIVATE LOGIC HANDLERS
    # ==========================================
    
    def _handle_wa(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        if prev_token and '助詞' in str(prev_token.part_of_speech()):
            return f"Contrastive topic marker: Emphasizes the preceding particle '{prev_token.surface()}'."
        return "Topic marker: Sets the theme or subject of the sentence (often implies contrast)."

    def _handle_ni(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        definition = None
        
        if prev_token:
            prev_pos = str(prev_token.part_of_speech())
            prev_base = prev_token.dictionary_form()
            time_words = ['明日', '今日', '昨日', '今', '後', '前']
            if '時' in prev_pos or prev_base in time_words:
                definition = "Time marker: Indicates the specific time an action occurs."
                
        for j, future_token in enumerate(tokens):
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            base_verb = future_token.dictionary_form() 
            
            if '動詞' in pos:
                if base_verb in ['ある', 'いる']:
                    definition = "Location marker: Indicates the location of existence."
                if base_verb in ['行く', '来る', '帰る']:
                    definition = "Destination marker: Indicates where movement is headed."
                if base_verb == 'なる':
                    definition = "Result marker: Indicates the result of a change."
                break

        if not definition:
            definition = "Target/Location marker: Indicates the target of an action."
        return definition

    def _handle_de(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        if prev_token:
            prev_pos = str(prev_token.part_of_speech())
            if '数詞' in prev_pos or '助数詞' in prev_pos:
                return "Limit/Scope marker: Indicates a time limit, price, or quantity."
            if '地名' in prev_pos:
                return "Location marker: Indicates the specific place where an action occurs."
            if '名詞' in prev_pos or '代名詞' in prev_pos:
                return "Location/Means marker: Indicates where an action occurs, or the tool/method used."
                
        for j, future_token in enumerate(tokens[i+1:], start=i+1):
            pos = str(future_token.part_of_speech())
            base_verb = future_token.dictionary_form()
            if '動詞' in pos:
                if base_verb in ['できる', '作る']:
                     return "Material marker: Indicates what something is made from."
                break

        return "Context marker: Indicates means, method, or location."

    def _handle_ga(self, token, context):
        tokens, i = context['tokens'], context['index']
        next_token = tokens[i+1] if i < len(tokens) - 1 else None
        
        if next_token and next_token.surface() in ['、', '。', '']:
             return "Conjunctive particle: Connects two clauses, meaning 'but' or 'and'."

        for j, future_token in enumerate(tokens):
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            word = future_token.dictionary_form()
            
            if '形容詞' in pos:  
                return "Subject marker: Identifies the subject of the following adjective/state."
            elif word in ['ある', 'いる', 'あります', 'います']:
                return "Subject marker: Marks the subject of existence (what exists)."
            elif word in ['できる', 'できます', 'わかる', 'わかります']:
                return "Subject marker: Marks the subject of potential or understanding."
            elif '動詞' in pos:  
                return "Subject marker: Identifies the actor of the following verb."
                
        return "Subject marker: Identifies the grammatical subject."
    
    def _handle_wo(self, token, context):
        tokens, i = context['tokens'], context['index']
        for j, future_token in enumerate(tokens):
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            base_verb = future_token.dictionary_form()
            
            if '動詞' in pos:
                if base_verb in ['歩く', '走る', '飛ぶ', '渡る', '通る', '曲がる', '散歩する']:
                    return "Route/Traversal marker: Indicates the space where movement happens."
                if base_verb in ['出る', '降りる', '卒業する', '出発する']:
                    return "Departure marker: Indicates the place left behind."
                break   

        return "Target marker: Identifies the receiver of the action."

    def _handle_no(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        if prev_token:
            prev_pos = str(prev_token.part_of_speech())
            if '動詞' in prev_pos or '形容詞' in prev_pos:
                return "Nominalizer: Turns the preceding verb or adjective phrase into a noun."
        return "Possessive/Modifier: Links nouns together (A's B, or B of A)."

    def _handle_to(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        definition = None

        for j, future_token in enumerate(tokens):
            if (j <= i):
                j = i + 1
                continue
            if future_token.surface() in ['、', '。']:
                break 
            base_verb = future_token.dictionary_form()
            
            if base_verb in ['思う', '言う', '考える', '聞く', '信じる']:
                return "Quotation marker: Marks a quote, thought, or definition."
        
        if prev_token and '動詞' in str(prev_token.part_of_speech()):
            if prev_token.surface() == prev_token.dictionary_form():
                definition = "Conditional marker: 'If / When' (indicates a natural or inevitable consequence)."
                
        if not definition:
            definition = "Conjunctive/Comitative marker: 'And' (exhaustive list) or 'With' (a person)."
        return definition

    def _handle_mo(self, token, context):
        return "Inclusive topic marker: 'Also', 'Too', or 'Even'."
    
    def _handle_he(self, token, context):
        return "Direction marker: Indicates the destination or direction of an action ('to / towards')."

    def _handle_ka(self, token, context):
        tokens, i = context['tokens'], context['index']
        if i == len(tokens) - 1 or tokens[i+1].surface() in ['。', '？', '！', '、']:
            return "Question particle: Turns the sentence into a question."
        return "Alternative marker: Indicates 'Or' between choices, or marks an embedded question."

    def _handle_ne(self, token, context):
        return "Interaction particle: Seeks agreement, confirmation, or softens a statement ('right?' / 'isn't it?')."

    def _handle_yo(self, token, context):
        return "Assertion particle: Emphasizes new information, a warning, or a strong assertion."

    def _handle_kara(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        if prev_token:
            prev_pos = str(prev_token.part_of_speech())
            if '動詞' in prev_pos or '形容詞' in prev_pos:
                return "Reason marker: Indicates the cause or reason ('because / since')."
        return "Origin marker: Indicates a starting point in time or space ('from')."

    def _handle_made(self, token, context):
        return "Limit marker: Indicates an endpoint in time or space ('until / up to / as far as')."

    def _romaji_wa(self, token, context):
        return 'wa'
        
    def _romaji_he(self, token, context):
        return 'e'