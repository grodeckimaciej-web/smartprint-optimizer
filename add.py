import streamlit as st
import pandas as pd
import re
import math
import plotly.express as px

# --- KONFIGURACJA UI ---
st.set_page_config(page_title="SmartPrint AI Optimizer", layout="wide", page_icon="🖨️")

# Custom CSS dla lepszego wyglądu
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (USTAWIENIA I PARAMETRY) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1617/1617460.png", width=100)
    st.header("⚙️ Konfiguracja")
    
    waste_factor = st.slider("Naddatek materiału (%)", 10, 50, 30) / 100 + 1
    overlap_cm = st.number_input("Zakładka na bryty (cm)", value=3)
    
    st.divider()
    st.subheader("📦 Magazyn (Opcjonalnie)")
    manual_w = st.number_input("Szerokość rolki (cm)", value=0, help="0 = automat")
    manual_l = st.number_input("Długość rolki (m)", value=0)

# --- LOGIKA BIZNESOWA ---
def process_data(text):
    data = []
    lines = text.split('\n')
    for line in lines:
        if not line.strip(): continue
        match = re.search(r'(\d+)x(\d+)', line)
        s_match = re.search(r'_(\d+)szt', line)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            qty = int(s_match.group(1)) if s_match else 1
            # Logika brytowania i maszyn (z poprzednich kroków)
            s_net, d_net = min(w, h), max(w, h)
            limit = manual_w if manual_w > 0 else 500
            
            bryty = math.ceil(s_net / limit) if s_net > limit else 1
            s_brytu = (s_net / bryty) + overlap_cm if bryty > 1 else s_net
            
            # Wykluczenie Mesh z Agfy
            is_mesh = "mesh" in line.lower()
            if is_mesh:
                maszyna = "Durst P5 500"
            else:
                maszyna = "Durst P5 500" if s_brytu > 320 else "Agfa Jeti Tauro"
            
            roll_used = manual_w if manual_w > 0 else (500 if s_brytu > 320 else 320)
            mb = (((s_brytu * bryty) / 100) * (d_net / 100) * qty * waste_factor) / (roll_used / 100)
            
            data.append({"Plik": line, "Maszyna": maszyna, "Format": f"{w}x{h}", "Suma mb": round(mb, 2), "Sqm Brutto": round(mb * (roll_used/100), 2)})
    return data

# --- GŁÓWNY PANEL ---
st.title("🖨️ SmartPrint AI Optimizer")
st.caption("System wsparcia decyzji dla maszyn Agfa, Durst i Vutek")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📥 Dane wejściowe")
    raw_input = st.text_area("Wklej listę plików:", height=300, 
                             placeholder="Nazwa_300x100cm_5szt.pdf\nSiatka_1200x400cm_1szt.pdf")
    process_btn = st.button("🚀 Optymalizuj Produkcję", use_container_width=True)

with col2:
    if process_btn and raw_input:
        results = process_data(raw_input)
        if results:
            df = pd.DataFrame(results)
            
            # Statystyki Top
            m1, m2, m3 = st.columns(3)
            m1.metric("Suma MB", f"{df['Suma mb'].sum():.2f}")
            m2.metric("Suma m² Brutto", f"{df['Sqm Brutto'].sum():.2f}")
            m3.metric("Liczba plików", len(df))
            
            # Wykres obciążenia
            st.subheader("📊 Obciążenie maszyn")
            fig = px.bar(df, x='Maszyna', y='Suma mb', color='Maszyna', title="Metry bieżące na maszynę")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela wyników
            st.subheader("📋 Plan cięcia i druku")
            st.dataframe(df, use_container_width=True)
            
            # Eksport
            st.download_button("📥 Pobierz Plan (CSV)", df.to_csv().encode('utf-8'), "plan.csv")
        else:
            st.error("Nie znaleziono poprawnych wymiarów w nazwach plików.")
            # --- NOWA SEKCJA W SIDEBARZE ---
st.sidebar.divider()
st.sidebar.subheader("🎯 Prace uzupełniające (Fillery)")
filler_name = st.sidebar.text_input("Nazwa wypełniacza", "Naklejka_Logo")
filler_w = st.sidebar.number_input("Szerokość fillera (cm)", value=20)
filler_h = st.sidebar.number_input("Wysokość fillera (cm)", value=20)

# --- ZAKTUALIZOWANA LOGIKA W PĘTLI OBLICZENIOWEJ ---
# (Wewnątrz funkcji przelicz_zlecenia)

# Obliczamy wolne miejsce na szerokości rolki
wolna_szerokosc = roll_used - szer_brytu

if wolna_szerokosc >= filler_w:
    # Ile sztuk fillera zmieści się obok głównej pracy na całej długości?
    sztuk_w_rzedzie = math.floor(wolna_szerokosc / (filler_w + 1)) # +1cm odstępu
    rzędów = math.floor(dlug_n / (filler_h + 1))
    max_fillerow = sztuk_w_rzedzie * rzędów * sztuki
    sugestia_fillera = f"Możesz dołożyć {max_fillerow} szt. ({filler_name})"
else:
    sugestia_fillera = "Brak miejsca"
