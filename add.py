import streamlit as st
import pandas as pd
import re
import math
import plotly.express as px

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SmartPrint AI Optimizer", layout="wide", page_icon="🖨️")

st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (PARAMETRY I FILLERY) ---
with st.sidebar:
    st.header("⚙️ Konfiguracja Globalna")
    waste_factor = st.slider("Naddatek materiału (%)", 0, 50, 30) / 100 + 1
    overlap_cm = st.number_input("Zakładka na bryty (cm)", min_value=0, value=3)
    
    st.divider()
    st.subheader("📦 Magazyn / Wymuszenie Roli")
    manual_w = st.number_input("Szerokość rolki (cm) [0 = Auto]", value=0)
    
    st.divider()
    st.subheader("🎯 Prace uzupełniające (Fillery)")
    filler_name = st.text_input("Nazwa naklejki/fillera", "Naklejka_Logo")
    filler_w = st.number_input("Szerokość fillera (cm)", min_value=1, value=20)
    filler_h = st.number_input("Wysokość fillera (cm)", min_value=1, value=20)

# --- GŁÓWNA LOGIKA ALGORYTMU ---
def process_data(text):
    data = []
    lines = text.split('\n')
    
    for line in lines:
        if not line.strip(): continue
        
        # Ekstrakcja danych (Regex)
        match = re.search(r'(\d+)x(\d+)', line)
        s_match = re.search(r'_(\d+)szt', line)
        
        if match:
            w, h = int(match.group(1)), int(match.group(2))
            qty = int(s_match.group(1)) if s_match else 1
            
            # Wymiary netto (zakładamy, że drukujemy węższym bokiem po szerokości rolki)
            s_net, d_net = min(w, h), max(w, h)
            limit = manual_w if manual_w > 0 else 500
            
            # Brytowanie
            bryty = math.ceil(s_net / limit) if s_net > limit else 1
            s_brytu = (s_net / bryty) + overlap_cm if bryty > 1 else s_net
            
            # Dobór maszyny (Zabezpieczenie przed Mesh na Agfie)
            is_mesh = "mesh" in line.lower()
            if is_mesh:
                maszyna = "Durst P5 500 (Mesh Triage)"
            else:
                maszyna = "Durst P5 500" if s_brytu > 320 else "Agfa Jeti Tauro"
                
            # Wybór szerokości rolki
            roll_used = manual_w if manual_w > 0 else (500 if s_brytu > 320 else (320 if s_brytu > 260 else 260))
            
            # Kalkulacja metrów bieżących
            mb = (d_net / 100) * bryty * qty * waste_factor
            sqm_brutto = mb * (roll_used / 100)
            
            # --- MODUŁ FILL THE GAP (Nesting) ---
            wolna_szerokosc = roll_used - s_brytu
            sugestia_fillera = "Brak miejsca"
            
            if wolna_szerokosc >= filler_w:
                # Odejmujemy 1 cm na margines bezpieczeństwa / cięcie
                sztuk_w_rzedzie = math.floor(wolna_szerokosc / (filler_w + 1))
                rzedow = math.floor(d_net / (filler_h + 1))
                
                # Maksymalna ilość uwzględniająca liczbę brytów i sztuk głównej pracy
                max_fillerow = sztuk_w_rzedzie * rzedow * bryty * qty
                
                if max_fillerow > 0:
                    sugestia_fillera = f"➕ Dołóż {max_fillerow} szt. ({filler_name})"

            data.append({
                "Plik": line[:35] + ("..." if len(line)>35 else ""),
                "Maszyna": maszyna,
                "Szer. Roli": f"{roll_used} cm",
                "Format": f"{w}x{h}",
                "Bryty": bryty,
                "Suma mb": round(mb, 2),
                "Wolny Pasek": f"{round(wolna_szerokosc, 1)} cm",
                "Optymalizacja (Nesting)": sugestia_fillera,
                "Sqm_Num": sqm_brutto # Ukryte do wykresów
            })
    return data

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("🖨️ SmartPrint AI Optimizer")
st.caption("Wersja Zoptymalizowana i Zweryfikowana (v5.1)")

col1, col2 = st.columns([1, 2.5])

with col1:
    st.subheader("📥 Zlecenia")
    raw_input = st.text_area("Wklej listę plików (.pdf):", height=250, 
                             placeholder="Baner_300x100cm_5szt.pdf\nSiatkaMesh_1200x400cm_1szt.pdf")
    process_btn = st.button("🚀 Optymalizuj Produkcję", use_container_width=True, type="primary")

with col2:
    if process_btn and raw_input:
        results = process_data(raw_input)
        if results:
            df = pd.DataFrame(results)
            
            # KPI Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Wymagane Metry Bieżące", f"{df['Suma mb'].sum():.1f} mb")
            m2.metric("Powierzchnia Brutto", f"{df['Sqm_Num'].sum():.1f} m²")
            m3.metric("Ilość Zleceń", len(df))
            
            # Ukrywamy kolumnę techniczną Sqm_Num z widoku tabeli
            display_df = df.drop(columns=['Sqm_Num'])
            
            st.subheader("📋 Karta Technologiczna")
            st.dataframe(display_df, use_container_width=True)
            
            # Wizualizacja obciążenia
            st.subheader("📊 Wykres Obciążenia (Load Balancing)")
            fig = px.bar(df, x='Maszyna', y='Suma mb', color='Maszyna', 
                         title="Dystrybucja materiału na park maszynowy",
                         text_auto='.1f')
            st.plotly_chart(fig, use_container_width=True)
            
            # Pobieranie CSV
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Pobierz Raport Produkcyjny (CSV)", csv, "plan_produkcji.csv")
        else:
            st.error("Nie rozpoznano formatów wklejonych plików. Upewnij się, że używasz formatu SzerokośćxWysokość.")
