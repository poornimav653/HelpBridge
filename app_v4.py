from __future__ import annotations

import html
import hashlib
import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from i18n import LANGS, TEXT
from ai_support import generate_reply

APP_DIR = Path(__file__).resolve().parent
RESOURCE_FILE = APP_DIR / "data" / "resources.csv"
STALE_AFTER_DAYS = 365
NATIONAL_WORDS = {"national", "nationwide", "online", "all", "all india", "india"}
EXIT_URL = "https://www.google.com"

# Discreet mode must be read BEFORE set_page_config so the tab title/icon can change.
DISCREET = bool(st.session_state.get("discreet", False))
st.set_page_config(
    page_title="Notes" if DISCREET else "HelpBridge | Find the right support",
    page_icon="📝" if DISCREET else "💜",
    layout="wide",
)

# --------------------------------------------------------------------------
# Language helper
# --------------------------------------------------------------------------
def current_lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str, **fmt):
    value = TEXT.get(current_lang(), {}).get(key)
    if value is None:
        value = TEXT["en"][key]
    return value.format(**fmt) if fmt and isinstance(value, str) else value


# Internal category keys match the CSV; display names come from i18n.
CATEGORY_SLUG = {
    "Emergency assistance": "emergency",
    "Counselling": "counselling",
    "Legal guidance": "legal",
    "Shelter & housing": "shelter",
    "Medical help": "medical",
}
CATEGORY_ICONS = {
    "Emergency assistance": "🚨",
    "Counselling": "💬",
    "Legal guidance": "⚖️",
    "Shelter & housing": "🏠",
    "Medical help": "✚",
}
ALL_CATEGORIES = list(CATEGORY_SLUG)

