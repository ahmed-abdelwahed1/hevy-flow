<div align="center">
  <h1>🏋️ Hevy Flow</h1>

  <p><strong>An end-to-end Data Engineering ETL pipeline for Hevy workout logs.</strong></p>

  ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
  ![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
  ![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)
  ![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
  ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
  ![Plotly](https://img.shields.io/badge/Plotly-%233F4F75.svg?style=for-the-badge&logo=plotly&logoColor=white)

</div>

<br/>

Extracts workout logs from the [Hevy](https://www.hevyapp.com/) fitness tracking app, transforms and cleans the raw data, loads it into a **Supabase (PostgreSQL)** database, and presents insights through an interactive **Streamlit** dashboard.

---

## 🛠️ Tech Stack

**Core Libraries & Tools:**
* **Language:** Python 3.12
* **Environment:** Conda (`environment.yml`)
* **Data Processing:** `pandas` for ETL transformations
* **Database:** Supabase (PostgreSQL)
* **DB Adapter:** `psycopg2-binary`
* **Visualization:** Streamlit & Plotly Express/Graph Objects
* **Config Management:** `python-dotenv`

---

## 🏗️ Architecture

### High-Level Flow
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
---

### Detailed Pipeline Flow
```mermaid
flowchart TD

subgraph group_g_raw["Raw data"]
  node_n_raw_csv["workouts.csv<br/>csv export<br/>[workouts.csv]"]
end

subgraph group_g_etl["ETL pipeline"]
  node_n_main["main<br/>etl orchestrator<br/>[main.py]"]
  node_n_extract["extract<br/>csv ingest<br/>[extract.py]"]
  node_n_transform["transform<br/>data shaping<br/>[transform.py]"]
  node_n_load["load<br/>db writer<br/>[load.py]"]
  node_n_pandas(("pandas<br/>dataframe library"))
  node_n_supabase[("Supabase<br/>warehouse")]
end

subgraph group_g_app["Analytics UI"]
  node_n_dashboard["dashboard<br/>streamlit app<br/>[dashboard.py]"]
  node_n_streamlit(("Streamlit<br/>ui runtime"))
  node_n_plotly(("Plotly<br/>charting"))
end

subgraph group_g_ops["Ops & config"]
  node_n_config["config<br/>[config.py]"]
  node_n_dotenv(("dotenv<br/>env loader"))
  node_n_env["environment.yml<br/>conda env<br/>[environment.yml]"]
  node_n_ci["CI workflow<br/>automation<br/>[ci.yml]"]
  node_n_tests["tests<br/>test suite"]
end

node_n_raw_csv -->|"ingests"| node_n_extract
node_n_main -.->|"runs"| node_n_extract
node_n_main -.->|"runs"| node_n_transform
node_n_main -.->|"runs"| node_n_load
node_n_extract -->|"uses"| node_n_pandas
node_n_extract -->|"passes data"| node_n_transform
node_n_transform -->|"uses"| node_n_pandas
node_n_transform -->|"produces"| node_n_load
node_n_load -->|"writes"| node_n_supabase
node_n_dashboard -->|"reads"| node_n_supabase
node_n_dashboard -->|"built on"| node_n_streamlit
node_n_dashboard -->|"charts with"| node_n_plotly
node_n_config -.->|"configures"| node_n_extract
node_n_config -.->|"configures"| node_n_load
node_n_config -.->|"configures"| node_n_dashboard
node_n_dotenv -->|"loads"| node_n_config
node_n_env -.->|"includes"| node_n_pandas
node_n_env -.->|"includes"| node_n_streamlit
node_n_ci -.->|"runs"| node_n_tests
node_n_ci -.->|"checks"| node_n_main
node_n_ci -.->|"checks"| node_n_dashboard
node_n_tests -.->|"covers"| node_n_extract
node_n_tests -.->|"covers"| node_n_transform
node_n_tests -.->|"covers"| node_n_load
node_n_tests -.->|"covers"| node_n_main

click node_n_raw_csv "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/data/workouts.csv"
click node_n_main "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/main.py"
click node_n_extract "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/extract.py"
click node_n_transform "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/transform.py"
click node_n_load "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/etl/load.py"
click node_n_dashboard "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/dashboard.py"
click node_n_config "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/config.py"
click node_n_env "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/environment.yml"
click node_n_ci "https://github.com/ahmed-abdelwahed1/hevy-flow/blob/main/.github/workflows/ci.yml"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_n_raw_csv toneBlue
class node_n_main,node_n_extract,node_n_transform,node_n_load,node_n_pandas,node_n_supabase toneAmber
class node_n_dashboard,node_n_streamlit,node_n_plotly toneMint
class node_n_config,node_n_dotenv,node_n_env,node_n_ci,node_n_tests toneRose
```

## 📂 Project Structure

```text
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

---

## 💻 Setup & Usage

### 1. Prerequisites

- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda)
- A [Supabase](https://supabase.com/) project (free tier works)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/hevy-flow.git
cd hevy-flow

# Create and activate the Conda environment
conda env create -f environment.yml
conda activate hevy-flow

# Configure environment variables
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 3. Running the Data Pipeline

```bash
python main.py
```

### 4. Launching the Dashboard

```bash
streamlit run dashboard.py
```
