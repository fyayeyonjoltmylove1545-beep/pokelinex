import streamlit as st
from PIL import Image
from datetime import datetime
import base64
import sys
import os
import uuid

from google import genai
from google.genai import types
from supabase import create_client, Client


# =========================
# API / SUPABASE AYARLARI
# =========================

SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase bağlantı bilgileri bulunamadı. Secrets ayarlarını kontrol edin.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

MODEL_NAME = "gemini-3.1-flash-lite"

GOOGLE_API_KEY = None

try:
    GOOGLE_API_KEY = st.secrets.get("GEMINI_API_KEY")
except Exception:
    pass

if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY")

if isinstance(GOOGLE_API_KEY, str):
    GOOGLE_API_KEY = GOOGLE_API_KEY.strip()

if not GOOGLE_API_KEY:
    st.error(
        "⚠️ Gemini API anahtarı bulunamadı.\n\n"
        "Streamlit Cloud kullanıyorsan uygulamanın "
        "Settings > Secrets bölümünde GEMINI_API_KEY "
        "tanımlı olduğundan emin ol."
    )
    st.stop()


@st.cache_resource
def get_genai_client(api_key):
    return genai.Client(api_key=api_key)


client = get_genai_client(GOOGLE_API_KEY)


# =========================================================
# 3. KULLANICI OTURUMU
# =========================================================

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = uuid.uuid4().hex

if "chat" not in st.session_state:
    st.session_state.chat = None

if "web_search_state" not in st.session_state:
    st.session_state.web_search_state = None


# =========================================================
# 4. LOGO
# =========================================================

BOT_AVATAR = get_asset_path("PokeLineX-bot-logo.png")


# =========================================================
# 5. ARKA PLAN SİSTEMİ
# =========================================================

