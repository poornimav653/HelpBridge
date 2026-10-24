# HelpBridge

### Find support that fits your needs, at your own pace.

HelpBridge is a support navigation app that helps people explore useful services without needing to share their whole story. Choose a support area, answer a few optional questions, and browse service contacts and official links.

> **In immediate danger?** Contact local emergency services if it is safe. In India, call **112**.

## Features

- Guided questions to help narrow down useful next steps.
- Support categories for emotional support, safety planning, legal help, shelter, and health and wellbeing.
- Search and filters for service name, keyword, availability, and location.
- Clickable phone numbers that open a compatible calling app.
- Safety planning prompts and a session-only saved-resources list.
- English, Hindi, and Kannada interface options.
- Accessibility settings such as larger text, higher contrast, and reduced motion.
- A downloadable contact sheet.

Features and resource availability depend on the app version and `data/resources.csv`.

## Built with

- Python
- [Streamlit](https://streamlit.io/)
- pandas
- CSV resource data

## Run on Windows

1. Open the project folder in VS Code.
2. Choose **Terminal > New Terminal**.
3. Install the app packages:

   ```powershell
   py -m pip install -r requirements.txt
   ```

4. Start the app:

   ```powershell
   py -m streamlit run app_v4.py
   ```

5. Open the Local URL shown in the terminal, usually `http://localhost:8501`.
6. To stop the app, return to the terminal and press **Ctrl+C**.

## Project layout

```text
HelpBridge/
|-- app_v4.py
|-- i18n.py
|-- requirements.txt
`-- data/
    `-- resources.csv
```

## Resource data

The app reads service listings from `data/resources.csv`. Preserve these column names when editing it:

```text
name, category, description, contact, website, location,
country, state, district, pincode, available_24_7, verified_on, source
```

Use official or reliable sources for contact details. Fill district and PIN fields only when a source confirms them. Keep `verified_on` and `source` up to date. Leave unknown details blank instead of guessing.

## Privacy and safety

- HelpBridge helps people find resources; it does not replace emergency services, legal advice, medical care, or counselling.
- Avoid entering names or identifying details unless the app specifically needs them.
- Phone links open a compatible calling app. They do not place a call automatically or open call history.
- Check a service's official source for current availability before relying on a listing.

## Share online

Push the project to GitHub, then deploy it with [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud). Select `app_v4.py` as the entrypoint and include `requirements.txt`, `i18n.py`, and `data/resources.csv` in the repository.

## Contributing

1. Keep the app welcoming, clear, and accessible.
2. Cite a source for new service details.
3. Do not add unverified phone numbers, addresses, or PIN codes.
4. Keep user privacy and personal safety in mind.

---

**HelpBridge** - a starting point for finding support.

