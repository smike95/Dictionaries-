import os
import sqlite3
import urllib.parse
from deep_translator import GoogleTranslator
import streamlit as st

# Налаштування сторінки
st.set_page_config(
    page_title="Ігрові Словники - Перевірка",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LANGUAGES = ["de", "en", "es", "fr", "it", "nl", "pl", "pt", "uk"]
# Виправлено: animal.txt змінено на animals.txt
CATEGORIES = ["animals.txt", "food.txt", "nature.txt", "travel.txt"]
LEVEL_SIZE = 10  # 10 слів на рівень

DB_NAME = "game_progress.db"


# --- РОБОТА З БАЗОЮ ДАНИХ НА СЕРВЕРІ ---
def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_decisions (
            lang TEXT,
            cat TEXT,
            word_idx INTEGER,
            word TEXT,
            status TEXT,
            PRIMARY KEY (lang, cat, word_idx)
        )
    """)
  conn.commit()
  conn.close()


def save_decision_to_db(lang, cat, word_idx, word, status):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT OR REPLACE INTO user_decisions (lang, cat, word_idx, word, status)
        VALUES (?, ?, ?, ?, ?)
    """,
      (lang, cat, word_idx, word, status),
  )
  conn.commit()
  conn.close()


def load_all_decisions_from_db():
  if not os.path.exists(DB_NAME):
    return {}
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute("SELECT lang, cat, word_idx, word, status FROM user_decisions")
  rows = cursor.fetchall()
  conn.close()

  decisions = {}
  for lang, cat, word_idx, word, status in rows:
    if lang not in decisions:
      decisions[lang] = {}
    if cat not in decisions[lang]:
      decisions[lang][cat] = {}
    decisions[lang][cat][word_idx] = {"word": word, "status": status}
  return decisions


init_db()


# Функція перекладу на українську
def translate_to_uk(word, src_lang):
  if src_lang == "uk" or not word:
    return word
  try:
    return GoogleTranslator(source=src_lang, target="uk").translate(word)
  except Exception:
    return word


# Завантаження словників з папок репозиторію
@st.cache_data
def load_all_dicts():
  all_data = {}
  for lang in LANGUAGES:
    all_data[lang] = {}
    for cat in CATEGORIES:
      path = os.path.join(lang, cat)
      words = []
      if os.path.exists(path):
        try:
          with open(path, "r", encoding="utf-8") as f:
            words = [line.strip() for line in f.readlines() if line.strip()]
        except Exception:
          try:
            with open(path, "r", encoding="cp1251") as f:
              words = [line.strip() for line in f.readlines() if line.strip()]
          except Exception:
            pass
      if not words:
        words = [cat.replace(".txt", "").upper()]
      all_data[lang][cat] = words
  return all_data


dict_data = load_all_dicts()

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ СЕСІЇ ---
if "step" not in st.session_state:
  st.session_state.step = "select_lang"
if "selected_lang" not in st.session_state:
  st.session_state.selected_lang = None
if "selected_cat" not in st.session_state:
  st.session_state.selected_cat = None
if "selected_level" not in st.session_state:
  st.session_state.selected_level = None
if "editing_word_idx" not in st.session_state:
  st.session_state.editing_word_idx = None

st.session_state.user_decisions = load_all_decisions_from_db()


# ==========================================
# КРОК 1: ВИБІР МОВИ
# ==========================================
if st.session_state.step == "select_lang":
  st.title("🌍 Виберіть мову словника")
  st.markdown("---")

  cols = st.columns(3)
  for i, lang in enumerate(LANGUAGES):
    with cols[i % 3]:
      if st.button(f"📌 {lang.upper()}", use_container_width=True, key=f"l_{lang}"):
        st.session_state.selected_lang = lang
        st.session_state.step = "select_cat"
        st.rerun()

