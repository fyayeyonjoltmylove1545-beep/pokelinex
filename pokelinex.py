import streamlit as st
from PIL import Image
import sqlite3
from datetime import datetime
import base64
import sys
import os

from google import genai
from google.genai import types


# =========================================================
# 0. DOSYA YOLU YARDIMCISI
# =========================================================

def get_asset_path(filename):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, filename)


# =========================================================
# 1. SAYFA YAPILANDIRMASI
# =========================================================

st.set_page_config(
    page_title="PokéLineX: PokeAI Asistanı",
    page_icon="⚡",
    layout="wide"
)


# =========================================================
# 2. GEMINI API AYARLARI
# =========================================================

# Modeli değiştirmek gerekirse sadece bu satırı değiştir.
MODEL_NAME = "gemini-3.1-flash-lite"


# API anahtarını Streamlit Secrets'tan al
GOOGLE_API_KEY = None

try:
    GOOGLE_API_KEY = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass


# Alternatif olarak ortam değişkenini kontrol et
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")


# API anahtarı bulunamazsa uygulamayı durdur
if not GOOGLE_API_KEY:
    st.error(
        "⚠️ Gemini API anahtarı bulunamadı.\n\n"
        "Lütfen `.streamlit/secrets.toml` dosyanı kontrol et."
    )
    st.stop()


# Gemini istemcisi
@st.cache_resource
def get_genai_client(api_key):
    return genai.Client(api_key=api_key)


client = get_genai_client(GOOGLE_API_KEY)


# =========================================================
# 3. VERİTABANI
# =========================================================

conn = sqlite3.connect(
    "poke_history.db",
    check_same_thread=False
)

c = conn.cursor()


# Sohbet geçmişi tablosu
c.execute("""
CREATE TABLE IF NOT EXISTS history (
    email TEXT,
    role TEXT,
    content TEXT,
    timestamp TEXT,
    session_id TEXT
)
""")

conn.commit()


# Kullanıcı tablosu
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    email TEXT UNIQUE,
    password TEXT
)
""")

conn.commit()


# =========================================================
# 4. SOHBET ID
# =========================================================

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = (
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )


# =========================================================
# 5. LOGO VE DOSYA YOLLARI
# =========================================================

BOT_AVATAR = get_asset_path(
    "PokeLineX-bot-logo.png"
)


# =========================================================
# 6. ARKA PLAN SİSTEMİ
# =========================================================

def set_bg(image_filename):

    image_path = get_asset_path(
        image_filename
    )

    if os.path.exists(image_path):

        with open(image_path, "rb") as f:
            data = base64.b64encode(
                f.read()
            ).decode()

        st.markdown(
            f"""
            <style>

            .stApp {{
                background-image:
                    url("data:image/png;base64,{data}");

                background-size: cover;
                background-attachment: fixed;
            }}

            h1 {{
                color: white !important;

                text-shadow:
                    2px 2px 8px black;

                background-color:
                    rgba(0, 0, 0, 0.4);

                padding: 10px;
                border-radius: 10px;

                width: fit-content;
            }}

            .stChatMessage {{
                background-color:
                    rgba(0, 0, 0, 0.7) !important;

                border:
                    1px solid
                    rgba(255, 255, 255, 0.2);

                border-radius: 15px;

                padding: 15px;
                margin-bottom: 10px;

                color: white !important;

                box-shadow:
                    2px 2px 15px
                    rgba(0,0,0,0.5);
            }}

            .stChatMessage p,
            .stChatMessage span {{
                color: white !important;
            }}

            [data-testid="stSidebar"] {{
                background-color:
                    rgba(0, 0, 0, 0.8) !important;
            }}

            [data-testid="stSidebar"] * {{
                color: white !important;
            }}

            .stFileUploader {{
                background-color:
                    rgba(255, 255, 255, 0.1);

                padding: 10px;
                border-radius: 10px;
            }}

            </style>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# 7. TEMA SEÇİMİ
# =========================================================

if os.path.exists(BOT_AVATAR):
    st.sidebar.image(
        BOT_AVATAR,
        width=80
    )


st.sidebar.subheader(
    "Tema Seçimi"
)


template = st.sidebar.selectbox(
    "Karakter Teması",
    [
        "Pikachu",
        "Gengar",
        "Charizard"
    ]
)


templates = {

    "Pikachu":
        "pikachu_bg.jpg",

    "Gengar":
        "gengar_bg.jpg",

    "Charizard":
        "charizard_bg.jpg"
}


set_bg(
    templates[template]
)


