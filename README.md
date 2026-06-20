# Bungo (文語) 🌸

Bungo is a local-first, deterministic, high-fidelity Japanese-to-English parsing and learning engine. 

Unlike commercial translators (like Google Translate or DeepL) that optimize for "fluent" English by destroying grammatical information, Bungo favors **structural breakdown and mathematical grammar mapping**. It exposes the raw skeleton of Japanese sentences, making it an invaluable tool for language learners who want to understand *how* a sentence works, not just what it means.

## 🧠 Core Philosophy & Features

* **Morphological Analysis:** Utilizes SudachiPy to intelligently slice unspaced Japanese text into atomic tokens.
* **Deterministic Grammar Math:** Replaces black-box LLMs with a cascading, rule-based engine. Bungo calculates context using look-ahead and look-behind matrix scanners:
    * *Te-Form Windowing:* Mathematically bundles auxiliary verbs (e.g., `て` + `いる` = `ている` [Continuous State]).
    * *Homophone Scanning:* Differentiates identical auxiliary verbs (like `られる` for Passive vs. Potential) by scanning surrounding environmental particles (e.g., `に` vs `が`).
    * *Slang Interception:* Normalizes Tokyo street slang and contractions (e.g., `ちゃった` -> `てしまった`) before dictionary processing.
* **Local-First Architecture:** Performs all tokenization and dictionary lookups entirely locally using a custom, relational SQLite build of the JMdict database. No APIs, no internet connection required.
* **Rich UI Formatting (MVC):** Features a dark-themed, native desktop interface built with PyQt6, complete with dynamic Furigana alignment, literal translation string generation, and color-coded grammar badges.

## 🛠️ Technical Stack

* **Language:** Python 3
* **NLP & Tokenization:** SudachiPy, pykakasi
* **Database:** SQLite3, lxml (for parsing JMdict XML)
* **User Interface:** PyQt6 (Desktop Native)
* **Packaging:** PyInstaller (Standalone executable compilation)

## 🚀 Installation & Execution

### Running Locally (Development)
1. Clone the repository.
2. Create a virtual environment and install the dependencies:
   ```bash
   pip install sudachipy sudachidict_core pykakasi PyQt6 lxml
3. Run the database builder: python src/db_builder.py
4. Launch the application: python src/ui.py