# Live Forex Trading Analyzer Application - SAP Fiori

A full-stack real-time forex trading analysis platform that connects to MetaTrader 5 (MT5), streams live market data, computes technical indicators, and presents everything through a modern SAP Fiori (OpenUI5) dark-themed interface.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-6.0-green)
![OpenUI5](https://img.shields.io/badge/OpenUI5-1.120.17-orange)
![Redis](https://img.shields.io/badge/Redis-Required-red)
![MT5](https://img.shields.io/badge/MetaTrader5-Integration-yellow)

---

## Features

### Dashboard
- Live price tiles for all configured currency pairs
- Real-time trend direction indicators
- Trade quality score badges (0-100)

### Interactive Chart
- **TradingView Lightweight Charts** for candlestick rendering
- **Drawing tools** powered by Fabric.js canvas overlay:
  - Trendlines, horizontal lines, rays
  - Fibonacci retracements
  - Rectangle zones & pitchforks
  - Text labels & price ranges
- Live pattern match overlays via WebSocket

### Technical Analysis Engine
- **Indicators**: EMA (20/50/200), RSI, ADX
- **Market Structure**: Swing highs/lows, Break of Structure (BOS), Change of Character (CHoCH)
- **Smart Features**: Equal highs/lows detection, Support/Resistance zones
- **Trade Score**: Configurable weighted scoring across 8 criteria (trend, structure, S/R zone, liquidity sweep, RSI, volume, session, news impact)

### Trade Journal
- Log trades with pair, direction, entry/SL/TP, lot size, result
- Screenshot uploads and notes
- Auto-captures context (trade score, session, trend at time of entry)

### Analytics
- Win rate and average PnL tracking
- Pattern outcome statistics
- Historical pattern occurrence browsing

### Pattern Recognition
- Save custom pattern templates
- Automatic scanning with similarity matching (>=90% threshold)
- Alert system for pattern matches

### Settings
- Default risk percentage configuration
- Swing lookback period (3/5/8/13 candles)
- Sound and browser notification toggles
- Configurable trade-score weights
- MT5 connection status monitoring

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| Django 6.0 | Web framework |
| Django REST Framework | REST API |
| Django Channels + Daphne | WebSocket support (ASGI) |
| Celery + Celery Beat | Background task scheduling |
| Redis | Message broker, caching, channel layer |
| MetaTrader5 Python API | Live market data source |
| pandas | Indicator computation |
| SQLite | Persistent storage |

### Frontend
| Technology | Purpose |
|---|---|
| OpenUI5 1.120.17 | SAP Fiori UI framework (sap_horizon_dark theme) |
| TradingView Lightweight Charts | Candlestick chart rendering |
| Fabric.js | Canvas-based drawing tools |
| UI5 CLI | Development server with proxy middleware |

---

## Architecture

```
                    +-----------+
                    |   MT5     |
                    | Terminal  |
                    +-----+-----+
                          |
                    +-----v-----+
                    |  Celery   |
                    |  Workers  |
                    +-----+-----+
                          |
                +---------v---------+
                |      Redis        |
                | (Cache + Broker)  |
                +---------+---------+
                          |
                +---+-----v-----+---+
                |  Django + Daphne  |
                |  (REST + WS)      |
                |  Port 8000        |
                +---+-----+-----+---+
                    |     |
              REST  |     | WebSocket
                    |     |
                +---v-----v-----+
                |   OpenUI5     |
                |   Frontend    |
                |   Port 8080   |
                +---------------+
```

---

## API Endpoints

### Market (`/api/market/`)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/candles/` | OHLCV candle data for a pair/timeframe |
| GET | `/analysis/` | Full indicator + structure + trade-score analysis |
| GET | `/ticks/` | Latest tick prices for all pairs |
| GET | `/account/` | MT5 account details |
| GET | `/session/` | Current trading session info |
| GET | `/news/` | Upcoming economic calendar events |
| POST | `/risk/` | Position size calculator |
| GET/PUT | `/settings/` | User preferences |
| CRUD | `/drawings/` | Chart annotations |
| CRUD | `/patterns/` | Pattern templates |
| POST | `/patterns/<id>/find_matches/` | Search for similar patterns |
| CRUD | `/alerts/` | System alerts |
| POST | `/alerts/acknowledge_all/` | Mark all alerts as read |

### Journal (`/api/journal/`)
| Method | Endpoint | Description |
|---|---|---|
| CRUD | `/entries/` | Trade journal entries |

### WebSocket (`ws://localhost:8000/ws/`)
- Live tick price updates
- Analysis computation results
- Pattern match notifications
- Alert broadcasts

---

## Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Redis Server** (running on default port 6379)
- **MetaTrader 5** terminal (installed and logged in)

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Shivananda8051/Live-Forex-Trading-analyzer-Application-SAP-Fiori.git
cd Live-Forex-Trading-analyzer-Application-SAP-Fiori
```

### 2. Backend setup
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install django djangorestframework django-cors-headers channels daphne celery redis MetaTrader5 pandas
cd backend
python manage.py migrate
```

### 3. Frontend setup
```bash
cd frontend
npm install
```

### 4. Start Redis
Ensure Redis server is running on `localhost:6379`.

### 5. Start MetaTrader 5
Open MT5 terminal and log in to your trading account.

---

## Running the Application

### Quick Start (Windows)
```bash
run.bat
```
This sequentially starts: Redis, Daphne (port 8000), Celery Worker, Celery Beat, and UI5 dev server (port 8080). The browser opens automatically.

### Manual Start
```bash
# Terminal 1 - Django ASGI Server
cd backend
daphne -b 0.0.0.0 -p 8000 backend.asgi:application

# Terminal 2 - Celery Worker
cd backend
celery -A backend worker -l info -P solo

# Terminal 3 - Celery Beat Scheduler
cd backend
celery -A backend beat -l info

# Terminal 4 - UI5 Frontend
cd frontend
npx ui5 serve --open
```

### Stopping (Windows)
```bash
stop.bat
```

---

## Background Tasks

| Task | Interval | Description |
|---|---|---|
| `poll_mt5_ticks` | 10s | Fetches tick prices, caches in Redis, pushes to WebSocket |
| `poll_mt5_candles` | 120s | Fetches candles across 7 timeframes (M1-W1) |
| `compute_indicators` | Periodic | Computes EMAs, RSI, ADX, market structure, trade scores |
| `scan_patterns` | Periodic | Matches current price against saved pattern templates |

---

## License

This project is for educational and personal trading analysis purposes.

---

## Disclaimer

This software is for educational purposes only. It is not financial advice. Trading forex involves substantial risk of loss and is not suitable for every investor. Past performance is not indicative of future results. Use at your own risk.
