import json
import os
import sys

class GrammarRuleEngine:
    def __init__(self):
        # 1. Load the Data Layer from JSON
        self._load_json_rules()

        # 2. Logic Registries (These stay in Python because they map to actual functions)
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

        self.romaji_overrides = {
            'は': self._romaji_wa,
            'へ': self._romaji_he
        }

    def _load_json_rules(self):
        """Safely loads static rule maps from the JSON file."""
        if getattr(sys, 'frozen', False):
            # If compiled by PyInstaller
            base_path = sys._MEIPASS
        else:
            # If running in a local dev environment (assumes rules.py is in src/)
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        json_path = os.path.join(base_path, 'data', 'rules_dictionary.json')

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.punctuation_registry = data.get('punctuation_registry', {})
                self.verb_lemma_map = data.get('verb_lemma_map', {})
                self.contraction_map = data.get('contraction_map', {})
                self.collocation_map = data.get('collocation_map', {})
        except FileNotFoundError:
            print(f"CRITICAL WARNING: {json_path} not found! Rule maps will be empty.")
            self.punctuation_registry = {}
            self.verb_lemma_map = {}
            self.contraction_map = {}
            self.collocation_map = {}

    # ==========================================
    # PUBLIC ROUTING METHODS (Called by Engine)
    # ==========================================

    def get_explanation(self, token, context):
        """
        Primary entry point for particle definitions.
        Called by engine.py ONLY if token POS contains '助詞'.
        """
        word = token.surface()
        
        # If the particle requires high-fidelity context logic, route it
        if word in self.logic_registry:
            return self.logic_registry[word](token, context)
        
        # Static grammatical overrides for less context-dependent particles
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
    
        # Return None so engine.py knows to fallback to JMdict.
        return None

    def get_te_form_explanation(self, token, context):
        """
        Determines the semantic meaning of the て/で form by looking ahead.
        RETURNS: (definition_string, tokens_to_skip)
        """
        tokens = context['tokens']
        i = context['index']
        
        # Ensure we don't go out of bounds
        if i + 1 < len(tokens):
            next_token = tokens[i+1]
            next_base = next_token.dictionary_form()
            
            # 1. The Progressive/State Operator
            if next_base in ['いる', '居る', 'います', 'いた']:
                return "[Continuous / State of Being] Indicates an ongoing action or current state.", 1
                
            # 2. The Preparatory Operator
            elif next_base in ['おく', '置く', 'おきます', 'おいた']:
                return "[Preparatory Action] Action done in advance for future readiness.", 1
                
            # 3. The Regret/Completion Operator
            elif next_base in ['しまう', '仕舞う', 'ちゃう', 'しまった']:
                return "[Regret / Completion] Completed action, often with a sense of regret or finality.", 1
                
            # 4. The Trial Operator
            elif next_base in ['みる', '見る', 'みます', 'みた']:
                return "[Trial Action] Trying something out to see what happens.", 1
                
            # 5. The Benefactive Operators
            elif next_base in ['あげる', 'くれる', 'もらう', '頂く']:
                return "[Benefactive Favor] Action done as a favor for someone.", 1

        # Default: If it's followed by a comma, noun, or normal verb, consume nothing!
        return "[Conjunction] 'And then' / Connects clauses or sequential actions.", 0
    
    def get_casual_contraction_explanation(self, token):
        base = token.dictionary_form()
        surface = token.surface()
        
        # Check the base form first, then check the surface form
        explanation = self.contraction_map.get(base)
        if not explanation:
            explanation = self.contraction_map.get(surface)
            
        return explanation
    
    def get_romaji_override(self, token, context):
        """
        Determines if a particle requires a non-standard romaji reading based on context.
        """
        word = token.surface()
        if word in self.romaji_overrides:
            return self.romaji_overrides[word](token, context)
        return None
    
    def get_auxiliary_explanation(self, token, context):
        """
        Translates auxiliary verb suffixes into mathematical grammar functions.
        """
        aux_explanation = None

        base_form = token.dictionary_form()
        surface_form = token.surface()
        
        # The Verb-Math Registry
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

        # Major Auxilary Check
        # 1. Passive / Potential / Respect (れる / られる)
        if base_form in ['れる', 'られる']:
            tokens = context['tokens']
            current_index = context['index']
            
            # --- CONTEXT SCANNER ---
            # Look backwards up to 5 tokens to find strong particle clues in the clause
            for j in range(current_index - 1, max(-1, current_index - 6), -1):
                prev_token = tokens[j]
                prev_base = prev_token.dictionary_form()
                prev_pos = prev_token.part_of_speech()
                
                # If we hit a punctuation mark, stop scanning (we've left the clause)
                if prev_base in ['。', '、', '！', '？']:
                    break
                    
                if '助詞' in prev_pos:
                    if prev_base == 'に':
                        return "[Passive] Indicates the action is done TO the subject (marked by 'ni')."
                    elif prev_base == 'が':
                        return "[Potential] Indicates the ABILITY to perform the action."
            # Fallback
            return "[Passive / Potential] Can indicate the action is done TO the subject (Passive), the subject has the ABILITY to do it (Potential), or formal respect." 
        # 2. Causative (せる / させる)
        elif base_form in ['せる', 'させる']:
            return "[Causative] Indicates making, forcing, or allowing someone to do an action." 
        # 3. Desire (たい / たがる)
        elif base_form in ['たい', 'たがる']:
            return "[Desire] Expresses the speaker's want or desire to perform the action."
        # 4. Appearance / Hearsay (そうだ / そうです)
        elif base_form in ['そうだ', 'そうです', 'そう']:
            return "[Appearance / Hearsay] Indicates that something 'looks like' or 'is said to be' a certain way."
        # 5. Formal Negation (ぬ / ず)
        elif base_form in ['ぬ', 'ず']:
            return "[Negative (Formal)] Classical/Written form of 'nai'. Indicates negation."
        
        # Check for base_form definition, then fallback to surface_form if not found
        aux_explanation = aux_math.get(base_form)
        if not aux_explanation:
            aux_explanation = aux_math.get(surface_form, "Auxiliary verb suffix")
        return aux_explanation

    # ==========================================
    # PRIVATE LOGIC HANDLERS (To be expanded next)
    # ==========================================
    
    def _handle_wa(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        # Double Particle Check (e.g., には, では, からは)
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
            
            # 1. Time Check (Broadened)
            # Checks for specific time words OR the Sudachi 'time' tag
            time_words = ['明日', '今日', '昨日', '今', '後', '前']
            if '時' in prev_pos or prev_base in time_words:
                definition = "Time marker: Indicates the specific time an action occurs."
                
        # Forward Scan for Verbs
        for j, future_token in enumerate(tokens):
            # Skip to future tokens only
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            base_verb = future_token.dictionary_form() # Use the root verb!
            
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
            
            # 1. Limit/Scope Check (Patched to include Counters)
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
        
        # 1. Conjunctive Check: Is it at the end of a clause? (followed by a comma or period or space)
        next_token = tokens[i+1] if i < len(tokens) - 1 else None
        if next_token and next_token.surface() in ['、', '。', '']:
             return "Conjunctive particle: Connects two clauses, meaning 'but' or 'and'."

        # 2. Forward Scan: Look for specific verbs or adjectives
        for j, future_token in enumerate(tokens):
            # Skip to future tokens only
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            word = future_token.dictionary_form()
            
            if '形容詞' in pos:  # Adjective
                return "Subject marker: Identifies the subject of the following adjective/state."
                
            elif word in ['ある', 'いる', 'あります', 'います']:
                return "Subject marker: Marks the subject of existence (what exists)."
                
            elif word in ['できる', 'できます', 'わかる', 'わかります']:
                return "Subject marker: Marks the subject of potential or understanding."
                
            elif '動詞' in pos:  # General Verb
                return "Subject marker: Identifies the actor of the following verb."
                
        return "Subject marker: Identifies the grammatical subject."
    
    def _handle_wo(self, token, context):
        tokens, i = context['tokens'], context['index']
        
        # Forward Scan for specific verb types
        for j, future_token in enumerate(tokens):
            # Skip to future tokens only
            if (j <= i):
                j = i + 1
                continue
            pos = str(future_token.part_of_speech())
            base_verb = future_token.dictionary_form()
            
            if '動詞' in pos:
                # 1. Motion Verbs (Traversal/Route) - e.g., 公園を歩く (Walk through the park)
                if base_verb in ['歩く', '走る', '飛ぶ', '渡る', '通る', '曲がる', '散歩する']:
                    return "Route/Traversal marker: Indicates the space where movement happens."
                    
                # 2. Departure Verbs - e.g., 家を出る (Leave the house)
                if base_verb in ['出る', '降りる', '卒業する', '出発する']:
                    return "Departure marker: Indicates the place left behind."
                break   

        # 3. Default
        return "Target marker: Identifies the receiver of the action."

    def _handle_no(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        
        if prev_token:
            prev_pos = str(prev_token.part_of_speech())
            
            # 1. Nominalizer Check: If 'の' follows a verb or adjective, it acts like "the act of"
            if '動詞' in prev_pos or '形容詞' in prev_pos:
                return "Nominalizer: Turns the preceding verb or adjective phrase into a noun."

        # 2. Default Possessive/Modification
        return "Possessive/Modifier: Links nouns together (A's B, or B of A)."

    def _handle_to(self, token, context):
        tokens, i = context['tokens'], context['index']
        prev_token = tokens[i-1] if i > 0 else None
        definition = None

        # 1. Forward scan for quotation verbs
        for j, future_token in enumerate(tokens):
            # Skip to future tokens only
            if (j <= i):
                j = i + 1
                continue
            # Stop scanning if we hit punctuation that likely ends the clause
            if future_token.surface() in ['、', '。']:
                break 
            base_verb = future_token.dictionary_form()
            
            # Quotation Check - e.g., ...と思う (I think that...)
            if base_verb in ['思う', '言う', '考える', '聞く', '信じる']:
                return "Quotation marker: Marks a quote, thought, or definition."
        
        # 2. Conditional Check: If 'と' follows a dictionary-form verb
        if prev_token and '動詞' in str(prev_token.part_of_speech()):
            # A strict rule: Conditional 'と' almost always follows the base form
            if prev_token.surface() == prev_token.dictionary_form():
                definition = "Conditional marker: 'If / When' (indicates a natural or inevitable consequence)."
                
        # 3. Default
        if not definition:
            definition = "Conjunctive/Comitative marker: 'And' (exhaustive list) or 'With' (a person)."
        return definition

    def _handle_mo(self, token, context):
        # 'も' is largely consistent, but often replaces 'は', 'が', or 'を'
        return "Inclusive topic marker: 'Also', 'Too', or 'Even'."
    
    def _handle_he(self, token, context):
        # 'へ' is almost exclusively a directional marker
        return "Direction marker: Indicates the destination or direction of an action ('to / towards')."

    def _handle_ka(self, token, context):
        tokens, i = context['tokens'], context['index']
        
        # 1. End of sentence check
        if i == len(tokens) - 1 or tokens[i+1].surface() in ['。', '？', '！', '、']:
            return "Question particle: Turns the sentence into a question."
            
        # 2. Embedded question or "Or"
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
            # If it follows a verb or adjective, it usually means "Because"
            if '動詞' in prev_pos or '形容詞' in prev_pos:
                return "Reason marker: Indicates the cause or reason ('because / since')."
                
        return "Origin marker: Indicates a starting point in time or space ('from')."

    def _handle_made(self, token, context):
        return "Limit marker: Indicates an endpoint in time or space ('until / up to / as far as')."

    # --- Phonetic Handlers ---
    def _romaji_wa(self, token, context):
        # Always 'wa' when functioning as a particle
        return 'wa'
        
    def _romaji_he(self, token, context):
        # Always 'e' when functioning as a directional particle
        return 'e'