# =========================================================
# 8. OTOMATİK GİRİŞ
# =========================================================

USER_FILE = "last_user.txt"


if "user_email" not in st.session_state:

    if os.path.exists(USER_FILE):

        with open(
            USER_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            st.session_state.user_email = (
                f.read().strip()
            )

    else:

        st.session_state.user_email = None


# =========================================================
# 9. GİRİŞ / KAYIT EKRANI
# =========================================================

if not st.session_state.user_email:

    if os.path.exists(BOT_AVATAR):

        st.image(
            BOT_AVATAR,
            width=100
        )


    st.title(
        "⚡ PokéLineX: Giriş Yap / Kayıt Ol"
    )


    tab1, tab2 = st.tabs(
        [
            "Giriş Yap",
            "Kayıt Ol"
        ]
    )


    # -----------------------------------------------------
    # GİRİŞ
    # -----------------------------------------------------

    with tab1:

        login_email = st.text_input(
            "Gmail Adresi:",
            key="login_email"
        )


        login_pass = st.text_input(
            "Şifre:",
            type="password",
            key="login_pass"
        )


        if st.button("Giriş Yap"):

            if "@gmail.com" in login_email:

                c.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE email=?
                    AND password=?
                    """,
                    (
                        login_email,
                        login_pass
                    )
                )


                user = c.fetchone()


                if user:

                    st.session_state.user_email = (
                        login_email
                    )


                    with open(
                        USER_FILE,
                        "w",
                        encoding="utf-8"
                    ) as f:

                        f.write(login_email)


                    st.success(
                        "Giriş başarılı!"
                    )

                    st.rerun()

                else:

                    st.error(
                        "E-posta veya şifre hatalı!"
                    )

            else:

                st.error(
                    "Lütfen geçerli bir Gmail adresi girin."
                )


    # -----------------------------------------------------
    # KAYIT
    # -----------------------------------------------------

    with tab2:

        reg_email = st.text_input(
            "Gmail Adresi:",
            key="reg_email"
        )


        reg_pass = st.text_input(
            "Şifre Belirleyin:",
            type="password",
            key="reg_pass"
        )


        if st.button("Hesap Oluştur"):

            if (
                "@gmail.com" in reg_email
                and len(reg_pass) >= 4
            ):

                try:

                    c.execute(
                        "INSERT INTO users VALUES (?, ?)",
                        (
                            reg_email,
                            reg_pass
                        )
                    )

                    conn.commit()


                    st.success(
                        "Hesabınız oluşturuldu! "
                        "Şimdi Giriş Yap sekmesinden "
                        "giriş yapabilirsiniz."
                    )

                except sqlite3.IntegrityError:

                    st.error(
                        "Bu e-posta adresi zaten kayıtlı!"
                    )

            else:

                st.error(
                    "Geçerli bir Gmail adresi ve "
                    "en az 4 haneli bir şifre girin."
                )


    st.stop()


# =========================================================
# 10. POKELINEX SİSTEM TALİMATI
# =========================================================

POKE_SYSTEM_INSTRUCTION = """

Senin adın PokéLineX.

Sen Pokémon konusunda uzmanlaşmış
bir yapay zeka asistanısın.

Görevlerin:

- Pokémon bilgilerini açıklamak
- Pokémon oyunlarında yardımcı olmak
- Pokémon TCG hakkında bilgi vermek
- Pokémon haberlerini takip etmek
- Yeni oyunları araştırmak
- Etkinlikleri takip etmek
- Güncellemeleri ve yamaları araştırmak
- Pokémon içerikleri üreten kullanıcılara
  video ve içerik fikirleri konusunda yardımcı olmak

Kullanıcı güncel bir Pokémon haberi,
yeni TCG paketi,
oyun güncellemesi,
etkinlik,
duyuru veya benzeri güncel bir konu sorarsa
canlı web araması kullan.

Mümkün olduğunda güvenilir kaynakları tercih et:

- Pokémon.com
- Bulbapedia
- Serebii
- PokéBeach
- Pokémon Database
- Nintendo Life
- PokéOS

Türkçe cevap ver.

Kullanıcıyla doğal,
yardımsever,
bilgili ve samimi bir şekilde konuş.

"""


# =========================================================
# 11. SIDEBAR KONTROLLERİ
# =========================================================

st.sidebar.title(
    f"👤 {st.session_state.user_email}"
)

st.sidebar.markdown("---")

st.sidebar.subheader(
    "Kontroller"
)


use_web_search = st.sidebar.checkbox(
    "🌐 Web Araması (Canlı)",
    value=False
)


# =========================================================
# 12. GEMINI CONFIG
# =========================================================

if use_web_search:

    current_config = (
        types.GenerateContentConfig(

            system_instruction=
                POKE_SYSTEM_INSTRUCTION,

            tools=[
                types.Tool(
                    google_search=
                        types.GoogleSearch()
                )
            ]
        )
    )

else:

    current_config = (
        types.GenerateContentConfig(

            system_instruction=
                POKE_SYSTEM_INSTRUCTION
        )
    )


# =========================================================
# 13. CHAT OLUŞTURMA FONKSİYONU
# =========================================================

def create_chat():

    c.execute(
        """
        SELECT role, content
        FROM history
        WHERE email=?
        AND session_id=?
        ORDER BY timestamp ASC
        """,
        (
            st.session_state.user_email,
            st.session_state.current_session_id
        )
    )


    db_history = c.fetchall()


    formatted_history = []


    for role, content in db_history:

        gemini_role = (
            "model"
            if role == "assistant"
            else "user"
        )


        formatted_history.append(
            {
                "role": gemini_role,

                "parts": [
                    {
                        "text": content
                    }
                ]
            }
        )


    return client.chats.create(

        model=MODEL_NAME,

        config=current_config,

        history=formatted_history
    )


# =========================================================
# 14. WEB ARAMA DURUMU DEĞİŞİRSE CHAT'İ YENİLE
# =========================================================

if "web_search_state" not in st.session_state:

    st.session_state.web_search_state = (
        use_web_search
    )


if (
    st.session_state.web_search_state
    != use_web_search
):

    st.session_state.web_search_state = (
        use_web_search
    )

    st.session_state.chat = create_chat()


# =========================================================
# 15. GEÇMİŞİ SİL
# =========================================================

if st.sidebar.button(
    "🗑️ Geçmişi Sil"
):

    c.execute(
        """
        DELETE FROM history
        WHERE email=?
        AND session_id=?
        """,
        (
            st.session_state.user_email,
            st.session_state.current_session_id
        )
    )


    conn.commit()


    st.session_state.chat = (
        client.chats.create(

            model=MODEL_NAME,

            config=current_config,

            history=[]
        )
    )


    st.rerun()


# =========================================================
# 16. YENİ SOHBET
# =========================================================

if st.sidebar.button(
    "➕ Yeni Sohbet"
):

    st.session_state.current_session_id = (
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    )


    st.session_state.chat = (
        client.chats.create(

            model=MODEL_NAME,

            config=current_config,

            history=[]
        )
    )


    st.rerun()


# =========================================================
# 17. CHAT İLK KEZ OLUŞTURULUYOR
# =========================================================

if "chat" not in st.session_state:

    st.session_state.chat = create_chat()


# =========================================================
# 18. ANA BAŞLIK
# =========================================================

col1, col2 = st.columns(
    [1, 6]
)


with col1:

    if os.path.exists(BOT_AVATAR):

        st.image(
            BOT_AVATAR,
            width=120
        )


with col2:

    st.title(
        "PokéLineX: PokeAI Asistanı"
    )


# =========================================================
# 19. MESAJ GEÇMİŞİ
# =========================================================

c.execute(
    """
    SELECT role, content
    FROM history
    WHERE email=?
    AND session_id=?
    ORDER BY timestamp ASC
    """,
    (
        st.session_state.user_email,
        st.session_state.current_session_id
    )
)


for role, content in c.fetchall():

    avatar = (
        BOT_AVATAR
        if (
            role == "assistant"
            and os.path.exists(BOT_AVATAR)
        )
        else None
    )


    with st.chat_message(
        role,
        avatar=avatar
    ):

        st.markdown(content)


# =========================================================
# 20. MEDYA VE MESAJ ALANI
# =========================================================

st.markdown("---")


col_btn, col_input = st.columns(
    [1, 11]
)


with col_btn:

    with st.popover("➕"):

        uploaded_file = (
            st.file_uploader(

                "Görsel Yükle",

                type=[
                    "jpg",
                    "png",
                    "jpeg"
                ],

                key="media_upload"
            )
        )


with col_input:

    user_input = st.chat_input(
        "Pokémonlar hakkında sor...",
        key="poke_chat_input_main"
    )


# =========================================================
# 21. MESAJ GÖNDER
# =========================================================

if user_input:

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


    # Kullanıcı mesajını veritabanına kaydet
    c.execute(
        """
        INSERT INTO history
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            st.session_state.user_email,
            "user",
            user_input,
            now,
            st.session_state.current_session_id
        )
    )


    conn.commit()


    # Kullanıcı mesajını göster
    with st.chat_message("user"):

        st.markdown(
            user_input
        )


    # -----------------------------------------------------
    # AI CEVABI
    # -----------------------------------------------------

    with st.chat_message(
        "assistant",
        avatar=(
            BOT_AVATAR
            if os.path.exists(BOT_AVATAR)
            else None
        )
    ):

        try:

            # ---------------------------------------------
            # GÖRSEL + MESAJ
            # ---------------------------------------------

            if uploaded_file:

                img = Image.open(
                    uploaded_file
                )


                response = (
                    st.session_state.chat
                    .send_message(
                        [
                            user_input,
                            img
                        ]
                    )
                )


            # ---------------------------------------------
            # SADECE MESAJ
            # ---------------------------------------------

            else:

                response = (
                    st.session_state.chat
                    .send_message(
                        user_input
                    )
                )


            # Cevabı al
            response_text = response.text


            # Cevabı ekrana yaz
            st.markdown(
                response_text
            )


            # AI cevabını kaydet
            c.execute(
                """
                INSERT INTO history
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    st.session_state.user_email,
                    "assistant",
                    response_text,
                    now,
                    st.session_state.current_session_id
                )
            )


            conn.commit()


        except Exception as e:

            error_text = str(e)


            # ---------------------------------------------
            # 429
            # ---------------------------------------------

            if (
                "429" in error_text
                or
                "RESOURCE_EXHAUSTED"
                in error_text
            ):

                st.error(
                    "⚠️ API kullanım kotası "
                    "dolmuş olabilir."
                )


                st.code(
                    error_text,
                    language="text"
                )


            # ---------------------------------------------
            # 401
            # ---------------------------------------------

            elif (
                "401" in error_text
                or
                "UNAUTHENTICATED"
                in error_text
                or
                "Unauthorized"
                in error_text
            ):

                st.error(
                    "🔐 Gemini API kimlik "
                    "doğrulama hatası (401)."
                )


                st.warning(
                    "API anahtarını ve "
                    "Gemini API erişimini "
                    "kontrol edin."
                )


                st.code(
                    error_text,
                    language="text"
                )


            # ---------------------------------------------
            # DİĞER HATALAR
            # ---------------------------------------------

            else:

                st.error(
                    "⚠️ PokéLineX hata verdi:"
                )


                st.code(
                    error_text,
                    language="text"
                )


# =========================================================
# 22. SOHBET GEÇMİŞLERİ
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "💬 Sohbet Geçmişi"
)


c.execute(
    """
    SELECT session_id, MIN(content)
    FROM history
    WHERE email=?
    AND role='user'
    GROUP BY session_id
    ORDER BY MIN(timestamp) DESC
    """,
    (
        st.session_state.user_email,
    )
)


user_sessions = c.fetchall()


for sess_id, first_msg in user_sessions:

    button_label = (
        first_msg[:25] + "..."
        if len(first_msg) > 25
        else first_msg
    )


    is_active = (
        "⚡ "
        if (
            sess_id
            ==
            st.session_state.current_session_id
        )
        else "🗨️ "
    )


    if st.sidebar.button(
        f"{is_active}{button_label}",
        key=f"session_{sess_id}"
    ):

        st.session_state.current_session_id = (
            sess_id
        )


        st.session_state.chat = (
            create_chat()
        )


        st.rerun()


# =========================================================
# 23. ÇIKIŞ
# =========================================================

if st.sidebar.button(
    "🚪 Çıkış Yap"
):

    if os.path.exists(USER_FILE):

        os.remove(USER_FILE)


    st.session_state.user_email = None

    st.rerun()


# =========================================================
# 24. GÜVENİLİR KAYNAKLAR
# =========================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "🌐 Güvenilir Kaynaklar"
)


st.sidebar.markdown(
    "[Serebii](https://www.serebii.net) | "
    "[Bulbapedia](https://bulbapedia.bulbagarden.net)"
)


st.sidebar.markdown(
    "[PokéDB](https://pokemondb.net) | "
    "[Official Pokémon](https://www.pokemon.com)"
)


st.sidebar.markdown(
    "[PokéOS](https://www.pokeos.com) | "
    "[PokéBeach](https://www.pokebeach.com)"
)


st.sidebar.markdown("---")


st.sidebar.caption(
    f"PokéLineX v1.5 | {MODEL_NAME}"
)