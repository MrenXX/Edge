# Unit Conversion Engine for Part 2 - Eco-Edge
# Converts heterogeneous energy units to canonical kWh

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

@dataclass
class ConversionResult:
    original_value: float
    original_unit: str
    converted_value_kwh: float
    factor_used: float
    factor_source: str
    notes: Optional[str] = None

class ConversionEngine:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = "C:/Users/sl3ag/Downloads/edge/part2/pipeline/config/conversions.yaml"
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        if self.config_path.exists():
            self._config = self._parse_yaml(self.config_path.read_text())

    def _parse_yaml(self, content: str) -> Dict[str, Any]:
        result = {}
        current_key = None
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key, value = key.strip(), value.strip()
                if key == 'conversions':
                    result[key] = {}
                    current_key = key
                elif key in ['pcs_factors', 'bill_overrides', 'tolerances']:
                    result[key] = {}
                    current_key = key
                elif current_key in result:
                    if value:
                        try:
                            result[current_key][key] = float(value) if '.' in value else int(value)
                        except:
                            result[current_key][key] = value
        return result

    def convert(self, value: float, unit: str, pcs: Optional[float] = None, bill_override: Optional[str] = None) -> ConversionResult:
        unit = unit.upper()
        if unit == 'TH':
            return ConversionResult(value, 'TH', value * 1.163, 1.163, 'default')
        elif unit == 'NM3':
            if pcs is None:
                pcs = self._config.get('pcs_factors', {}).get('default', 10.079)
            return ConversionResult(value, 'NM3', value * pcs * 1.163, pcs * 1.163, 'default', 'PCS=' + str(pcs))
        elif unit in ['MWH', 'GWH', 'GJ', 'GCAL', 'BTU', 'TOE']:
            f = {'MWH': 1000, 'GWH': 1e6, 'GJ': 0.277778, 'GCAL': 1163, 'BTU': 0.000293071, 'TOE': 11630}.get(unit, 1)
            return ConversionResult(value, unit, value * f, f, 'default')
        else:
            return ConversionResult(value, unit, value, 1, 'unknown', 'Unknown: ' + unit)

    def validate_th_nm3(self, th: float, nm3: float, pcs: float) -> Dict[str, Any]:
        calc = nm3 * pcs
        dev = abs(th - calc) / calc * 100 if calc else 0
        return {'is_valid': dev <= 2, 'deviation': dev, 'calculated_th': calc, 'th_printed': th}