# key -> (icon, categories)
NEEDS = {
    "danger": ("🚨", ["Emergency assistance"]),
    "talk": ("💬", ["Counselling"]),
    "safe_place": ("🏠", ["Shelter & housing"]),
    "legal": ("⚖️", ["Legal guidance"]),
    "medical": ("✚", ["Medical help"]),
    "unsure": ("🧭", None),
}
CLARIFIERS = {
    "unsafe": ["Emergency assistance", "Shelter & housing"],
    "overwhelmed": ["Counselling", "Medical help"],
    "rights": ["Legal guidance", "Counselling"],
    "several": ALL_CATEGORIES,
}
TIMINGS = ["now", "soon", "explore"]
PLAN_COPY = {
    "en": {
        "nav": "Safety plan", "back": "Back to support", "title": "A safety plan, at your pace",
        "intro": "Use this optional checklist to think through practical next steps. Skip anything that does not feel right or safe for you.",
        "device": "Use this only if it feels safe on your device. The checklist does not ask for names, addresses, or your story.",
        "urgent": "If you are in immediate danger in India, contact emergency services on 112 if it is safe. Women Helpline 181 may also help; state availability can vary.",
        "steps": [
            "Think of one trusted person you could contact if you need support.",
            "Consider a safer place you could go and a way to get there, if needed.",
            "If it is safe, consider keeping essentials accessible, such as keys, ID, medication, and a phone charger.",
            "If useful, agree on a simple code word with someone you trust to signal that you need help.",
            "Choose a safe way and time to contact support; consider whether this device is private enough to use.",
            "Keep important support numbers somewhere you can access safely.",
        ],
        "session": "Your checkmarks stay only for this app session. The downloaded copy is a blank printable checklist.",
        "download": "Download blank checklist", "clear": "Clear checkmarks",
        "emergency_link": "112 emergency information", "women_link": "Women Helpline 181 information",
    },
    "hi": {
        "nav": "सुरक्षा योजना", "back": "सहायता पर वापस जाएँ", "title": "अपनी गति से सुरक्षा योजना",
        "intro": "व्यावहारिक अगले कदम सोचने के लिए इस वैकल्पिक सूची का उपयोग करें। जो बात आपके लिए सही या सुरक्षित न लगे, उसे छोड़ दें।",
        "device": "इसका उपयोग तभी करें जब यह उपकरण आपके लिए सुरक्षित हो। यहाँ नाम, पता या आपकी पूरी कहानी नहीं माँगी जाती।",
        "urgent": "यदि भारत में तुरंत खतरा हो, तो सुरक्षित होने पर आपातकालीन सहायता के लिए 112 पर संपर्क करें। महिला हेल्पलाइन 181 भी सहायता कर सकती है; राज्य के अनुसार उपलब्धता अलग हो सकती है।",
        "steps": [
            "किसी ऐसे भरोसेमंद व्यक्ति के बारे में सोचें जिससे ज़रूरत पड़ने पर संपर्क कर सकें।",
            "ज़रूरत पड़ने पर जाने के लिए किसी सुरक्षित जगह और वहाँ पहुँचने के तरीके पर विचार करें।",
            "यदि सुरक्षित हो, तो चाबियाँ, पहचान पत्र, दवा और फोन चार्जर जैसी ज़रूरी चीज़ें पास रखने पर विचार करें।",
            "यदि उपयोगी लगे, तो किसी भरोसेमंद व्यक्ति के साथ मदद माँगने के लिए एक सरल संकेत शब्द तय करें।",
            "सहायता से संपर्क करने का सुरक्षित तरीका और समय चुनें; सोचें कि यह उपकरण निजी है या नहीं।",
            "महत्वपूर्ण सहायता नंबर ऐसी जगह रखें जहाँ आप उन्हें सुरक्षित रूप से देख सकें।",
        ],
        "session": "आपके निशान केवल इस ऐप सत्र तक रहते हैं। डाउनलोड की गई प्रति खाली प्रिंट करने योग्य सूची है।",
        "download": "खाली सूची डाउनलोड करें", "clear": "निशान हटाएँ",
        "emergency_link": "112 आपातकालीन जानकारी", "women_link": "महिला हेल्पलाइन 181 की जानकारी",
    },
    "kn": {
        "nav": "ಸುರಕ್ಷತಾ ಯೋಜನೆ", "back": "ಬೆಂಬಲಕ್ಕೆ ಹಿಂತಿರುಗಿ", "title": "ನಿಮ್ಮ ವೇಗದಲ್ಲಿ ಸುರಕ್ಷತಾ ಯೋಜನೆ",
        "intro": "ಪ್ರಾಯೋಗಿಕ ಮುಂದಿನ ಕ್ರಮಗಳನ್ನು ಯೋಚಿಸಲು ಈ ಐಚ್ಛಿಕ ಪಟ್ಟಿಯನ್ನು ಬಳಸಿ. ನಿಮಗೆ ಸರಿಯೆನಿಸದ ಅಥವಾ ಸುರಕ್ಷಿತವಲ್ಲದ ಅಂಶಗಳನ್ನು ಬಿಟ್ಟುಬಿಡಿ.",
        "device": "ನಿಮ್ಮ ಸಾಧನ ಸುರಕ್ಷಿತವೆನಿಸಿದಾಗ ಮಾತ್ರ ಇದನ್ನು ಬಳಸಿ. ಇಲ್ಲಿ ಹೆಸರು, ವಿಳಾಸ ಅಥವಾ ನಿಮ್ಮ ಸಂಪೂರ್ಣ ಕಥೆಯನ್ನು ಕೇಳುವುದಿಲ್ಲ.",
        "urgent": "ಭಾರತದಲ್ಲಿ ತಕ್ಷಣದ ಅಪಾಯವಿದ್ದರೆ, ಸುರಕ್ಷಿತವಾಗಿದ್ದರೆ ತುರ್ತು ಸಹಾಯಕ್ಕೆ 112 ಸಂಪರ್ಕಿಸಿ. ಮಹಿಳಾ ಸಹಾಯವಾಣಿ 181 ಸಹಾಯ ಮಾಡಬಹುದು; ರಾಜ್ಯದಂತೆ ಲಭ್ಯತೆ ಬದಲಾಗಬಹುದು.",
        "steps": [
            "ಬೆಂಬಲ ಬೇಕಾದಾಗ ಸಂಪರ್ಕಿಸಬಹುದಾದ ಒಬ್ಬ ವಿಶ್ವಾಸಾರ್ಹ ವ್ಯಕ್ತಿಯನ್ನು ಯೋಚಿಸಿ.",
            "ಅಗತ್ಯವಿದ್ದರೆ ಹೋಗಬಹುದಾದ ಸುರಕ್ಷಿತ ಸ್ಥಳ ಮತ್ತು ಅಲ್ಲಿಗೆ ತಲುಪುವ ಮಾರ್ಗವನ್ನು ಪರಿಗಣಿಸಿ.",
            "ಸುರಕ್ಷಿತವಾಗಿದ್ದರೆ, ಕೀಲಿ, ಗುರುತಿನ ಚೀಟಿ, ಔಷಧಿ ಮತ್ತು ಫೋನ್ ಚಾರ್ಜರ್‌ನಂತಹ ಅಗತ್ಯ ವಸ್ತುಗಳನ್ನು ಹತ್ತಿರ ಇಡುವುದನ್ನು ಪರಿಗಣಿಸಿ.",
            "ಉಪಯುಕ್ತವೆನಿಸಿದರೆ, ಸಹಾಯ ಬೇಕೆಂದು ತಿಳಿಸಲು ವಿಶ್ವಾಸಾರ್ಹ ವ್ಯಕ್ತಿಯೊಂದಿಗೆ ಸರಳ ಸಂಕೇತ ಪದವನ್ನು ನಿಗದಿಪಡಿಸಿ.",
            "ಬೆಂಬಲವನ್ನು ಸಂಪರ್ಕಿಸಲು ಸುರಕ್ಷಿತ ವಿಧಾನ ಮತ್ತು ಸಮಯವನ್ನು ಆರಿಸಿ; ಈ ಸಾಧನ ಖಾಸಗಿಯೇ ಎಂದು ಪರಿಗಣಿಸಿ.",
            "ಮುಖ್ಯ ಸಹಾಯ ಸಂಖ್ಯೆಗಳನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ನೋಡಬಹುದಾದ ಸ್ಥಳದಲ್ಲಿ ಇಡಿ.",
        ],
        "session": "ನಿಮ್ಮ ಗುರುತುಗಳು ಈ ಆಪ್ ಸೆಷನ್‌ನಲ್ಲಿ ಮಾತ್ರ ಇರುತ್ತವೆ. ಡೌನ್‌ಲೋಡ್ ಮಾಡಿದ ಪ್ರತಿಯು ಖಾಲಿ ಮುದ್ರಿಸಬಹುದಾದ ಪಟ್ಟಿ.",
        "download": "ಖಾಲಿ ಪಟ್ಟಿಯನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ", "clear": "ಗುರುತುಗಳನ್ನು ತೆರವುಗೊಳಿಸಿ",
        "emergency_link": "112 ತುರ್ತು ಮಾಹಿತಿ", "women_link": "ಮಹಿಳಾ ಸಹಾಯವಾಣಿ 181 ಮಾಹಿತಿ",
    },
}
EXTRA_UI = {
    "en": {
        "filter_24": "Show only 24/7 services",
        "no_24": "No verified 24/7 services were found in this category. Turn off the filter to see other options.",
        "search": "Search services",
        "search_ph": "Try a service name, contact, or keyword",
        "no_search": "No services match that search. Try another word or clear the search box.",
        "save": "Save for this visit",
        "saved": "Saved resources",
        "unsave": "Remove saved",
        "remove": "Remove",
        "saved_note": "This temporary list is kept for this app session and clears when the session ends.",
        "saved_empty": "You have not saved any resources yet.",
        "country_label": "Country (optional)",
        "country_ph": "Type a country, for example India",
        "no_country": "No resources are listed for {country} in the current data.",
        "pincode_label": "PIN code (optional)",
        "pincode_ph": "Enter a 6-digit PIN code",
        "bad_pincode": "Enter a 6-digit PIN code, or leave this box blank.",
        "no_pincode": "No resource is tagged to PIN code {pincode} yet. Showing broader resources.",
        "state_label": "State / UT (optional)",
        "state_ph": "Type a state, for example Karnataka",
        "all_india": "All India — nationwide services only",
        "district_label": "Choose district (optional)",
        "any_district": "Any district",
        "district_empty": "District-level listings are not in the data yet. You can enter a district; available state-wide and nationwide resources will still be shown.",
        "district_no_data": "No verified listing is specific to {district} yet. Showing state-wide and nationwide resources.",
        "district_need_state": "Choose a state / UT above to use the district filter.",
        "district_ph": "Type a district name (optional)",
        "accessibility": "Accessibility",
        "large_text": "Larger text",
        "high_contrast": "Higher contrast",
        "reduce_motion": "Reduce animation",
        "accessibility_note": "These display settings apply for this app session.",
    },
    "hi": {
        "filter_24": "केवल 24/7 उपलब्ध सेवाएँ दिखाएँ",
        "no_24": "इस श्रेणी में कोई सत्यापित 24/7 सेवा नहीं मिली। अन्य विकल्प देखने के लिए फ़िल्टर बंद करें।",
        "search": "सेवाएँ खोजें",
        "search_ph": "सेवा का नाम, संपर्क या कोई शब्द लिखें",
        "no_search": "इस खोज से कोई सेवा नहीं मिली। दूसरा शब्द आज़माएँ या खोज बॉक्स खाली करें।",
        "save": "इस सत्र के लिए सहेजें",
        "saved": "सहेजे गए संसाधन",
        "unsave": "सहेजे गए से हटाएँ",
        "remove": "हटाएँ",
        "saved_note": "यह अस्थायी सूची केवल इस ऐप सत्र में रहती है और सत्र समाप्त होने पर हट जाती है।",
        "saved_empty": "आपने अभी तक कोई संसाधन सहेजा नहीं है।",
        "country_label": "देश (वैकल्पिक)",
        "country_ph": "देश का नाम लिखें, जैसे भारत",
        "no_country": "मौजूदा डेटा में {country} के लिए कोई संसाधन सूचीबद्ध नहीं है।",
        "pincode_label": "पिन कोड (वैकल्पिक)",
        "pincode_ph": "6 अंकों का पिन कोड लिखें",
        "bad_pincode": "6 अंकों का पिन कोड लिखें या यह बॉक्स खाली छोड़ें।",
        "no_pincode": "अभी पिन कोड {pincode} के लिए कोई संसाधन नहीं है। व्यापक क्षेत्र के संसाधन दिखाए जा रहे हैं।",
        "state_label": "राज्य / केंद्र शासित प्रदेश (वैकल्पिक)",
        "state_ph": "राज्य का नाम लिखें, जैसे कर्नाटक",
        "all_india": "पूरा भारत — केवल राष्ट्रीय सेवाएँ",
        "district_label": "ज़िला चुनें (वैकल्पिक)",
        "any_district": "कोई भी ज़िला",
        "district_empty": "अभी डेटा में ज़िला-स्तर की सेवाएँ नहीं हैं। आप ज़िले का नाम लिख सकते हैं; उपलब्ध राज्य और राष्ट्रीय सेवाएँ फिर भी दिखेंगी।",
        "district_no_data": "अभी {district} के लिए कोई सत्यापित सूची नहीं है। राज्य और राष्ट्रीय सेवाएँ दिखाई जा रही हैं।",
        "district_need_state": "ज़िले से फ़िल्टर करने के लिए ऊपर राज्य / केंद्र शासित प्रदेश चुनें।",
        "district_ph": "ज़िले का नाम लिखें (वैकल्पिक)",
        "accessibility": "सुलभता विकल्प",
        "large_text": "बड़ा पाठ",
        "high_contrast": "अधिक स्पष्ट कंट्रास्ट",
        "reduce_motion": "एनिमेशन कम करें",
        "accessibility_note": "ये प्रदर्शन सेटिंग इस ऐप सत्र के लिए लागू हैं।",
    },
    "kn": {
        "filter_24": "24/7 ಲಭ್ಯವಿರುವ ಸೇವೆಗಳನ್ನು ಮಾತ್ರ ತೋರಿಸಿ",
        "no_24": "ಈ ವಿಭಾಗದಲ್ಲಿ ಪರಿಶೀಲಿಸಿದ 24/7 ಸೇವೆಗಳು ಸಿಗಲಿಲ್ಲ. ಇತರ ಆಯ್ಕೆಗಳನ್ನು ನೋಡಲು ಫಿಲ್ಟರ್ ಆಫ್ ಮಾಡಿ.",
        "search": "ಸೇವೆಗಳನ್ನು ಹುಡುಕಿ",
        "search_ph": "ಸೇವೆಯ ಹೆಸರು, ಸಂಪರ್ಕ ಅಥವಾ ಕೀವರ್ಡ್ ನಮೂದಿಸಿ",
        "no_search": "ಈ ಹುಡುಕಾಟಕ್ಕೆ ಯಾವುದೇ ಸೇವೆ ಸಿಗಲಿಲ್ಲ. ಬೇರೆ ಪದ ಬಳಸಿ ಅಥವಾ ಹುಡುಕಾಟವನ್ನು ತೆರವುಗೊಳಿಸಿ.",
        "save": "ಈ ಭೇಟಿಗಾಗಿ ಉಳಿಸಿ",
        "saved": "ಉಳಿಸಿದ ಸಂಪನ್ಮೂಲಗಳು",
        "unsave": "ಉಳಿಸಿದವುಗಳಿಂದ ತೆಗೆದುಹಾಕಿ",
        "remove": "ತೆಗೆದುಹಾಕಿ",
        "saved_note": "ಈ ತಾತ್ಕಾಲಿಕ ಪಟ್ಟಿ ಈ ಆಪ್ ಸೆಷನ್‌ನಲ್ಲಿ ಮಾತ್ರ ಇರುತ್ತದೆ; ಸೆಷನ್ ಮುಗಿದಾಗ ತೆರವಾಗುತ್ತದೆ.",
        "saved_empty": "ನೀವು ಇನ್ನೂ ಯಾವುದೇ ಸಂಪನ್ಮೂಲಗಳನ್ನು ಉಳಿಸಿಲ್ಲ.",
        "country_label": "ದೇಶ (ಐಚ್ಛಿಕ)",
        "country_ph": "ದೇಶದ ಹೆಸರನ್ನು ನಮೂದಿಸಿ, ಉದಾ. ಭಾರತ",
        "no_country": "ಪ್ರಸ್ತುತ ಡೇಟಾದಲ್ಲಿ {country}ಗೆ ಯಾವುದೇ ಸಂಪನ್ಮೂಲಗಳಿಲ್ಲ.",
        "pincode_label": "ಪಿನ್ ಕೋಡ್ (ಐಚ್ಛಿಕ)",
        "pincode_ph": "6 ಅಂಕಿಯ ಪಿನ್ ಕೋಡ್ ನಮೂದಿಸಿ",
        "bad_pincode": "6 ಅಂಕಿಯ ಪಿನ್ ಕೋಡ್ ನಮೂದಿಸಿ ಅಥವಾ ಈ ಜಾಗವನ್ನು ಖಾಲಿ ಬಿಡಿ.",
        "no_pincode": "ಇನ್ನೂ {pincode} ಪಿನ್ ಕೋಡ್‌ಗೆ ಸಂಪನ್ಮೂಲ ಗುರುತಿಸಲಾಗಿಲ್ಲ. ವಿಶಾಲ ಪ್ರದೇಶದ ಸಂಪನ್ಮೂಲಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
        "state_label": "ರಾಜ್ಯ / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ (ಐಚ್ಛಿಕ)",
        "state_ph": "ರಾಜ್ಯದ ಹೆಸರನ್ನು ನಮೂದಿಸಿ, ಉದಾ. ಕರ್ನಾಟಕ",
        "all_india": "ಭಾರತದೆಲ್ಲೆಡೆ — ರಾಷ್ಟ್ರೀಯ ಸೇವೆಗಳು ಮಾತ್ರ",
        "district_label": "ಜಿಲ್ಲೆ ಆಯ್ಕೆಮಾಡಿ (ಐಚ್ಛಿಕ)",
        "any_district": "ಯಾವುದೇ ಜಿಲ್ಲೆ",
        "district_empty": "ಇನ್ನೂ ಜಿಲ್ಲೆ-ಮಟ್ಟದ ಸೇವೆಗಳು ಡೇಟಾದಲ್ಲಿಲ್ಲ. ನೀವು ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ನಮೂದಿಸಬಹುದು; ಲಭ್ಯ ರಾಜ್ಯ ಮತ್ತು ರಾಷ್ಟ್ರೀಯ ಸೇವೆಗಳು ಕಾಣಿಸುತ್ತವೆ.",
        "district_no_data": "ಇನ್ನೂ {district}ಗೆ ನಿರ್ದಿಷ್ಟ ಪರಿಶೀಲಿಸಿದ ಪಟ್ಟಿ ಇಲ್ಲ. ರಾಜ್ಯ ಮತ್ತು ರಾಷ್ಟ್ರೀಯ ಸೇವೆಗಳನ್ನು ತೋರಿಸಲಾಗುತ್ತಿದೆ.",
        "district_need_state": "ಜಿಲ್ಲೆಯ ಮೂಲಕ ಫಿಲ್ಟರ್ ಮಾಡಲು ಮೇಲಿನ ರಾಜ್ಯ / ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶವನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "district_ph": "ಜಿಲ್ಲೆಯ ಹೆಸರನ್ನು ನಮೂದಿಸಿ (ಐಚ್ಛಿಕ)",
        "accessibility": "ಪ್ರವೇಶಸಾಧ್ಯತೆ",
        "large_text": "ದೊಡ್ಡ ಅಕ್ಷರಗಳು",
        "high_contrast": "ಹೆಚ್ಚಿನ ಕಾಂಟ್ರಾಸ್ಟ್",
        "reduce_motion": "ಚಲನೆ ಕಡಿಮೆ ಮಾಡಿ",
        "accessibility_note": "ಈ ಪ್ರದರ್ಶನ ಸೆಟ್ಟಿಂಗ್‌ಗಳು ಈ ಆಪ್ ಸೆಷನ್‌ಗೆ ಅನ್ವಯಿಸುತ್ತವೆ.",
    },
}


