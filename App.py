import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests
import random

# =============================================================
# चरण 1: पोर्टल कॉन्फ़िगरेशन और पुलिस 'यूनिफॉर्म' थीम (Khaki & Navy)
# =============================================================
st.set_page_config(
    page_title="जिला पुलिस डेली ड्यूटी पोर्टल", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# कैशे क्लियर ताकि डेटा हमेशा लाइव गूगल शीट से फ्रेश लोड हो
st.cache_data.clear()

# 👮 पुलिसिया कलर पैलेट: खाकी, गहरा नीला (#002147), लाल (#800000)
st.markdown("""
    <style>
    /* पूरे ऐप का बैकग्राउंड खाकी शेड में */
    .stApp, .main {
        background: linear-gradient(135deg, #f5f5dc 0%, #e3d5b8 100%) !important;
    }
    
    /* स्ट्रीमलिट के डिफॉल्ट टॉप हेडर को छुपाना */
    #MainMenu, header, footer, [data-testid="stHeader"], .stAppHeader {
        visibility: hidden !important;
        display: none !important;
    }

    /* मुख्य कंटेनर की पैडिंग सेटिंग */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        max-width: 95% !important;
    }

    /* पुलिस स्टाइल बटन - गहरा नीला, गोल्डन बॉर्डर और सफेद अक्षर */
    .stButton>button {
        background-color: #002147 !important;
        color: #ffffff !important;
        border: 2px solid #d4af37 !important;
        border-radius: 6px !important;
        padding: 10px 24px !important;
        font-weight: bold !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #800000 !important;
        color: #ffffff !important;
        border-color: #ffffff !important;
    }

    /* टैब्स की स्टाइलिंग - खाकी वर्दी पर नीली और सुनहरी पट्टी */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #002147 !important;
        padding: 8px !important;
        border-radius: 8px 8px 0 0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #ffffff !important;
        font-size: 16px !important;
        font-weight: bold !important;
        padding: 10px 20px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d4af37 !important;
        color: #002147 !important;
        border-radius: 4px !important;
    }

    /* हेडिंग्स - खाकी वर्दी पर गहरे नीले और लाल बॉर्डर के अक्षर */
    h1, h2, h3, h4 {
        color: #002147 !important;
        font-weight: bold !important;
    }
    
    /* डेटा फ़्रेम/टेबल को बॉर्डर देना */
    [data-testid="stDataFrame"] {
        background-color: #ffffff !important;
        border: 3px solid #002147 !important;
        border-radius: 8px !important;
        padding: 5px !important;
    }

    /* इनपुट और सेलेक्ट बॉक्स के बॉर्डर्स को गहरा करना */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {
        border: 2px solid #002147 !important;
        border-radius: 6px !important;
    }

    /* अलर्ट बॉक्स - पुलिस पेट्रोलिंग लाइट जैसा लाल और सुनहरा */
    .alert-box {
        background-color: #800000 !important;
        color: white !important;
        padding: 15px !important;
        border-radius: 8px !important;
        border-left: 10px solid #d4af37 !important;
        margin-bottom: 15px !important;
        font-weight: bold !important;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.15);
    }
    </style>
""", unsafe_allow_html=True)

# 👮 जनपद बलरामपुर के समस्त थानों एवं इकाइयों की सूची
THANA_LIST = [
    "कोतवाली नगर", "कोतवाली देहात", "तुलसीपुर", "गैसड़ी", "पचपेड़वा", "कोतवाली जरवा", 
    "महाराजगंज", "ललिया", "हरैया", "उतरौला", "सादुल्लानगर", "रेहरा बाज़ार", 
    "गौरा चौराहा", "गैड़ास बुजुर्ग", "श्रीदत्तगंज", "ए0एच0टी0 थाना", "रिजर्व पुलिस line", "महिला थाना", "साइबर क्राइम थाना"
]

# ड्यूटी एवं कार्यभार स्थिति के प्रकार
DUTY_TYPES = [
    "लॉ एंड ओरडर (L&O)", "वीआईपी (VIP) ड्यूटी", "पिकेट/गश्त", "कोर्ट ड्यूटी", 
    "समन तामीला", "तफ्तीश/जांच", "आकस्मिक अवकाश", "प्रसूति अवकाश", 
    "सामान्य अवकाश", "मेडिकल अवकाश", "गैर हाजिर", "निलम्बित", "अन्य"
]

# सुरक्षित लॉगिन क्रेडेंशियल्स (CUG नंबर्स एवं मास्टर आईडी)
USER_CREDENTIALS = {
    "hq_master":  "hq@123", 
    "9454403022": "thana@3022",
    "9454403019": "thana@3019",
    "9454403020": "thana@3020",
    "9454404895": "thana@4895",
    "9454403025": "thana@3025",
    "9454403023": "thana@3023",
    "9454403026": "thana@3026",
    "9454403030": "thana@3030",
    "9454403021": "thana@3021",
    "9454403024": "thana@3024",
    "9454403027": "thana@3027",
    "9454403031": "thana@3031",
    "7317724235": "thana@4235",
    "9454403028": "thana@3028",
    "7398638787": "thana@8787",
    "9454403039": "thana@3039",
    "9454402345": "thana@2345",
    "7839855506": "thana@5506",
    "7839855004": "thana@5004"
}

# CUG नंबर के अनुसार थानों का ऑटोमैटिक एलाइनमेंट मैपिंग
THANA_MAPPING = {
    "9454403019": "कोतवाली नगर",
    "9454403020": "कोतवाली देहात",
    "9454404895": "महिला थाना",
    "9454403022": "गौरा चौराहा",
    "9454403025": "ललिया",
    "9454403023": "हरैया",
    "9454403026": "महाराजगंज",
    "9454403030": "तुलसीपुर",
    "9454403021": "गैसड़ी",
    "9454403024": "कोतवाली जरवा",
    "9454403027": "पचपेड़वा",
    "9454403031": "उतरौला",
    "7317724235": "श्रीदत्तगंज",
    "7398638787": "गैड़ास बुजुर्ग",
    "9454403028": "रेहरा बाज़ार",
    "9454403039": "सादुल्लानगर",
    "9454402345": "रिजर्व पुलिस लाइन",
    "7839855506": "ए0एच0टी0 थाना",
    "7839855004": "साइबर क्राइम थाना"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None

# 🛠️ बिल्कुल सटीक और सुरक्षित मॉनिटरिंग फ़िल्टर लॉजिक
def filter_duty_data(df, selected_date, selected_thana, selected_duty):
    if df.empty:
        return df
    
    filtered_df = df.copy()
    filtered_df.columns = [str(c).strip() for c in filtered_df.columns]
    
    # 1. थाना कॉलम फ़िल्टर
    if selected_thana and selected_thana != "सभी थाने":
        thana_col = None
        for c in filtered_df.columns:
            if 'थाना' in c or 'thana' in c.lower() or 'इकाई' in c:
                thana_col = c
                break
        if thana_col:
            filtered_df[thana_col] = filtered_df[thana_col].astype(str).str.strip()
            short_name = selected_thana.replace("कोतवाली", "").strip()
            thana_mask = filtered_df[thana_col].apply(lambda x: selected_thana in str(x) or short_name in str(x) or str(x) in selected_thana)
            filtered_df = filtered_df[thana_mask]

    # 2. ड्यूटी का प्रकार फ़िल्टर
    if selected_duty and selected_duty != "सभी ड्यूटी":
        duty_col = None
        for c in filtered_df.columns:
            if 'ड्यूटी' in c or 'प्रकार' in c or 'duty' in c.lower():
                duty_col = c
                break
        if duty_col:
            filtered_df = filtered_df[filtered_df[duty_col].astype(str).str.contains(str(selected_duty), case=False, na=False)]

    # 3. स्मार्ट तारीख फ़िल्टर (मजबूत लॉजिक के साथ)
    d_dash = selected_date.strftime("%d-%m-%Y")
    d_slash = selected_date.strftime("%d/%m/%Y")
    d_y_dash = selected_date.strftime("%Y-%m-%d")
    d_short_slash = selected_date.strftime("%e/%m/%Y").strip()
    
    date_col = None
    for c in filtered_df.columns:
        if 'तारीख' in c or 'दिनांक' in c or 'date' in c.lower() or 'timestamp' in c.lower() or 'time' in c.lower():
            date_col = c
            break
            
    if date_col and not filtered_df.empty:
        filtered_df[date_col] = filtered_df[date_col].astype(str).str.strip()
        # यहाँ चेक कर रहे हैं कि सिलेक्टेड तारीख स्ट्रिंग का हिस्सा है या नहीं (Timestamp को हैंडल करने के लिए)
        date_mask = filtered_df[date_col].apply(lambda x: d_dash in str(x) or d_slash in str(x) or d_y_dash in str(x) or d_short_slash in str(x))
        filtered_df = filtered_df[date_mask]
            
    return filtered_df

# 📸 यूज़र द्वारा प्रदान किया गया एसपी सर की फोटो का नया लाइव यूआरएल
SP_PHOTO_URL = "https://uppolice.gov.in/en/officerprofile?transid=2701&slugName=fatehgarh"

# =============================================================
# चरण 2: सुरक्षित लॉगिन गेटवे (Police UI)
# =============================================================
if not st.session_state.logged_in:
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image(SP_PHOTO_URL, width=135, use_container_width=False)
    with col_title:
        st.markdown("<h1 style='color:#002147; margin-bottom:2px;'>🚨 उत्तर प्रदेश पुलिस | जनपद बलरामपुर</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-top:0px; color:#002147;'>दैनिक ड्यूटी मैनेजमेंट फीडिंग एवं मॉनिटरिंग पोर्टल</h3>", unsafe_allow_html=True)
        st.markdown("<b style='color:#800000;'>'सुरक्षा आपकी, संकल्प हमारा' - पुलिस अधीक्षक कार्यालय, बलरामपुर</b>", unsafe_allow_html=True)
        
    st.markdown("<hr style='border:1px solid #002147;'>", unsafe_allow_html=True)
    
    with st.container():
        col_main, _ = st.columns([2, 1])
        with col_main:
            st.markdown("### 🔐 सुरक्षित लॉगिन गेटवे")
            username = st.text_input("यूज़रनेम (CUG नंबर या मास्टर आईडी)", key="login_username")
            password = st.text_input("पासवर्ड (Password)", type="password", key="login_password")
            
            if st.button("🔓 पोर्टल में प्रवेश करें", type="primary", use_container_width=True):
                if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_role = username
                    st.rerun()
                else:
                    st.error("❌ गलत यूज़रनेम या पासवर्ड! कृपया दोबारा जांचें।")

# =============================================================
# चरण 3: मुख्य सुरक्षित क्षेत्र (लॉगिन के पश्चात)
# =============================================================
else:
    col_main_title, col_logout = st.columns([8, 2])
    with col_main_title:
        st.markdown("### 🚓 बलरामपुर पुलिस डेली ड्यूटी पोर्टल")
    with col_logout:
        if st.button("🔒 पोर्टल लॉगआउट", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.rerun()
            
    st.markdown("<hr style='border:1px solid #002147;'>", unsafe_allow_html=True)

    # =============================================================
    # मिकैनिज्म अ: केवल HQ_MASTER के लिए (मुख्यालय मास्टर व्यू)
    # =============================================================
    if st.session_state.user_role == "hq_master":
        col_sp_img, col_sp_txt = st.columns([1, 5])
        with col_sp_img:
            st.image(SP_PHOTO_URL, width=135)
        with col_sp_txt:
            st.markdown("<h2 style='color:#002147; margin-bottom:2px;'>पुलिस अधीक्षक कार्यालय, बलरामपुर</h2>", unsafe_allow_html=True)
            st.markdown("<h4 style='color:#800000; margin-top:0px;'>⚖️ 'सुरक्षा आपकी, संकल्प हमारा'</h4>", unsafe_allow_html=True)
            
        st.markdown("---")
        
        # डायनेमिक टाइमस्टैम्प जनरेशन ताकि डेटा कैश न हो और हर बार लाइव लोड हो
        live_stamp = random.randint(100000, 999999)
        DYNAMIC_DUTY_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=127153860&cache_bypass={live_stamp}&t={live_stamp}"
        DYNAMIC_MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=0&cache_bypass={live_stamp}&t={live_stamp}"

        # 🔔 पूर्व-चेतावनी प्रणाली (Leave Expiry Alerts)
        try:
            df_duty_check = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
            df_duty_check.columns = [str(c).strip() for c in df_duty_check.columns]
            
            end_date_col = next((c for c in df_duty_check.columns if 'तक' in c or 'end' in c.lower() or 'expiry' in c.lower()), None)
            name_col_c = next((c for c in df_duty_check.columns if 'नाम' in c or 'name' in c.lower()), None)
            thana_col_c = next((c for c in df_duty_check.columns if 'थाना' in c or 'thana' in c.lower() or 'इकाई' in c), None)
            type_col_c = next((c for c in df_duty_check.columns if 'ड्यूटी' in c or 'प्रकार' in c), None)
            
            if end_date_col and name_col_c:
                today = datetime.now().date()
                alert_list = []
                
                for _, r in df_duty_check.dropna(subset=[end_date_col, name_col_c]).iterrows():
                    try:
                        val_str = str(r[end_date_col]).strip()
                        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                            try:
                                clean_date = datetime.strptime(val_str.split()[0], fmt).date()
                                break
                            except:
                                continue
                        
                        if clean_date and today >= clean_date >= (today - timedelta(days=2)):
                            thana_info = r[thana_col_c] if thana_col_c else "अज्ञात इकाई"
                            type_info = r[type_col_c] if type_col_c else "अवकाश"
                            alert_list.append(f"⚠️ **{r[name_col_c]}** ({thana_info}) - {type_info} समाप्ति तिथि: {clean_date.strftime('%d-%m-%Y')}")
                    except:
                        continue
                
                if alert_list:
                    st.markdown("### 🔔 अवकाश वापसी पूर्व-चेतावनी अलर्ट")
                    for alert in alert_list[:5]:
                        st.markdown(f"<div class='alert-box'>{alert} <br> 👉 कर्मचारी की आमद/वापसी सुनिश्चित कराएं।</div>", unsafe_allow_html=True)
        except:
            pass

        st.header("📊 मुख्यालय मॉनिटरिंग डैशबोर्ड (Master Page)")
        
        try:
            df_duty = pd.read_csv(DYNAMIC_DUTY_SHEET_URL)
            df_duty.columns = [str(c).strip() for c in df_duty.columns]
            df_duty = df_duty.fillna("").astype(str)
        except Exception as e:
            st.error(f"⚠️ मुख्य डेटाबेस से संपर्क नहीं हो पा रहा है: {e}")
            df_duty = pd.DataFrame()
            
        tab1, tab2 = st.tabs(["📋 लाइव ड्यूटी मॉनिटर", "👮 जनपद के समस्त पुलिसकर्मियों का विवरण"])
        
        with tab1:
            st.subheader("🔍 लाइव ड्यूटी फ़िल्टर पैनल")
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_date = st.date_input("तारीख चुनें", datetime.now(), key="hq_date")
            with col2:
                filter_thana = st.selectbox("थाना फ़िल्टर", ["सभी थाने"] + THANA_LIST, key="hq_thana")
            with col3:
                filter_duty = st.selectbox("ड्यूटी का प्रकार", ["सभी ड्यूटी"] + DUTY_TYPES, key="hq_duty")
            
            # फ़िल्टर फ़ंक्शन को फ्रेश डेटा के साथ रन करना
            filtered_df = filter_duty_data(df_duty, filter_date, filter_thana, filter_duty)
            
            if not filtered_df.empty:
                st.success(f"📊 **{filter_thana}** का दिनांक **{filter_date.strftime('%d-%m-%Y')}** का लाइव रिकॉर्ड [कुल: {len(filtered_df)} रिकॉर्ड]")
                st.dataframe(filtered_df, use_container_width=True)
            else:
                st.warning(f"⚠️ चयनित तारीख ({filter_date.strftime('%d-%m-%Y')}) और चयनित थाने ({filter_thana}) में कोई ड्यूटी रिकॉर्ड उपलब्ध नहीं मिला।")

        with tab2:
            st.subheader("🗂️ थाना वार पुलिसकर्मी सूची (मास्टर रिकॉर्ड)")
            search_master_thana = st.selectbox("थाना चुनें", ["जनपद के सभी थाने"] + THANA_LIST)
            
            try:
                df_master = pd.read_csv(DYNAMIC_MASTER_SHEET_URL)
                df_master.columns = [str(c).strip() for c in df_master.columns]
                df_master = df_master.fillna("").astype(str)
                
                if search_master_thana != "जनपद के सभी थाने":
                    thana_col_m = next((c for c in df_master.columns if 'थाना' in c or 'thana' in c.lower()), None)
                    if thana_col_m:
                        filtered_master = df_master[df_master[thana_col_m].str.strip() == search_master_thana.strip()]
                    else:
                        filtered_master = df_master[df_master.apply(lambda r: r.str.contains(search_master_thana)).any(axis=1)]
                else:
                    filtered_master = df_master.copy()
                
                st.dataframe(filtered_master, use_container_width=True)
            except Exception as e:
                st.error(f"मास्टर सूची लोड करने में त्रुटि: {e}")

    # =============================================================
    # मिकैनिज्म ब: केवल थानों के लिए (फीडिंग फॉर्म एवं लाइव व्यू दोनों सक्रिय)
    # =============================================================
    else:
        cug_user = st.session_state.user_role
        assigned_thana = THANA_MAPPING.get(cug_user, "अज्ञात थाना")
        
        thana_tab1, thana_tab2 = st.tabs(["📝 नई ड्यूटी फीड करें", "🔍 अपने थाने की लाइव ड्यूटी देखें"])
        
        # थानों के लिए भी फ्रेश लाइव यूआरएल सेटअप
        thana_stamp = random.randint(100000, 999999)
        THANA_DUTY_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=127153860&cache_bypass={thana_stamp}&t={thana_stamp}"
        THANA_MASTER_SHEET_URL = f"https://docs.google.com/spreadsheets/d/1WFvkW8CXYIN_bKJWN5m7Ieh814LlFLjYqZVpjivJhdA/export?format=csv&gid=0&cache_bypass={thana_stamp}&t={thana_stamp}"

        with thana_tab1:
            st.header(f"📝 दैनिक ड्यूटी एवं अवकाश फीडिंग फॉर्म - {assigned_thana}")
            selected_thana = st.selectbox("आपका थाना (🔒锁)", [assigned_thana], disabled=True, key="thana_form_lock")
            
            staff_options = ["-- चुनें / Select Staff --"]
            staff_dict = {}
            
            try:
                df_all_staff = pd.read_csv(THANA_MASTER_SHEET_URL)
                df_all_staff.columns = [str(c).strip() for c in df_all_staff.columns]
                df_all_staff = df_all_staff.fillna("").astype(str)
                
                thana_col_staff = next((c for c in df_all_staff.columns if 'थाना' in c or 'thana' in c.lower()), None)
                if thana_col_staff:
                    short_assigned = assigned_thana.replace("कोतवाली", "").strip()
                    df_thana_staff = df_all_staff[df_all_staff[thana_col_staff].apply(lambda x: assigned_thana in str(x) or short_assigned in str(x))]
                else:
                    df_thana_staff = df_all_staff[df_all_staff.apply(lambda r: r.str.contains(assigned_thana)).any(axis=1)]
                
                for _, row in df_thana_staff.iterrows():
                    col_list = list(df_all_staff.columns)
                    pno_col = next((c for c in col_list if 'pno' in c.lower() or 'नंबर' in c or 'न०' in c), col_list[0])
                    name_col = next((c for c in col_list if 'नाम' in c.lower() or 'name' in c.lower() or 'कर्मचारी' in c), col_list[1])
                    rank_col = next((c for c in col_list if 'पद' in c or 'rank' in c.lower() or 'designation' in c.lower()), None)
                    
                    pno_val = str(row[pno_col])
                    pno_clean = pno_val.split('.')[0] if '.' in pno_val else pno_val
                    
                    display_text = f"{pno_clean} | {row[name_col]} | {row[rank_col] if rank_col else ''}"
                    staff_options.append(display_text)
                    staff_dict[display_text] = {"pno": pno_clean, "name": row[name_col], "rank": row[rank_col] if rank_col else "आरक्षी"}
            except Exception as e:
                st.error(f"कर्मचारी सूची लोड करने में समस्या: {e}")

            selected_staff = st.selectbox("सूची से कर्मचारी चुनें", staff_options, key="thana_staff_select")
            
            pno, name, rank = "", "", ""
            if selected_staff != "-- चुनें / Select Staff --":
                pno = staff_dict[selected_staff]["pno"]
                name = staff_dict[selected_staff]["name"]
                rank = staff_dict[selected_staff]["rank"]

            st.markdown("---")
            duty_type = st.selectbox("ड्यूटी / अवकाश का प्रकार", DUTY_TYPES, key="dynamic_duty_type_select")
            
            leave_start, leave_end = "", ""
            is_leave_selected = "अवकाश" in duty_type or "गैर हाजिर" in duty_type
            
            if is_leave_selected:
                st.markdown("<div style='background-color:#002147; color:white; padding:12px; border-radius:6px; margin-bottom:10px;'><b>⏳ अवकाश समयावधि लॉक करें</b></div>", unsafe_allow_html=True)
                c_date1, c_date2 = st.columns(2)
                with c_date1:
                    s_dt = st.date_input("अवकाश कब से (Start Date)", datetime.now(), key="dynamic_start_date")
                with c_date2:
                    e_dt = st.date_input("अवकाश कब तक (End Date)", datetime.now() + timedelta(days=3), key="dynamic_end_date")
                leave_start = s_dt.strftime("%d-%m-%Y")
                leave_end = e_dt.strftime("%d-%m-%Y")
                duty_submission_text = f"{duty_type} ({leave_start} से {leave_end})"
            else:
                duty_submission_text = duty_type

            # मुख्य डेटा सबमिशन फॉर्म
            with st.form("duty_form_submission", clear_on_submit=True):
                st.write(f"चयनित कार्यभार स्थिति: **{duty_submission_text}**")
                
                submit_btn = st.form_submit_button("🚀 रिकॉर्ड सबमिट करें", type="primary", use_container_width=True)
                
                if submit_btn:
                    if name and pno:
                        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSecM8onnA6CMYAtkzIGcRhxSAfnUtdKd9NM8Jxxv4bzajHovA/formResponse"
                        
                        payload = {
                            "entry.154343115": pno,
                            "entry.2122326148": name,
                            "entry.1503406512": rank, 
                            "entry.926857669": assigned_thana,
                            "entry.88588834": duty_submission_text
                        }
                        try:
                            res = requests.post(form_url, data=payload)
                            st.success(f"✔️ {name} का记录 ({duty_submission_text}) सफलतापूर्वक दर्ज हो गया है।")
                            st.balloons()
                        except:
                            st.error("कनेक्शन त्रुटि! फॉर्म सबमिट नहीं हो सका।")
                    else:
                        st.error("❌ कृपया पहले ऊपर दी गई सूची से किसी पुलिसकर्मी का चयन करें!")

        with thana_tab2:
            st.header(f"🔍 डेली ड्यूटी रजिस्टर - {assigned_thana}")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                thana_filter_date = st.date_input("तारीख चुनें", datetime.now(), key="thana_view_date")
            with col_t2:
                thana_filter_duty = st.selectbox("ड्यूटी का विवरण (फ़िल्टर)", ["सभी ड्यूटी"] + DUTY_TYPES, key="thana_view_duty")
                
            if st.button("🔄 अपने थाने का रिकॉर्ड देखें / रीफ्रेश करें", type="primary", use_container_width=True):
                try:
                    df_thana_duty = pd.read_csv(THANA_DUTY_SHEET_URL)
                    df_thana_duty.columns = [str(c).strip() for c in df_thana_duty.columns]
                    df_thana_duty = df_thana_duty.fillna("").astype(str)
                    
                    final_thana_df = filter_duty_data(df_thana_duty, thana_filter_date, assigned_thana, thana_filter_duty)
                    
                    if not final_thana_df.empty:
                        st.success(f"📊 **{assigned_thana}** का लाइव ड्यूटी रिकॉर्ड:")
                        st.dataframe(final_thana_df, use_container_width=True)
                    else:
                        st.warning(f"⚠️ वर्तमान में चयनित तारीख में इस इकाई का कोई भी रिकॉर्ड दर्ज नहीं मिला।")
                except Exception as e:
                    st.error(f"⚠️ लाइव डेटा सिंक करने में तकनीकी समस्या: {e}")
