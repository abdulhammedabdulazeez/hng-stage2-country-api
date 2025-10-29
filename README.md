# Country Currency & Exchange API

A RESTful API that fetches country data from external APIs, stores it in PostgreSQL, and provides CRUD operations with currency exchange rate calculations.

## Features

- Fetch and cache country data from RestCountries API
- Get real-time exchange rates from Open Exchange Rates API
- Calculate estimated GDP for each country
- Filter countries by region and currency
- Sort by GDP or population
- Generate summary images with top countries
- Full CRUD operations

## Tech Stack

- FastAPI, PostgreSQL, SQLModel, Alembic, Pillow

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/countries/refresh` | Fetch and cache all countries data |
| GET | `/countries` | Get all countries (with filters: `?region=Africa&sort=gdp_desc`) |
| GET | `/countries/{name}` | Get single country by name |
| DELETE | `/countries/{name}` | Delete country record |
| GET | `/status` | Get system status |
| GET | `/countries/image` | Get summary image (PNG) |

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL

### Installation

1. **Clone and setup:**
```bash
git clone <repo-url>
cd hng-stage2-task
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
# Copy .env.example to .env and update DATABASE_URL
cp .env.example .env
```

3. **Setup database:**
```bash
createdb country_db  # Create PostgreSQL database
alembic upgrade head  # Run migrations
```

4. **Run server:**
```bash
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## Testing

```bash
# Refresh data
curl -X POST http://localhost:8000/countries/refresh

# Get countries
curl http://localhost:8000/countries

# Filter by region
curl "http://localhost:8000/countries?region=Africa&sort=gdp_desc"

# Get one country
curl http://localhost:8000/countries/Nigeria

# Get status
curl http://localhost:8000/status

# Get summary image
curl http://localhost:8000/countries/image --output summary.png
```

## Deployment (Railway)

1. Create Railway account and new project
2. Add PostgreSQL database
3. Connect GitHub repository
4. Set `DATABASE_URL` environment variable (add `+asyncpg` to URL)
5. Deploy automatically on git push

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `DEBUG` | Enable debug mode | No |

## External APIs

- RestCountries API: https://restcountries.com/v2/all
- Open Exchange Rates API: https://open.er-api.com/v6/latest/USD

## Error Responses

- **400**: `{"error": "Validation failed", "details": {...}}`
- **404**: `{"error": "Country not found"}`
- **503**: `{"error": "External data source unavailable"}`
- **500**: `{"error": "Internal server error"}`

---

**HNG Internship - Stage 2 Task**