def extra_text(key: str) -> str:
    return EXTRA_UI.get(current_lang(), EXTRA_UI["en"]).get(key, EXTRA_UI["en"][key])


for key, default in {"stage": "need", "need": None, "clarify": None, "timing": None, "active_view": "support", "saved_resources": {}, "access_large_text": False, "access_high_contrast": False, "access_reduce_motion": False}.items():
    st.session_state.setdefault(key, default)

# --------------------------------------------------------------------------
# Styling
# Palette: dusk #2A2138, paper #F6F4F8, teal #2F7F7C, lantern #F0C987
# --------------------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Noto+Sans+Devanagari:wght@400;600&family=Noto+Sans+Kannada:wght@400;600&display=swap');
:root { --ink:#2A2138; --muted:#62596D; --paper:#F6F4F8; --mist:#E7E0EF; --line:#DDD5E6; --teal:#2F7F7C; --teal-dark:#256664; --teal-tint:#EEF6F5; --lantern:#F0C987;
  --sans:'Figtree','Noto Sans Devanagari','Noto Sans Kannada',system-ui,sans-serif;
  --serif:'Fraunces','Noto Sans Devanagari','Noto Sans Kannada',Georgia,serif; }
.stApp { background: var(--paper); color: var(--ink); font-family: var(--sans); }
.stApp p, .stApp label, .stApp li, .stApp input, .stApp button, .stApp summary { font-family: var(--sans); }
[data-testid="stChatMessage"] { background: #fff !important; border: 1px solid var(--line); border-radius: 14px; }
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span { color: var(--ink) !important; }
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] textarea:focus {
  color: var(--ink) !important;
  -webkit-text-fill-color: var(--ink) !important;
  caret-color: var(--ink) !important;
  background: #fff !important;
}
[data-testid="stChatInput"] textarea::placeholder {
  color: var(--muted) !important;
  -webkit-text-fill-color: var(--muted) !important;
  opacity: 1 !important;
}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDeployButton"], #MainMenu { display: none !important; }
.st-key-topbar { position: sticky; top: 0; z-index: 1000; background: var(--paper); padding: .55rem 0 .45rem; margin-bottom: .6rem; border-bottom: 1px solid var(--line); }
.st-key-topbar [data-testid="stRadio"] label p { font-weight: 600; color: var(--ink); }
.block-container { max-width: 1080px; padding: 2rem 2rem 3.5rem; }
.quick-exit { position: fixed; top: .9rem; right: 1.1rem; z-index: 99999; background: #fff; color: var(--ink) !important; text-decoration: none !important; border: 1.5px solid var(--ink); border-radius: 999px; padding: .45rem 1rem; font-weight: 600; font-size: .88rem; }
.quick-exit:hover { background: var(--ink); color: #fff !important; }
.quick-exit:focus-visible, .stApp button:focus-visible, .stApp a:focus-visible { outline: 3px solid var(--lantern); outline-offset: 2px; }
.hero { position: relative; overflow: hidden; background: var(--ink); border-radius: 28px; padding: 3rem 3.2rem 3.2rem; margin: 1rem 0 2rem; }
.hero-text { position: relative; z-index: 1; max-width: 560px; }
.hero h1 { font-family: var(--serif); font-weight: 600; color: #fff; font-size: clamp(2rem, 4.2vw, 3.2rem); line-height: 1.12; letter-spacing: -.01em; margin: 0; padding: 0; }
.hero p { color: #DCD2E8; font-size: 1.1rem; line-height: 1.7; margin: 1.1rem 0 0; max-width: 480px; }
.hero-promise { margin-top: 1.5rem; color: var(--lantern); font-weight: 600; }
.hero svg { position: absolute; right: -10px; bottom: 0; width: 56%; height: auto; }
.draw { stroke-dasharray: 760; animation: draw 2.4s ease-out both; }
@keyframes draw { from { stroke-dashoffset: 760; } to { stroke-dashoffset: 0; } }
@media (prefers-reduced-motion: reduce) { .draw { animation: none; } }
.progress { height: 5px; background: var(--mist); border-radius: 999px; overflow: hidden; margin: .4rem 0 .5rem; }
.progress > div { height: 100%; background: var(--teal); border-radius: 999px; }
.step-label { color: var(--muted); font-size: .92rem; font-weight: 600; }
.q { font-family: var(--serif); font-weight: 600; font-size: 1.7rem; line-height: 1.3; color: var(--ink); margin: .6rem 0 .25rem; }
.q-copy { color: var(--muted); margin: 0 0 1.3rem; }
.cat { background: #fff; border: 1.5px solid var(--line); border-radius: 14px; padding: 1.15rem 1.2rem 1.1rem; min-height: 150px; margin-bottom: .5rem; }
.cat.urgent-card { border-color: var(--lantern); background: #FFFAF0; }
.cat-icon { font-size: 1.55rem; line-height: 1; margin-bottom: .7rem; }
.cat h3 { font-family: var(--serif); font-weight: 600; font-size: 1.1rem; line-height: 1.35; color: var(--ink); margin: 0 0 .35rem; padding: 0; }
.cat p { color: var(--muted); font-size: .93rem; line-height: 1.6; margin: 0; }
.results-head { font-family: var(--serif); font-weight: 600; font-size: 1.8rem; color: var(--ink); margin: .4rem 0 .2rem; }
.cat-head { font-family: var(--serif); font-weight: 600; font-size: 1.3rem; color: var(--ink); margin: 1.8rem 0 .15rem; }
.cat-sub { color: var(--muted); margin: 0 0 .8rem; }
.urgent { background: #FFF6E5; border: 1.5px solid var(--lantern); border-radius: 14px; padding: 1rem 1.2rem; margin: 1rem 0; line-height: 1.7; }
.badge { display: inline-block; font-size: .8rem; font-weight: 600; border-radius: 999px; padding: .15rem .65rem; margin: 0 .4rem .3rem 0; background: var(--teal-tint); color: var(--teal-dark); border: 1px solid #BFDCDA; }
.badge.warn { background: #FFF6E5; color: #7A5A18; border-color: var(--lantern); }
.res-meta { color: var(--muted); font-size: .92rem; margin-top: .3rem; }
.res-meta a { color: var(--teal-dark); font-weight: 600; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; border-color: var(--line); background: #fff; }
.stTextInput input { border-radius: 10px; }
.stTextInput label p, .stSelectbox label p { font-weight: 600; color: var(--ink) !important; }
.stAlert { border-radius: 13px; }
.stButton > button, .stLinkButton > a, .stDownloadButton > button { border-radius: 999px; font-weight: 600; min-height: 2.6rem; }
.stButton > button { border: 1.5px solid var(--ink); background: transparent; color: var(--ink); }
.stButton > button:hover { background: var(--mist); border-color: var(--ink); color: var(--ink); }
.stDownloadButton > button { background: var(--teal); border: 1.5px solid var(--teal); color: #fff; }
.stDownloadButton > button:hover { background: var(--teal-dark); border-color: var(--teal-dark); color: #fff; }
.stLinkButton > a { background: var(--ink); color: #fff !important; border: 1.5px solid var(--ink); }
.stLinkButton > a:hover { background: #3E3252; border-color: #3E3252; }
.footer-note { color: var(--muted); font-size: .86rem; line-height: 1.7; max-width: 760px; }
@media (max-width: 800px) { .block-container { padding: 1rem 1rem 2.5rem; } .hero { padding: 2.2rem 1.5rem; border-radius: 22px; } .hero svg { display: none; } }
</style>
""",
    unsafe_allow_html=True,
)

if st.session_state.access_large_text:
    st.markdown(
        "<style>.stApp p,.stApp label,.stApp li,.stApp input,.stApp button,.stApp summary {font-size:1.12rem !important;line-height:1.7 !important;}</style>",
        unsafe_allow_html=True,
    )
if st.session_state.access_high_contrast:
    st.markdown(
        """<style>
        .stApp {background:#fff !important;color:#111 !important;}
        .stApp p,.stApp label,.stApp li,.stApp h1,.stApp h2,.stApp h3,.stApp summary {color:#111 !important;}
        .hero h1,.hero p {color:#fff !important;}
        .hero-promise {color:#ffe28a !important;}
        .cat,.stApp [data-testid="stVerticalBlockBorderWrapper"] {border-color:#555 !important;}
        .cat h3,.cat p,.res-meta,.footer-note {color:#222 !important;}
        .res-meta a {color:#003f7d !important;text-decoration:underline !important;}
        .badge {background:#fff !important;border-color:#00574f !important;color:#00574f !important;}
        .badge.warn {border-color:#704800 !important;color:#563700 !important;}
        .stButton > button,.stLinkButton > a {border-width:2px !important;}
        </style>""",
        unsafe_allow_html=True,
    )
if st.session_state.access_reduce_motion:
    st.markdown(
        "<style>.draw {animation:none !important;stroke-dashoffset:0 !important;}</style>",
        unsafe_allow_html=True,
    )

# Press Esc twice to leave quickly. Runs once per browser tab.
components.html(
    """<script>
(function () {
  var w = window.parent;
  if (w.__hbEsc) return;
  w.__hbEsc = true;
  var last = 0;
  w.document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var now = Date.now();
    if (now - last < 800) { w.location.replace('%s'); }
    last = now;
  });
})();
</script>""" % EXIT_URL,
    height=0,
)

def toggle_safety_plan() -> None:
    st.session_state.active_view = "support" if st.session_state.active_view == "safety_plan" else "safety_plan"


def clear_safety_checklist() -> None:
    for index in range(1, 7):
        st.session_state[f"safety_step_{index}"] = False


# Top controls: language + discreet mode (sticky so they are always visible)
try:
    topbar = st.container(key="topbar")
except TypeError:  # older Streamlit without container keys
    topbar = st.container()
with topbar:
    c1, c2, c3 = st.columns([3.2, 2.2, 2])
    with c1:
        st.radio("🌐 Language / भाषा / ಭಾಷೆ", list(LANGS), format_func=LANGS.get, horizontal=True, key="lang")
    with c2:
        st.checkbox(t("discreet"), key="discreet", help=t("discreet_help"))
    with c3:
        with st.popover(extra_text("accessibility"), width="stretch"):
            st.caption(extra_text("accessibility_note"))
            st.checkbox(extra_text("large_text"), key="access_large_text")
            st.checkbox(extra_text("high_contrast"), key="access_high_contrast")
            st.checkbox(extra_text("reduce_motion"), key="access_reduce_motion")
            st.divider()
            plan_labels = PLAN_COPY.get(current_lang(), PLAN_COPY["en"])
            st.button(
                plan_labels["back"] if st.session_state.active_view == "safety_plan" else plan_labels["nav"],
                key="toggle_safety_plan",
                on_click=toggle_safety_plan,
                width="stretch",
            )

st.markdown(
    f'<a class="quick-exit" href="{EXIT_URL}" target="_self" rel="noopener">{html.escape(t("quick_exit"))}</a>',
    unsafe_allow_html=True,
)


def bridge_svg() -> str:
    x0, x1, deck_y, top_y = 20, 580, 170, 20
    hangers = []
    for i in range(1, 10):
        p = i / 10
        x = x0 + (x1 - x0) * p
        y = deck_y - 2 * (deck_y - top_y) * p * (1 - p)
        hangers.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x:.0f}" y2="{deck_y}"/>')
    return (
        '<svg viewBox="0 0 600 200" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" '
        'stroke="#B9A5D4" stroke-width="1.6" stroke-linecap="round">'
        f'<line x1="0" y1="{deck_y}" x2="600" y2="{deck_y}" stroke-width="2.4"/>'
        f'<path class="draw" d="M{x0} {deck_y} Q300 {top_y} {x1} {deck_y}" stroke-width="2.4"/>'
        f'<g opacity=".65">{"".join(hangers)}</g>'
        '<circle cx="300" cy="95" r="6" fill="#F0C987" stroke="none"/></svg>'
    )


def render_safety_plan() -> None:
    copy = PLAN_COPY.get(current_lang(), PLAN_COPY["en"])
    st.subheader(copy["title"])
    st.write(copy["intro"])
    st.info(copy["device"])
    st.warning(copy["urgent"])
    c1, c2 = st.columns(2)
    with c1:
        st.link_button(copy["emergency_link"], "https://112.gov.in/")
    with c2:
        st.link_button(copy["women_link"], "https://wcd.gov.in/offerings/women--helpline--scheme")
    checklist_title = {"en": "Checklist", "hi": "जाँच सूची", "kn": "ಪರಿಶೀಲನಾ ಪಟ್ಟಿ"}.get(current_lang(), "Checklist")
    st.markdown("#### " + checklist_title)
    for index, step in enumerate(copy["steps"], start=1):
        st.checkbox(step, key=f"safety_step_{index}")
    st.caption(copy["session"])
    checklist_html = """<!doctype html><html lang="%s"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><style>body{font:17px/1.6 system-ui,sans-serif;max-width:760px;margin:2rem auto;padding:0 1rem;color:#292436}li{margin:1rem 0}.note{padding:1rem;background:#f4f1f7;border-radius:10px}</style><h1>%s</h1><p>%s</p><ol>%s</ol><p class="note">%s</p></html>""" % (
        html.escape(current_lang()), html.escape(copy["title"]), html.escape(copy["title"]),
        html.escape(copy["intro"]), "".join(f"<li>☐ {html.escape(step)}</li>" for step in copy["steps"]),
        html.escape(copy["device"]),
    )
    st.download_button(copy["download"], checklist_html.encode("utf-8"), file_name="helpbridge-safety-checklist.html", mime="text/html")
    st.button(copy["clear"], key="clear_safety_checklist", on_click=clear_safety_checklist)


if st.session_state.active_view == "safety_plan":
    render_safety_plan()
    st.stop()


st.markdown(
    f"""<div class="hero">{bridge_svg()}<div class="hero-text">
<h1>{html.escape(t("hero_h1"))}</h1>
<p>{html.escape(t("hero_p"))}</p>
<div class="hero-promise">{html.escape(t("hero_promise"))}</div>
</div></div>""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Guided navigation
# --------------------------------------------------------------------------
def pick_need(key: str) -> None:
    st.session_state.need = key
    st.session_state.clarify = None
    if key == "danger":
        st.session_state.timing = "now"
        st.session_state.stage = "results"
    elif key == "unsure":
        st.session_state.stage = "clarify"
    else:
        st.session_state.stage = "timing"


def pick_clarify(key: str) -> None:
    st.session_state.clarify = key
    st.session_state.stage = "timing"


def pick_timing(key: str) -> None:
    st.session_state.timing = key
    st.session_state.stage = "results"


def go_back() -> None:
    stage, need = st.session_state.stage, st.session_state.need
    if stage == "results":
        st.session_state.stage = "need" if need == "danger" else "timing"
    elif stage == "timing":
        st.session_state.stage = "clarify" if need == "unsure" else "need"
    else:
        st.session_state.stage = "need"


def start_over() -> None:
    st.session_state.update(stage="need", need=None, clarify=None, timing=None, saved_resources={})


def option_card(column, icon: str, title: str, text: str, key: str, on_click, urgent: bool = False) -> None:
    with column:
        st.markdown(
            f'<div class="cat{" urgent-card" if urgent else ""}"><div class="cat-icon">{icon}</div>'
            f"<h3>{html.escape(title)}</h3><p>{html.escape(text)}</p></div>",
            unsafe_allow_html=True,
        )
        st.button(t("choose"), key=f"{st.session_state.stage}_{key}", on_click=on_click, args=(key,), use_container_width=True)


def question_header(step: int, total: int, question: str, copy: str) -> None:
    st.markdown(
        f'<div class="step-label">{html.escape(t("step", a=step, b=total))}</div>'
        f'<div class="progress"><div style="width:{int(step / total * 100)}%"></div></div>'
        f'<div class="q">{html.escape(question)}</div><p class="q-copy">{html.escape(copy)}</p>',
        unsafe_allow_html=True,
    )


def nav_buttons() -> None:
    left, right, _ = st.columns([1, 1.4, 6], gap="small")
    left.button(t("back"), on_click=go_back, key=f"back_{st.session_state.stage}")
    right.button(t("start_over"), on_click=start_over, key=f"restart_{st.session_state.stage}")


# --------------------------------------------------------------------------
# Resource data (verified entries only)
# Optional translated columns: name_hi, description_hi, name_kn, description_kn
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _read_csv(path: str, modified: float) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")


def load_resources() -> pd.DataFrame:
    if not RESOURCE_FILE.exists():
        return pd.DataFrame()
    try:
        frame = _read_csv(str(RESOURCE_FILE), RESOURCE_FILE.stat().st_mtime).copy()
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        st.error(f"data/resources.csv could not be read: {error}. Check that it is a valid UTF-8 CSV.")
        return pd.DataFrame()
    frame.columns = [re.sub(r"\s+", "_", str(c).strip().lower()) for c in frame.columns]
    return frame


def val(row: pd.Series, *names: str) -> str:
    for name in names:
        value = str(row.get(name, "")).strip()
        if value:
            return value
    return ""


def localized(row: pd.Series, base: str, *fallbacks: str) -> str:
    lang = current_lang()
    if lang != "en":
        translated = val(row, f"{base}_{lang}")
        if translated:
            return translated
    return val(row, base, *fallbacks)


def verified_date(row: pd.Series) -> date | None:
    parsed = pd.to_datetime(val(row, "verified_on"), errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def source_page_label() -> str:
    return {"en": "View source", "hi": "स्रोत पृष्ठ देखें", "kn": "ಮೂಲವನ್ನು ನೋಡಿ"}.get(current_lang(), "View source")


def is_yes(value: str) -> bool:
    return value.strip().lower() in {"yes", "y", "true", "1"}


def contact_html(contact: str) -> str:
    """Make phone numbers within contact text tap-to-call, preserving labels."""
    safe = html.escape(contact)
    if "@" in contact and " " not in contact:
        return f'<a href="mailto:{safe}">{safe}</a>'

    # Supports short emergency numbers (112, 1091), ordinary numbers, and
    # several numbers embedded in notes such as "181 for referral".
    number_pattern = re.compile(r"(?<!\w)(?:\+?\d[\d(). -]*\d|\d{3,6})(?!\w)")

    def make_phone_link(match: re.Match[str]) -> str:
        label = match.group(0)
        digits = "".join(ch for ch in label if ch.isdigit())
        if not 3 <= len(digits) <= 15:
            return html.escape(label)
        dial = ("+" if label.lstrip().startswith("+") else "") + digits
        return f'<a href="tel:{dial}" aria-label="Call {html.escape(label, quote=True)}">{html.escape(label)}</a>'

    return number_pattern.sub(make_phone_link, safe)


def state_value(row: pd.Series) -> str:
    return (val(row, "state") or val(row, "location", "area")).strip()


def is_national_location(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in NATIONAL_WORDS or normalized.startswith("india ")


def district_choices(resources: pd.DataFrame, state: str) -> list[str]:
    if resources.empty or not state or "district" not in resources.columns:
        return []
    matching_state = resources.apply(lambda row: state_value(row).strip().casefold() == state.strip().casefold(), axis=1)
    districts = resources.loc[matching_state, "district"].astype(str).str.strip()
    return sorted((value for value in districts.unique() if value and value.casefold() != "nan"), key=str.casefold)


def pick_matches(resources: pd.DataFrame, category: str, country: str, state: str, district: str, pincode: str, urgent: bool) -> tuple[pd.DataFrame, str]:
    matches = resources[resources["category"].astype(str).str.strip().str.casefold() == category.casefold()]
    if len(matches):
        matches = matches[matches.apply(lambda row: verified_date(row) is not None, axis=1)]
    note = ""
    if country and not matches.empty:
        if "country" in matches.columns:
            country_values = matches["country"].astype(str).str.strip().str.casefold()
            matches = matches[country_values == country.strip().casefold()]
        elif country.strip().casefold() != "india":
            matches = matches.iloc[0:0]
        if matches.empty:
            return matches, extra_text("no_country").format(country=country.strip())
    if not matches.empty:
        place_values = matches.apply(state_value, axis=1)
        is_national = place_values.map(is_national_location)
        if state == "__ALL_INDIA__":
            matches = matches[is_national]
            if district:
                note = extra_text("district_need_state")
        else:
            is_local = place_values.str.strip().str.casefold() == state.strip().casefold()
            if is_local.any():
                if district and "district" in matches.columns:
                    district_values = matches["district"].astype(str).str.strip()
                    is_requested_district = district_values.str.casefold() == district.strip().casefold()
                    is_statewide = district_values.eq("") | district_values.str.casefold().eq("nan")
                    matches = matches[(is_local & (is_requested_district | is_statewide)) | is_national]
                    if not (is_local & is_requested_district).any():
                        note = extra_text("district_no_data").format(district=district)
                else:
                    matches = matches[is_local | is_national]
            else:
                matches = matches[is_national]
                note = t("note_national", loc=state)
    if pincode and not matches.empty:
        if "pincode" in matches.columns:
            pin_values = matches["pincode"].astype(str).str.replace(r"\s+", "", regex=True)
            pin_match = pin_values == pincode
            general = pin_values.eq("") | pin_values.str.casefold().eq("nan")
            if not pin_match.any():
                note = extra_text("no_pincode").format(pincode=pincode)
            matches = matches[pin_match | general]
        else:
            note = extra_text("no_pincode").format(pincode=pincode)
    if urgent and "available_24_7" in matches.columns and not matches.empty:
        matches = matches.assign(_k=matches["available_24_7"].map(lambda value: not is_yes(value))).sort_values("_k", kind="stable").drop(columns="_k")
    return matches, note


def resource_key(row: pd.Series) -> str:
    identity = "\x1f".join(str(row.get(name, "")).strip() for name in ("name", "category", "contact", "website", "source", "source_url"))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def toggle_saved_resource(key: str, record: dict) -> None:
    saved = dict(st.session_state.get("saved_resources", {}))
    if key in saved:
        saved.pop(key)
    else:
        saved[key] = record
    st.session_state["saved_resources"] = saved


def remove_saved_resource(key: str) -> None:
    saved = dict(st.session_state.get("saved_resources", {}))
    saved.pop(key, None)
    st.session_state["saved_resources"] = saved


def show_resource(row: pd.Series) -> dict:
    title = localized(row, "name", "resource_name") or "—"
    description = localized(row, "description", "details")
    contact = val(row, "contact", "phone", "email")
    website = val(row, "website", "url", "link")
    source = val(row, "source", "source_url")
    place = val(row, "location", "area")
    checked = verified_date(row)
    checked_label = ""
    h24 = is_yes(val(row, "available_24_7"))
    with st.container(border=True):
        st.markdown(f"#### {title}")
        badges = []
        if h24:
            badges.append(f'<span class="badge">{html.escape(t("open24"))}</span>')
        if checked:
            stamp = checked.strftime("%m/%Y")
            if (date.today() - checked).days > STALE_AFTER_DAYS:
                checked_label = t("stale", date=stamp)
                badges.append(f'<span class="badge warn">{html.escape(checked_label)}</span>')
            else:
                checked_label = t("verified", date=stamp)
                badges.append(f'<span class="badge">{html.escape(checked_label)}</span>')
        if badges:
            st.markdown("".join(badges), unsafe_allow_html=True)
        if description:
            st.write(description)
        details = [d for d in (html.escape(place) if place else "", contact_html(contact) if contact else "") if d]
        if details:
            st.markdown(f'<div class="res-meta">{" &nbsp;|&nbsp; ".join(details)}</div>', unsafe_allow_html=True)
        if website:
            link = website if website.startswith(("https://", "http://")) else f"https://{website}"
            st.link_button(t("open_site"), link)
        if source:
            source_link = source if source.startswith(("https://", "http://")) else f"https://{source}"
            st.link_button(source_page_label(), source_link)
        else:
            st.caption("Source link not provided.")
        key = resource_key(row)
        saved = st.session_state.get("saved_resources", {})
        st.button(
            extra_text("unsave") if key in saved else extra_text("save"),
            key=f"save_resource_{key}",
            on_click=toggle_saved_resource,
            args=(key, row.to_dict()),
        )
    return {"name": title, "contact": contact, "website": website, "place": place, "h24": h24, "source": source, "checked": checked_label}


# --------------------------------------------------------------------------
# Take-away contact sheet (neutral, unbranded, works offline once downloaded)
# --------------------------------------------------------------------------
SHEET_TEMPLATE = """<!doctype html>
<html lang="%%LANG%%"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%%TITLE%%</title>
<style>
body{font-family:system-ui,'Noto Sans Devanagari','Noto Sans Kannada',sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#222;line-height:1.6}
h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.6rem;border-bottom:1px solid #ccc;padding-bottom:.2rem}
.item{margin:.8rem 0}.meta{color:#555;font-size:.95rem}.note{background:#f4f4f4;padding:.8rem 1rem;border-radius:8px;margin-top:1.4rem}
@media print{a{color:#000;text-decoration:none}}
</style></head><body>
<h1>%%TITLE%%</h1>
<ol>%%STEPS%%</ol>
%%BODY%%
<p class="note">%%EMERG%%</p>
</body></html>"""


def build_contact_sheet(groups: list[tuple[str, list[dict]]]) -> bytes:
    steps = "".join(f"<li>{html.escape(s)}</li>" for s in t("takeaway_steps"))
    body = []
    for label, items in groups:
        body.append(f"<h2>{html.escape(label)}</h2>")
        for it in items:
            bits = []
            if it["contact"]:
                bits.append(contact_html(it["contact"]))
            if it["place"]:
                bits.append(html.escape(it["place"]))
            if it["h24"]:
                bits.append(html.escape(t("open24")))
            if it["website"]:
                bits.append(html.escape(it["website"]))
            if it["checked"]:
                bits.append(html.escape(it["checked"]))
            if it["source"]:
                source_url = it["source"] if it["source"].startswith(("https://", "http://")) else f"https://{it['source']}"
                bits.append(f'<a href="{html.escape(source_url, quote=True)}">{html.escape(source_page_label())}</a>')
            body.append(
                f'<div class="item"><strong>{html.escape(it["name"])}</strong>'
                f'<div class="meta">{" | ".join(bits)}</div></div>'
            )
    page = (
        SHEET_TEMPLATE.replace("%%LANG%%", current_lang())
        .replace("%%TITLE%%", html.escape(t("takeaway_title")))
        .replace("%%STEPS%%", steps)
        .replace("%%BODY%%", "".join(body))
        .replace("%%EMERG%%", html.escape(t("takeaway_emerg")))
    )
    return page.encode("utf-8")


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------
stage = st.session_state.stage
need = st.session_state.need
total_steps = 3 if need == "unsure" else 2

if stage == "need":
    question_header(1, total_steps, t("q_need"), t("q_need_c"))
    items = list(NEEDS.items())
    for start in range(0, len(items), 3):
        cols = st.columns(3, gap="medium")
        for col, (key, (icon, _)) in zip(cols, items[start : start + 3]):
            option_card(col, icon, t(f"need_{key}"), t(f"need_{key}_d"), key, pick_need, urgent=(key == "danger"))

elif stage == "clarify":
    question_header(2, 3, t("q_clar"), t("q_clar_c"))
    cols = st.columns(2, gap="medium")
    for i, key in enumerate(CLARIFIERS):
        option_card(cols[i % 2], "🧭", t(f"clar_{key}"), "", key, pick_clarify)
    nav_buttons()

elif stage == "timing":
    question_header(3 if need == "unsure" else 2, total_steps, t("q_time"), t("q_time_c"))
    cols = st.columns(3, gap="medium")
    for col, key in zip(cols, TIMINGS):
        option_card(col, "🕒", t(f"time_{key}"), t(f"time_{key}_d"), key, pick_timing)
    nav_buttons()

else:
    if need == "danger":
        categories = ["Emergency assistance"]
    elif need == "unsure":
        categories = list(CLARIFIERS.get(st.session_state.clarify, ALL_CATEGORIES))
    else:
        categories = list(NEEDS[need][1])
    timing = st.session_state.timing
    urgent = need == "danger" or timing == "now"
    if urgent and "Emergency assistance" not in categories:
        # Keep the selected categories and put emergency options first when help is needed now.
        categories.insert(0, "Emergency assistance")

    st.markdown(f'<div class="results-head">{html.escape(t("results_head"))}</div>', unsafe_allow_html=True)
    if need == "danger":
        st.markdown(f'<div class="urgent">{t("urgent_danger")}</div>', unsafe_allow_html=True)
    elif timing == "now":
        st.markdown(f'<div class="urgent">{html.escape(t("urgent_now"))}</div>', unsafe_allow_html=True)

    resources = load_resources()
    country = st.text_input(
        extra_text("country_label"),
        placeholder=extra_text("country_ph"),
        key="resource_country",
    ).strip()
    raw_pincode = st.text_input(
        extra_text("pincode_label"),
        placeholder=extra_text("pincode_ph"),
        max_chars=6,
        key="resource_pincode",
    ).strip()
    pincode = raw_pincode if not raw_pincode or re.fullmatch(r"\d{6}", raw_pincode) else ""
    if raw_pincode and not pincode:
        st.warning(extra_text("bad_pincode"))
    state_entry = st.text_input(
        extra_text("state_label"),
        placeholder=extra_text("state_ph"),
        key="resource_state_text",
    ).strip()
    state = state_entry or "__ALL_INDIA__"
    selected_state = state_entry
    available_districts = district_choices(resources, selected_state)
    district = st.text_input(
        extra_text("district_label"),
        placeholder=extra_text("district_ph"),
        key="resource_district_text",
    ).strip()
    if selected_state and not available_districts:
        st.caption(extra_text("district_empty"))
    elif not selected_state:
        st.caption(extra_text("district_need_state"))
    search_term = st.text_input(extra_text("search"), placeholder=extra_text("search_ph"), key="resource_search").strip().casefold()

    groups: list[tuple[str, list[dict]]] = []
    only_24_7 = st.checkbox(extra_text("filter_24"), key="only_24_7")
    if resources.empty:
        st.info("The resource list is not connected yet. Add data/resources.csv to show services here.")
        st.caption("CSV columns: name, category, description, contact, website, location, country, state, district, pincode, available_24_7, verified_on, source.")
    elif "category" not in resources.columns:
        st.warning("The CSV needs a `category` column so HelpBridge can match services to support areas.")
    else:
        if "name" in resources.columns and resources["name"].astype(str).str.upper().str.startswith("EXAMPLE").any():
            st.warning("Sample data is loaded. Replace the EXAMPLE rows in data/resources.csv with verified services before sharing this app.")
        for category in categories:
            slug = CATEGORY_SLUG[category]
            label = t(f"cat_{slug}")
            st.markdown(
                f'<div class="cat-head">{CATEGORY_ICONS[category]} {html.escape(label)}</div>'
                f'<p class="cat-sub">{html.escape(t(f"cat_{slug}_d"))}</p>',
                unsafe_allow_html=True,
            )
            matches, note = pick_matches(resources, category, country, state, district, pincode, urgent)
            if note:
                st.caption(note)
            if only_24_7:
                if "available_24_7" in matches.columns:
                    matches = matches[matches["available_24_7"].map(is_yes)]
                else:
                    matches = matches.iloc[0:0]
            if search_term and not matches.empty:
                search_columns = [
                    column for column in (
                        "name", "resource_name", "name_hi", "name_kn",
                        "description", "details", "description_hi", "description_kn",
                        "contact", "phone", "email", "location", "area", "country", "state", "district", "pincode",
                    ) if column in matches.columns
                ]
                if search_columns:
                    found = matches[search_columns].astype(str).apply(
                        lambda column: column.str.casefold().str.contains(re.escape(search_term), na=False)
                    ).any(axis=1)
                    matches = matches[found]
                else:
                    matches = matches.iloc[0:0]
            if matches.empty:
                message = extra_text("no_search") if search_term else (extra_text("no_24") if only_24_7 else t("no_verified"))
                st.info(message)
                continue
            shown = [show_resource(row) for _, row in matches.iterrows()]
            groups.append((label, shown))

    saved_records = st.session_state.get("saved_resources", {})
    with st.expander(f"{extra_text('saved')} ({len(saved_records)})", expanded=bool(saved_records)):
        st.caption(extra_text("saved_note"))
        if not saved_records:
            st.caption(extra_text("saved_empty"))
        else:
            for saved_key, record in list(saved_records.items()):
                saved_row = pd.Series(record)
                saved_name = localized(saved_row, "name", "resource_name") or "—"
                saved_description = localized(saved_row, "description", "details")
                saved_contact = val(saved_row, "contact", "phone", "email")
                saved_website = val(saved_row, "website", "url", "link")
                saved_source = val(saved_row, "source", "source_url")
                with st.container(border=True):
                    st.write(saved_name)
                    if saved_description:
                        st.caption(saved_description)
                    if saved_contact:
                        st.write(saved_contact)
                    if saved_website:
                        website_link = saved_website if saved_website.startswith(("https://", "http://")) else f"https://{saved_website}"
                        st.link_button(t("open_site"), website_link)
                    if saved_source:
                        source_link = saved_source if saved_source.startswith(("https://", "http://")) else f"https://{saved_source}"
                        st.link_button(source_page_label(), source_link)
                    st.button(extra_text("remove"), key=f"remove_saved_{saved_key}", on_click=remove_saved_resource, args=(saved_key,))

    if groups:
        st.write("")
        st.download_button(
            t("takeaway_btn"),
            data=build_contact_sheet(groups),
            file_name="contacts.html",
            mime="text/html",
            key="download_sheet",
        )
        st.caption(t("takeaway_warn"))
    st.write("")
    nav_buttons()

st.divider()
with st.expander("💬 Chat with HelpBridge", expanded=False):
    st.caption(
        "In immediate danger? Call 112 if you can. Share only what feels comfortable; "
        "please do not include names, exact addresses, or passwords. This chat gives general "
        "support information, not therapy, medical or legal advice, or emergency service. "
        "It is not saved after your app session, but browser history, shared devices, or "
        "phone and network monitoring may still show your activity."
    )
    st.session_state.setdefault("chat_messages", [])
    st.session_state.setdefault("chat_times", [])
    for chat_message in st.session_state.chat_messages:
        with st.chat_message(chat_message["role"]):
            st.markdown(chat_message["content"])

    prompt = st.chat_input("What would you like help thinking through?", key="helpbridge_chat_input")
    if prompt:
        prompt = prompt.strip()
        if prompt:
            now = time.time()
            recent_times = [sent_at for sent_at in st.session_state.chat_times if now - sent_at < 300]
            if len(prompt) > 1000:
                st.warning("Please keep your message under 1000 characters.")
            elif len(recent_times) >= 15:
                st.warning("You've sent a lot of messages. Please wait a few minutes and try again.")
            else:
                st.session_state.chat_times = recent_times + [now]
                st.session_state.chat_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                with st.chat_message("assistant"):
                    with st.spinner("Thinking…"):
                        reply, used_fallback = generate_reply(
                            prompt,
                            st.session_state.chat_messages[:-1],
                            st.session_state.get("resource_state_text", ""),
                        )
                    st.markdown(reply)
                    if used_fallback:
                        st.caption("This is basic guidance, not an AI reply. The AI may be unavailable or this may be an urgent message.")
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})

    if st.session_state.chat_messages and st.button("Clear chat", key="clear_helpbridge_chat"):
        st.session_state.chat_messages = []
        st.rerun()

with st.expander(t("privacy_title")):
    st.markdown("\n".join(f"- {point}" for point in t("privacy_points")))
st.markdown(f'<p class="footer-note">{html.escape(t("footer"))}</p>', unsafe_allow_html=True)
