# 💜 HelpBridge

### Find support that fits your needs, at your own pace

HelpBridge is a support navigation prototype. It helps visitors explore useful services through a few optional questions, location filters, and a text-based AI assistant—without requiring them to write out their whole story.

> **Project status:** Prototype. Resource coverage, safety language, translations, and chatbot behavior need continued review before wider real-world use.

## What it includes

- A guided flow for emergency assistance, counselling, legal guidance, shelter and housing, and medical help.
- Search and optional country, state/UT, district, PIN-code, and 24/7 filters for service listings.
- Tap-to-call numbers, service websites, and source links.
- Session-only saved resources, contact-sheet download, and an optional safety-planning checklist.
- English, Hindi, and Kannada interface text, plus larger text, higher contrast, and reduced-motion settings.
- A Claude-powered text assistant with keyword-based resource matching and basic fallback guidance.

## Run locally on Windows

Open this project folder in VS Code, choose **Terminal → New Terminal**, and run:

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app_v4.py
```

Open the Local URL printed in the terminal, usually `http://localhost:8501`. Keep the terminal open while using the app. Press **Ctrl+C** in that terminal to stop it.

## Configure the AI assistant

Create a `.env` file in the project folder and add your Anthropic API key:

```dotenv
ANTHROPIC_API_KEY=your-anthropic-api-key
# Optional: set a model available to your account
CLAUDE_MODEL=claude-sonnet-5
```

The app shows basic fallback guidance when a key is missing or the AI service is unavailable. Keep the API key private: **never commit `.env`, paste the key into app code, or share it in chat.** The `.env` file is excluded by `.gitignore`.

For Streamlit Community Cloud, add `ANTHROPIC_API_KEY` in the app's **Secrets** settings instead of uploading `.env`.

## Resource data

Service listings live in `data/resources.csv`. Preserve these column names:

```text
name, category, description, contact, website, location, country, state,
district, pincode, available_24_7, verified_on, source
```

Use one service per row. Keep category names consistent with the app, use reliable sources, and update `verified_on` when an entry is checked. A verification date does not guarantee that a service is currently available. Leave unknown location details blank instead of guessing.

Check the CSV format with:

```powershell
py resource_validation.py
```

To also attempt online checks of website and source links:

```powershell
py resource_validation.py --check-links
```

Some sites block automated checks, so review warnings manually. Check official service sources before relying on a listing.

## How the chatbot works

1. Recent chat turns are kept in the active Streamlit session.
2. `ai_support.py` screens for selected urgent phrases before calling the model.
3. Keyword hints look for matching, dated records in the resource CSV.
4. Claude receives the user's message and recent conversation turns and can choose only among matched resource references; the app formats contact details from the CSV.
5. If the API is unavailable, HelpBridge displays basic fallback guidance.

The chatbot is text-only and uses starter keyword and safety patterns. Pattern matching can miss indirect or unfamiliar wording; it is not a therapist, doctor, lawyer, or emergency service and cannot contact emergency responders.

## Privacy and safety

- The current app has no account system or application database. Answers, chat history, saved resources, and checklist marks are held in the active app session.
- When AI is enabled, the current message and recent chat turns are sent to Anthropic. Avoid entering names, exact addresses, passwords, or details you do not want to share with the AI provider.
- Discreet mode changes the browser tab's title and icon; it does not hide page content. Quick exit navigates elsewhere but does not erase browser history.
- Tap-to-call links open a compatible calling app; they do not place a call automatically. Devices may keep call history if a call is made.
- In India, the app points visitors to **112** for immediate danger. Use the site only if it feels safe; shared devices and monitoring may reveal activity.

## Project layout

```text
HelpBridge/
├── app_v4.py                 # Streamlit app and guided support flow
├── ai_support.py             # Chatbot, resource matching, and safety handling
├── i18n.py                   # English, Hindi, and Kannada interface text
├── resource_validation.py    # Resource CSV checks
├── requirements.txt          # Python dependencies
└── data/
    └── resources.csv         # Service listings and source details
```

## Deploy with Streamlit Community Cloud

1. Push the project files to GitHub. Include `app_v4.py`, `ai_support.py`, `i18n.py`, `requirements.txt`, `.gitignore`, and `data/resources.csv`.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app from that GitHub repository and select `app_v4.py` as the entrypoint.
3. Add `ANTHROPIC_API_KEY` in the app's Secrets settings. Do not upload `.env` or commit the key.
4. Choose whether the app should be public or private, then deploy and check the app logs.

A public app can be opened by anyone with its link. Review privacy and safety expectations before sharing it with people who may enter sensitive information.

## Before wider use

Review every service listing and source, ask fluent speakers to review Hindi and Kannada safety wording, and test emergency and fallback behavior. HelpBridge helps visitors explore options; it does not replace local professional support or emergency care.
