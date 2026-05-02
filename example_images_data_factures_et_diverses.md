# DATASET CONTEXT: Provided Image Samples (Parts 2 & 3)
**Client / Factory Name:** SOCIETE ADWYA (This is the target pharmaceutical factory).
**Objective:** Contextualize the raw data formats provided for Document Extraction, Unit Normalization, and Anomaly Detection.

## 1. Grid Electricity Document (STEG - Achat et Vente)
**Type:** Meter Reading Sheet for Energy Purchase and Sale (September 2025).
**Hackathon Target:** Part 2 (Document Extraction & Pipeline).
*   **Context:** Because the factory has a Tri-generation system, they both *consume* from and *inject* into the grid.
*   **Data Structure:** 
    *   Split into "Achat" (Purchase) and "Vente" (Sale/Injection).
    *   Uses 4-time-slot tariffs: `Jour` (Day), `Pointe` (Peak), `Soir` (Evening), `Nuit` (Night).
    *   Tracks both Active Energy and Reactive Energy (`Réactive`).
*   **Extraction Challenge:** Extracting tabular data comparing `Ancien` (Old) and `Nouveau` (New) indices across 3 different physical meters (`N°CTR` registers).

## 2. SCADA / HMI Alarm Log (Digital Screen)
**Type:** Export/Screenshot of the Tri-generation & Chiller Alarm System (April 2026).
**Hackathon Target:** Part 2 (Anomaly Detection) & Part 3 Track A (Edge Inference/Predicting Failures).
*   **Context:** This is raw log data from the factory's embedded systems showing live faults.
*   **Key Anomalies for AI Model to Detect:**
    *   `OVERFLOW_TEMP_HIGH (Chiller)`: Critical thermal anomaly in the cooling loop.
    *   `T4xx.2 Act. Combustion chamber - too low (S)`: Heat/combustion failure in the gas engine.
    *   `ABSO_PUMP_NOT_RESPOND (Chiller)`: Physical pump failure.
    *   `WCCRT... Connection GAMMA disconnected`: IoT/Networking communication failure to the Gamma zone.

## 3. Water Bill (SONEDE)
**Type:** Scanned Paper Water Invoice (Feb 2023).
**Hackathon Target:** Part 2 (Document Extraction & Normalization).
*   **Context:** Water is heavily used for the factory's steam boilers and chiller cooling towers.
*   **Data Structure:**
    *   Billed in Cubic Meters (`m³`). Example extraction: `3633 m³`.
    *   Split into two costs: `Frais consommation eau` (Consumption) and `Frais assainissement` (Sanitation/Wastewater). 

## 4. Natural Gas Bill (STEG - Facture Mensuelle Gaz)
**Type:** Monthly Gas Invoice (May 2024).
**Hackathon Target:** Part 2 (Unit Normalization & CO2 Estimation).
*   **Context:** This is the primary energy source (fuels the Tri-generation plant and the 2 Steam Boilers).
*   **Validation Check:** The document shows `DEBIT SOUSCRIT: 6000`. This perfectly matches the PDF audit stating a "6000 th/h" detente rampe subscription.
*   **Normalization Challenge:** The bill tracks physical volume in Normal Cubic Meters (`NM3` - e.g., 204,884 NM3), but prices and measures energy in Thermies (`TH` - e.g., 1,782,471 TH), utilizing a correction factor (`PCS` / Facteur de correction). 
*   **Action Required:** Your pipeline must automatically extract `NM3` or `TH` and **normalize it to `kWh`** to unify the dashboard and calculate accurate CO2 emissions based on gas combustion factors.