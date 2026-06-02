import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import time

# =============================================================
# चरण 1: पोर्टल कॉन्फ़िगरेशन और पुलिस 'यूनिफॉर्म' थीम (Khaki & Navy)
# =============================================================
st.set_page_config(
    page_title="जिला पुलिस डेली ड्यूटी पोर्टल", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# कैशे की पूरी तरह से सफाई ताकि लाइव डेटा ही दिखे
st.cache_data.clear()

# 👮 बलरामपुर पुलिस कस्टमाइज्ड थीम स्टाइलिंग
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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
    }
    .stButton>button:hover {
        background-color: #800000 !important;
        color: #ffffff !important;
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #002147 !important; padding: 8px !important; }
    .stTabs [data-baseweb="tab"] { color: #ffffff !important; font-weight: bold !important; }
    .stTabs [aria-selected="true"] { background-color: #d4af37 !important; color: #002147 !important; }
    h1, h2, h3, h4 { color: #002147 !important; font-weight: bold !important; }
    [data-testid="stDataFrame"] { background-color: #ffffff !important; border: 3px solid #002147 !important; }
    </style>
""", unsafe_allow_html=True)

# 👮 जनपद बलरामपुर के समस्त थानों एवं इकाइयों की सूची
THANA_LIST = [
    "कोतवाली नगर", "कोतवाली देहात", "तुलसीपुर", "गैसड़ी", "पचपेड़वा", "कोतवाली जरवा", 
    "महाराजगंज", "ललिया", "हरैया", "उतरौला", "सादुल्लानगर", "रेहरा बाज़ार", 
    "गौरा चौराहा", "गैड़ास बुजुर्ग", "श्रीदत्तगंज", "ए0एच0टी0 थाना", "रिजर्व पुलिस line", "महिला थाना", "साइबर क्राइम थाना"
]

DUTY_TYPES = [
    "लॉ एंड ओरडर (L&O)", "वीआईपी (VIP) – ड्यूटी", "पिकेट/गश्त", "कोर्ट ड्यूटी", 
    "समन तामीला", "तफ्तीश/जांच", "आकस्मिक अवकाश", "प्रसूति अवकाश", 
    "सामान्य अवकाश", "मेडिकल अवकाश", "गैर हाजिर", "निलम्बित", "अन्य"
]

# सुरक्षित लॉगिन क्रेडेंशियल्स
USER_CREDENTIALS = {
    "hq_master":  "hq@123", "9454403019": "thana@3019", "9454403020": "thana@3020",
    "9454404895": "thana@4895", "9454403022": "thana@3022", "9454403025": "thana@3025",
    "9454403023": "thana@3023", "9454403026": "thana@3026", "9454403030": "thana@3030",
    "9454403021": "thana@3021", "9454403024": "thana@3024", "9454403027": "thana@3027",
    "9454403031": "thana@3031", "7317724235": "thana@4235", "9454403028": "thana@3028",
    "7398638787": "thana@8787", "9454403039": "thana@3039", "9454402345": "thana@2345",
    "7839855506": "thana@5506", "7839855004": "thana@5004"
}

# CUG नंबर के अनुसार थानों का मैपिंग लॉजिक
THANA_MAPPING = {
    "9454403019": "कोतवाली नगर", "9454403020": "कोतवाली देहात", "9454404895": "महिला थाना",
    "9454403022": "गौरा चौराहा", "9454403025": "ललिया", "9454403023": "हरैया",
    "9454403026": "महाराजगंज", "9454403030": "तुलसीपुर", "9454403021": "गैसड़ी",
    "9454403024": "कोतवाली जरवा", "9454403027": "पचपेड़वा", "9454403031": "उतरौला",
    "7317724235": "श्रीदत्तगंज", "7398638787": "गैड़ास बुजुर्ग", "9454403028": "रेहरा बाज़ार",
    "9454403039": "सादुल्लानगर", "9454402345": "रिजर्व पुलिस लाइन", "7839855506": "ए0एच0टी0 थाना",
    "7839855004": "साइबर क्राइम थाना"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# 🛠️ 100% फुलप्रूफ डायनेमिक फ़िल्टर इंजन
def filter_duty_data(df, selected_date, selected_thana, selected_duty):
    if df.empty:
        return df
    
    filtered_df = df.copy()
    filtered_df.columns = [str(c).strip() for c in filtered_df.columns]
    
    date_col, thana_col, duty_col = None, None, None
    
    # कॉलम ढूंढने का स्मार्ट तरीका
    for c in filtered_df.columns:
        c_low = c.lower()
        if any(x in c_low for x in ['तारीख', 'दिनांक', 'date', 'timestamp', 'time']):
            date_col = c
        if any(x in c_low for x in ['थाना', 'thana', 'इकाई', 'unit', 'place']):
            thana_col = c
        elif filtered_df[c].astype(str).str.contains('|'.join(THANA_LIST), case=False, na=False).any():
            thana_col = c
        if any(x in c_low for x in ['ड्यूटी', 'duty', 'प्रकार', 'status', 'विवरण']):
            duty_col = c

    # 1. ⏱️ टाइमस्टैम्प से केवल तारीख निकालकर मैच करना (ताकि समय रुकावट न बने)
    if date_col:
        try:
            filtered_df['parsed_date_internal'] = pd.to_datetime(filtered_df[date_col], errors='coerce').dt.date
            filtered_df = filtered_df[filtered_df['parsed_date_internal'] == selected_date]
            filtered_df = filtered_df.drop(columns=['parsed_date_internal'])
        except Exception:
            d_dash = selected_date.strftime("%d-%m-%Y")
            d_slash = selected_date.strftime("%d/%m/%Y")
            d_short_slash = f"{int(selected_date.strftime('%d'))}/{int(selected_date.strftime('%m'))}/{selected_date.strftime('%Y')}"
            def match_date_fallback(val):
                s = str(val).strip()
                return any(f in s for f in [d_dash, d_slash, d_short_slash])
            filtered_df = filtered_df[filtered_df[date_col].apply(match_date_fallback)]

    # 2. 🎯 थाना फ़िल्टर (केवल तभी काम करेगा जब "सभी थाने" न हो)
    if selected_thana and selected_thana != "सभी थाने" and thana_col:
        short_name = selected_thana.replace("कोतवाली", "").strip()
        def match_thana(val):
            s = str(val).strip().lower()
            if not s or s == 'nan': return False
            return (selected_thana.lower() in s or short_name.lower() in s)
        filtered_df = filtered_df[filtered_df[thana_col].apply(match_thana)]

    # 3. ड्यूटी फ़िल्टर
    if selected_duty and selected_duty != "सभी ड्यूटी" and duty_col:
        def match_duty(val):
            s = str(val).strip().lower()
            if not s or s == 'nan': return False
            return (str(selected_duty).lower() in s)
        filtered_df = filtered_df[filtered_df[duty_col].apply(match_duty)]
            
    return filtered_df

SP_PHOTO_URL = "https://drive.google.com/file/d/1F96XGFoFst9RPcvjqet1SCpy4HiK6Qdu/view?usp=drive_link"

# =============================================================
# चरण 2: सुरक्षित लॉगिन गेटवे
# =============================================================
if not st.session_state.logged_in:
    col_logo, col_title = st.columns([1, 4])
    with col_logo: st.image(SP_PHOTO_URL, width=135)
    with col_title:
        st.markdown("<h1 style='color:#002147;'>🚨 उत्तर प्रदेश police | जनपद बलरामपुर</h1>", unsafe_allow_html=True)
        st.markdown("<h3>दैनिक ड्यूटी मैनेजमेंट फीडिंग एवं मॉनिटरिंग पोर्टल</h3>", unsafe_allow_html=True)
    
    with st.container():
        username = st.text_input("यूज़रनेम (CUG नंबर या मास्टर आईडी)", key="login_username")
        password = st.text_input("पासवर्ड (Password)", type="password", key="login_password")
        if st.button("🔓 पोर्टल में प्रवेश करें", use_container_width=True):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                st.session_state.logged_in = True
                st.session_state.user_role = username
                st.rerun()
            else:
                st.error("❌ गलत लॉगिन विवरण।")

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
    DYNAMIC_DUTY_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=127153860&cache_bypass={live_t}"
    DYNAMIC_MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=0&cache_bypass={live_t}"

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
                    df_duty = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    filtered_df = filter_duty_data(df_duty, filter_date, filter_thana, filter_duty)
                    
                    st.success(f"📊 रिकॉर्ड लोड हो गया है [कुल: {len(filtered_df)} रिकॉर्ड]")
                    st.dataframe(filtered_df, use_container_width=True)
                except Exception as e:
                    st.error(f"कनेक्शन फेल: {e}")

        with tab2:
            st.subheader("👮 थाना वार पुलिसकर्मी सूची (मास्टर रिकॉर्ड)")
            search_master_thana = st.selectbox("थाना चुनें", ["जनपद के सभी थाने"] + THANA_LIST, key="master_thana_dropdown")
            
            if st.button("🔍 मास्टर सूची लोड करें", use_container_width=True, key="load_master_btn"):
                try:
                    df_master = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                    df_master.columns = [str(c).strip() for c in df_master.columns]
                    df_master = df_master.fillna("").astype(str)
                    
                    if search_master_thana != "जनपद के सभी थाने":
                        thana_col_m = None
                        for col_m in df_master.columns:
                            if any(x in col_m.lower() for x in ['थाना', 'thana', 'इकाई', 'unit']):
                                thana_col_m = col_m
                                break
                        
                        if thana_col_m:
                            short_search_name = search_master_thana.replace("कोतवाली", "").strip()
                            filtered_master = df_master[df_master[thana_col_m].str.contains(short_search_name, case=False, na=False)]
                        else:
                            short_search_name = search_master_thana.replace("कोतवाली", "").strip()
                            filtered_master = df_master[df_master.apply(lambda r: r.str.contains(short_search_name, case=False)).any(axis=1)]
                    else:
                        filtered_master = df_master.copy()
                        
                    st.success(f"🗂️ {search_master_thana} का मास्टर रिकॉर्ड [कुल: {len(filtered_master)} पुलिसकर्मी]")
                    st.dataframe(filtered_master, use_container_width=True)
                except Exception as e: 
                    st.error(f"त्रुटि: {e}")

    # === थाना यूजर व्यू ===
    else:
        assigned_thana = THANA_MAPPING.get(st.session_state.user_role, "अज्ञात थाना")
        thana_tab1, thana_tab2 = st.tabs(["📝 ड्यूटी फीड करें", "🔍 लाइव ड्यूटी देखें"])
        
        with thana_tab1:
            st.subheader(f"फीडिंग फॉर्म - {assigned_thana}")
            staff_options = ["-- चुनें / Select Staff --"]
            staff_dict = {}
            try:
                df_all_staff = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                df_all_staff.columns = [str(c).strip() for c in df_all_staff.columns]
                df_all_staff = df_all_staff.fillna("").astype(str)
                
                thana_col_staff = None
                for c_st in df_all_staff.columns:
                    if any(x in c_st.lower() for x in ['थाना', 'thana', 'unit']):
                        thana_col_staff = c_st
                        break
                
                if thana_col_staff:
                    short_assigned = assigned_thana.replace("कोतवाली", "").strip()
                    df_thana_staff = df_all_staff[df_all_staff[thana_col_staff].str.contains(short_assigned, case=False, na=False)]
                else:
                    df_thana_staff = df_all_staff.copy()
                
                for _, row in df_thana_staff.iterrows():
                    col_list = list(df_all_staff.columns)
                    pno_col = next((c for c in col_list if 'pno' in c.lower() or 'नंबर' in c or 'न०' in c), col_list[0])
                    name_col = next((c for c in col_list if 'नाम' in c.lower() or 'name' in c.lower()), col_list[1])
                    rank_col = next((c for c in col_list if 'पद' in c or 'rank' in c.lower() or 'पदनाम' in c), None)
                    
                    pno_val = str(row[pno_col]).split('.')[0]
                    # यहाँ वास्तविक पदनाम निकाला जा रहा है, अगर खाली है तभी डिफ़ॉल्ट 'आरक्षी' लगेगा
                    actual_rank = str(row[rank_col]).strip() if (rank_col and str(row[rank_col]).strip() != "") else "आरक्षी"
                    
                    display_text = f"{pno_val} | {row[name_col]} | {actual_rank}"
                    staff_options.append(display_text)
                    staff_dict[display_text] = {"pno": pno_val, "name": row[name_col], "rank": actual_rank}
            except Exception as e: 
                pass

            selected_staff = st.selectbox("सूची से कर्मचारी चुनें", staff_options, key="thana_staff_select")
            
            pno, name, rank = "", "", ""
            if selected_staff != "-- चुनें / Select Staff --" and selected_staff in staff_dict:
                pno = staff_dict[selected_staff]["pno"]
                name = staff_dict[selected_staff]["name"]
                rank = staff_dict[selected_staff]["rank"]

            st.markdown("---")
            duty_type = st.selectbox("ड्यूटी / अवकाश का प्रकार", DUTY_TYPES, key="dynamic_duty_type_select")
            
            with st.form("submission_form", clear_on_submit=True):
                # फ़ॉर्म के अंदर वेरिएबल्स को सुरक्षित रखने के लिए st.hidden_input या सीधे डिस्प्ले का उपयोग किया गया है
                st.write(f"चयनित पद/नाम: **{rank} {name} ({pno})**")
                
                if st.form_submit_button("🚀 रिकॉर्ड सबमिट करें", type="primary", use_container_width=True):
                    # फ़ॉर्म सबमिशन लॉजिक में यह सुनिश्चित किया गया है कि वास्तविक सिलेक्टेड रैंक ही पास हो
                    if name and pno and rank:
                        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSecM8onnA6CMYAtkzIGcRhxSAfnUtdKd9NM8Jxxv4bzajHovA/formResponse"
                        payload = {
                            "entry.154343115": pno, 
                            "entry.2122326148": name, 
                            "entry.1503406512": rank, # अब यहाँ मास्टर शीट की सही रैंक जाएगी
                            "entry.926857669": assigned_thana, 
                            "entry.88588834": duty_type
                        }
                        try:
                            res = requests.post(form_url, data=payload)
                            st.success(f"✔️ {rank} {name} का रिकॉर्ड सफलतापूर्वक दर्ज हो गया है!")
                        except: 
                            st.error("सबमिशन फेल हुआ। कृपया इंटरनेट कनेक्शन जांचें।")
                    else:
                        st.error("❌ कृपया फॉर्म सबमिट करने से पहले ऊपर सूची से कर्मचारी चुनें!")

        with thana_tab2:
            thana_filter_date = st.date_input("तारीख चुनें", datetime.now().date(), key="th_view_d")
            if st.button("🔄 अपने थाने का रिकॉर्ड देखें / रीफ्रेश करें", type="primary", use_container_width=True):
                try:
                    df_thana_duty = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    final_thana_df = filter_duty_data(df_thana_duty, thana_filter_date, assigned_thana, "सभी ड्यूटी")
                    
                    st.success(f"📊 केवल **{assigned_thana}** का लाइव रिकॉर्ड [कुल: {len(final_thana_df)} रिकॉर्ड]:")
                    st.dataframe(final_thana_df, use_container_width=True)
                except Exception as e: 
                    st.error(str(e))
