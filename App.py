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
    
    /* समरी कार्ड्स के लिए विशेष डिज़ाइन */
    .metric-card {
        background-color: #ffffff;
        border-left: 5px solid #002147;
        border-radius: 6px;
        padding: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

THANA_LIST = [
    "कोतवाली नगर", "कोतवाली देहात", "तुलसीपुर", "गैसड़ी", "पचपेड़वा", "कोतवाली जरवा", 
    "महाराजगंज", "ललिया", "हरैया", "उतरौला", "सादुल्लानगर", "रेहरा बाज़ार", 
    "गौरा चौराहा", "गैड़ास बुजुर्ग", "श्रीदत्तगंज", "ए0एच0टी0 थाना", "रिजर्व पुलिस line", "महिला थाना", "साइबर क्राइम थाना"
]

DUTY_TYPES = ["लॉ एंड ओरडर (L&O)", "वीआईपी (VIP) – ड्यूटी", "पिकेट/गश्त", "कोर्ट ड्यूटी", "समन तामीला", "तफ्तीश/जांच","चाइल्ड केयर अवकाश", "पितृत्व अवकाश", "मातृत्व अवकाश", "आकस्मिक अवकाश","प्रसूति अवकाश", "उपार्जित अवकाश", "सामान्य अवकाश", "गैर हाजिर", "निलम्बित", "अन्य"]

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
        filtered_df = filtered_df[filtered_df[thana_col].astype(str).str.strip() == selected_thana.strip()]

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
        st.markdown("<h3 style='margin-top:0;'>दैनिक ड्यूटी मैनेजमेंट portal</h3>", unsafe_allow_html=True)
    
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
    
    DYNAMIC_DUTY_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=127153860&cache_bypass={live_t}"
    DYNAMIC_MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0&cache_bypass={live_t}"

    # === मुख्यालय मास्टर व्यू ===
    if st.session_state.user_role == "hq_master":
        st.header("📊 मुख्यालय मॉनिटरिंग डैशबोर्ड (Master Page)")
        tab1, tab2 = st.tabs(["📋 लाइव ड्यूटी मॉनिटर", "👮 कर्मी विवरण एवं स्मार्ट सर्च"])
        
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1: filter_date = st.date_input("तारीख", datetime.now().date(), key="hq_d")
            with col2: filter_thana = st.selectbox("थाना", ["सभी थाने"] + THANA_LIST, key="hq_t")
            with col3: filter_duty = st.selectbox("ड्यूटी प्रकार", ["सभी ड्यूटी"] + DUTY_TYPES, key="hq_du")
            
            if st.button("🔍 लाइव डेटा सर्च / रीफ्रेश करें", type="primary", use_container_width=True):
                try:
                    # दोनों शीट को लोड करना (मास्टर स्ट्रेंथ कैलकुलेशन के लिए)
                    df_all_duties = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    df_master_strength = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                    df_master_strength.columns = [str(c).strip() for c in df_master_strength.columns]
                    
                    # 1. मास्टर लिस्ट से कुल स्वीकृत कर्मी संख्या निकालना (थाने के अनुसार या पूरे जनपद का)
                    if filter_thana == "सभी थाने":
                        total_allowed_strength = len(df_master_strength)
                    else:
                        total_allowed_strength = len(df_master_strength[df_master_strength.iloc[:, 4].astype(str).str.strip() == filter_thana.strip()])

                    # फ़िल्टर्ड लाइव ड्यूटी डेटा प्राप्त करना
                    filtered_df = filter_duty_data(df_all_duties, filter_date, filter_thana, filter_duty)
                    
                    if not filtered_df.empty:
                        filtered_df.columns = [str(c).strip() for c in filtered_df.columns]
                        duty_col_check = next((c for c in filtered_df.columns if any(x in c.lower() for x in ['ड्यूटी', 'duty'])), None)
                        
                        # 🎯 कैलकुलेशन लॉजिक
                        total_fed_today = len(filtered_df) # आज जितने रिकॉर्ड दर्ज हुए
                        not_fed_count = max(0, total_allowed_strength - total_fed_today) # जितने दर्ज नहीं हुए
                        
                        leave_count = 0
                        absent_count = 0
                        sus_count = 0
                        if duty_col_check:
                            duty_series = filtered_df[duty_col_check].astype(str)
                            leave_count = duty_series.str.contains("अवकाश").sum()
                            absent_count = duty_series.str.contains("गैर हाजिर").sum()
                            sus_count = duty_series.str.contains("निलम्बित").sum()
                        
                        active_duty = total_fed_today - (leave_count + absent_count + sus_count)
                        
                        # 📊 नया अपग्रेडेड 7-कॉलम डैशबोर्ड ग्रिड (पूरे जनपद या चुनिंदा थाने के लाइव गैप एनालिसिस के साथ)
                        st.markdown(f"<h5>📌 स्टैटिस्टिक्स रिपोर्ट: {filter_thana} ({filter_date.strftime('%d-%m-%Y')})</h5>", unsafe_allow_html=True)
                        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6, m_col7 = st.columns(7)
                        
                        m_col1.markdown(f"<div class='metric-card' style='border-left-color:#17a2b8;'><h6 style='margin:0;color:#17a2b8;'>कुल स्वीकृत कर्मी</h6><h2 style='margin:5px 0;color:#17a2b8;'>{total_allowed_strength}</h2></div>", unsafe_allow_html=True)
                        m_col2.markdown(f"<div class='metric-card' style='border-left-color:#002147;'><h6 style='margin:0;color:#002147;'>आज दर्ज कर्मी</h6><h2 style='margin:5px 0;color:#002147;'>{total_fed_today}</h2></div>", unsafe_allow_html=True)
                        m_col3.markdown(f"<div class='metric-card' style='border-left-color:#dc3545; background-color:#fff5f5;'><h6 style='margin:0;color:#dc3545;'>दर्ज नहीं (शेष)</h6><h2 style='margin:5px 0;color:#dc3545;'>{not_fed_count}</h2></div>", unsafe_allow_html=True)
                        m_col4.markdown(f"<div class='metric-card' style='border-left-color:#28a745;'><h6 style='margin:0;color:#28a745;'>सक्रिय ड्यूटी पर</h6><h2 style='margin:5px 0;color:#28a745;'>{active_duty}</h2></div>", unsafe_allow_html=True)
                        m_col5.markdown(f"<div class='metric-card' style='border-left-color:#ffc107;'><h6 style='margin:0;color:#ffc107;'>अवकाश पर</h6><h2 style='margin:5px 0;color:#ffc107;'>{leave_count}</h2></div>", unsafe_allow_html=True)
                        m_col6.markdown(f"<div class='metric-card' style='border-left-color:#b55d00;'><h6 style='margin:0;color:#b55d00;'>गैर हाजिर</h6><h2 style='margin:5px 0;color:#b55d00;'>{absent_count}</h2></div>", unsafe_allow_html=True)
                        m_col7.markdown(f"<div class='metric-card' style='border-left-color:#6c757d;'><h6 style='margin:0;color:#6c757d;'>निलम्बित</h6><h2 style='margin:5px 0;color:#6c757d;'>{sus_count}</h2></div>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)

                        filtered_df = filtered_df.reset_index(drop=True)
                        filtered_df.index = filtered_df.index + 1
                        filtered_df.index.name = "क्रम सं०"
                    else:
                        # यदि कोई भी डेटा दर्ज नहीं है तो केवल स्ट्रेंथ कार्ड्स दिखाना
                        m_col1, m_col2, m_col3 = st.columns(3)
                        m_col1.markdown(f"<div class='metric-card' style='border-left-color:#17a2b8;'><h6 style='margin:0;color:#17a2b8;'>कुल स्वीकृत कर्मी</h6><h2 style='margin:5px 0;color:#17a2b8;'>{total_allowed_strength}</h2></div>", unsafe_allow_html=True)
                        m_col2.markdown(f"<div class='metric-card' style='border-left-color:#002147;'><h6 style='margin:0;color:#002147;'>आज दर्ज कर्मी</h6><h2 style='margin:5px 0;color:#002147;'>0</h2></div>", unsafe_allow_html=True)
                        m_col3.markdown(f"<div class='metric-card' style='border-left-color:#dc3545;'><h6 style='margin:0;color:#dc3545;'>दर्ज नहीं (शेष)</h6><h2 style='margin:5px 0;color:#dc3545;'>{total_allowed_strength}</h2></div>", unsafe_allow_html=True)
                    
                    st.success(f"📊 रिकॉर्ड लोड हो गया है [कुल प्रदर्शित सूची: {len(filtered_df)} रिकॉर्ड]")
                    st.dataframe(filtered_df, use_container_width=True)
                except Exception as e: st.error(f"कनेक्शन फेल: {e}")

        with tab2:
            st.subheader("🔍 कर्मियों की खोज (स्मार्ट सर्च इंजन)")
            sc1, sc2, sc3 = st.columns([2, 2, 2])
            with sc1: search_master_thana = st.selectbox("थाना अनुसार फ़िल्टर", ["जनपद के सभी थाने"] + THANA_LIST, key="m_select")
            with sc2: search_pno = st.text_input("PNO नंबर से खोजें (Exact/Partial)", "").strip()
            with sc3: search_name = st.text_input("कर्मचारी के नाम से खोजें", "").strip()
            
            if st.button("🔍 मास्टर सूची लोड / सर्च करें", use_container_width=True):
                try:
                    df_master = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                    df_master.columns = [str(c).strip() for c in df_master.columns]
                    
                    if search_master_thana != "जनपद के सभी थाने":
                        df_master = df_master[df_master.iloc[:, 4].astype(str).str.strip() == search_master_thana.strip()]
                    
                    if search_pno:
                        df_master = df_master[df_master.iloc[:, 1].astype(str).str.contains(search_pno, case=False, na=False)]
                        
                    if search_name:
                        df_master = df_master[df_master.iloc[:, 2].astype(str).str.contains(search_name, case=False, na=False)]
                    
                    if not df_master.empty:
                        df_master = df_master.reset_index(drop=True)
                        df_master.index = df_master.index + 1
                        df_master.index.name = "क्रम सं०"
                        
                    st.success(f"🔍 खोज के आधार पर {len(df_master)} कर्मियों का विवरण मिला।")
                    st.dataframe(df_master, use_container_width=True)
                except Exception as e: st.error(str(e))

    # === थाना यूज़र व्यू ===
    else:
        assigned_thana = THANA_MAPPING.get(st.session_state.user_role, "अज्ञात थाना")
        thana_tab1, thana_tab2 = st.tabs(["📝 दैनिक ड्यूटी feeding", "🔍 लाइव ड्यूटी देखें"])
        
        with thana_tab1:
            st.subheader(f"ड्यूटी एंट्री फॉर्म - {assigned_thana}")
            
            staff_options = ["-- चुनें / Select Staff --"]
            staff_dict = {}
            try:
                df_all_staff = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                df_all_staff.columns = [str(c).strip() for c in df_all_staff.columns]
                
                df_thana_staff = df_all_staff[df_all_staff.iloc[:, 4].astype(str).str.strip() == assigned_thana.strip()]
                
                idx = 1
                for _, row in df_thana_staff.iterrows():
                    pno_val = str(row.iloc[1]).split('.')[0].strip()
                    name_val = str(row.iloc[2]).strip()
                    rank_val = str(row.iloc[3]).strip()
                    
                    display_text = f"{idx} | {name_val} | PNO: {pno_val} | {rank_val}"
                    staff_options.append(display_text)
                    staff_dict[display_text] = {"pno": pno_val, "name": name_val, "rank": rank_val}
                    idx += 1
            except Exception as e: 
                st.error(f"शीट रीन्डेक्स एरर: {str(e)}")

            selected_staff = st.selectbox("सूची से कर्मचारी चुनें (क्रम | नाम | PNO | पदनाम)", staff_options)
            pno, name, rank = "", "", ""
            
            if selected_staff != "-- चुनें / Select Staff --":
                pno = staff_dict[selected_staff]["pno"]
                name = staff_dict[selected_staff]["name"]
                rank = staff_dict[selected_staff]["rank"]
                st.markdown(f"🚩 **चयनित विवरण:** `नाम: {name}` | `PNO: {pno}` | `पदनाम: {rank}`")
                
            duty_type = st.selectbox("ड्यूटी / अवकाश का प्रकार", DUTY_TYPES)
            
            is_leave = "अवकाश" in duty_type
            is_absent_or_sus = duty_type in ["गैर हाजिर", "निलम्बित"]
            
            with st.form("sub_form", clear_on_submit=True):
                leave_start = datetime.now().date()
                leave_end = datetime.now().date()
                
                if is_leave:
                    st.info(f"ℹ️ {duty_type} की समयावधि दर्ज करें:")
                    col_start, col_end = st.columns(2)
                    with col_start:
                        leave_start = st.date_input("प्रारम्भ तिथि (From Date)", datetime.now().date(), key="lv_st")
                    with col_end:
                        leave_end = st.date_input("समाप्ति तिथि (To Date)", datetime.now().date(), key="lv_ed")
                    
                    if leave_start > leave_end:
                        st.error("❌ त्रुटि: प्रारम्भ तिथि, समाप्ति तिथि से बाद की नहीं हो सकती!")
                        
                elif is_absent_or_sus:
                    st.info(f"ℹ️ {duty_type} होने की तिथि दर्ज करें:")
                    leave_start = st.date_input("प्रारम्भ तिथि / किस दिनांक से (From Date)", datetime.now().date(), key="abs_st")
                
                duty_remark = st.text_input("📋 ड्यूटी रिमार्क / विशेष टिप्पणी (जैसे: कोर्ट का नाम, वीआईपी रूट या आदेश संख्या - ऐच्छिक)", "").strip()
                
                if st.form_submit_button("🚀 ड्यूटी सबमिट करें", type="primary", use_container_width=True):
                    if name and pno:
                        today_date = datetime.now().date()
                        is_duplicate = False
                        existing_duty = ""
                        
                        try:
                            df_check = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                            df_check.columns = [str(c).strip() for c in df_check.columns]
                            
                            d_col = next((c for c in df_check.columns if any(x in c.lower() for x in ['तारीख', 'दिनांक', 'date', 'timestamp'])), None)
                            p_col = next((c for c in df_check.columns if any(x in c.lower() for x in ['pno', 'पीएनओ', 'नम्बर'])), None)
                            du_col = next((c for c in df_check.columns if any(x in c.lower() for x in ['ड्यूटी', 'duty'])), None)
                            
                            if d_col and p_col:
                                df_check['temp_date'] = pd.to_datetime(df_check[d_col], errors='coerce').dt.date
                                match_rows = df_check[(df_check['temp_date'] == today_date) & (df_check[p_col].astype(str).str.contains(str(pno)))]
                                
                                if not match_rows.empty:
                                    is_duplicate = True
                                    existing_duty = str(match_rows.iloc[0][du_col]) if du_col else "अन्य ड्यूटी"
                        except:
                            pass
                        
                        if is_leave and leave_start > leave_end:
                            st.error("❌ कृपया सही समयावधि चुनें!")
                        elif is_duplicate:
                            st.error(f"⚠️ एलर्ट: {name} (PNO: {pno}) की ड्यूटी आज की तारीख ({today_date.strftime('%d-%m-%Y')}) में पहले से ही '[ {existing_duty} ]' पर लगी है। कृपया किसी और कर्मी को चुनें।")
                        else:
                            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSecM8onnA6CMYAtkzIGcRhxSAfnUtdKd9NM8Jxxv4bzajHovA/formResponse"
                            
                            final_duty_string = duty_type
                            if is_leave:
                                final_duty_string = f"{duty_type} ({leave_start.strftime('%d/%m/%Y')} से {leave_end.strftime('%d/%m/%Y')} तक)"
                            elif is_absent_or_sus:
                                final_duty_string = f"{duty_type} (दिनांक {leave_start.strftime('%d/%m/%Y')} से)"
                            
                            if duty_remark:
                                final_duty_string = f"{final_duty_string} - [{duty_remark}]"
                                
                            payload = {"entry.154343115": pno, "entry.2122326148": name, "entry.1503406512": rank, "entry.926857669": assigned_thana, "entry.88588834": final_duty_string}
                            
                            success_flag = False
                            try:
                                requests.post(form_url, data=payload)
                                success_flag = True
                            except:
                                st.error("❌ नेटवर्क या कनेक्शन फेल हुआ। कृपया दोबारा प्रयास करें।")
                            
                            if success_flag:
                                st.success(f"✔️ {name} का रिकॉर्ड सफलतापूर्वक दर्ज हो गया है!")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.error("❌ कृपया पहले सूची से कर्मचारी का चयन करें!")

        with thana_tab2:
            thana_filter_date = st.date_input("तारीख चुनें", datetime.now().date(), key="th_v_d")
            if st.button("🔄 रिकॉर्ड देखें / रीफ्रेश", type="primary", use_container_width=True):
                try:
                    df_thana_duty = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
                    df_thana_duty.columns = [str(c).strip() for c in df_thana_duty.columns]
                    thana_col_check = next((c for c in df_thana_duty.columns if any(x in c.lower() for x in ['थाना', 'thana', 'unit'])), None)
                    
                    if thana_col_check:
                        df_thana_duty = df_thana_duty[df_thana_duty[thana_col_check].astype(str).str.strip() == assigned_thana.strip()]
                    
                    final_thana_df = filter_duty_data(df_thana_duty, thana_filter_date, assigned_thana, "सभी ड्यूटी")
                    
                    if not final_thana_df.empty:
                        final_thana_df = final_thana_df.reset_index(drop=True)
                        final_thana_df.index = final_thana_df.index + 1
                        final_thana_df.index.name = "क्रम सं०"
                        
                    st.dataframe(final_thana_df, use_container_width=True)
                except Exception as e: st.error(str(e))
