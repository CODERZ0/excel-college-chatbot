EXCEL ENGINEERING COLLEGE — EXTREME OFFLINE CHATBOT UPDATE

This version replaces the ChatterBot response engine with a fully offline,
section-aware retrieval engine. It loads the complete supplied knowledge_base.txt.
It adds course detection and per-browser-session context, including follow-up
questions such as "I want to join B.Tech AI and Data Science" and then "what
documents do I need?".

INSTALL
1. Stop Flask (Ctrl+C).
2. Back up your existing app.py and chatbot.py. Do not delete database.sqlite3.
3. Copy chatbot.py and knowledge_base.txt to the project root beside app.py.
4. Replace app.py with the included app.py. It preserves /, /get, /login, /result.
   The /get response still works with the existing frontend's ?msg=... request.
5. Do NOT replace templates/index.html or static/styles/style.css.
6. Activate your existing venv and run:
      python app.py
7. Browse to http://127.0.0.1:5000

DEPENDENCIES
The new retrieval engine uses only Python's standard library. Flask is needed
for the web app. mysql-connector-python is needed only for the existing MySQL
login route. ChatterBot is no longer used by this chatbot.py, so it is not
required for this retrieval engine.

IMPORTANT
- Existing database.sqlite3 is left untouched; this engine does not read or
  write it. Keep it as a backup of the former ChatterBot project.
- app.py uses a development secret key. Set app.secret_key to a private,
  random value before deploying publicly.
- The existing login form's password comparison is retained for compatibility;
  for a real deployment, store password hashes and verify them instead.
- Some content in the uploaded knowledge base contains third-party source
  labels and details flagged as needing confirmation. The bot retrieves only
  what the file says; verify fees, active intake, deadlines and current
  placement numbers before presenting them as official current facts.
- This is offline retrieval, not a generative LLM. It improves matching,
  course recognition and follow-up context, but cannot reason beyond the file.
