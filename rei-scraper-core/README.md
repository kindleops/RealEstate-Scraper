# 🧠 REI Scraper Core  
**Automated Real Estate Intelligence Engine**

---

### 🚀 Overview
`rei-scraper-core` is a fully automated **DealMachine property scraper and uploader** designed for 24/7 operation.  
It logs in, applies smart filters (Vacant + High Equity), extracts property data, and uploads structured records to Airtable —  
powering **AI-driven real estate acquisition pipelines**.

---

### 🏗️ Core Features
✅ Automated login and navigation  
✅ Dynamic ZIP search and scrolling  
✅ Smart filter detection (Vacant, High Equity, etc.)  
✅ Sidebar property scraping with clean data extraction  
✅ Automatic upload to Airtable (or local JSON backup)  
✅ Modular logging system with emoji-based live feedback  
✅ Retry logic and human-like delays for anti-bot protection  
✅ 24/7 deployable cloud runtime (Render, AWS, or Lambda)  

---

### 🧬 Example Output
\`\`\`
🚀 Starting DealMachine Scraper...
✅ Login successful
===== Processing ZIP: 33127 =====
✅ Properties loaded
✅ Applied filters: Vacant, High Equity
✅ Scraped 26 valid properties
✅ Uploaded to Airtable
[✓] Completed ZIP: 33127 — 26 properties uploaded
✅ Scraper finished successfully.
\`\`\`

---

### 📂 Project Structure
\`\`\`
rei-scraper-core/
│
├── main.py                  # Entry point (loop through ZIPs, orchestrate runs)
├── login_utils.py           # Handles login automation
├── zip_scraper.py           # Per-ZIP search, filter, and property scraping
├── airtable_uploader.py     # Uploads structured records to Airtable
├── utils/
│   ├── logger.py            # Color + emoji logging system
│   ├── config.py            # Credentials and Airtable base keys
│   └── helpers.py           # Type enforcement and cleanup utilities
│
└── requirements.txt         # Dependencies (Selenium, Brave, Airtable, etc.)
\`\`\`

---

### ⚙️ Setup & Installation

#### 1️⃣ Clone the Repo
\`\`\`bash
git clone https://github.com/kindleops/rei-scraper-core.git
cd rei-scraper-core
\`\`\`

#### 2️⃣ Install Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

#### 3️⃣ Configure Environment
Create a \`.env\` file:
\`\`\`bash
DEALMACHINE_EMAIL=youremail@example.com
DEALMACHINE_PASSWORD=yourpassword
AIRTABLE_API_KEY=keyXXXXXXX
AIRTABLE_BASE_ID=appXXXXXXX
AIRTABLE_TABLE_NAME=Properties
\`\`\`

#### 4️⃣ Run the Scraper
\`\`\`bash
python main.py
\`\`\`

---

### 🧩 Debug Tips
If you see:
\`\`\`
⚠️ Skipping record #1: payload is not a dict
\`\`\`
It means your data is being passed as strings instead of dictionaries.  
Fix: enforce real dicts before upload or parse with \`ast.literal_eval()\`.

Add this line before upload for inspection:
\`\`\`python
print(f"First 3 records: {scraped_records[:3]}")
\`\`\`

---

### ☁️ Cloud Deployment
Run 24/7 on:
- 🟩 **Render** (simple cron + container)
- 🟦 **AWS EC2 / Lambda**
- 🟪 **Vercel / Fly.io / Railway**
- 🟥 **Docker + PM2** for persistent VPS execution

---

### 🧠 Future Add-Ons
- AI property scoring (Compflow.ai integration)
- Automated comp generation
- Lead qualification and SMS trigger
- Real-time campaign creation (LeadCommand.ai)
- Adaptive retries with OpenAI decision layer

---

### 🪙 License
Proprietary. © 2025 KindleOps / Reivesti Technology.  
All rights reserved. Unauthorized use is strictly prohibited.

---

**Built for precision. Engineered for dominance.**  
**→** `Reivesti Technology | AI Real Estate Infrastructure`
