# Visual food inflation - Sample Dash App
This folder contains a minimal **Dash application** that demonstrates how to visualize the processed sample inflation data produced by the preprocessing pipeline.
## Folder structure
preprocessing_mini_sample/
├─ sample_data/ # Output files created by the preprocessing pipeline
│ ├─ country-year_mean.csv
│ ├─ Inflation_2001.geojson
│ └─ Inflation_2002.geojson
│
├─ app/
│ ├─ sample_app.py # Dash application
│ ├─ requirements.txt # Dependencies for running the app
│ └─ README.md # This file
## ️ How to Run the app

You can run the app **locally**, on **Binder**, or on **Google Colab**. The app expects the data in `../sample_data/` relative to `app/sample_app.py`.

### A) Run Locally (macOS / Linux / Windows)
1. **Open a terminal at the repo root, then go into the app folder:** 
 ```bash
cd preprocessing_mini_sample/app
```
2. **Recommended: Create a virtual environment**
 
 macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
 Windows (PowerShell):
```bash
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```
3. **Install dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
4. **Run the app**
 ```bash
python sample_app.py
```
5. **Open the app**
The app will start a local server (default http://127.0.0.1:8050/).
Open this link in your browser to interact with the dashboard.

## B) Run on Binder
Binder lets you run the app entirely in the cloud, no install needed.
1. **Click the Binder badge below.**
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Soph231/Food_inflation_visualization/HEAD?labpath=preprocessing_mini_sample%2Fapp%2FRun_App_in_Binder.ipynb)

2. **Wait while Binder builds your environment (this can take 1–5 minutes the first time).**
Once ready, it will automatically proxy port 8050 and open the Dash app in your browser.
3. Run the codes in the note book. After the app is started successfuly server links will be provided, copy and paste
the default http://127.0.0.1:8050/

## C) Run on Google Colab
Open the Run_App_in_Colab.ipynb by following the link below, run the code in the cells to get a public app server
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soph231/Food_inflation_visualization/blob/main/preprocessing_mini_sample/app/Run_App_in_Colab.ipynb)

## Note:
Binder sessions are temporary (they reset when you close the tab or after ~10 minutes idle). For quick demos this is fine — for longer work, preferably run locally or use Colab.

**App Default behavior**
The app automatically scans ../sample_data/ for available Inflation_*.geojson files.

A year dropdown is populated dynamically.

By default, the most recent year (e.g., 2002 in this sample dataset) is displayed.
### Notes
This sample uses a very small dataset (AUS and NZ for 2001–2002).

For full-scale usage, generate yearly GeoJSON files and CSV summaries with the preprocessing pipeline notebook (Inflation_data_preprocessing_pipeline_example.ipynb).

The app code is path-relative, so it will continue to work if this folder is renamed (e.g., from preprocessing_mini_sample/ → sample_pipeline/).
