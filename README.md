<img width="906" height="681" alt="image" src="https://github.com/user-attachments/assets/02197b4c-4b2d-431a-84c6-44c863646778" /># Bungo (文語) 🌸

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
Home Page:
<img width="906" height="681" alt="image" src="https://github.com/user-attachments/assets/8d6c643f-344d-4f1d-904a-a2ec81decb79" />
Home Page w/ Text:
<img width="835" height="372" alt="image" src="https://github.com/user-attachments/assets/9014b118-5b2e-447a-9180-784ff0acd63a" />
Translated Text:
<img width="841" height="356" alt="image" src="https://github.com/user-attachments/assets/1a918b8e-7a2e-4ac2-8ae6-fa1851496e50" />
Clicking on noun 'Daigakusei' to expand kanji meaning:
<img width="831" height="419" alt="image" src="https://github.com/user-attachments/assets/947fe0e0-3656-4262-a106-0cd69239cfc1" />
Clcking on particle 'no' to expand definition:
<img width="831" height="236" alt="image" src="https://github.com/user-attachments/assets/9072aa6d-e2c3-44d7-841c-08b7ca9f9e60" />
History Tab:
<img width="259" height="378" alt="image" src="https://github.com/user-attachments/assets/25de274d-6d4f-40df-8462-2112aa9e3d96" />

### Running Locally (Development)
1. Clone the repository.
2. Create a virtual environment and install the dependencies:
   ```bash
   pip install sudachipy sudachidict_core pykakasi PyQt6 lxml
3. Run the database builder: python src/db_builder.py
4. Launch the application: python src/ui.py
