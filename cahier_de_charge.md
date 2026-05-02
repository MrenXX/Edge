**Re·Tech Fusion**

_Industrial AI & IoT Hackathon Challenge_

INSAT - University of Carthage

_This document is the official challenge specification. Teams are free to use any technology, language, or methodology to solve each part. The recommendations herein are suggestions, not requirements. Innovation is always rewarded._

# Challenge Overview

Industrial companies manage multiple sites, acquired subsidiaries, and heterogeneous energy data. Today, consolidating energy data for CO2 emission calculations is slow, manual, error-prone, and not scalable. This challenge asks teams to build an end-to-end intelligent system: from raw IoT sensor data all the way to predictive modeling, anomaly detection, and actionable insights.

The challenge is structured across three progressive parts and a final pitching session. Parts 2 and 3 are announced simultaneously on Day 2, giving teams full visibility to plan their architecture. Part 1 focuses on building and connecting IoT infrastructure. Parts 2 and 3 can be tackled in parallel.

| **Timeline**   | **Details**                                               |
| -------------- | --------------------------------------------------------- |
| Teams          | 5 members per team                                        |
| Day 1 - 14:00  | Opening Ceremony                                          |
| Day 1 - 23:00  | Part 1 Announcement                                       |
| Day 2 - 14:00  | Part 1 Submission Deadline                                |
| Day 2 Midnight | Part 2 Submission Deadline + Part 3 Announcement          |
| Day 3 - 05:00  | Part 3 Submission Deadline + Start of 1-Hour Grace Period |
| Day 3 - 07:00  | Presentation Submission Deadline                          |
| Day 3 - 09 :00 | Start of Pitching Part                                    |

**Teams are encouraged to prioritize depth over covering all features.**

The core of the challenge is document extraction, unit normalization, and CO₂ estimation.  
CHECK Prizes and scoring to undestand full vision .

**Part 1 - IoT Device & Protocol**

_Announced Day 1 at 23: - Deadline Day 2 at 14:00_

## Objective

