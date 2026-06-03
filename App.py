import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import time

# =============================================================
# चरण 1: पोर्टल कॉन्फ़िगरेशन और पुलिस 'यूनिफॉर्म' थीम
# =============================================================
st.set_page_config(
    page_title="जिला पुलिस डेली ड्यूटी पोर्टल", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# लाइव एक्सेल/गूगल शीट एंट्रीज तुरंत दिखाने के लिए कैशे क्लियरिंग
st.cache_data.clear()

st.markdown("""
    <style>
    .stApp, .main {
        background: linear-gradient(135deg, #f5f5dc 0%, #e3d5b8 100%) !important;
    }
    #MainMenu, header, footer, [data-testid="stHeader"], .stAppHeader {
        visibility: hidden !important;
        display: none !important;
    }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 95% !important;
    }
    .stButton>button {
        background-color: #002147 !important;
        color: #ffffff !important;
        border: 2px solid #d4af37 !important;
        border-radius: 6px !important;
        font-weight: bold !important;
    }
    [data-testid="stDataFrame"] { background-color: #ffffff !important; border: 3px solid #002147 !important; }
    </style>
""", unsafe_allow_html=True)

THANA_LIST = [
    "कोतवाली नगर", "कोतवाली देहात", "तुलसीपुर", "गैसड़ी", "पचपेड़वा", "कोतवाली जरवा", 
    "महाराजगंज", "ललिया", "हरैया", "उतरौला", "सादुल्लानगर", "रेहरा बाज़ार", 
    "गौरा चौराहा", "गैड़ास बुजुर्ग", "श्रीदत्तगंज", "ए0एच0टी0 थाना", "रिजर्व पुलिस line", "महिला थाना", "साइबर क्राइम थाना"
]

DUTY_TYPES = ["लॉ एंड ओरडर (L&O)", "वीआईपी (VIP) – ड्यूटी", "पिकेट/गश्त", "कोर्ट ड्यूटी", "समन तामीला", "तफ्तीश/जांच", "आकस्मिक अवकाश", "सामान्य अवकाश", "गैर हाजिर", "निलम्बित", "अन्य"]

USER_CREDENTIALS = {
    "hq_master":  "hq@123", "9454403019": "thana@3019", "9454403020": "thana@3020",
    "9454404895": "thana@4895", "9454403022": "thana@3022", "9454403025": "thana@3025",
    "9454403023": "thana@3023", "9454403026": "thana@3026", "9454403030": "thana@3030",
    "9454403021": "thana@3021", "9454403024": "thana@3024", "9454403027": "thana@3027",
    "9454403031": "thana@3031", "7317724235": "thana@4235", "9454403028": "thana@3028",
    "7398638787": "thana@8787", "9454403039": "thana@3039", "9454402345": "thana@2345",
    "7839855506": "thana@5506", "7839855004": "thana@5004"
}

THANA_MAPPING = {
    "9454403019": "कोतवाली नगर", "9454403020": "कोतवाली देहात", "9454404895": "महिला थाना",
    "9454403022": "गौरा चौराहा", "9454403025": "ललिया", "9454403023": "हरैया",
    "9454403026": "महाराजगंज", "9454403030": "तुलसीपुर", "9454403021": "गैसड़ी",
    "9454403024": "कोतवाली जरवा", "9454403027": "पचपेड़वा", "9454403031": "उतरौला",
    "7317724235": "श्रीदत्तगंज", "7398638787": "गैड़ास बुजुर्ग", "9454403028": "रेहरा बाज़ार",
    "9454403039": "सादुल्लानगर", "9454402345": "रिजर्व पुलिस line", "7839855506": "ए0एच0टी0 थाना",
    "7839855004": "साइबर क्राइम थाना"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

def filter_duty_data(df, selected_date, selected_thana, selected_duty):
    if df.empty: return df
    filtered_df = df.copy()
    filtered_df.columns = [str(c).strip() for c in filtered_df.columns]
    
    date_col, thana_col, duty_col = None, None, None
    for c in filtered_df.columns:
        c_low = c.lower()
        if any(x in c_low for x in ['तारीख', 'दिनांक', 'date', 'timestamp', 'time']): date_col = c
        if any(x in c_low for x in ['थाना', 'thana', 'इकाई', 'unit']): thana_col = c
        if any(x in c_low for x in ['ड्यूटी', 'duty', 'प्रकार']): duty_col = c

    if date_col:
        try:
            filtered_df['parsed_date_internal'] = pd.to_datetime(filtered_df[date_col], errors='coerce').dt.date
            filtered_df = filtered_df[filtered_df['parsed_date_internal'] == selected_date]
            filtered_df = filtered_df.drop(columns=['parsed_date_internal'])
        except Exception:
            d_dash = selected_date.strftime("%d-%m-%Y")
            filtered_df = filtered_df[filtered_df[date_col].astype(str).str.contains(d_dash)]

    if selected_thana and selected_thana != "सभी थाने" and thana_col:
        short_name = selected_thana.replace("कोतवाली", "").strip()
        filtered_df = filtered_df[filtered_df[thana_col].astype(str).str.contains(short_name, case=False, na=False)]

    if selected_duty and selected_duty != "सभी ड्यूटी" and duty_col:
        filtered_df = filtered_df[filtered_df[duty_col].astype(str).str.contains(str(selected_duty), case=False, na=False)]
            
    return filtered_df

SP_PHOTO_URL = "https://docs.google.com/uc?export=view&id=1A_bC_D_EFG_HIJKLMNOP" 

# =============================================================
# चरण 2: लॉगिन गेटवे
# =============================================================
if not st.session_state.logged_in:
    col_logo, col_title = st.columns([1, 4])
    with col_logo: 
        try: st.image(SP_PHOTO_URL, width=135)
        except Exception: st.markdown("<h1 style='font-size: 80px; margin: 0;'>👮</h1>", unsafe_allow_html=True)
            
    with col_title:
        st.markdown("<h1 style='color:#002147; margin-bottom:0;'>🚨 उत्तर प्रदेश पुलिस | जनपद बलरामपुर</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0;'>दैनिक ड्यूटी मैनेजमेंट पोर्टल</h3>", unsafe_allow_html=True)
    
    with st.container():
        username = st.text_input("यूज़रनेम (CUG नंबर या मास्टर आईडी)")
        password = st.text_input("पासवर्ड (Password)", type="password")
        if st.button("🔓 पोर्टल में प्रवेश करें", use_container_width=True):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.logged_in = True
                st.session_state.user_role = username
                st.rerun()
            else: st.error("❌ गलत लॉगिन विवरण।")

# =============================================================
# चरण 3: मुख्य सुरक्षित क्षेत्र
# =============================================================
else:
    col_m, col_l = st.columns([8, 2])
    with col_m: st.markdown("### 🚓 बलरामपुर पुलिस डेली ड्यूटी पोर्टल")
    with col_l:
        if st.button("🔒 पोर्टल लॉगआउट", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.rerun()

    st.markdown("<hr style='border:1px solid #002147;'>", unsafe_allow_html=True)

    live_t = int(time.time())
    SPREADSHEET_ID = "1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA"
    
    # मूल लाइव डेटा सोर्स जहाँ फॉर्म का डेटा जाता है
    DYNAMIC_DUTY_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=127153860&cache_bypass={live_t}"
    DYNAMIC_MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0&cache_bypass={live_t}"

    # === मुख्यालय मास्टर व्यू ===
    if st.session_state.user_role == "hq_master":
        st.header("📊 मुख्यालय मॉनिटरिंग डैशबोर्ड (Master Page)")
        tab1, tab2 = st.tabs(["📋 लाइव ड्यूटी मॉनिटर", "👮 समस्त थानों के कर्मी विवरण"])
        
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1: filter_date = st.date_input("तारीख", datetime.now().date(), key="hq_d")
            with col2: filter_thana = st.selectbox("थाना", ["सभी थाने"] + THANA_LIST, key="hq_t")
            with col3: filter_duty = st.selectbox("ड्यूटी प्रकार", ["सभी ड्यूटी"] + DUTY_TYPES, key="hq_du")
            
            if st.button("🔍 लाइव डेटा सर्च / रीफ्रेश करें", type="primary", use_container_width=True):
                try:
                    df_all_duties = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    filtered_df = filter_duty_data(df_all_duties, filter_date, filter_thana, filter_duty)
                    
                    # 🔍 क्रम संख्या हमेशा 1 से शुरू होगी (Reset Index) 🔍
                    if not filtered_df.empty:
                        filtered_df = filtered_df.reset_index(drop=True)
                        filtered_df.index = filtered_df.index + 1
                        filtered_df.index.name = "क्रम सं०"
                    
                    st.success(f"📊 रिकॉर्ड लोड हो गया है [कुल: {len(filtered_df)} रिकॉर्ड]")
                    st.dataframe(filtered_df, use_container_width=True)
                except Exception as e: st.error(f"कनेक्शन फेल: {e}")

        with tab2:
            search_master_thana = st.selectbox("थाना चुनें", ["जनपद के सभी थाने"] + THANA_LIST, key="m_select")
            if st.button("🔍 मास्टर सूची लोड करें", use_container_width=True):
                try:
                    df_master = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                    if search_master_thana != "जनपद के सभी थाने":
                        short_search = search_master_thana.replace("कोतवाली", "").strip()
                        thana_col_m = next((c for c in df_master.columns if 'थाना' in c or 'thana' in c.lower()), df_master.columns[0])
                        df_master = df_master[df_master[thana_col_m].astype(str).str.contains(short_search, case=False, na=False)]
                    
                    if not df_master.empty:
                        df_master = df_master.reset_index(drop=True)
                        df_master.index = df_master.index + 1
                        df_master.index.name = "क्रम सं०"
                        
                    st.dataframe(df_master, use_container_width=True)
                except Exception as e: st.error(str(e))

    # === थाना यूज़र व्यू ===
    else:
        assigned_thana = THANA_MAPPING.get(st.session_state.user_role, "अज्ञात थाना")
        thana_tab1, thana_tab2 = st.tabs(["📝 दैनिक ड्यूटी फीडिंग", "🔍 लाइव ड्यूटी देखें"])
        
        with thana_tab1:
            st.subheader(f"ड्यूटी एंट्री फॉर्म - {assigned_thana}")
            
            staff_options = ["-- चुनें / Select Staff --"]
            staff_dict = {}
            try:
                df_all_staff = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                df_all_staff.columns = [str(c).strip() for c in df_all_staff.columns]
                short_assigned = assigned_thana.replace("कोतवाली", "").strip()
                thana_col_staff = next((c for c in df_all_staff.columns if 'थाना' in c or 'thana' in c.lower()), df_all_staff.columns[0])
                df_thana_staff = df_all_staff[df_all_staff[thana_col_staff].astype(str).str.contains(short_assigned, case=False, na=False)]
                
                for _, row in df_thana_staff.iterrows():
                    pno_val = str(row.iloc[0]).split('.')[0]
                    display_text = f"{pno_val} | {row.iloc[1]}"
                    staff_options.append(display_text)
                    staff_dict[display_text] = {"pno": pno_val, "name": row.iloc[1], "rank": "आरक्षी"}
            except Exception: pass

            selected_staff = st.selectbox("सूची से कर्मचारी चुनें", staff_options)
            pno, name, rank = "", "", ""
            if selected_staff != "-- चुनें / Select Staff --":
                pno = staff_dict[selected_staff]["pno"]
                name = staff_dict[selected_staff]["name"]
                rank = staff_dict[selected_staff]["rank"]
                
            duty_type = st.selectbox("ड्यूटी / अवकाश का प्रकार", DUTY_TYPES)
            
            with st.form("sub_form", clear_on_submit=True):
                if st.form_submit_button("🚀 ड्यूटी सबमिट करें", type="primary", use_container_width=True):
                    if name and pno:
                        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSecM8onnA6CMYAtkzIGcRhxSAfnUtdKd9NM8Jxxv4bzajHovA/formResponse"
                        payload = {"entry.154343115": pno, "entry.2122326148": name, "entry.1503406512": rank, "entry.926857669": assigned_thana, "entry.88588834": duty_type}
                        try:
                            requests.post(form_url, data=payload)
                            st.success(f"✔️ {name} का रिकॉर्ड दर्ज हो गया है!")
                            time.sleep(1)
                            st.rerun()
                        except: st.error("कनेक्शन फेल हुआ।")

        with thana_tab2:
            thana_filter_date = st.date_input("तारीख चुनें", datetime.now().date(), key="th_v_d")
            if st.button("🔄 रिकॉर्ड देखें / रीफ्रेश", type="primary", use_container_width=True):
                try:
                    df_thana_duty = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    final_thana_df = filter_duty_data(df_thana_duty, thana_filter_date, assigned_thana, "सभी ड्यूटी")
                    
                    # 🔍 थानों के लिए भी क्रम संख्या हमेशा 1 से शुरू होगी (Reset Index) 🔍
                    if not final_thana_df.empty:
                        final_thana_df = final_thana_df.reset_index(drop=True)
                        final_thana_df.index = final_thana_df.index + 1
                        final_thana_df.index.name = "क्रम सं०"
                        
                    st.dataframe(final_thana_df, use_container_width=True)
                except Exception as e: st.error(str(e))
