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


# =========================================================
# 0. DOSYA YOLU YARDIMCISI & SAYFA YAPILANDIRMASI
# =========================================================

def get_asset_path(filename):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, filename)

st.set_page_config(
    page_title="PokéLineX: PokeAI Asistanı",
    page_icon="⚡",
    layout="wide"
)


# =========================================================
# 1. API / SUPABASE AYARLARI
# =========================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Supabase bağlantı bilgileri bulunamadı. Secrets ayarlarını kontrol edin.")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# 2. ÇOKLU GEMINI API KEY ROTASYONU (KOTA KORUMASI)
# =========================================================

MODEL_NAME = "gemini-3.1-flash-lite"

# Yedekli API Key Listesi
api_keys = []

key1 = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
key2 = st.secrets.get("GEMINI_API_KEY_2") or os.environ.get("GEMINI_API_KEY_2")

if key1: api_keys.append(key1.strip())
if key2: api_keys.append(key2.strip())

if not api_keys:
    st.error("⚠️ Hiçbir Gemini API anahtarı bulunamadı! Lütfen Secrets bölümünü kontrol edin.")
    st.stop()

def get_genai_client(api_key):
    return genai.Client(api_key=api_key)


# =========================================================
# 3. KULLANICI OTURUMU & OTOMATİK GİRİŞ (AUTOLOGIN)
# =========================================================

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = uuid.uuid4().hex

if "chat" not in st.session_state:
    st.session_state.chat = None

if "web_search_state" not in st.session_state:
    st.session_state.web_search_state = None

# URL Parametresi ile Otomatik Oturum Hatırlama Kontrolü
query_params = st.query_params
if not st.session_state.user_email and "session_token" in query_params:
    saved_token = query_params["session_token"]
    try:
        res = supabase.table("users").select("email").eq("session_token", saved_token).execute()
        if res.data:
            st.session_state.user_email = res.data[0]["email"]
    except Exception:
        pass


# =========================================================
# 4. LOGO & ARKA PLAN
# =========================================================

BOT_AVATAR = get_asset_path("PokeLineX-bot-logo.png")

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
# 5. TEMA SEÇİMİ
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
# 6. GİRİŞ / KAYIT EKRANI (KALICI OTURUM DESTEKLİ)
# =========================================================

if not st.session_state.user_email:

    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=100)

    st.title("⚡ PokéLineX: Giriş Yap / Kayıt Ol")

    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])

    with tab1:
        login_email = st.text_input("Gmail Adresi:", key="login_email").strip().lower()
        login_pass = st.text_input("Şifre:", type="password", key="login_pass")
        remember_me = st.checkbox("Beni Hatırla (Tekrar Giriş Yapma)", value=True)

        if st.button("Giriş Yap", type="primary"):
            if login_email.endswith("@gmail.com"):
                res = supabase.table("users").select("*").eq("email", login_email).eq("password", login_pass).execute()

                if res.data:
                    st.session_state.user_email = login_email
                    st.session_state.current_session_id = uuid.uuid4().hex
                    st.session_state.chat = None
                    st.session_state.web_search_state = None

                    # Oturumu Hatırla: Supabase'e token kaydet ve URL'e ekle
                    if remember_me:
                        token = uuid.uuid4().hex
                        try:
                            supabase.table("users").update({"session_token": token}).eq("email", login_email).execute()
                            st.query_params["session_token"] = token
                        except Exception:
                            pass

                    st.success("Giriş başarılı! Yönlendiriliyorsunuz...")
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
                    supabase.table("users").insert({"email": reg_email, "password": reg_pass}).execute()
                    st.success("Hesabınız oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsiniz.")
                except Exception:
                    st.error("Bu e-posta adresi zaten kayıtlı veya bir hata oluştu!")
            else:
                st.error("Geçerli bir Gmail adresi ve en az 4 karakterli bir şifre girin.")

    st.stop()


# =========================================================
# 7. POKELINEX SİSTEM TALİMATI
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
# 8. SIDEBAR & KONTROLLER
# =========================================================

st.sidebar.title(f"👤 {st.session_state.user_email}")
st.sidebar.markdown("---")
st.sidebar.subheader("Kontroller")

