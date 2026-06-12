# Hevy Flow 

An end-to-end **Data Engineering ETL pipeline** that extracts workout logs from the [Hevy](https://www.hevyapp.com/) fitness tracking app, transforms and cleans the raw data, loads it into a **Supabase (PostgreSQL)** database, and presents insights through an interactive **Streamlit** dashboard.

## Architecture

```mermaid
graph LR
    A["Phase 1<br/>Extract CSV"] --> B["Phase 2<br/>Transform & Clean"]
    B --> C["Phase 3<br/>Load to Supabase"]
    C --> D["Phase 4<br/>Streamlit Dashboard"]

    style A fill:#4CAF50,color:#fff,stroke:#388E3C,stroke-width:2px
    style B fill:#2196F3,color:#fff,stroke:#1976D2,stroke-width:2px
    style C fill:#FF9800,color:#fff,stroke:#F57C00,stroke-width:2px
    style D fill:#9C27B0,color:#fff,stroke:#7B1FA2,stroke-width:2px
```

### Detailed Pipeline Flow

```mermaid
flowchart TD

subgraph group_group_etl["ETL Pipeline"]
  node_main_py["main.py<br/>etl entrypoint<br/>[main.py]"]
  node_extract_py["Extract<br/>csv ingest<br/>[extract.py]"]
  node_transform_py["Transform<br/>cleaning logic<br/>[transform.py]"]
  node_load_py["Load<br/>db writer<br/>[load.py]"]
end

subgraph group_group_analytics["Analytics App"]
  node_dashboard_py["dashboard.py<br/>analytics ui<br/>[dashboard.py]"]
  node_streamlit(("Streamlit<br/>ui framework"))
  node_plotly(("Plotly<br/>charting"))
end

subgraph group_group_config["Config & Runtime"]
  node_config_py["config.py<br/>settings<br/>[config.py]"]
  node_env_example[".env.example<br/>env template<br/>[.env.example]"]
  node_environment_yml["environment.yml<br/>conda env<br/>[environment.yml]"]
  node_pandas(("Pandas<br/>dataframe lib"))
  node_psycopg2(("psycopg2<br/>db adapter"))
  node_dotenv(("python-dotenv<br/>env loader"))
end

subgraph group_group_storage["Data Store"]
  node_workouts_csv["workouts.csv<br/>raw export<br/>[workouts.csv]"]
  node_supabase_db[("Supabase<br/>postgres warehouse")]
end

node_main_py -->|"runs"| node_extract_py
node_main_py -->|"runs"| node_transform_py
node_main_py -->|"runs"| node_load_py
node_extract_py -->|"reads"| node_workouts_csv
node_extract_py -->|"uses"| node_pandas
node_transform_py -->|"uses"| node_pandas
node_transform_py -->|"consumes"| node_extract_py
node_load_py -->|"writes"| node_supabase_db
node_load_py -->|"uses"| node_psycopg2
node_dashboard_py -->|"reads"| node_supabase_db
node_dashboard_py -->|"uses"| node_streamlit
node_dashboard_py -->|"uses"| node_plotly
node_config_py -->|"documents"| node_env_example
node_config_py -->|"loads"| node_dotenv
node_main_py -->|"configures"| node_config_py
node_dashboard_py -->|"configures"| node_config_py
node_environment_yml -->|"pins"| node_pandas
node_environment_yml -->|"pins"| node_psycopg2

click node_main_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/main.py"
click node_extract_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/extract.py"
click node_transform_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/transform.py"
click node_load_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/load.py"
click node_workouts_csv "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/data/workouts.csv"
click node_dashboard_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/dashboard.py"
click node_config_py "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/config.py"
click node_env_example "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/.env.example"
click node_environment_yml "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/environment.yml"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_main_py,node_extract_py,node_transform_py,node_load_py toneBlue
class node_dashboard_py,node_streamlit,node_plotly toneAmber
class node_config_py,node_env_example,node_environment_yml,node_pandas,node_psycopg2,node_dotenv toneMint
class node_workouts_csv,node_supabase_db toneRose
```

## Tech Stack

<div align="center">

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)

</div>

**Core Libraries & Tools:**
* **Language:** Python 3.12
* **Environment:** Conda (`environment.yml`)
* **Data Processing:** `pandas` for ETL transformations
* **Database:** Supabase (PostgreSQL)
* **DB Adapter:** `psycopg2-binary`
* **Visualization:** Streamlit & Plotly Express/Graph Objects
* **Config Management:** `python-dotenv`

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