def set_bg(image_filename):
    image_path = get_asset_path(image_filename)

    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{data}");
                background-size: cover;
                background-attachment: fixed;
            }}
            h1 {{
                color: white !important;
                text-shadow: 2px 2px 8px black;
                background-color: rgba(0, 0, 0, 0.4);
                padding: 10px;
                border-radius: 10px;
                width: fit-content;
            }}
            .stChatMessage {{
                background-color: rgba(0, 0, 0, 0.7) !important;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 15px;
                padding: 15px;
                margin-bottom: 10px;
                color: white !important;
                box-shadow: 2px 2px 15px rgba(0,0,0,0.5);
            }}
            .stChatMessage p, .stChatMessage span {{
                color: white !important;
            }}
            [data-testid="stSidebar"] {{
                background-color: rgba(0, 0, 0, 0.8) !important;
            }}
            [data-testid="stSidebar"] * {{
                color: white !important;
            }}
            .stFileUploader {{
                background-color: rgba(255, 255, 255, 0.1);
                padding: 10px;
                border-radius: 10px;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# 6. TEMA SEÇİMİ
# =========================================================

if os.path.exists(BOT_AVATAR):
    st.sidebar.image(BOT_AVATAR, width=80)

st.sidebar.subheader("Tema Seçimi")

template = st.sidebar.selectbox(
    "Karakter Teması",
    ["Pikachu", "Gengar", "Charizard"]
)

templates = {
    "Pikachu": "pikachu_bg.jpg",
    "Gengar": "gengar_bg.jpg",
    "Charizard": "charizard_bg.jpg"
}

set_bg(templates[template])


# =========================================================
# 7. GİRİŞ / KAYIT EKRANI (SUPABASE)
# =========================================================

if not st.session_state.user_email:

    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=100)

    st.title("⚡ PokéLineX: Giriş Yap / Kayıt Ol")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        login_email = st.text_input("Gmail Adresi:", key="login_email").strip().lower()
        login_pass = st.text_input("Şifre:", type="password", key="login_pass")

        if st.button("Giriş Yap", type="primary"):
            if login_email.endswith("@gmail.com"):
                # Supabase Sorgusu
                res = supabase.table("users").select("*").eq("email", login_email).eq("password", login_pass).execute()

                if res.data:
                    st.session_state.user_email = login_email
                    st.session_state.current_session_id = uuid.uuid4().hex
                    st.session_state.chat = None
                    st.session_state.web_search_state = None
                    st.success("Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("E-posta veya şifre hatalı!")
            else:
                st.error("Lütfen geçerli bir Gmail adresi girin.")

    with tab2:
        reg_email = st.text_input("Gmail Adresi:", key="reg_email").strip().lower()
        reg_pass = st.text_input("Şifre Belirleyin:", type="password", key="reg_pass")

        if st.button("Hesap Oluştur"):
            if reg_email.endswith("@gmail.com") and len(reg_pass) >= 4:
                try:
                    # Supabase Kayıt
                    supabase.table("users").insert({"email": reg_email, "password": reg_pass}).execute()
                    st.success("Hesabınız oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsiniz.")
                except Exception:
                    st.error("Bu e-posta adresi zaten kayıtlı veya bir hata oluştu!")
            else:
                st.error("Geçerli bir Gmail adresi ve en az 4 karakterli bir şifre girin.")

    st.stop()


# =========================================================
# 8. POKELINEX SİSTEM TALİMATI
# =========================================================

POKE_SYSTEM_INSTRUCTION = """
Senin adın PokéLineX.

Sen Pokémon konusunda uzmanlaşmış bir yapay zeka asistanısın.

Görevlerin:
- Pokémon bilgilerini açıklamak
- Pokémon oyunlarında yardımcı olmak
- Pokémon TCG hakkında bilgi vermek
- Pokémon haberlerini takip etmek
- Yeni oyunları araştırmak
- Etkinlikleri takip etmek
- Güncellemeleri ve yamaları araştırmak
- Pokémon içerikleri üreten kullanıcılara video ve içerik fikirleri konusunda yardımcı olmak

Kullanıcı güncel bir Pokémon haberi, yeni TCG paketi, oyun güncellemesi, etkinlik, duyuru veya benzeri güncel bir konu sorarsa canlı web araması kullan.

Mümkün olduğunda güvenilir kaynakları tercih et:
- Pokémon.com
- Bulbapedia
- Serebii
- PokéBeach
- Pokémon Database
- Nintendo Life
- PokéOS

Türkçe cevap ver.
Kullanıcıyla doğal, yardımsever, bilgili ve samimi bir şekilde konuş.
"""


# =========================================================
# 9. SIDEBAR & KONTROLLER
# =========================================================

st.sidebar.title(f"👤 {st.session_state.user_email}")
st.sidebar.markdown("---")
st.sidebar.subheader("Kontroller")

use_web_search = st.sidebar.checkbox("🌐 Web Araması (Canlı)", value=False)


# =========================================================
# 10. GEMINI CONFIG
# =========================================================

if use_web_search:
    current_config = types.GenerateContentConfig(
        system_instruction=POKE_SYSTEM_INSTRUCTION,
        tools=[types.Tool(google_search=types.GoogleSearch())]
    )
else:
    current_config = types.GenerateContentConfig(
        system_instruction=POKE_SYSTEM_INSTRUCTION
    )


# =========================================================
# 11. CHAT OLUŞTURMA (SUPABASE HISTORIES)
# =========================================================

def create_chat():
    res = supabase.table("history").select("role, content").eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).order("timestamp", desc=False).execute()

    formatted_history = []
    for item in res.data:
        gemini_role = "model" if item["role"] == "assistant" else "user"
        formatted_history.append({
            "role": gemini_role,
            "parts": [{"text": item["content"]}]
        })

    return client.chats.create(
        model=MODEL_NAME,
        config=current_config,
        history=formatted_history
    )


# =========================================================
# 12. WEB ARAMA DURUMU DEĞİŞİNCE CHAT'İ YENİLE
# =========================================================

if st.session_state.web_search_state != use_web_search:
    st.session_state.web_search_state = use_web_search
    st.session_state.chat = create_chat()


# =========================================================
# 13. GEÇMİŞİ SİL
# =========================================================

if st.sidebar.button("🗑️ Geçmişi Sil"):
    supabase.table("history").delete().eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).execute()
    st.session_state.chat = create_chat()
    st.rerun()


# =========================================================
# 14. YENİ SOHBET
# =========================================================

if st.sidebar.button("➕ Yeni Sohbet"):
    st.session_state.current_session_id = uuid.uuid4().hex
    st.session_state.chat = create_chat()
    st.rerun()


# =========================================================
# 15. ANA BAŞLIK
# =========================================================

col1, col2 = st.columns([1, 6])

with col1:
    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=120)

with col2:
    st.title("PokéLineX: PokeAI Asistanı")


# =========================================================
# 16. MESAJ GEÇMİŞİ
# =========================================================

res_history = supabase.table("history").select("role, content").eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).order("timestamp", desc=False).execute()