use_web_search = st.sidebar.checkbox("🌐 Web Araması (Canlı)", value=False)


# =========================================================
# 9. HAFIZA YÖNETİMİ (SIDEBAR MODÜLÜ)
# =========================================================

st.sidebar.markdown("---")
st.sidebar.subheader("🧠 Yönetilebilir Hafıza")

with st.sidebar.expander("➕ Yeni Hafıza Ekle"):
    new_mem = st.text_input("Kayıt edilecek bilgi:", key="new_memory_input")
    if st.button("Hafızaya Kaydet"):
        if new_mem.strip():
            supabase.table("user_memories").insert({
                "email": st.session_state.user_email,
                "memory_text": new_mem.strip()
            }).execute()
            st.success("Hafızaya eklendi!")
            st.session_state.chat = None
            st.rerun()

res_memories = supabase.table("user_memories").select("*").eq("email", st.session_state.user_email).order("created_at", desc=True).execute()

if res_memories.data:
    for mem in res_memories.data:
        m_col1, m_col2 = st.sidebar.columns([4, 1])
        with m_col1:
            st.caption(f"• {mem['memory_text']}")
        with m_col2:
            if st.button("🗑️", key=f"del_mem_{mem['id']}"):
                supabase.table("user_memories").delete().eq("id", mem["id"]).execute()
                st.session_state.chat = None
                st.rerun()
else:
    st.sidebar.caption("Henüz kaydedilmiş bir hafıza yok.")


# =========================================================
# 10. GEMINI CONFIG VE DİNAMİK HAFIZA ENTEGRASYONU
# =========================================================

user_memories_text = ""
if res_memories.data:
    mem_list = [f"- {m['memory_text']}" for m in res_memories.data]
    user_memories_text = "\n\nKULLANICI HAKKINDA BİLİNEN ÖZEL BİLGİLER (HAFIZA):\n" + "\n".join(mem_list)

full_system_instruction = POKE_SYSTEM_INSTRUCTION + user_memories_text

def get_config(enable_search=True):
    if enable_search:
        return types.GenerateContentConfig(
            system_instruction=full_system_instruction,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    return types.GenerateContentConfig(
        system_instruction=full_system_instruction
    )


# =========================================================
# 11. CHAT OLUŞTURMA (SUPABASE HISTORIES)
# =========================================================

def create_chat(active_client, enable_search=True):
    res = supabase.table("history").select("role, content").eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).order("timestamp", desc=False).execute()

    formatted_history = []
    for item in res.data:
        gemini_role = "model" if item["role"] == "assistant" else "user"
        formatted_history.append({
            "role": gemini_role,
            "parts": [{"text": item["content"]}]
        })

    return active_client.chats.create(
        model=MODEL_NAME,
        config=get_config(enable_search),
        history=formatted_history
    )


# =========================================================
# 12. WEB ARAMA VEYA HAFIZA DEĞİŞİNCE CHAT'İ YENİLE
# =========================================================

if st.session_state.web_search_state != use_web_search or st.session_state.chat is None:
    st.session_state.web_search_state = use_web_search
    st.session_state.chat = create_chat(get_genai_client(api_keys[0]), use_web_search)


# =========================================================
# 13. KONTROL BUTONLARI
# =========================================================

if st.sidebar.button("🗑️ Geçmişi Sil"):
    supabase.table("history").delete().eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).execute()
    st.session_state.chat = create_chat(get_genai_client(api_keys[0]), use_web_search)
    st.rerun()

if st.sidebar.button("➕ Yeni Sohbet"):
    st.session_state.current_session_id = uuid.uuid4().hex
    st.session_state.chat = create_chat(get_genai_client(api_keys[0]), use_web_search)
    st.rerun()


# =========================================================
# 14. ANA BAŞLIK
# =========================================================

col1, col2 = st.columns([1, 6])

with col1:
    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=120)

with col2:
    st.title("PokéLineX: PokeAI Asistanı")


# =========================================================
# 15. MESAJ GEÇMİŞİ
# =========================================================

res_history = supabase.table("history").select("role, content").eq("email", st.session_state.user_email).eq("session_id", st.session_state.current_session_id).order("timestamp", desc=False).execute()

