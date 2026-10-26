import os
import sqlite3
import urllib.parse
import requests
import streamlit as st

# Налаштування сторінки
st.set_page_config(
    page_title="Перевірка ігрових словників",
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


# Надійний переклад через публічний GTX API Google
@st.cache_data
def translate_to_uk(word, src_lang):
  if not word or src_lang == "uk":
    return word
  try:
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src_lang}&tl=uk&dt=t&q={urllib.parse.quote(word)}"
    res = requests.get(url, timeout=3).json()
    if res and isinstance(res, list) and len(res) > 0 and res[0]:
      return res[0][0][0]
  except Exception:
    pass
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

# --- ІНІЦІАЛІЗАЦІЯ СТАНУ СЕСІЇ ---
if "step" not in st.session_state:
  st.session_state.step = "select_lang"
if "selected_lang" not in st.session_state:
  st.session_state.selected_lang = None
if "selected_cat" not in st.session_state:
  st.session_state.selected_cat = None
if "selected_level" not in st.session_state:
  st.session_state.selected_level = None
if "show_suggestions" not in st.session_state:
  st.session_state.show_suggestions = False

st.session_state.user_decisions = load_all_decisions_from_db()

# --- CSS СТИЛІ ---
st.markdown("""
    <style>
    .main-title {
        font-size: 26px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    @media (max-width: 9999px) {
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
        }
        [data-testid="column"] {
            flex: 1 1 auto !important;
            min-width: unset !important;
        }
    }
    div.stButton > button {
        width: 100% !important;
        border-radius: 6px !important;
        padding: 4px 6px !important;
        font-size: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# ЕКРАН 1: ВИБІР МОВИ
# ==========================================
if st.session_state.step == "select_lang":
  st.markdown(
      '<div class="main-title">🌍 Виберіть мову словника</div>',
      unsafe_allow_html=True,
  )
  st.markdown("---")

  cols = st.columns(3)
  for i, lang in enumerate(LANGUAGES):
    flag = LANG_FLAGS.get(lang, "📌")
    with cols[i % 3]:
      if st.button(
          f"{flag} {lang.upper()}", use_container_width=True, key=f"l_{lang}"
      ):
        st.session_state.selected_lang = lang
        st.session_state.step = "select_cat"
        st.rerun()

# ==========================================
# ЕКРАН 2: ВИБІР КАТЕГОРІЇ
# ==========================================
elif st.session_state.step == "select_cat":
  lang = st.session_state.selected_lang
  flag = LANG_FLAGS.get(lang, "")

  col_b1, col_b2 = st.columns([1, 6])
  with col_b1:
    if st.button("❮ Назад", use_container_width=True):
      st.session_state.step = "select_lang"
      st.rerun()
  with col_b2:
    st.markdown(
        f'<div class="main-title">📁 Категорії ({flag} {lang.upper()})</div>',
        unsafe_allow_html=True,
    )

  st.markdown("---")

  cols = st.columns(2)
  for i, cat in enumerate(CATEGORIES):
    cat_words_foreign = dict_data.get(lang, {}).get(cat, [cat])
    cat_name_foreign = cat_words_foreign[0] if cat_words_foreign else cat

    cat_words_uk = dict_data.get("uk", {}).get(cat, [cat])
    cat_name_uk = cat_words_uk[0] if cat_words_uk else cat

    emoji_label = CAT_EMOJI.get(cat, "📁")

    with cols[i % 2]:
      btn_label = f"{emoji_label}\n{cat_name_foreign}\n({cat_name_uk})"
      if st.button(btn_label, use_container_width=True, key=f"c_{cat}"):
        st.session_state.selected_cat = cat
        st.session_state.step = "select_levels"
        st.rerun()

# ==========================================
# ЕКРАН 3: СІТКА ВИБОРУ РІВНІВ
# ==========================================
elif st.session_state.step == "select_levels":
  lang = st.session_state.selected_lang
  cat = st.session_state.selected_cat

  col_b1, col_b2 = st.columns([1, 6])
  with col_b1:
    if st.button("❮ Назад", use_container_width=True):
      st.session_state.step = "select_cat"
      st.rerun()
  with col_b2:
    cat_display_name = CAT_EMOJI.get(cat, cat)
    st.markdown(
        f'<div class="main-title">📊 Рівні: {cat_display_name}</div>',
        unsafe_allow_html=True,
    )

  st.markdown("---")

  cat_words = dict_data.get(lang, {}).get(cat, [cat])[1:]
  total_levels = max(1, (len(cat_words) + LEVEL_SIZE - 1) // LEVEL_SIZE)

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
# ЕКРАН 4: ІГРОВИЙ ЕКРАН (ТАБЛИЦЯ СЛІВ)
# ==========================================
elif st.session_state.step == "gameplay":
  lang = st.session_state.selected_lang
  cat = st.session_state.selected_cat
  lvl = st.session_state.selected_level

  full_list = dict_data.get(lang, {}).get(cat, [cat])
  cat_name_foreign = full_list[0] if full_list else ""
  uk_list = dict_data.get("uk", {}).get(cat, [cat])
  cat_name_uk = uk_list[0] if uk_list else ""
  words_list = full_list[1:] if len(full_list) > 1 else []

  total_levels = max(1, (len(words_list) + LEVEL_SIZE - 1) // LEVEL_SIZE)

  col_b1, col_b2 = st.columns([1, 8])
  with col_b1:
    if st.button("❮ Рівні", use_container_width=True):
      st.session_state.selected_level = None
      st.session_state.selected_level = None
      st.session_state.show_suggestions = False
      st.session_state.step = "select_levels"
      st.rerun()
  with col_b2:
    flag = LANG_FLAGS.get(lang, "")
    st.markdown(
        f"### {flag} {cat_name_foreign} ({cat_name_uk}) — Рівень {lvl} з"
        f" {total_levels}",
        unsafe_allow_html=True,
    )

  st.markdown("---")

  start_idx = (lvl - 1) * LEVEL_SIZE
  end_idx = min(start_idx + LEVEL_SIZE, len(words_list))
  level_words = words_list[start_idx:end_idx]

  if lang not in st.session_state.user_decisions:
    st.session_state.user_decisions[lang] = {}
  if cat not in st.session_state.user_decisions[lang]:
    st.session_state.user_decisions[lang][cat] = {}

  cat_decisions = st.session_state.user_decisions[lang][cat]

  # Шапка таблиці
  col_t1, col_t2, col_t3 = st.columns([6, 3, 3])
  with col_t1:
    st.markdown("**Слово**")
  with col_t2:
    st.markdown("**Переклад (укр.)**")
  with col_t3:
    st.markdown("**Зображення Google**")

  st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

  # Рядки слів
  for i, original_word in enumerate(level_words):
    global_idx = start_idx + i
    stored_data = cat_decisions.get(
        global_idx, {"word": original_word, "status": "yes"}
    )
    current_word = stored_data["word"]
    status = stored_data["status"]

    bg_color = "transparent"
    text_decoration = "none"
    text_color = "inherit"

    if status == "yes":
      bg_color = "#e6f4ea"
    elif status == "no":
      bg_color = "#fce8e6"
      text_decoration = "line-through"
      text_color = "#888888"

    c_btn_no, c_word, c_tr, c_img, c_btn_yes = st.columns([1, 4, 3, 1.5, 1.5])

    with c_btn_no:
      is_no = status == "no"
      btn_no_label = "❌" if is_no else "➖"
      if st.button(
          btn_no_label, key=f"no_{global_idx}", use_container_width=True
      ):
        save_decision_to_db(lang, cat, global_idx, current_word, "no")
        st.rerun()

    with c_word:
      st.markdown(
          f"<div style='background-color: {bg_color}; padding: 6px 8px;"
          " border-radius: 6px; font-weight: 500; text-decoration:"
          f" {text_decoration}; color: {text_color};'>{i+1}."
          f" <b>{current_word}</b></div>",
          unsafe_allow_html=True,
      )

    with c_tr:
      if lang == "uk":
        st.markdown(
            "<div style='padding-top: 6px; color: #666;'>—</div>",
            unsafe_allow_html=True,
        )
      else:
        uk_tr = translate_to_uk(current_word, lang)
        st.markdown(
            f"<div style='padding-top: 6px; color: {text_color}; text-decoration:"
            f" {text_decoration};'>{uk_tr}</div>",
            unsafe_allow_html=True,
        )

    with c_img:
      google_url = (
          f"https://www.google.com/search?q={urllib.parse.quote(current_word)}&tbm=isch"
      )
      st.markdown(
          f'<div style="padding-top: 4px;"><a href="{google_url}"'
          ' target="_blank" style="text-decoration: none; font-size: 20px;"'
          ' title="Google Картинки">🖼️</a></div>',
          unsafe_allow_html=True,
      )

    with c_btn_yes:
      is_yes = status == "yes" or status is None
      btn_yes_label = "✔" if is_yes else "➕"
      if st.button(
          btn_yes_label, key=f"yes_{global_idx}", use_container_width=True
      ):
        save_decision_to_db(lang, cat, global_idx, current_word, "yes")
        st.rerun()

  st.markdown("---")

  # --- ПОЛЕ ДОДАВАННЯ НОВОГО СЛОВА ---
  st.markdown("**Додати нове слово**")
  new_word_input = st.text_input(
      "Додати нове слово",
      placeholder=(
          f"Введіть слово ({lang.upper()})"
          if lang != "uk"
          else "Введіть слово українською"
      ),
      label_visibility="collapsed",
  )

  col_add_btn1, col_add_btn2 = st.columns([4, 1])
  with col_add_btn1:
    pass
  with col_add_btn2:
    add_clicked = st.button("➕ Додати", use_container_width=True, type="primary")


  # Функція для додавання/заміни слова
  def process_new_word(word_to_add):
    clean_new_word = word_to_add.strip().lower()
    all_existing_words = [
        cat_decisions.get(idx, {"word": w})["word"].lower()
        for idx, w in enumerate(words_list)
    ]

    if clean_new_word in all_existing_words:
      existing_idx = all_existing_words.index(clean_new_word)
      found_level = (existing_idx // LEVEL_SIZE) + 1
      st.warning(
          f"❌ Таке слово вже є у словнику на рівні {found_level} (позиція"
          f" {(existing_idx % LEVEL_SIZE) + 1})!"
      )
    else:
      target_idx = None
      for i in range(len(level_words)):
        g_idx = start_idx + i
        if cat_decisions.get(g_idx, {}).get("status") == "no":
          target_idx = g_idx
          break

      if target_idx is not None:
        save_decision_to_db(lang, cat, target_idx, word_to_add.strip(), "yes")
        st.success("✅ Слово успішно замість відхиленого на цьому рівні!")
        st.rerun()
      else:
        words_list.append(word_to_add.strip())
        new_global_idx = len(words_list) - 1
        save_decision_to_db(
            lang, cat, new_global_idx, word_to_add.strip(), "yes"
        )
        st.success("✅ Нове слово додано в кінець словника.")
        st.rerun()


  if add_clicked and new_word_input.strip():
    process_new_word(new_word_input.strip())

  st.markdown("<br>", unsafe_allow_html=True)

  # --- КНОПКИ НАВІГАЦІЇ ТА ПРОПОЗИЦІЇ ЗАМІНИ ---
  col_nav1, col_nav_sugg, col_nav2 = st.columns([1, 1, 1])

  with col_nav1:
    if lvl > 1:
      if st.button("❮ Попередній рівень", use_container_width=True):
        st.session_state.selected_level = lvl - 1
        st.session_state.show_suggestions = False
        st.rerun()

  with col_nav_sugg:
    if st.button("💡 Запропонувати слова на заміну", use_container_width=True):
      st.session_state.show_suggestions = not st.session_state.show_suggestions
      st.rerun()

  with col_nav2:
    if lvl < total_levels:
      if st.button(
          "Наступний рівень ❯", use_container_width=True, type="primary"
      ):
        st.session_state.selected_level = lvl + 1
        st.session_state.show_suggestions = False
        st.rerun()

  # Вивід інтерактивних пропозицій, якщо кнопка активована
  if st.session_state.show_suggestions:
    st.markdown("---")
    st.markdown("##### 💡 Натисніть на слово, щоб підставити його на заміну:")

    # Збираємо унікальні слова з інших рівнів цієї ж мови
    current_set = {w.lower() for w in words_list}
    available_suggestions = []
    full_lang_words = dict_data.get(lang, {}).get(cat, [])[1:]
    for lw in full_lang_words:
      if lw.lower() not in current_set:
        available_suggestions.append(lw)

    if available_suggestions:
      # Виводимо пропозиції у вигляді сітки клікабельних кнопок
      sugg_cols = st.columns(3)
      for idx, sug_word in enumerate(available_suggestions[:9]):
        with sugg_cols[idx % 3]:
          if st.button(f"✨ {sug_word}", key=f"sug_btn_{idx}", use_container_width=True):
            process_new_word(sug_word)
    else:
      st.info("Усі можливі слова з інших рівнів вже задіяні у цій категорії!")

  st.markdown("---")

  # Експорт оновленого словника
  if st.button(
      "📦 Експортувати оновлений словник категорії", use_container_width=True
  ):
    final_words_export = [cat_name_foreign]
    for idx, w_item in enumerate(words_list):
      decision = cat_decisions.get(idx, {"word": w_item, "status": "yes"})
      if decision["status"] != "no":
        final_words_export.append(decision["word"])

    file_content = "\n".join(final_words_export)
    st.download_button(
        label=f"💾 Завантажити {cat} ({lang.upper()})",
        data=file_content,
        file_name=f"updated_{lang}_{cat}",
        mime="text/plain",
        use_container_width=True,
    )
