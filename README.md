# Legacy System Integration API

> **Data Transformation Layer** — A RESTful integration layer that bridges legacy systems with modern applications by normalising and standardising inconsistent data formats.

---

## Overview

Many enterprises still rely on legacy systems (mainframes, flat-file exports, old XML services) that produce data in formats incompatible with modern APIs and databases. This project simulates a real-world **integration middleware layer** that:

- Accepts raw payloads from heterogeneous legacy sources
- Identifies the source format and applies the appropriate parser
- Normalises field values (dates → ISO 8601, amounts → float, emails → lowercase)
- Returns a clean, standardised JSON record regardless of origin

This pattern is commonly referred to as a **canonical data model** approach in enterprise integration architecture.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Framework | FastAPI 0.115 |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Testing | Pytest |
| Docs | Swagger UI (built-in) |

---

## Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/legacy-integration-api.git
cd legacy-integration-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs: `http://localhost:8000/docs`

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/api/v1/transform` | Transform a single legacy record |
| POST | `/api/v1/transform/batch` | Transform up to 100 records |
| GET | `/api/v1/formats` | List supported formats |

---

## Supported Formats

| Format ID | Description |
|-----------|-------------|
| `csv_flat_file` | Comma-separated single-row record |
| `xml_legacy` | Non-standard XML with varied tag names |
| `cobol_mainframe` | Fixed-position 84-char mainframe record |
| `fixed_width` | Space-padded columns with auto-detected breaks |
| `pipe_delimited` | Pipe-separated fields with optional header row |


---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client / Legacy System                   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP POST (raw payload)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI REST Layer                         │
│   POST /api/v1/transform         (single record)            │
│   POST /api/v1/transform/batch   (up to 100 records)        │
│   GET  /api/v1/formats           (list supported formats)   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Transformation Service (Core Logic)            │
│                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│   │  CSV     │  │   XML    │  │  COBOL   │               │
│   └──────────┘  └──────────┘  └──────────┘               │
│   ┌──────────┐  ┌──────────┐                               │
│   │FixedWidth│  │  Pipe    │                               │
│   └──────────┘  └──────────┘                               │
│                                                             │
│   → Date normalisation  → Amount parsing  → Field mapping  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Normalised JSON Record (Canonical Model)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
legacy-integration-api/
├── app/
│   ├── main.py                          # Application entry point
│   ├── models/schemas.py                # Pydantic request/response models
│   ├── routes/
│   │   ├── health.py                    # Health check endpoint
│   │   └── transformation.py            # Transformation endpoints
│   └── services/
│       └── transformation_service.py    # Core transformation logic
├── tests/
│   └── test_transformation.py           # Pytest test suite (13 tests)
├── requirements.txt
└── README.md
```

---

## Key Design Decisions

**Canonical Data Model**: All parsers produce the same intermediate dict structure, which maps cleanly onto the `NormalisedRecord` schema. Adding a new legacy format only requires writing a new parser function — no changes to routing or response logic.

**Heuristic vs Schema-driven parsing**: For formats without a fixed schema (CSV, fixed-width), the service applies content-based heuristics (regex for emails, currency codes, dates) to infer field semantics — mirroring real-world scenarios where legacy documentation is incomplete.

**Stateless by design**: No database dependency. Each request is self-contained, which simplifies deployment and allows the consuming system to decide on persistence strategy.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT
