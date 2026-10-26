import os
import sqlite3
import urllib.parse
from deep_translator import GoogleTranslator
import streamlit as st

# Налаштування сторінки
st.set_page_config(
    page_title="Перевірка словника",
    layout="centered",
    initial_sidebar_state="collapsed",
)

LANGUAGES = ["de", "en", "es", "fr", "it", "nl", "pl", "pt", "uk"]
LANG_FLAGS = {
    "de": "🇩🇪",
    "en": "🇬🇧",
    "es": "🇪🇸",
    "fr": "🇫🇷",
    "it": "🇮🇹",
    "nl": "🇳🇱",
    "pl": "🇵🇱",
    "pt": "🇵🇹",
    "uk": "🇺🇦",
}

CATEGORIES = ["animals.txt", "food.txt", "nature.txt", "travel.txt"]
CAT_EMOJI = {
    "animals.txt": "🐕 Тварини",
    "food.txt": "🍳 Їжа та напої",
    "nature.txt": "🌳 Природа",
    "travel.txt": "🚌 Подорожі",
}

LEVEL_SIZE = 10  # 10 слів на рівень
DB_NAME = "game_progress.db"


# --- БАЗА ДАНИХ СЕРВЕРА ---
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


def translate_to_uk(word, src_lang):
  if src_lang == "uk" or not word:
    return word
  try:
    return GoogleTranslator(source=src_lang, target="uk").translate(word)
  except Exception:
    return word


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

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ ---
if "selected_lang" not in st.session_state:
  st.session_state.selected_lang = "en"
if "selected_cat" not in st.session_state:
  st.session_state.selected_cat = "food.txt"
if "selected_level" not in st.session_state:
  st.session_state.selected_level = 1
if "editing_word_idx" not in st.session_state:
  st.session_state.editing_word_idx = None

st.session_state.user_decisions = load_all_decisions_from_db()

# --- СТИЛІ ДЛЯ СУЧАСНОГО ІНТЕРФЕЙСУ ---
st.markdown("""
    <style>
    .main-title {
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    .word-row {
        background-color: #ffffff;
        padding: 10px 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    </style>
""", unsafe_allow_html=True)

# Заголовок та кнопка меню справа
col_h1, col_h2, col_h3 = st.columns([1, 8, 1])
with col_h1:
  if st.button("❮", help="Назад"):
    pass
with col_h2:
  st.markdown(
      '<div class="main-title">Перевірка словника</div>', unsafe_allow_html=True
  )
with col_h3:
  st.markdown("### ⋮")

st.markdown("---")

# --- ВЕРХНІЙ БЛОК: ТРИ ФІЛЬТРИ В ОДИН РЯДОК (Мова, Категорія, Рівень) ---
curr_lang = st.session_state.selected_lang
curr_cat = st.session_state.selected_cat

