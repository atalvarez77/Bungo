Bungo (文語)
Bungo is a localized, local-first, highly analytical natural language processing (NLP) desktop application engineered to demystify complex Japanese syntax. Unlike traditional translators that output flat, abstracted translations, Bungo breaks sentences down to their fundamental atomic components, visualizing morphological structures, grammar particles, auxiliary suffixes, and individual Kanji metadata for advanced language acquisition.

The Problem with Classic Translators
Traditional machine translation engines (e.g., Google Translate, DeepL) are optimized for communicative fluency, not linguistic pedagogy. For individuals studying Japanese, they introduce several massive friction points:

The "Black Box" Translation: They obscure the why and how. A student cannot tell which word mapped to which English concept, or why a verb changed its form.

Aggressive Context Dropping: Japanese is a high-context language prone to zero-anaphora (omitting subjects/objects). Classic translators hallucinate pronouns or guess context incorrectly without informing the user.

Mangled Grammar Suffixes: Suffixes representing aspect, tense, politeness, or causation (e.g., 〜ませんでした, 〜ちゃった, 〜させられた) are flattened into their final semantic equivalents, preventing learners from recognizing the underlying "grammar math."

The Bungo Solution
Bungo flips this paradigm. It values architectural accuracy over prose fluency. It acts as a deterministic parser that unmasks the exact morphological matrix of a sentence by:

Isolating base lexemes from their agglutinated morphological chains.

Differentiating spatial/syntactic particles from normal content vocabulary.

Generating a structured "Literal Translation String" that strips all Japanese tokens, capitalizes content words, isolates auxiliary verbs, and cleanly encloses relational particles inside localized parentheses.

How It Works
Technical Architecture
Bungo splits processing across four decoupled modules:

Morphological Tokenization Engine: Driven by SudachiPy (using the split-mode splitting system). It ingests raw Japanese string text, tokenizes it based on systematic linguistic dictionaries, handles phonetic variations, and yields exact dictionary base-forms alongside deep multi-part-of-speech (POS) tags.

Relational Database Cluster (SQLite): A unified local repository constructed by custom-engineered scripts parsing huge raw upstream files:

JMdict XML: Structured tables housing vocabulary definitions.

KANJIDIC2 XML: A localized database containing definitions, historical radicals, Onyomi (Chinese), and Kunyomi (Japanese) character readings for over 10,000 unique Kanji.

Deterministic Rule Engine: Intercepts tokens to execute conditional grammar overrides (e.g., identifying when the ambiguous token だ acts as a casual copula, or isolating complex verbal inflections like まし + た).

Phonetic Conversion Interface: Powered by pykakasi, dynamically generating perfect Romaji metadata maps for every single parsed node.

UI/UX Mechanics
Built natively on PyQt6 using standard styling directives, Bungo prioritizes immediate, readable structural feedback:

The Original Sentence Canvas: Generates standard vertical QVBoxLayout columns stacked inline via a custom flex-wrapping widget. This completely bypasses legacy HTML <ruby> tag engine bugs, rendering gold Furigana hovering perfectly over structural Kanji characters. A dedicated global toggle makes this Furigana appear/disappear instantly.

Interactive Token Blocks: Every token becomes a custom QFrame container styled using contextual color variables based on parts of speech:

Blue: Verbs

Gold: Particles

Red: Nouns & Pronouns

Green: Adjectives (I-Adjectives & Na-Adjectives)

Purple: Auxiliary Verbs / Copulas

On-Demand Detail Popup: Clicking an interactive block triggers a border accent change and expands a summary pane translating Japanese linguistic jargon to readable English classifications while automatically unpacking specific internal Kanji breakdowns.

Persistent Translation History: Uses a right-sliding QDockWidget drawer backed by a light JSON local storage layer. It caches up to 50 historical entries, automatically removing old duplicate records and bubbling active selections to the top (LIFO execution) for fast lookups.

Tech Stack
Language: Python 3.10+

GUI Framework: PyQt6

NLP Tokenizer: SudachiPy (Core split dictionary)

Phonetic Engines: PyKakasi & Romkan

Database Engine: SQLite 3

