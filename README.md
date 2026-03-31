# DOH Discharge Data Dashboard

A Python-based web application for visualizing Department of Health (DOH) hospital discharge data. This project utilizes Plotly Dash to create interactive dashboards that analyze demographics, substance use diagnoses, and polysubstance trends.

## 🛠 Tech Stack

  * **Language**: Python 3.x
  * **Framework**: [Plotly Dash](https://dash.plotly.com/)
  * **Data Manipulation**: Pandas
  * **Database**: SQLite (local development) / MSSQL (production)
  * **Deployment**: Heroku (implied by `Procfile`)

## 🚀 Getting Started

### Prerequisites

Ensure you have Python installed on your system.

### Installation

1.  **Clone the repository**
    ```
    git clone https://github.com/jgeis/DOH doh_plotly
    cd doh_plotly
    ```

2.  **Create a Virtual Environment (Optional but Recommended)**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
    If on Jetstream2
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Database (Choose One)**

    The application supports both SQLite (local) and MSSQL (production). 

    **Option A: SQLite (Local Development - Default)**
    
    Create a `.env` file:
    ```bash
    cp .env.example .env
    ```
    
    Edit `.env` to ensure SQLite is selected:
    ```bash
    USE_MSSQL=false
    SQLITE_DB_PATH=DOH_AMHD_NO_PII.db
    ```

    **Option B: MSSQL (Production/Testing)**
    
    Edit `.env` with your MSSQL credentials:
    ```bash
    USE_MSSQL=true
    DB_SERVER=your-server.database.windows.net
    DB_NAME=your_database_name
    DB_USER=your_username
    DB_PASSWORD=your_password
    DB_DRIVER={ODBC Driver 17 for SQL Server}
    ```

### Database Setup

**For SQLite (Local):**

If the `DOH_AMHD_NO_PII.db` file is missing or needs to be refreshed with the latest CSV data:

If on Jetstream2, get the data files:
```
scp /Users/jgeis/Work/DOH/plotly/discharge_data_view_diag_mh.csv insert-username-here@insert-ip-address-here:/home/exouser/doh_plotly
```

```bash
source venv/bin/activate
python create_db.py
```

*This script will read the source CSV files and populate the SQLite database.*

Output should be: "✅ Database tables created successfully in SQLite"

*This will create tables in your local database and populate them from the CSV files.*

Output should be: "✅ Database tables created successfully"

### Test Database Connection

Verify your database connection is working:

```bash
python -c "from db_utils import test_connection; test_connection()"
```

**Expected output for SQLite:**
```
[db_utils] Testing SQLite connection...
[db_utils] Connected successfully!
[db_utils] SQLite version: 3.x.x
```

**Expected output for MSSQL:**
```
[db_utils] Testing MSSQL connection...
[db_utils] Connected successfully!
[db_utils] SQL Server version: ...
```

## 🏃‍♂️ Usage

### Run the Desktop Dashboard

To run the main multi-dashboard application locally:

```bash
source venv/bin/activate
nohup python run_dashboard.py > logfile.log 2>&1 &
```

send to background
```bash
Ctrl-Z
bg
```

Or directly (may cause comm errors in Anaconda):
```bash
python multi_dashboard.py
```

### Run the Mobile-Optimized Dashboard

To run the mobile-responsive version with optimized layouts:

```bash
python run_mobile.py
```

Or directly (may cause comm errors in Anaconda):
```bash
python mobile_app.py
```

### Access the Application

Open your web browser and navigate to `http://127.0.0.1:8050/` to view the dashboard.

**Note:** If you're in an Anaconda environment, always use the `run_dashboard.py` or `run_mobile.py` wrapper scripts to avoid Jupyter comm compatibility errors.

### Production Server


**currently hosted at:**
https://jetstream2.exosphere.app/exosphere/projects/e547d834b2fe4beda5061b60dfc9df1b/regions/IU/servers/80d60dfa-f665-448e-aa91-2599dabe67ae


### Follow previous instructions to get plotly running.

Copy files over from local to remote, do following on local machine:   
```bash
cd /Users/jgeis/Work/DOH/plotly/data

scp discharge_data_view_demographics.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/

scp discharge_data_view_diag_mh.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/

scp discharge_data_view_diag_su.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/

scp dose_data.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/

scp sudors_data_view_demographics\$.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/

scp sudors_data_view_diag_su\$.csv exouser@149.165.153.166:/home/exouser/doh_plotly/data/
```


**back on remote machine**  
```bash
sudo apt update  
sudo apt install nginx  
sudo apt install python3-gunicorn
sudo mv /home/exouser/doh_plotly/dash_app /etc/nginx/sites-available/
sudo vi /etc/nginx/sites-available/dash_app
```
verify dash-app file looks like this and has the correct server address (or ip address if not doing ssl certificate):
```bash
server {
    listen 80;
    server_name doh-plotly.asc190026.projects.jetstream-cloud.org;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**set up certificate**  
```bash
sudo snap install --classic certbot
sudo certbot --nginx -d doh-plotly.asc190026.projects.jetstream-cloud.org
```

**start nginx**  
```bash
sudo ln -s /etc/nginx/sites-available/dash_app /etc/nginx/sites-enabled
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

**If I do need gunicorn, use this:**  
-- I didn't even start gunicorn and it seems to work.  Good enough for the proof of concept I'm going for right now.  
```bash
gunicorn multi_dashboard:server --bind 127.0.0.1:8050
gunicorn --certfile=/etc/letsencrypt/live/doh-plotly.asc190026.projects.jetstream-cloud.org/fullchain.pem --keyfile=/etc/letsencrypt/live/doh-plotly.asc190026.projects.jetstream-cloud.org/privkey.pem --error-logfile=gunicorn_errors.log multi_dashboard:server --bind 127.0.0.1:8050
```


## 📊 Data Sources

The application visualizes data related to:

  * **discharge_data_view_demographics**: Patient demographic breakdowns.
  * **discharge_data_view_diag_su**: Specific focus on substance use (`diag_su`) and polysubstance occurrences.

## ☁️ Deployment

This project includes a `Procfile`, making it ready for deployment on platforms like **Heroku**.

### Deploy to Heroku

1.  **Create a new Heroku app**
    ```bash
    heroku create your-app-name
    ```

2.  **Set environment variables for MSSQL**
    ```bash
    heroku config:set USE_MSSQL=true
    heroku config:set DB_SERVER=your-server.database.windows.net
    heroku config:set DB_NAME=your_database_name
    heroku config:set DB_USER=your_username
    heroku config:set DB_PASSWORD=your_password
    heroku config:set DB_DRIVER="{ODBC Driver 17 for SQL Server}"
    ```

3.  **Deploy the application**
    ```bash
    git push heroku main
    ```

4.  **Verify the deployment**
    ```bash
    heroku logs --tail
    ```

The application will automatically use MSSQL in production when `USE_MSSQL=true` is set.

## 🔄 Switching Between Databases

The application seamlessly switches between SQLite and MSSQL based on the `USE_MSSQL` environment variable:

### Local Development (SQLite)
- Set `USE_MSSQL=false` or leave unset in `.env`
- Uses local `DOH_AMHD_NO_PII.db` file
- No MSSQL credentials needed

### Production/Testing (MSSQL)
- Set `USE_MSSQL=true` in `.env` or Heroku config
- Provide MSSQL connection credentials
- Same codebase works for both environments

**Key Benefits:**
- ✅ No code changes needed to switch databases
- ✅ Develop locally with SQLite, deploy to MSSQL
- ✅ Automatic database selection based on environment
- ✅ All dashboard files use unified `db_utils.execute_query()` function

## � Mobile Responsive Design

The application automatically adapts between desktop and mobile views to provide an optimized experience on all devices.

### How Mobile Views Work

**1. Automatic Detection**
- When the page loads, JavaScript checks the browser window width
- **< 768px** (Bootstrap's "md" breakpoint) = Mobile mode activated
- **≥ 768px** = Desktop mode

**2. Shell Swapping**
The entire app layout changes based on screen size:
- **Desktop Shell**: Uses standard horizontal tabs for navigation
- **Mobile Shell**: Uses segmented button controls wrapped in a `.mobile-root` class

**3. Responsive Layout Factory**
Each dashboard module (`app_alt.py`, `polysubstance_dashboard.py`, `polysubstance_alt.py`) implements a `layout_for(is_mobile=False)` function that adjusts chart heights:
- **Mobile**: Viewport-relative heights (e.g., `60vh`) for better scrolling
- **Desktop**: Fixed pixel heights (e.g., `400px`) for consistent layout

**4. CSS Media Queries** (`assets/mobile.css`)
Mobile-specific styles activate when both conditions are true:
- Screen width < 768px
- Element is inside `.mobile-root` wrapper

Key mobile optimizations:
- ✅ **Columns stack vertically** (100% width) instead of side-by-side
- ✅ **Tables scroll horizontally** to prevent squishing
- ✅ **Input font size = 16px** to prevent iOS auto-zoom
- ✅ **Touch-friendly buttons** with minimum 44px height
- ✅ **Tighter padding** (8px) for more screen space
- ✅ **Scaled-down Plotly toolbar** (90%) for mobile screens

**5. Dynamic Page Rendering**
Content updates automatically when:
- User switches tabs/pages
- Screen size triggers mode change
- Dashboard calls appropriate `layout_for(is_mobile)` method

**6. Viewport Meta Tag**
Proper mobile configuration ensures correct rendering:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
```

### Testing Mobile Views

**Using `mobile_app.py`:**
```bash
python mobile_app.py
```
Then resize your browser window below 768px or use browser DevTools device emulation.

**Using `multi_dashboard.py`:**
The standard dashboard is desktop-focused. Use `mobile_app.py` for full mobile optimization.

### Key Files for Mobile Support

- **`mobile_app.py`**: Mobile-optimized entry point with responsive shell swapping
- **`assets/mobile.css`**: Mobile-specific CSS with media queries
- **Dashboard modules**: Each has `layout_for(is_mobile)` for adaptive layouts

## �📂 Project Structure

  * **`app.py` / `app_alt.py`**: Main application entry points.
  * **`multi_dashboard.py`**: Likely the container for handling multiple dashboard views.
  * **`polysubstance_dashboard.py`**: Dashboard specific to analyzing polysubstance use data.
  * **`creative_dashboard.py`**: Dashboard containing creative/experimental visualizations.
  * **`create_db.py`**: Script to initialize and populate the SQLite database from source CSVs.
  * **`DOH_AMHD_NO_PII.db`**: SQLite database storing the processed discharge data.
  * **`assets/`**: Contains static assets (CSS, images) for the Dash application.
  * **`queries.sql`**: SQL queries used for data extraction and transformation.

## File Structure

### Core Application Files

**`multi_dashboard.py`** - Main application entry point. Creates the Dash app with tabbed navigation between different dashboard views (Discharges, Polysubstance, and optionally Co-occurring). Uses Bootstrap styling and keyboard shortcuts for accessibility.

**`app_alt.py`** - "Discharges (Alt Views)" dashboard page. Displays discharge data related to substance use with various views and interactive graphs. Contains its own layout and callbacks.

**`polysubstance_dashboard.py`** - "Polysubstance Use" dashboard page. Analyzes patients with multiple substance use diagnoses. Includes filtering, charts, and data tables focused on polysubstance patterns.

**`mobile_app.py`** - Mobile-optimized version of the dashboard. Safely imports other dashboard modules and adapts the layout for smaller screens with custom CSS.

**`creative_dashboard.py`** - Alternative creative/experimental dashboard implementation. Uses custom theming and provides different visualizations of the same data.

**`app.py`** - Early/basic dashboard version. Loads data and performs comparisons between distinct counts and raw counts, analyzes duplicates in the data.

### Data & Database Files

**`create_db.py`** - Database initialization script. Loads two CSV files (`discharge_data_view_diag_su.csv` and `discharge_data_view_demographics.csv`), renames columns, and creates database tables (`discharge_data_view_diag_su` and `discharge_data_view_demographics`). Automatically uses SQLite or MSSQL based on configuration.

**`config.py`** - Database configuration module. Manages environment variables and connection settings for both SQLite and MSSQL. Determines which database to use based on `USE_MSSQL` environment variable.

**`db_utils.py`** - Database utility functions. Provides unified interface for database operations that works with both SQLite and MSSQL. Contains `execute_query()`, `get_connection()`, and `test_connection()` functions.

**`queries.sql`** - Centralized SQL query repository. Contains named SQL queries used throughout the application (e.g., `load_discharge_data_view_diag_su`, `load_polysubstance_data`, `count_by_sex_distinct`). Keeps SQL separate from Python code for easier maintenance.

**`DOH_AMHD_NO_PII.db`** - SQLite database (created by `create_db.py` when using local mode) containing the discharge data tables.

**`.env`** - Environment configuration file (not committed to git). Contains database credentials and configuration. Copy from `.env.example` to get started.

**`.env.example`** - Template for environment variables. Shows all available configuration options for both SQLite and MSSQL.

**`discharge_data_view_diag_su.csv`** - Source data file containing diagnosis/substance use information (record_id, substance, etc.).

**`discharge_data_view_demographics.csv`** - Source data file containing patient demographics (record_id, county, city, age_group, sex, year, etc.).

### Utility & Helper Files

**`theme.py`** - Custom Plotly theme configuration. Defines colors, fonts, backgrounds, and styling for all charts. Creates a consistent "doh" template used across dashboards.

**`inspect_columns.py`** - Utility script to inspect and clean CSV column names. Helps verify the structure of the source data files.

**`run_dashboard.py`** - Wrapper script to fix Jupyter/comm compatibility issues in Anaconda environments. Patches the `comm.create_comm` function before importing Dash to prevent `NotImplementedError`. Use this to run `multi_dashboard.py` in Anaconda.

**`run_mobile.py`** - Wrapper script for mobile-optimized dashboard. Patches comm module before importing `mobile_app.py`. Use this to run the mobile-responsive version in Anaconda.

**`run_app.py`** - Alternative wrapper script (less successful version of `run_dashboard.py`).

### Deployment & Configuration Files

**`Procfile`** - Heroku deployment configuration. Specifies how to run the app in production using gunicorn: `web: gunicorn multi_dashboard:server`.

**`runtime.txt`** - Specifies Python version (3.11.9) for Heroku deployment.

**`requirements.txt`** - Python dependencies list: dash, dash-bootstrap-components, plotly, pandas, numpy, gunicorn.

**`README.md`** - Project documentation with setup and run instructions.

### Assets (CSS)

**`assets/tabs.css`** - Custom styling for tab navigation with brand colors, hover effects, and responsive design.

**`assets/mobile.css`** - Mobile-specific CSS rules that adjust grid layout and component sizing for screens under 768px wide.

Here is a documentation draft for your `README.md` file. It is based on the file structure (e.g., the `assets` folder and `Procfile` strongly suggest a Plotly Dash application) and the data filenames found in your repository.



### TODO
* do I need gunicorn?
* add <11 filters
* 


### NOTES
## To download MSSQL Tables while accounting for commas in data
Use the export_table.py script: 

& c:/Users/jgeis/DOH/doh_plotly/venv/Scripts/python.exe c:/Users/jgeis/DOH/doh_plotly/export_table.py