# ==========================================
# КРОК 2: ВИБІР КАТЕГОРІЇ
# ==========================================
elif st.session_state.step == "select_cat":
  lang = st.session_state.selected_lang
  st.title(f"📁 Виберіть категорію ({lang.upper()})")

  if st.button("⬅ Назад до вибору мови"):
    st.session_state.step = "select_lang"
    st.rerun()

  st.markdown("---")

  cols = st.columns(2)
  for i, cat in enumerate(CATEGORIES):
    cat_words_foreign = dict_data[lang][cat]
    cat_name_foreign = cat_words_foreign[0] if cat_words_foreign else cat

    cat_words_uk = dict_data["uk"][cat]
    cat_name_uk = cat_words_uk[0] if cat_words_uk else cat

    with cols[i % 2]:
      btn_label = f"🐾 {cat_name_foreign} ({cat_name_uk})"
      if st.button(btn_label, use_container_width=True, key=f"c_{cat}"):
        st.session_state.selected_cat = cat
        st.session_state.step = "select_levels"
        st.rerun()

# ==========================================
# КРОК 3: СІТКА РІВНІВ (по 10 слів)
# ==========================================
elif st.session_state.step == "select_levels":
  lang = st.session_state.selected_lang
  cat = st.session_state.selected_cat

  cat_words = dict_data[lang][cat][1:]
  total_levels = max(1, (len(cat_words) + LEVEL_SIZE - 1) // LEVEL_SIZE)

  st.title(
      f"📊 Рівні | Мова: {lang.upper()} | Категорія:"
      f" {cat.replace('.txt','').capitalize()}"
  )

  if st.button("⬅ Назад до категорій"):
    st.session_state.step = "select_cat"
    st.rerun()

  st.markdown("---")

  cols = st.columns(3)
  for lvl in range(1, total_levels + 1):
    start_idx = (lvl - 1) * LEVEL_SIZE
    end_idx = min(start_idx + LEVEL_SIZE, len(cat_words))
    lvl_words_count = end_idx - start_idx

    passed_count = 0
    if (
        lang in st.session_state.user_decisions
        and cat in st.session_state.user_decisions[lang]
    ):
      decisions = st.session_state.user_decisions[lang][cat]
      passed_count = sum(
          1
          for idx in range(start_idx, end_idx)
          if idx in decisions and decisions[idx]["status"] is not None
      )

    badge = (
        f" ✅ ({passed_count}/{lvl_words_count})" if passed_count > 0 else ""
    )

    with cols[(lvl - 1) % 3]:
      if st.button(
          f"Рівень {lvl}{badge}", use_container_width=True, key=f"lvl_{lvl}"
      ):
        st.session_state.selected_level = lvl
        st.session_state.step = "gameplay"
        st.rerun()

# ==========================================
# КРОК 4: ІГРОВИЙ ЕКРАН
# ==========================================
elif st.session_state.step == "gameplay":
  lang = st.session_state.selected_lang
  cat = st.session_state.selected_cat
  lvl = st.session_state.selected_level

  full_list = dict_data[lang][cat]
  cat_name_foreign = full_list[0] if full_list else ""
  cat_name_uk = dict_data["uk"][cat][0] if dict_data["uk"][cat] else ""
  words_list = full_list[1:]

  total_levels = max(1, (len(words_list) + LEVEL_SIZE - 1) // LEVEL_SIZE)

  # Кнопка повернення до сітки рівнів
  if st.button("⬅ До списку рівнів"):
    st.session_state.selected_level = None
    st.session_state.step = "select_levels"
    st.rerun()

  start_idx = (lvl - 1) * LEVEL_SIZE
  end_idx = min(start_idx + LEVEL_SIZE, len(words_list))
  level_words = words_list[start_idx:end_idx]

  col_head1, col_head2 = st.columns([10, 1])
  with col_head1:
    st.markdown(
        f"<h2>{cat_name_foreign} &nbsp;|&nbsp; 🇺🇦 <i>{cat_name_uk}</i>"
        f" &nbsp;—&nbsp; Рівень {lvl} з {total_levels}</h2>",
        unsafe_allow_html=True,
    )
  with col_head2:
    if st.button("❓", help="Довідка"):
      st.info(
          "Клік по слову — пошук у Google Картинках. Ліворуч — «Ні», праворуч —"
          " «Так». Олівець — редагувати."
      )

  st.markdown("---")

  if lang not in st.session_state.user_decisions:
    st.session_state.user_decisions[lang] = {}
  if cat not in st.session_state.user_decisions[lang]:
    st.session_state.user_decisions[lang][cat] = {}

  cat_decisions = st.session_state.user_decisions[lang][cat]

  for i, original_word in enumerate(level_words):
    global_idx = start_idx + i

    stored_data = cat_decisions.get(
        global_idx, {"word": original_word, "status": None}
    )
    current_word = stored_data["word"]
    status = stored_data["status"]

    col_no, col_word, col_yes = st.columns([1, 6, 1])

    with col_no:
      btn_no_style = "❌" if status == "no" else "➖ Ні"
      if st.button(btn_no_style, key=f"no_{global_idx}", use_container_width=True):
        save_decision_to_db(lang, cat, global_idx, current_word, "no")
        st.rerun()

    with col_word:
      if lang == "uk":
        display_text = current_word
      else:
        uk_tr = translate_to_uk(current_word, lang)
        display_text = f"{current_word}  ➔  🇺🇦 {uk_tr}"

      google_url = (
          f"https://www.google.com/search?q={urllib.parse.quote(current_word)}&tbm=isch"
      )

      c_w1, c_w2 = st.columns([5, 1])
      with c_w1:
        st.markdown(
            f'<div style="padding: 8px 0;"><a href="{google_url}" target="_blank"'
            f' style="font-size: 20px; font-weight: bold; text-decoration: none;'
            f' color: #0066cc;">{display_text} 🔍</a></div>',
            unsafe_allow_html=True,
        )
      with c_w2:
        if st.button("✏️", key=f"edit_btn_{global_idx}", help="Редагувати"):
          st.session_state.editing_word_idx = global_idx
          st.rerun()

      if st.session_state.get("editing_word_idx") == global_idx:
        new_val = st.text_input(
            "Введіть нове слово:",
            value=current_word,
            key=f"edit_input_{global_idx}",
        )
        if st.button("Зберегти", key=f"save_edit_{global_idx}"):
          if new_val.strip():
            save_decision_to_db(
                lang, cat, global_idx, new_val.strip(), "yes"
            )
            st.session_state.editing_word_idx = None
            st.rerun()

    with col_yes:
      btn_yes_style = "✔" if status == "yes" else "➕ Так"
      if st.button(btn_yes_style, key=f"yes_{global_idx}", use_container_width=True):
        save_decision_to_db(lang, cat, global_idx, current_word, "yes")
        st.rerun()

  st.markdown("---")

  # --- КНОПКИ ШВИДКОГО ПЕРЕКЛЮЧЕННЯ РІВНІВ ЗНИЗУ ---
  col_prev_lvl, col_next_lvl = st.columns(2)
  with col_prev_lvl:
    if lvl > 1:
      if st.button(
          "⬅ Попередній рівень", use_container_width=True, type="secondary"
      ):
        st.session_state.selected_level = lvl - 1
        st.rerun()
  with col_next_lvl:
    if lvl < total_levels:
      if st.button(
          "Наступний рівень ➡", use_container_width=True, type="primary"
      ):
        st.session_state.selected_level = lvl + 1
        st.rerun()

  st.markdown("---")

  st.subheader("📦 Новий комплект словників")
  if st.button(
      "📥 Згенерувати та завантажити новий словник для цієї категорії",
      type="primary",
  ):
    new_dict_words = [cat_name_foreign]
    for idx, w_item in enumerate(words_list):
      decision = cat_decisions.get(idx, {"word": w_item, "status": "yes"})
      if decision["status"] == "yes" or decision["word"] != w_item:
        new_dict_words.append(decision["word"])

    file_content = "\n".join(new_dict_words)
    st.download_button(
        label=f"💾 Завантажити {cat} ({lang.upper()})",
        data=file_content,
        file_name=f"new_{lang}_{cat}",
        mime="text/plain",
    )