Packaging Suite: PyInstaller

Development Engineering Hurdles & Solutions
1. The Multi-Tiered "Part of Speech" Crash
The Problem: SudachiPy passes down its POS structural markers as an immutable Python tuple (e.g., ('名詞', '普通名詞', '一般', '*')). When we tried passing this object directly into PyQt's standard text field renderer (setText()), it triggered an absolute application abort: TypeError: argument 1 has unexpected type 'tuple'.

The Solution: Implemented an inline data-type guard that parses incoming POS payloads, verifies structure using isinstance, maps matches cleanly to a centralized translation dictionary (POS_TRANSLATOR), and joins multiple nested attributes using string format standardizers (" - ".join()).

2. The Native Substring Color Trap
The Problem: Auxiliary verbs (助動詞) were accidentally getting stained blue (the identifier reserved for standard Verbs 動詞). This occurred because Python's iterative evaluation checked if the string substring '動詞' existed inside the target tag. Since '動詞' sits inside '助動詞', the engine exited evaluation early and assigned the incorrect color.

The Solution: Re-ordered the keys of the underlying styling dictionary (POS_COLORS), placing longer, highly explicit parameters like 助動詞 right at the very top of the lookup object so they match and execute before standard, generic sub-strings are checked.

3. Aggressive Parenthesis Truncation
The Problem: The initial algorithm built to strip descriptive noise from literal translations utilized an aggressive substring partition split: split('(')[0]. While this cleanly handled long grammatical particle definitions, it completely destroyed standard descriptive text like (public) park for 公園, stripping away the entire noun translation and leaving a blank space.

The Solution: Implemented an evaluation fork based on structural POS mapping. If a node is explicitly identified as a structural dependency (Particle/Aux-Verb), it goes through aggressive abbreviation. If it maps to a standard content word, it pulls the root translation while leaving noun parenthesis descriptors un-severed.

4. Frozen Asset Dependency Hell (pykakasi)
The Problem: When building the single-file executable, the third-party phonetic system pykakasi crashed instantly upon startup with a severe FileNotFoundError. PyInstaller was compiling the application code cleanly, but failed to notice an internal binary database (kanwadict4.db) deeply hidden within pykakasi's installation directory inside Python's system site-packages.

The Solution: Modified the compilation script using PyInstaller's collect_data_files library hook to physically scoop up the internal vendor directory assets. Then, injected an explicit overriding hook directly at the execution initialization line of src/ui.py to point pykakasi directly to the active application memory address (sys._MEIPASS) at runtime.

Execution and Compilation Guide
Local Development Setup
Ensure you have a modern Python environment installed. Clone the repository and execute the following bootstrap commands:

Bash
# 1. Install required framework and NLP packages
pip install PyQt6 sudachipy sudachidict_core pykakasi romkan pyinstaller

# 2. Seed your database (Make sure kanjidic2.xml is placed in data/raw/)
python src/build_kanjidic.py

# 3. Launch application via your environment terminal
python src/ui.py
Freezing & Bundling the Desktop Executable
To package the app into a standalone macOS Application Bundle (.app) or Windows Executable (.exe), configure and use the centralized .spec file pipeline.

Create/Verify Bungo.spec in your root workspace:

Python
# -*- mode: python ; coding: utf-8 -*-
import os
import pykakasi
from PyInstaller.utils.hooks import collect_data_files

pykakasi_data = collect_data_files('pykakasi')

a = Analysis(
    ['src/ui.py'],
    pathex=['src'],
    binaries=[],
    datas=[('data', 'data')] + pykakasi_data,
    hiddenimports=['engine', 'rules', 'pykakasi'],
    cipher=None,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Bungo',
    debug=False,
    console=False, # Set to True if debugging ghost terminal launches
    icon='/Users/a2macpro/Desktop/Coding Projects/Bungo/bungo_icon.icns'
)
Compile via the terminal:

# Clean out previous build artifacts to prevent cache errors
rm -rf build dist

# Run PyInstaller using your explicit specification instructions
pyinstaller Bungo.spec


Your compiled, portable desktop artifact will be located inside the generated dist/ directory.