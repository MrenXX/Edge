# KNOWLEDGE BASE: Factory Energy Audit (2024-2025)
**Industry:** Pharmaceutical (Human Medicine)
**Context:** Real-world data to be used as the target client for the "Re·Tech Fusion" Hackathon.

## 1. TARGET FOR PART 1: IoT DEVICE & PROTOCOL
*The factory lacks complete smart monitoring. Build the IoT solution around these specific missing links:*
*   **Target A (Boiler Monitoring):** The 2 Steam Boilers (1240 kW & 600 kW) have physical Gas and Steam meters installed, but **they are NOT connected to the central management system (GTE)**. 
*   **Target B (Cleanroom Environment):** Pharmaceutical cleanrooms (Zone Beta/Alpha/Gamma) require strict climate control. 
    *   **Constraint:** Temperature must be strictly maintained at `22°C +/- 3°C`.
    *   **Sensors Needed:** Temperature, Humidity (controlled by "Munters" systems), Power consumption.

## 2. TARGET FOR PART 2: DATA PIPELINE & UNIFICATION (ETL & AI)
*The pipeline must normalize heterogeneous data to `kWh` and calculate CO2.*
*   **Grid Electricity (STEG):** 30 kV HTA, 1300 kVA subscribed power. Billed on a "4-time-slot" pricing regime. (Needs normalization from kVA/Volt to kWh).
*   **Gas Consumption:** Rated in `Nm3/h` (273 Nm3/h for Tri-generation) and `th/h` (6000 th/h subscribed). (Needs normalization to kWh; factory assumes 1860 kW thermal from 273 Nm3/h).
*   **Steam:** 2 boilers outputting in Tons/hour (`T/h`). 
*   **Tri-generation (Local Power):** Produces 1200 kW (Electricity) + 1270 kW (Hot Water at 101°C) + 802 kW (Cooling/Eau Glacée).
*   **Anomaly Target (AI):** Predict grid vs. tri-generation usage based on time-of-day tariffs, or detect anomalies in boiler efficiency.

## 3. TARGET FOR PART 3 (TRACK A): EDGE INTELLIGENCE (Predictive Maintenance)
*Deploy an edge AI model on microcontrollers for critical equipment.*
*   **Target Equipment:** Air Compressors (132 kW & 110 kW). 
*   **Constraint:** Must be "oil-free" (Pharma standard). Operational pressure: 8 bars. 
*   **Edge AI Goal:** Run a local predictive maintenance model (<200ms latency) using dummy vibration/temperature sensors to predict compressor failure or pressure drops before they happen, as an outage ruins pharma production. 

## 4. TARGET FOR PART 3 (TRACK B): WASTE HEAT RECOVERY DESIGN
*The audit explicitly identifies major energy losses. Use these for the 3 required ROI/CO2 recovery scenarios:*
*   **Source 1: Air Compressors (Highest Potential):** Consume 132 kW & 110 kW. **~80% of this electrical energy is lost as heat.** 
*   **Source 2: Tri-Generation Unit:** ~20% of the natural gas consumed is currently lost as unrecovered heat/fumes.
*   **Source 3: Steam Boilers:** 
    *   5% to 10% of natural gas is lost through chimney fumes (no economizers installed).
    *   3% to 5% of thermal energy is lost via steam purges.
    *   Uninsulated valves and boiler bodies cause surface heat loss.
*   **Current Recovery baseline (to improve upon):** The factory currently recovers 161 kWh/h (Hot Water) and 258 kWh/h (Cooling) via plate heat exchangers and absorption chillers.

## 5. PITCH DECK QUANTIFIABLES (For the Jury)
*Use these exact factory specs to calculate hypothetical ROI and CO2 savings:*
*   **Total Transformer Power:** 1680 kVA.
*   **Lighting Load:** 61.41 kW (371,134 kWh/year). 
*   **Cooling Load (Chillers):** 2650 kW electric + 802 kW absorption.
*   **Cost metric:** Grid power carries a fixed power fee of ~78,000 DT/year just for subscription, plus usage. Optimize peak shaving!