for item in res_history.data:
    avatar = BOT_AVATAR if (item["role"] == "assistant" and os.path.exists(BOT_AVATAR)) else None
    with st.chat_message(item["role"], avatar=avatar):
        st.markdown(item["content"])


# =========================================================
# 16. MEDYA VE MESAJ ALANI
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
# 17. AKILLI MESAJ GÖNDERME VE DAYANIKLI KOTA YÖNETİMİ
# =========================================================

def send_message_with_fallback(prompt, uploaded_img=None):
    """
    Sırasıyla API keylerini dener. Kota aşımı yaşanırsa yedek keye geçer.
    Her ikisi de biterse web aramasını kapatıp genel hafızasından sevimli bir uyarı ile yanıt verir.
    """
    payload = [prompt, uploaded_img] if uploaded_img else prompt

    # 1. Aşama: Sırayla API Key'leri dene
    for idx, key in enumerate(api_keys):
        try:
            temp_client = get_genai_client(key)
            temp_chat = create_chat(temp_client, use_web_search)
            response = temp_chat.send_message(payload)
            return response.text, None
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                continue # Diğer keye geç
            else:
                return None, f"⚠️ Bir sorun oluştu: {err}"

    # 2. Aşama: Eğer hepsi dolduysa, Web Arama OLMADAN dene (Fallback)
    try:
        temp_client = get_genai_client(api_keys[0])
        fallback_chat = create_chat(temp_client, enable_search=False)
        response = fallback_chat.send_message(payload)
        
        cute_warning = (
            "⚡ *Pokédex canlı web aramaları şu an aşırı yoğun! B planına geçtik:* "
            "Canlı web aramasını geçici olarak devre dışı bıraktım ama sorunu genel Pokémon hafızamdan yanıtladım:\n\n"
        )
        return cute_warning + response.text, None
    except Exception as e:
        return None, "⚡ *Pikachu'nun şarjı bitti!* Canlı web araması kotaları şu an doldu. Lütfen 1 dakika bekleyip tekrar dene."


if user_input:
    user_input = user_input.strip()

    if not user_input:
        st.stop()

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
        img_obj = Image.open(uploaded_file) if uploaded_file else None
        response_text, error_msg = send_message_with_fallback(user_input, img_obj)

        if response_text:
            st.markdown(response_text)
            # Supabase'e Asistan Cevabını Kaydet
            supabase.table("history").insert({
                "email": st.session_state.user_email,
                "role": "assistant",
                "content": response_text,
                "session_id": st.session_state.current_session_id
            }).execute()
        else:
            st.error(error_msg)


# =========================================================
# 18. SOHBET GEÇMİŞLERİ (SIDEBAR)
# =========================================================

st.sidebar.markdown("---")
st.sidebar.subheader("💬 Sohbet Geçmişi")

res_sessions = supabase.table("history").select("session_id, content, timestamp").eq("email", st.session_state.user_email).eq("role", "user").order("timestamp", desc=False).execute()

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
        st.session_state.chat = create_chat(get_genai_client(api_keys[0]), use_web_search)
        st.rerun()


# =========================================================
# 19. ÇIKIŞ YAP
# =========================================================

if st.sidebar.button("🚪 Çıkış Yap"):
    st.session_state.user_email = None
    st.session_state.chat = None
    st.session_state.web_search_state = None
    st.query_params.clear() # Oturum tokenini temizle
    st.rerun()


# =========================================================
# 20. GÜVENİLİR KAYNAKLAR
# =========================================================

st.sidebar.markdown("---")
st.sidebar.subheader("🌐 Güvenilir Kaynaklar")
st.sidebar.markdown("[Serebii](https://www.serebii.net) | [Bulbapedia](https://bulbapedia.bulbagarden.net)")
st.sidebar.markdown("[PokéDB](https://pokemondb.net) | [Official Pokémon](https://www.pokemon.com)")
st.sidebar.markdown("[PokéOS](https://www.pokeos.com) | [PokéBeach](https://www.pokebeach.com)")

st.sidebar.markdown("---")
st.sidebar.caption(f"PokéLineX v2.0 | {MODEL_NAME}")
