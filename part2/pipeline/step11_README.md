# Step 11: Unit Normalization (25 pts)

## Overview
Converts heterogeneous energy units (TH, NM3, MWh, GWh, GJ, Gcal, BTU, toe) to canonical **kWh**.

## Files
```
part2/pipeline/
├── config/
│   └── conversions.yaml    # Conversion factors
└── core/
    └── conversion_engine.py # Engine implementation
```

## Usage
```python
from core.conversion_engine import ConversionEngine

engine = ConversionEngine()

# TH (Thermie) → kWh
result = engine.convert(1782471, 'TH')
print(result.converted_value_kwh)  # 2,073,013 kWh

# NM3 (gas volume) → kWh with PCS factor
result = engine.convert(204884, 'NM3', pcs=10.079)
print(result.converted_value_kwh)  # 2,401,625 kWh

# Validate TH matches NM3 × PCS
validation = engine.validate_th_nm3(1782471, 204884, 10.079)
print(validation)  # {'is_valid': False, 'deviation': 13.68%}
```

## Supported Units
| Unit | Factor → kWh | Notes |
|------|--------------|-------|
| TH | ×1.163 | Thermie (gas billing) |
| NM3 | ×PCS×1.163 | Normal cubic meters |
| MWh | ×1000 | |
| GWh | ×1,000,000 | |
| GJ | ×0.277778 | |
| Gcal | ×1163 | |
| BTU | ×0.000293071 | |
| toe | ×11,630 | |

## Key Points
- **Canonical unit: kWh** (per cahier_de_charge.md)
- **TH is authoritative** when printed on gas bill
- Default PCS factor: 10.079 (Tunisian standard)
- Validation tolerance: ±2% deviation allowed

## Test Data (from example_images_data_factures_et_diverses.md)
- Gas bill May 2024: 204,884 NM3, 1,782,471 TH, PCS 10.079
- Expected: TH × 1.163 = ~2,072,913 kWh