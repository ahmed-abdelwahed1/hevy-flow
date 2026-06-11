# Hevy-Flow 🏋️‍♂️📊

An end-to-end **Data Engineering ETL pipeline** that extracts workout logs from the [Hevy](https://www.hevyapp.com/) fitness tracking app, transforms and cleans the raw data, loads it into a **Supabase (PostgreSQL)** database, and presents insights through an interactive **Streamlit** dashboard.

## Architecture

```mermaid
graph LR
    A["📥 Phase 1<br/>Extract CSV"] --> B["🔧 Phase 2<br/>Transform & Clean"]
    B --> C["📤 Phase 3<br/>Load to Supabase"]
    C --> D["📊 Phase 4<br/>Streamlit Dashboard"]

    style A fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    style B fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    style C fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    style D fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
```

## Tech Stack

| Layer            | Technology                   |
|------------------|------------------------------|
| Language         | Python 3.12                  |
| Env Management   | Conda                        |
| Data Processing  | Pandas                       |
| Database         | Supabase (PostgreSQL)        |
| DB Adapter       | psycopg2                     |
| Dashboard        | Streamlit + Plotly            |
| Config           | python-dotenv                |

## Dataset

The pipeline processes a Hevy app export (`data/workouts.csv`) containing **2,628 set-level records** spanning **~2 years** (Jul 2024 – Jun 2026) across **14 columns**:

| Column | Description |
|---|---|
| `title` | Workout session name (e.g., PUSH, PULL, LEGS) |
| `start_time` / `end_time` | Session timestamps (text → parsed to datetime) |
| `exercise_title` | Exercise name |
| `set_index` | Set number within an exercise (0-indexed) |
| `weight_kg` | Weight in kg (null for bodyweight exercises) |
| `reps` | Repetitions performed |
| `rpe` | Rate of Perceived Exertion (6–10 scale) |
| `distance_km` / `duration_seconds` | For cardio/timed exercises |

## Setup

### Prerequisites

- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda)
- A [Supabase](https://supabase.com/) project (free tier works)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-username/hevy-flow.git
cd hevy-flow

# 2. Create and activate the Conda environment
conda env create -f environment.yml
conda activate hevy-flow

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your Supabase credentials
```

### Running the Pipeline

```bash
python main.py
```

### Launching the Dashboard

```bash
streamlit run dashboard.py
```

## Project Structure

```
hevy-flow/
├── data/
│   └── workouts.csv          # Raw Hevy export
├── etl/
│   ├── __init__.py
│   ├── extract.py            # Phase 1: CSV extraction & validation
│   ├── transform.py          # Phase 2: Cleaning & transformations
│   └── load.py               # Phase 3: Supabase loader
├── dashboard.py              # Phase 4: Streamlit analytics dashboard
├── config.py                 # Centralized configuration
├── main.py                   # Pipeline entry point
├── environment.yml           # Conda environment
├── .env.example              # Environment variable template
├── .gitignore
└── README.md
```

## Pipeline Phases

- [x] **Phase 1 — Extract**: Read CSV, validate schema, profile data quality
- [x] **Phase 2 — Transform**: Parse datetimes, handle nulls, derive columns, normalize
- [x] **Phase 3 — Load**: Create Supabase tables, upsert cleaned data
- [x] **Phase 4 — Visualize**: Streamlit dashboard with interactive charts

## License

This project is for portfolio and educational purposes.