# Вираховуємо кількість рівнів для поточної категорії
full_list = dict_data.get(curr_lang, {}).get(curr_cat, [curr_cat])
words_list = full_list[1:] if len(full_list) > 1 else []
total_levels = max(1, (len(words_list) + LEVEL_SIZE - 1) // LEVEL_SIZE)

if st.session_state.selected_level > total_levels:
  st.session_state.selected_level = total_levels

col_f1, col_f2, col_f3 = st.columns(3)

with col_f1:
  selected_lang_full = st.selectbox(
      "Мова",
      LANGUAGES,
      index=LANGUAGES.index(curr_lang),
      format_func=lambda x: f"{LANG_FLAGS.get(x, '')} {x.capitalize()}",
  )
  if selected_lang_full != curr_lang:
    st.session_state.selected_lang = selected_lang_full
    st.session_state.selected_level = 1
    st.rerun()

with col_f2:
  selected_cat_full = st.selectbox(
      "Категорія",
      CATEGORIES,
      index=CATEGORIES.index(curr_cat),
      format_func=lambda x: CAT_EMOJI.get(x, x),
  )
  if selected_cat_full != curr_cat:
    st.session_state.selected_cat = selected_cat_full
    st.session_state.selected_level = 1
    st.rerun()

with col_f3:
  selected_lvl_num = st.selectbox(
      "Рівень",
      range(1, total_levels + 1),
      index=st.session_state.selected_level - 1,
  )
  if selected_lvl_num != st.session_state.selected_level:
    st.session_state.selected_level = selected_lvl_num
    st.rerun()

st.markdown("---")

# Завантажуємо слова поточного рівня
lvl = st.session_state.selected_level
start_idx = (lvl - 1) * LEVEL_SIZE
end_idx = min(start_idx + LEVEL_SIZE, len(words_list))
level_words = words_list[start_idx:end_idx]

cat_name_foreign = full_list[0] if full_list else ""
uk_list = dict_data.get("uk", {}).get(curr_cat, [curr_cat])
cat_name_uk = uk_list[0] if uk_list else ""

if curr_lang not in st.session_state.user_decisions:
  st.session_state.user_decisions[curr_lang] = {}
if curr_cat not in st.session_state.user_decisions[curr_lang]:
  st.session_state.user_decisions[curr_lang][curr_cat] = {}

cat_decisions = st.session_state.user_decisions[curr_lang][curr_cat]

# Шаблони заголовків таблиці
col_t1, col_t2, col_t3 = st.columns([6, 3, 3])
with col_t1:
  st.markdown("**Слово**")
with col_t2:
  st.markdown("**Переклад (укр.)**")
with col_t3:
  st.markdown("**Зображення Google**")

st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

# Виведення 10 слів рівня у вигляді зручної таблиці
for i, original_word in enumerate(level_words):
  global_idx = start_idx + i
  stored_data = cat_decisions.get(
      global_idx, {"word": original_word, "status": "yes"}
  )
  current_word = stored_data["word"]
  status = stored_data["status"]

  c_btn_no, c_word, c_tr, c_img, c_btn_yes = st.columns([1, 4, 3, 1.5, 1.5])

  with c_btn_no:
    is_no = status == "no"
    btn_no_label = "❌" if is_no else "➖"
    if st.button(
        btn_no_label, key=f"no_{global_idx}", use_container_width=True
    ):
      save_decision_to_db(curr_lang, curr_cat, global_idx, current_word, "no")
      st.rerun()

  with c_word:
    st.markdown(
        f"<div style='padding-top: 6px; font-weight: 500;'>{i+1}. "
        f"<b>{current_word}</b></div>",
        unsafe_allow_html=True,
    )

  with c_tr:
    if curr_lang == "uk":
      st.markdown(
          "<div style='padding-top: 6px; color: #666;'>—</div>",
          unsafe_allow_html=True,
      )
    else:
      uk_tr = translate_to_uk(current_word, curr_lang)
      st.markdown(
          f"<div style='padding-top: 6px; color: #333;'>{uk_tr}</div>",
          unsafe_allow_html=True,
      )

  with c_img:
    google_url = (
        f"https://www.google.com/search?q={urllib.parse.quote(current_word)}&tbm=isch"
    )
    st.markdown(
        f'<div style="padding-top: 4px;"><a href="{google_url}"'
        ' target="_blank" style="text-decoration: none; font-size: 20px;"'
        f' title="Знайти в Google">🖼️</a></div>',
        unsafe_allow_html=True,
    )

  with c_btn_yes:
    is_yes = status == "yes" or status is None
    btn_yes_label = "✔" if is_yes else "➕"
    if st.button(
        btn_yes_label, key=f"yes_{global_idx}", use_container_width=True
    ):
      save_decision_to_db(curr_lang, curr_cat, global_idx, current_word, "yes")
      st.rerun()

st.markdown("---")

# --- ПОЛЕ ДОДАВАННЯ НОВОГО СЛОВА ---
st.markdown("**Додати нове слово**")
new_word_input = st.text_input(
    "Додати нове слово",
    placeholder=(
        f"Введіть слово ({curr_lang.upper()})"
        if curr_lang != "uk"
        else "Введіть слово українською"
    ),
    label_visibility="collapsed",
)

col_add_btn1, col_add_btn2 = st.columns([4, 1])
with col_add_btn1:
  pass
with col_add_btn2:
  add_clicked = st.button("➕ Додати", use_container_width=True, type="primary")

if add_clicked and new_word_input.strip():
  clean_new_word = new_word_input.strip().lower()

  # Перевірка на унікальність у всьому словнику категорії
  all_existing_words = [
      cat_decisions.get(idx, {"word": w})["word"].lower()
      for idx, w in enumerate(words_list)
  ]

  if clean_new_word in all_existing_words:
    # Знаходимо на якому рівні воно вже є
    existing_idx = all_existing_words.index(clean_new_word)
    found_level = (existing_idx // LEVEL_SIZE) + 1
    st.warning(
        f"❌ Таке слово вже є у словнику на рівні {found_level} (позиція"
        f" {(existing_idx % LEVEL_SIZE) + 1})!"
    )
  else:
    # Шукаємо перше відхилене слово ("no") на поточному рівні, щоб замінити його
    target_idx = None
    for i in range(len(level_words)):
      g_idx = start_idx + i
      if cat_decisions.get(g_idx, {}).get("status") == "no":
        target_idx = g_idx
        break

    if target_idx is not None:
      # Замінюємо відхилене слово
      save_decision_to_db(
          curr_lang, curr_cat, target_idx, new_word_input.strip(), "yes"
      )
      st.success(
          f"✅ Слово '{new_word_input.strip()}' успішно замість відхиленого"
          " слова на цьому рівні!"
      )
      st.rerun()
    else:
      # Якщо на рівні всі прийняті, додаємо в кінець списку слів
      words_list.append(new_word_input.strip())
      new_global_idx = len(words_list) - 1
      save_decision_to_db(
          curr_lang, curr_cat, new_global_idx, new_word_input.strip(), "yes"
      )
      st.success(
          "✅ Всі слова на рівні прийняті! Нове слово додано в кінець словника."
      )
      st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- КНОПКИ НАВІГАЦІЇ ПО РІВНЯХ ТА ПРОПОЗИЦІЇ ЗАМІНИ ---
col_nav1, col_nav_sugg, col_nav2 = st.columns([1, 1, 1])

with col_nav1:
  if lvl > 1:
    if st.button("❮ Попередній рівень", use_container_width=True):
      st.session_state.selected_level = lvl - 1
      st.rerun()

with col_nav_sugg:
  if st.button("💡 Запропонувати слова на заміну", use_container_width=True):
    # Шукаємо слова з інших мов/категорій або не задіяні
    suggestions = []
    current_set = {w.lower() for w in words_list}
    for l_key in LANGUAGES:
      l_words = dict_data.get(l_key, {}).get(curr_cat, [])[1:]
      for lw in l_words:
        # Перекладаємо на поточну мову якщо треба
        translated_s = (
            translate_to_uk(lw, l_key) if curr_lang == "uk" else lw
        )
        if translated_s.lower() not in current_set:
          suggestions.append(translated_s)

    if suggestions:
      st.info(
          "💡 Рекомендовані слова для заміни: "
          + ", ".join(suggestions[:5])
          + "..."
      )
    else:
      st.info("Усі можливі слова вже задіяні у цій категорії!")

with col_nav2:
  if lvl < total_levels:
    if st.button("Наступний рівень ❯", use_container_width=True, type="primary"):
      st.session_state.selected_level = lvl + 1
      st.rerun()

st.markdown("---")

# Експорт збереженого словника
if st.button("📦 Експортувати оновлений словник категорії", use_container_width=True):
  final_words_export = [cat_name_foreign]
  for idx, w_item in enumerate(words_list):
    decision = cat_decisions.get(idx, {"word": w_item, "status": "yes"})
    if decision["status"] != "no":
      final_words_export.append(decision["word"])

  file_content = "\n".join(final_words_export)
  st.download_button(
      label=f"💾 Завантажити {curr_cat} ({curr_lang.upper()})",
      data=file_content,
      file_name=f"updated_{curr_lang}_{curr_cat}",
      mime="text/plain",
      use_container_width=True,
  )
