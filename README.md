# 🎯 Vietlott AI Prediction Pipeline v3.0

> ⚠️ **Disclaimer:** Xổ số là ngẫu nhiên. Hệ thống này khai thác thống kê & xác suất lịch sử. Mục đích: nghiên cứu & giải trí.

AI-powered lottery prediction pipeline for Vietlott (Power 6/55, Mega 6/45, 6/35), built entirely on **free-tier services** with full automation via GitHub Actions.

---

## 🏗 Architecture

| Layer | Tool | Free Limit |
|-------|------|-----------|
| Database | Supabase PostgreSQL | 500 MB |
| Model Storage | Supabase Storage | 1 GB |
| Automation | GitHub Actions | 2,000 min/month |
| GPU Training | Kaggle Notebooks | 30h GPU/week |
| Notifications | Telegram Bot | Free |

## Cycle Logic

Each **cycle** = 1 AI prediction (6 numbers) tracked across **5 consecutive draws**:

```
AI generates 6 numbers → tracked for 5 draws → Evaluate → Retrain? → New cycle
```

---

## 🚀 Quick Start

### 1. Setup Supabase
1. Create project at [supabase.com](https://supabase.com)
2. Run `database/schema.sql` in the SQL Editor
3. Create a Storage bucket named `models`

### 2. Setup Telegram Bot
1. Chat with `@BotFather` → `/newbot`
2. Get token + chat_id

### 3. Add GitHub Secrets
Go to repo → Settings → Secrets → Actions:
```
SUPABASE_URL, SUPABASE_KEY, SUPABASE_STORAGE_BUCKET
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
KAGGLE_USERNAME, KAGGLE_KEY, KAGGLE_NOTEBOOK
```

### 4. Initial Data Crawl (Local)
```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your keys

# Crawl 3 years of history
python scripts/01_initial_crawl.py --lottery all --days 1095

# Dry run first
python scripts/01_initial_crawl.py --lottery power_655 --days 7 --dry-run
```

### 5. Train Models (Local or Kaggle)
```bash
# Local
python scripts/02_local_training.py --lottery all --version 3.0

# Upload to Supabase Storage
python scripts/03_upload_models.py --lottery all --version 3.0
```

### 6. Go Live
Push to GitHub — Actions run automatically on schedule.

---

## 📅 Automation Schedule

| Workflow | Schedule (ICT) | Action |
|----------|---------------|--------|
| `crawl_655.yml` | T3, T5, T7 @ 18:30 | Fetch & store result |
| `crawl_645.yml` | T4, T6, CN @ 18:30 | Fetch & store result |
| `check_results.yml` | After each crawl | Dò kết quả → Telegram |
| `manage_cycle.yml` | After check | Generate new cycle |
| `retrain_evaluation.yml` | After cycle #5 / Weekly | Evaluate & retrain |

---

## 📁 Project Structure

```
├── .github/workflows/     # Automated jobs
├── config/                # Model params JSON
├── database/schema.sql    # DB setup
├── scripts/               # One-time local scripts
├── src/
│   ├── crawlers/          # Vietlott scrapers
│   ├── models/
│   │   ├── statistical/   # Frequency, Gap, Position
│   │   └── ml/            # LSTM, XGBoost, Markov
│   ├── pipeline/          # Cycle, Predict, Check, Evaluate
│   ├── notifications/     # Telegram templates
│   └── utils/             # Supabase client, config, logger
├── tests/                 # pytest unit tests
└── kaggle/                # GPU training notebook
```

---

## 🤖 Ensemble Model

```
LSTM (40%) + XGBoost (35%) + Statistical (25%)
                    ↓
         Top candidates with low/mid/high balance
                    ↓
              6 final numbers
```

Weights auto-adjust after each 5-draw cycle based on performance.

---

## 📊 Telegram Notifications

| Event | Message |
|-------|---------|
| New prediction | Bộ số AI + weights |
| Daily crawl | Kết quả kỳ xổ |
| Each of 5 draws | Dò kết quả + lịch sử |
| Cycle complete | Tổng kết + retrain decision |

---

## 🧪 Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## 📈 Implementation Roadmap

| # | Task | Time |
|---|------|------|
| 1 | Supabase setup + run schema | 0.5 ngày |
| 2 | Telegram bot setup | 0.5 ngày |
| 3 | Initial crawl (3 năm data) | 1 ngày |
| 4 | Train models locally / Kaggle | 2 ngày |
| 5 | Upload models + verify | 0.5 ngày |
| 6 | GitHub Actions test dry run | 1 ngày |
| 7 | Go live + monitor 2 cycle | Ongoing |

**Total cost: $0/tháng ✅**
