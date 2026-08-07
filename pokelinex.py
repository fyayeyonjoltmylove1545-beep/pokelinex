import streamlit as st
from PIL import Image
import sqlite3
from datetime import datetime
import base64
import sys
import os
import google.generativeai as genai

# --- API MÜŞTERİSİ TANIMLAMA ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(
        api_key=st.secrets["GEMINI_API_KEY"],
        client_options={"api_endpoint": "generativelanguage.googleapis.com/v1alpha"}
    )
else:
    genai.configure(
        api_key="AQ.Ab8RN6IRl1h-ov1P5eRm5JcWqtISbhoT78juPAtfxgLLBQcrdQ",
        client_options={"api_endpoint": "generativelanguage.googleapis.com/v1alpha"}
    )

# --- 0. DİNAMİK DOSYA YOLU YARDIMCISI ---
def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, filename)

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(page_title="PokéLineX: PokeAI Asistanı", page_icon="⚡", layout="wide")

# Veritabanı Bağlantıları
conn = sqlite3.connect('poke_history.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS history 
             (email TEXT, role TEXT, content TEXT, timestamp TEXT, session_id TEXT)''')
conn.commit()

c.execute('''CREATE TABLE IF NOT EXISTS users (email TEXT UNIQUE, password TEXT)''')
conn.commit()

# Sohbet Kimliği Kontrolü
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# --- 2. LOGO VE GÖRSEL AYARLARI ---
BOT_AVATAR = get_asset_path("PokeLineX-bot-logo.png")

def set_bg(image_filename):
    image_path = get_asset_path(image_filename)
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        st.markdown(f"""
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
            """, unsafe_allow_html=True)

# --- 3. OTOMATİK GİRİŞ SİSTEMİ ---
USER_FILE = "last_user.txt"

if "user_email" not in st.session_state:
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            st.session_state.user_email = f.read().strip()
    else:
        st.session_state.user_email = None

if not st.session_state.user_email:
    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=100)
    st.title("⚡ PokéLineX: Giriş Yap / Kayıt Ol")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        login_email = st.text_input("Gmail Adresi:", key="login_email")
        login_pass = st.text_input("Şifre:", type="password", key="login_pass")
        
        if st.button("Giriş Yap"):
            if "@gmail.com" in login_email:
                c.execute("SELECT * FROM users WHERE email=? AND password=?", (login_email, login_pass))
                user = c.fetchone()
                
                if user:
                    st.session_state.user_email = login_email
                    with open(USER_FILE, "w") as f:
                        f.write(login_email)
                    st.success("Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("E-posta veya şifre hatalı!")
            else:
                st.error("Lütfen geçerli bir Gmail adresi girin.")

    with tab2:
        reg_email = st.text_input("Gmail Adresi:", key="reg_email")
        reg_pass = st.text_input("Şifre Belirleyin:", type="password", key="reg_pass")
        
        if st.button("Hesap Oluştur"):
            if "@gmail.com" in reg_email and len(reg_pass) >= 4:
                try:
                    c.execute("INSERT INTO users VALUES (?, ?)", (reg_email, reg_pass))
                    conn.commit()
                    st.success("Hesabınız oluşturuldu! Şimdi Giriş Yap sekmesinden giriş yapabilirsiniz.")
                except sqlite3.IntegrityError:
                    st.error("Bu e-posta adresi zaten kayıtlı!")
            else:
                st.error("Geçerli bir Gmail adresi ve en az 4 haneli bir şifre girin.")
                
    st.stop()

# --- 4. TEMA VE YAN PANEL AYARLARI ---
if os.path.exists(BOT_AVATAR):
    st.sidebar.image(BOT_AVATAR, width=80)

st.sidebar.subheader("Tema Seçimi")
template = st.sidebar.selectbox("Karakter Teması", ["Pikachu", "Gengar", "Charizard"])

templates = {
    "Pikachu": "pikachu_bg.jpg",
    "Gengar": "gengar_bg.jpg",
    "Charizard": "charizard_bg.jpg"
}
set_bg(templates[template])

POKE_SYSTEM_INSTRUCTION = """
Senin adın PokéLineX. Bir Pokémon ansiklopedisisin ve güncel Pokémon haberlerini takip eden uzman bir asistansın.
Kullanıcı yeni duyurulan TCG paketlerini, yeni çıkan Pokémon oyunlarını, etkinlikleri ve yamaları sorduğunda yanıt ver.
Sadece Pokémon ve ilgili oyun/medya konularını konuş, Türkçe cevap ver.
"""

st.sidebar.title(f"👤 {st.session_state.user_email}")
st.sidebar.markdown("---")
st.sidebar.subheader("Kontroller")

# ESKİ SDK SOHBET BAŞLATMA
def get_active_chat():
    c.execute("SELECT role, content FROM history WHERE email=? AND session_id=? ORDER BY timestamp ASC", 
              (st.session_state.user_email, st.session_state.current_session_id))
    db_history = c.fetchall()
    
    formatted_history = []
    for role, content in db_history:
        gemini_role = "model" if role == "assistant" else "user"
        formatted_history.append({
            "role": gemini_role,
            "parts": [content]
        })
    
    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        system_instruction=POKE_SYSTEM_INSTRUCTION
    )
    return model.start_chat(history=formatted_history)

if st.sidebar.button("Geçmişi Sil"):
    c.execute("DELETE FROM history WHERE email=? AND session_id=?", 
              (st.session_state.user_email, st.session_state.current_session_id))
    conn.commit()
    st.session_state.chat = get_active_chat()
    st.rerun()

if st.sidebar.button("➕ Yeni Sohbet"):
    st.session_state.current_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.chat = get_active_chat()
    st.rerun()

# --- 5. SOHBET OTURUMUNU BAŞLATMA ---
if "chat" not in st.session_state:
    st.session_state.chat = get_active_chat()

# --- 6. ANA EKRAN VE MESAJ GEÇMİŞİ ---
col1, col2 = st.columns([1, 6])
with col1:
    if os.path.exists(BOT_AVATAR):
        st.image(BOT_AVATAR, width=120)
with col2:
    st.title("PokéLineX: PokeAI Asistanı")

c.execute("SELECT role, content FROM history WHERE email=? AND session_id=? ORDER BY timestamp ASC", 
          (st.session_state.user_email, st.session_state.current_session_id))
for role, content in c.fetchall():
    avatar = BOT_AVATAR if (role == "assistant" and os.path.exists(BOT_AVATAR)) else None
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)

# --- 7. MEDYA VE MESAJ GİRİŞ ALANI ---
st.markdown("---")
col_btn, col_input = st.columns([1, 11])

with col_btn:
    with st.popover("➕"):
        uploaded_file = st.file_uploader("Görsel Yükle", type=["jpg", "png", "jpeg"], key="media_upload")

with col_input:
    user_input = st.chat_input("Pokémonlar hakkında sor...", key="poke_chat_input_main")

if user_input:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", 
              (st.session_state.user_email, "user", user_input, now, st.session_state.current_session_id))
    conn.commit()
    
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar=BOT_AVATAR if os.path.exists(BOT_AVATAR) else None):
        try:
            if uploaded_file:
                img = Image.open(uploaded_file)
                vision_model = genai.GenerativeModel(
                    model_name="gemini-3.1-flash-lite",
                    system_instruction=POKE_SYSTEM_INSTRUCTION
                )
                response = vision_model.generate_content([user_input, img])
                response_text = response.text
            else:
                try:
                    response = st.session_state.chat.send_message(user_input)
                except Exception:
                    st.session_state.chat = get_active_chat()
                    response = st.session_state.chat.send_message(user_input)
                
                response_text = response.text
            
            st.markdown(response_text)
            
            c.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", 
                      (st.session_state.user_email, "assistant", response_text, now, st.session_state.current_session_id))
            conn.commit()
        except Exception as e:
            st.error(f"Hata: {e}")

# --- 8. GEÇMİŞ SOHBETLER LİSTESİ ---
st.sidebar.markdown("---")
st.sidebar.subheader("Sohbet Geçmişi")

c.execute('''
    SELECT session_id, MIN(content) 
    FROM history 
    WHERE email=? AND role='user' 
    GROUP BY session_id 
    ORDER BY MIN(timestamp) DESC
''', (st.session_state.user_email,))

user_sessions = c.fetchall()

for sess_id, first_msg in user_sessions:
    button_label = first_msg[:25] + "..." if len(first_msg) > 25 else first_msg
    is_active = "⚡ " if sess_id == st.session_state.current_session_id else "🗨️ "
    
    if st.sidebar.button(f"{is_active}{button_label}", key=sess_id):
        st.session_state.current_session_id = sess_id
        st.session_state.chat = get_active_chat()
        st.rerun()

if st.sidebar.button("Çıkış Yap"):
    if os.path.exists(USER_FILE):
        os.remove(USER_FILE)
    st.session_state.user_email = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Güvenilir Kaynaklar")
st.sidebar.caption("[Serebii](https://www.serebii.net) | [Bulbapedia](https://bulbapedia.bulbagarden.net)")
st.sidebar.caption("[PokeDB](https://pokemondb.net) | [Official](https://www.pokemon.com)")
st.sidebar.caption("[PokeOS](https://www.pokeos.com) | [PokeBeach](https://www.pokebeach.com)")
st.sidebar.caption("PokéLineX v1.4 | Gemini ile oluşturuldu")
