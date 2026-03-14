# ⚽ Football Championship Manager

A full-stack football league management system with admin panel, public views, and Telegram bot reporting.

---

## 📁 Project Structure

```
football-championship/
├── server.py        ← Python/Flask REST API backend
├── index.html       ← Complete single-page frontend
├── bot.py           ← Telegram bot for match reporting
├── championship.db  ← SQLite database (auto-created on first run)
└── README.md
```

---

## 🚀 Quick Start

### 1. Backend (Python + Flask)

**Requirements:** Python 3.8+, Flask (already installed)

```bash
# Start the API server (port 3001)
python3 server.py
```

You'll see:
```
⚽  Initialising database...
✅  Database ready
🚀  Starting Football Championship API on http://localhost:3001
```

The database is auto-seeded with 8 demo teams, 14 matches, and an admin account.

---

### 2. Frontend

Open `index.html` in any browser — **no build step needed**.

```bash
# Option A: open directly
open index.html      # macOS
xdg-open index.html  # Linux

# Option B: serve via Python (recommended, avoids CORS in some browsers)
python3 -m http.server 8080
# then open http://localhost:8080
```

> **Note:** The frontend works in "Demo Mode" even without the backend — it uses built-in sample data. Start the backend to persist real data.

---

### 3. Telegram Bot (Optional)

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram → get your token
2. Set the token and run:

```bash
export BOT_TOKEN=123456789:ABCdef...your_token
export API_URL=http://localhost:3001/api   # optional, this is the default
python3 bot.py
```

#### Bot Commands
| Command | Description |
|---|---|
| `/start` | Welcome message + menu |
| `/standings` | Current league table |
| `/results` | Recent match results |
| `/upcoming` | Scheduled fixtures |
| `/report` | Submit a match report |
| `/help` | Show help |

---

## 🔐 Admin Login

| Credential | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

Click **"Admin Login"** in the sidebar to access the admin panel.

---

## 🛠 API Endpoints

### Public
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/standings` | Full league table |
| GET | `/api/teams` | All teams (supports `?search=`) |
| GET | `/api/teams/:id` | Team detail + stats |
| GET | `/api/matches` | Matches (supports `?status=&page=&matchweek=`) |
| GET | `/api/matches/:id` | Single match |
| GET | `/api/stats` | Overview statistics |
| POST | `/api/reports` | Submit a report |

### Admin (requires `Authorization: Bearer <token>`)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login` | Get JWT token |
| POST | `/api/teams` | Create team |
| PUT | `/api/teams/:id` | Update team |
| DELETE | `/api/teams/:id` | Delete team |
| POST | `/api/matches` | Create match |
| PUT | `/api/matches/:id` | Update match / enter score |
| DELETE | `/api/matches/:id` | Delete match |
| GET | `/api/reports` | View all reports |
| PUT | `/api/reports/:id` | Update report status |

---

## 📐 Database Schema

```sql
admins    (id, username, password, created_at)
teams     (id, name, short_name, logo_color, city, founded, coach, created_at)
matches   (id, home_team_id, away_team_id, home_score, away_score,
           match_date, matchweek, venue, status, created_at)
standings (id, team_id, played, won, drawn, lost, goals_for,
           goals_against, goal_difference, points, updated_at)
reports   (id, match_id, reporter_name, telegram_user_id, message,
           status, admin_note, created_at)
```

**Points system:** Win = 3pts · Draw = 1pt · Loss = 0pts  
**Sorting:** Points → Goal Difference → Goals For → Name  
**Standings recalculate automatically** after every match insert/update/delete.

---

## 🎨 Features

### Admin Panel
- ✅ Add / Edit / Delete teams with color picker
- ✅ Add / Edit / Delete matches with score entry
- ✅ Automatic standings recalculation
- ✅ Review and resolve user reports
- ✅ Dashboard with stats overview

### Public View
- ✅ Live league table with zone indicators (CL / EL / Relegation)
- ✅ Match results grouped by matchweek
- ✅ Team cards with full statistics
- ✅ Team detail modal with recent form
- ✅ Match detail modal
- ✅ Report submission form
- ✅ Search teams

### Telegram Bot
- ✅ View standings, results, fixtures
- ✅ Multi-step report flow with match selector
- ✅ Reports saved to database
- ✅ Admin can review in dashboard

### Technical
- ✅ JWT authentication (manual implementation, no extra libs)
- ✅ CORS support
- ✅ Demo mode (frontend works without backend)
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Pagination
- ✅ SQLite WAL mode for performance

---

## 🔧 Configuration

### Backend
```bash
export PORT=3001           # API port (default: 3001)
export JWT_SECRET=mysecret  # JWT signing key
```

### Bot
```bash
export BOT_TOKEN=...        # Required: from @BotFather
export API_URL=http://localhost:3001/api  # Backend URL
```

---

## 📦 No External Dependencies

| Component | Tech | Install required? |
|---|---|---|
| Backend | Python + Flask + SQLite | Flask only (pre-installed) |
| Frontend | Vanilla HTML/CSS/JS | None — open in browser |
| Bot | Python stdlib only | None |