for item in res_history.data:
    avatar = BOT_AVATAR if (item["role"] == "assistant" and os.path.exists(BOT_AVATAR)) else None
    with st.chat_message(item["role"], avatar=avatar):
        st.markdown(item["content"])


# =========================================================
# 17. MEDYA VE MESAJ ALANI
# =========================================================

st.markdown("---")

col_btn, col_input = st.columns([1, 11])

with col_btn:
    with st.popover("➕"):
        uploaded_file = st.file_uploader(
            "Görsel Yükle",
            type=["jpg", "png", "jpeg"],
            key="media_upload"
        )

with col_input:
    user_input = st.chat_input("Pokémonlar hakkında sor...", key="poke_chat_input_main")


# =========================================================
# 18. MESAJ GÖNDER
# =========================================================

if user_input:
    user_input = user_input.strip()

    if not user_input:
        st.stop()

    if st.session_state.chat is None:
        st.session_state.chat = create_chat()

    # Supabase'e Kullanıcı Mesajını Kaydet
    supabase.table("history").insert({
        "email": st.session_state.user_email,
        "role": "user",
        "content": user_input,
        "session_id": st.session_state.current_session_id
    }).execute()

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=(BOT_AVATAR if os.path.exists(BOT_AVATAR) else None)):
        try:
            if uploaded_file:
                img = Image.open(uploaded_file)
                response = st.session_state.chat.send_message([user_input, img])
            else:
                response = st.session_state.chat.send_message(user_input)

            response_text = response.text if response.text else "Üzgünüm, cevap oluşturamadım."

            st.markdown(response_text)

            # Supabase'e Asistan Cevabını Kaydet
            supabase.table("history").insert({
                "email": st.session_state.user_email,
                "role": "assistant",
                "content": response_text,
                "session_id": st.session_state.current_session_id
            }).execute()

        except Exception as e:
            error_text = str(e)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                st.error("⚠️ API kullanım kotası dolmuş olabilir.")
                st.code(error_text, language="text")
            elif "401" in error_text or "UNAUTHENTICATED" in error_text or "Unauthorized" in error_text:
                st.error("🔐 Gemini API kimlik doğrulama hatası (401).")
                st.warning("Streamlit Secrets içindeki GEMINI_API_KEY değerini kontrol edin.")
                st.code(error_text, language="text")
            else:
                st.error("⚠️ PokéLineX hata verdi:")
                st.code(error_text, language="text")


# =========================================================
# 19. SOHBET GEÇMİŞLERİ (SIDEBAR)
# =========================================================

st.sidebar.markdown("---")
st.sidebar.subheader("💬 Sohbet Geçmişi")

# Supabase üzerinden oturum listesi çekme
res_sessions = supabase.table("history").select("session_id, content, timestamp").eq("email", st.session_state.user_email).eq("role", "user").order("timestamp", desc=False).execute()

# Benzersiz session_id'lerin ilk mesajlarını bulalım
seen_sessions = {}
for row in res_sessions.data:
    s_id = row["session_id"]
    if s_id not in seen_sessions:
        seen_sessions[s_id] = row["content"]

for sess_id, first_msg in seen_sessions.items():
    button_label = first_msg[:25] + "..." if len(first_msg) > 25 else first_msg
    is_active = "⚡ " if sess_id == st.session_state.current_session_id else "🗨️ "

    if st.sidebar.button(f"{is_active}{button_label}", key=f"session_{sess_id}"):
        st.session_state.current_session_id = sess_id
        st.session_state.chat = create_chat()
        st.rerun()


# =========================================================
# 20. ÇIKIŞ
# =========================================================

if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user_email = None
    st.session_state.chat = None
    st.session_state.web_search_state = None
    st.rerun()


# =========================================================
# 21. GÜVENİLİR KAYNAKLAR
# =========================================================

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 Güvenilir Kaynaklar")
st.sidebar.markdown("[Serebii](https://www.serebii.net) | [Bulbapedia](https://bulbapedia.bulbagarden.net)")
st.sidebar.markdown("[PokéDB](https://pokemondb.net) | [Official Pokémon](https://www.pokemon.com)")
st.sidebar.markdown("[PokéOS](https://www.pokeos.com) | [PokéBeach](https://www.pokebeach.com)")

st.sidebar.markdown("---")
st.sidebar.caption(f"PokéLineX v1.7 | {MODEL_NAME}")