Build a connected device or software client that reads data from multiple sensors and transmits it reliably, securely, and continuously to a server (in one of participants pc's). Your device is the starting point of the entire data pipeline used in Parts 2 and 3.

## What to Deliver

- A physical IoT device (e.g. ESP32, arduino with bleuthooth/wifi module, lora based cards ) reads from preferably 3 distinct sensor types (e.g. CO<sub>2</sub>, temperature, power consumption, humidity, pressure, distance , IMU …) that sends data continuously to a server (HTTP POST or MQTT) .
- Handling disconnection and reconnects automatically without data loss is an advantage .  
   making something similar to the factory's documentation needs is also an advantage
- Includes a README documenting your setup, sensor types, and connection method.  
   simualting workflow .

## Evaluation Criteria

| **Criterion**                   | **How it is measured**                                                                                        | **Points**  |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----------- |
| Solution delivered & functional | Server receives valid data in a precised timeframe . from a sensor.                                           | **30 pts**  |
| Multi-sensor coordination       | Distinct sensor types with correct units, all active simultaneously                                           | **25 pts**  |
| Protocol design & security      | reconnection handling, optional TLS/HTTPS                                                                     | **15 pts**  |
| Uptime & continuity             | Percentage of 5-minute windows with at least 1 valid message received                                         | **15 pts**  |
| Data quality                    | Percentage of values within physically valid ranges (no null, no -999)                                        | **10 pts**  |
| Bonus - Innovation              | OTA update, device-side buffering, custom sensors . <br>anything that's unique and still aligning with schema | **+15 pts** |

|     | **\>> Hardware Note**<br><br>See whats availabe in the stand and ask and we would try to provide what you need for your innovation ! |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ |

### Possible tools & libraries

- Arduino / ESP-IDF /
- paho-mqtt (Python) - MQTT client for software simulator
- ArduinoJson - JSON serialization on microcontrollers
- Postman / curl - test your endpoint before wiring hardware

**Part 2 - Data Pipeline, Unification & Modeling**

_Deadline Day 3 at 00:00 (25hours)_

## Context & Objective

Industrial energy data is heterogeneous: different suppliers, different document formats (PDF invoices, scanned bills, Excel tables), and different measurement units. Combined with the IoT sensor data from Part 1, teams must build a coherent data pipeline that unifies everything, enables CO<sub>2</sub> emission estimation, detects sensor faults and anomalies, and presents results through a functional interface.

## Test Dataset (distributed at 00 :00)

Each team receives the same standardized test dataset containing:

- An amount of heterogeneous energy documents: PDF invoices, scanned bills, multi-sheet Excel files…
- Documents use mixed units: kWh, MWh, Gcal, BTU, toe, GJ all must be normalized to one unit
- A ground-truth annotation file for prediction model validation
- IoT readings from Part 1 datacollection //maybe we should measure it ourselves for ground truth and common ground )
- anomalies hidden in the values dataset detection is scored (// optional )

## What to Deliver

### 2.1 - Data extraction & unification pipeline

- Automatic extraction of key fields from all document types: date, energy quantity, unit, supplier, site,
- Unit normalization to a single canonical unit (kWh recommended) with traceable conversion factors
- **Merging of document data with IoT sensor data(taken from part 1) into a unified, timestamped framework dashboard oriented business layer (showing key kpis gain loss anomlies ect).**
- Pipeline must be reproducible: documented steps, no manual interventions .

### 2.2 - CO<sub>2</sub> emission & energy modeling

- Estimation of CO<sub>2</sub> emissions from unified energy data using emission factors
- Energy trend forecasting: at minimum short-term prediction, ideally multi-horizon

### OPTIONAL ;1/ Anomaly & fault detection

- Detection of sensor faults (e.g. stuck sensor, spike, dropout, drift) in the IoT data stream
- Detection of anomalous energy consumption patterns in document data
- Each detected anomaly must include: type, timestamp, sensor/site, confidence score

### 3 / Interface & dashboard

- Visual dashboard showing unified data, CO<sub>2</sub> KPIs, trends, and detected anomalies
- Any technology accepted: Grafana, React, Streamlit, plain HTML - functionality over aesthetics
- Dashboard must be working and can be tested live

## Scoring

| **Criterion**                | **Measurement method**                                           | **Points**  |
| ---------------------------- | ---------------------------------------------------------------- | ----------- |
| Document extraction accuracy | score across all test documents                                  | **40 pts**  |
| Unit normalization accuracy  | Accuracy on conversions prepared by organizers via global values | **25 pts**  |
| Bonus Anomaly detection      | Anomaly detection in the data with ground truth                  | **+15 pts** |
| CO2 estimation quality       | Prediction vs organizer reference values (ground truth)          | **15pts**   |
| Dashboard quality            | Jury evaluation: clarity, relevance, usability                   | **20 pts**  |
| Dockerized pipeline          | docker compose up works from cold start, API documented          | **20 pts**  |
| Bonus Innovation             | Novel algorithm, creative visualization, additional data sources | **+25 pts** |

## Submission

Teams must submit via at least one of the following methods:

- GitHub repository with README, code, and a short demo video or screenshots
- Submission endpoint on the challenge platform: POST your extraction results as JSON platform returns F1 scores instantly  
   same with anomaly /co2 estiomate
- Live demo URL if the service is deployed

Minimum expected solution ;  
\-Basic extraction from at least one document type (PDF or Excel)

\-Correct unit normalization to kWh

\- A simple Dashboard

**Side note ; sometimes the best models results are just algorithmic/ science inspired methods rather then sophisticated models feel free to test , learn and apply and don't be afraid of the evaluation**

**Part 3 - Edge Intelligence or Energy Recovery Design**

_Two tracks: choose one or attempt both_

## Overview

Part 3 has two tracks. Teams choose the one that best fits their skills, or attempt both for maximum points. Both tracks address the same real-world need: resilience and sustainability at the edge of industrial systems.

**Track A : Edge Inference & On-Device Anomaly Detection**

_Deploy your model on the device itself. No cloud required._

### Objective

When the network connection fails, the IoT device must continue operating intelligently. Teams build a lightweight model that runs entirely on the microcontroller: it predicts sensor values from recent history, detects anomalies locally, and gracefully resumes cloud sync when reconnected.

### What to deliver

- A trained predictive model compressed and deployable on constrained hardware (ESP32, RPi Zero, or emulated)
- Model size under card constaints (RAM…)
- Inference latency under 200ms on device
- Demonstrated local anomaly detection: device flags anomalies without server contact
- Evidence of deployment: photo, video, or emulator log showing model running on target hardware + posssibe on place testing

| **Criterion**                      | **Measurement method**                                                            | **Points**  |
| ---------------------------------- | --------------------------------------------------------------------------------- | ----------- |
| Model size constraint met          | Binary check                                                                      | **15 pts**  |
| Inference latency on device        | Measured average by tools like logs /TYPuinferences on target hardware            | **10 pts**  |
| Prediction accuracy (MAE ratio)    | Pc live simulation held-out sequence from Part 2 data maybe broken sensor testing | **25 pts**  |
| Working model visible and teteable | Continuity of service and working solution.                                       | **25 pts**  |
| Bonus - Multi-sensor model         | Single model predicting multiple sensor types simultaneously                      | **+15 pts** |

**Track B : Waste Heat Recovery Opportunity Design**

_Conceive and prioritize an energy recovery solution for an industrial site._

### Objective

Industrial sites lose a significant fraction of energy as waste heat: from process fumes, compressors, cooling systems, and thermal equipment. Most recovery opportunities are never exploited because they are poorly identified and not economically prioritized. Teams design a method or tool to systematically identify, characterize, and rank heat recovery opportunities.

### What to deliver

- A systematic method or tool to identify waste heat sources from site data (documents, sensors, process descriptions)
- Characterization of each source: temperature level, thermal flux, availability profile, location
- A prioritization framework with scored criteria: recoverable energy potential, CO₂ reduction, integration complexity, implementation cost, return on investment
- At least 3 concrete recovery scenarios with quantified impact estimates
- Any format accepted: tool, decision model, scored spreadsheet with methodology, or a designed software prototype

| **Criterion**                                 | **Measurement method**                                             | **Points**  |
| --------------------------------------------- | ------------------------------------------------------------------ | ----------- |
| Source identification completeness            | Coverage and accuracy of waste heat sources identified             | **20 pts**  |
| Prioritization framework quality and solution | Multi-criteria model: rigor, weighting justification, usability    | **25 pts**  |
| Quantified impact estimates                   | Energy, CO2, and ROI figures with traceable calculations           | **20 pts**  |
| Deliverable quality                           | Clarity, reproducibility, practical applicability                  | **10 pts**  |
| Bonus \*Interactive tool                      | Working prototype (simulation , notebook, mathemathical evidence ) | **+15 pts** |

**Pitching Session - Top Teams**

_Day 3 starting at 08:30 - 15 minutes per team (8 min presentation + 7 min Q&A)_

## Format

The top teams (determined by combined Part 1 + 2 + 3 scores after the 05:00 freeze) present their complete solution to the jury. This session rewards coherence, clarity of thought, and depth of understanding over raw technical output.

| **Section**        | **Content expected**                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| 8 min presentation | Problem framing, architecture overview, key design decisions, what you would do with more time |
| 7 min Q&A          | Jury questions on technical choices, failure modes, scalability, and business applicability    |

## Evaluation Criteria

| **Criterion**                      | **What jury evaluates**                                             | **Points** |
| ---------------------------------- | ------------------------------------------------------------------- | ---------- |
| Technical depth +jury decision     | Understanding of algorithms, trade-offs, and failure modes          | **35 pts** |
| Scalability & industrial relevance | Would this work at real scale? Does it address the sponsor's needs? | **25 pts** |

|     | **\>> What makes a great pitch in this challenge**<br><br>Show the data flowing end-to-end: device → server → pipeline → dashboard → anomaly alert in one continuous demo<br><br>Quantify everything: uptime %, F1 score, model size in KB, CO2 kg saved. Numbers build credibility.and HOW MUCH MONEY IS ON THE TABLE.<br><br>Acknowledge what broke and how you fixed it - juries trust teams who understand their own limits<br><br>Connect your solution to the sponsor's actual problem: heterogeneous formats, scalability |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

# Rules

- Teams up to 5 participants (preferably). No cross-team collaboration on code or models.
- All code must be original or use open-source libraries with compatible licenses **. Use of LLMs is permissible as long you take accountability of the results .**
- All submissions must be pushed to the platform or GitHub before 05:00 on Day 3. Late submissions receive a 20% penalty per hour, Per part.
- Teams are responsible for their own network access, power, and hardware reliability.