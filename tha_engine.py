#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
True Health Age (THA) - Deterministic Hazard->Age Engine (no ML)
- Loads a YAML config with alignment metadata, groups, order, and options.
- Consumes raw form values (strings or numbers) and maps to bins 0..4.
- Computes THA via Gompertz slope (MRDT), with per-domain caps + global clamp.
- Returns domain and item contributions in years, plus group ordering for UI.
"""

import json, math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

try:
    import yaml  
except Exception:
    yaml = None

def gompertz_b(mrdt_years: float) -> float:
    if mrdt_years <= 0:
        raise ValueError("MRDT must be positive")
    return math.log(2.0) / mrdt_years

@dataclass(frozen=True)
class THAResult:
    THA: float
    AgeAccel: float
    domainYears: Dict[str, float]
    itemYears: Dict[str, float]
    algo_version: str
    b: float
    groups: Dict[str, List[str]]

def _score_multiselect(item: Dict[str, Any], selected: List[str]) -> float:
    """
    Score multi-select questions based on selected options and their weights.
    Returns a composite score that will be mapped to bins.
    """
    if not selected:
        return 0.0

    # Check if "None" or "Not sure" is selected alone
    if len(selected) == 1 and selected[0] in ["None", "Not sure", "No"]:
        return 0.0

    # Get scoring weights from config
    weights = item.get("scoring_weights", {})
    if not weights:
        # No weights defined, use count-based scoring
        # Filter out "None" and "Not sure" from count
        valid_selections = [s for s in selected if s not in ["None", "Not sure", "No"]]
        return float(len(valid_selections))

    # Calculate weighted score
    total_score = 0.0
    for option in selected:
        if option in weights:
            total_score += weights[option]

    return total_score

def _raw_to_bin(item: Dict[str, Any], raw: Optional[Union[str, float, int, List]]) -> Optional[int]:
    """Map a raw form value to bin index 0..N based on YAML options or ranges."""
    if raw is None:
        return None

    max_bin = len(item["hr"]) - 1  # Support variable-length HR arrays

    # Multi-select handling (list of selected options)
    if isinstance(raw, list) and item.get("input_type") == "multi_select":
        score = _score_multiselect(item, raw)

        # Map score to bins based on thresholds
        # For family_history and personal_conditions, use count-based mapping
        if item["id"] in ["family_history", "personal_conditions"]:
            # Map score to bins: 0-0.5 = best, 0.5-1.5 = one condition, 1.5-2.5 = several, 2.5+ = many
            if score < 0.1:  # None or "Not sure" only
                return max_bin  # Best bin (rightmost)
            elif score < 0.3:  # One minor condition
                return max_bin - 1
            elif score < 0.6:  # Several conditions or one major
                return max_bin - 2
            else:  # Many conditions
                return 0  # Worst bin

        # Default multi-select mapping
        return min(int(score), max_bin)

    # free text handling (no scoring, just collection)
    if item.get("input_type") == "free_text":
        return None  # Use default HR (1.0)

    # explicit options map (string code -> bin)
    if "options" in item and isinstance(raw, str):
        mapping = item["options"]
        if raw not in mapping:
            raise ValueError(f"Unknown option '{raw}' for {item['id']}")
        return int(mapping[raw])
    # numeric ranges (value -> bin)
    if "options_range" in item and (isinstance(raw, (int, float)) or isinstance(raw, tuple)):
        # Check if this is a gender-specific question
        has_gender_ranges = any("gender" in rng for rng in item["options_range"])

        if has_gender_ranges:
            # Need to get gender from context (passed as tuple: (value, gender))
            if isinstance(raw, tuple) and len(raw) == 2:
                value, gender = raw
            else:
                # Default to male thresholds if gender not specified
                value = raw
                gender = "male"

            for rng in item["options_range"]:
                if rng.get("gender") != gender:
                    continue
                lo = rng.get("min", float("-inf"))
                hi = rng.get("max", float("inf"))
                lo = float("-inf") if lo in ("-inf", None) else float(lo)
                hi = float("inf")  if hi in ("inf", None)  else float(hi)
                if lo <= float(value) <= hi:
                    return int(rng["bin"])
        else:
            # Standard numeric range matching
            for rng in item["options_range"]:
                lo = rng.get("min", float("-inf"))
                hi = rng.get("max", float("inf"))
                lo = float("-inf") if lo in ("-inf", None) else float(lo)
                hi = float("inf")  if hi in ("inf", None)  else float(hi)
                if lo <= float(raw) <= hi:
                    return int(rng["bin"])

        raise ValueError(f"Value {raw} not in any range for {item['id']}")
    # direct bin index (0 to max_bin)
    if isinstance(raw, int) and 0 <= raw <= max_bin:
        return raw
    raise ValueError(f"Cannot interpret answer for {item['id']}: {raw}")

class THAEngine:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.version = cfg.get("algo_version", "THA-unknown")
        self.mrdt_years = float(cfg["mrdt_years"])
        self.b = gompertz_b(self.mrdt_years)
        self.age_clamp_years = float(cfg.get("age_clamp_years", 10.0))
        self.domains = cfg["domains"]
        # sort items by declared order to match UX flow
        self.items = sorted(cfg["items"], key=lambda it: it.get("order", 999))
        # build groups (section -> ordered item ids)
        self.groups: Dict[str, List[str]] = {}
        for it in self.items:
            grp = it.get("group", "ungrouped")
            self.groups.setdefault(grp, []).append(it["id"])
        self._validate()

    def _calculate_bmi(self, height_val: Optional[float], weight_val: Optional[float],
                       height_unit: str = "cm", weight_unit: str = "kg") -> Optional[float]:
        """
        Calculate BMI from height and weight.
        Height can be in cm or inches, weight in kg or lbs.
        Returns BMI value or None if data is missing.
        """
        if height_val is None or weight_val is None or height_val <= 0 or weight_val <= 0:
            return None

        # Convert to metric (cm and kg)
        if height_unit in ["in", "inches"]:
            height_cm = height_val * 2.54
        elif height_unit in ["ft", "feet"]:
            height_cm = height_val * 30.48
        else:
            height_cm = height_val

        if weight_unit in ["lbs", "pounds", "lb"]:
            weight_kg = weight_val * 0.453592
        else:
            weight_kg = weight_val

        # BMI = weight(kg) / (height(m))^2
        height_m = height_cm / 100.0
        if height_m <= 0:
            return None

        bmi = weight_kg / (height_m ** 2)
        return bmi

    def _bmi_to_lnhr(self, bmi: Optional[float]) -> float:
        """
        Map BMI to ln(HR) based on established risk categories.
        BMI categories:
          <18.5: Underweight (HR ~1.20)
          18.5-24.9: Normal (HR 1.00, reference)
          25-29.9: Overweight (HR ~1.15)
          30-34.9: Obese Class I (HR ~1.40)
          35+: Obese Class II+ (HR ~1.80)
        """
        if bmi is None:
            return math.log(1.05)  # Missing data penalty

        if bmi < 18.5:
            return math.log(1.20)  # Underweight
        elif bmi < 25.0:
            return math.log(1.00)  # Normal (reference)
        elif bmi < 30.0:
            return math.log(1.15)  # Overweight
        elif bmi < 35.0:
            return math.log(1.40)  # Obese Class I
        else:
            return math.log(1.80)  # Obese Class II+

    def _validate(self) -> None:
        for d, caps in self.domains.items():
            if "ln_cap_lo" not in caps or "ln_cap_hi" not in caps:
                raise ValueError(f"Domain {d} missing ln_cap_lo/ln_cap_hi")
            if caps["ln_cap_lo"] > caps["ln_cap_hi"]:
                raise ValueError(f"Domain {d} has inverted caps")
        for it in self.items:
            # Allow variable-length HR arrays (3-7 bins typical)
            if "hr" not in it or len(it["hr"]) < 2:
                raise ValueError(f"{it['id']} must have at least 2 HR values")
            # Validate bins field matches HR length
            if "bins" in it and len(it["bins"]) != len(it["hr"]):
                raise ValueError(f"{it['id']}: bins length ({len(it['bins'])}) must match hr length ({len(it['hr'])})")

    def _item_lnhr(self, item: Dict[str, Any], bin_index: Optional[int]) -> float:
        hr = item["hr"][bin_index] if bin_index is not None else item.get("missing_hr", 1.0)
        if hr <= 0:
            raise ValueError(f"HR must be >0 for {item['id']}")
        return math.log(hr)

    def compute(self, chron_age_years: float, answers: Dict[str, Any]) -> THAResult:
        """answers may contain raw option strings, numeric values, or direct bin indices (0..N)."""
        per_domain_ln: Dict[str, float] = {d: 0.0 for d in self.domains.keys()}
        itemYears: Dict[str, float] = {}

        # Calculate BMI if height and weight are provided
        height_val = answers.get("height", None)
        weight_val = answers.get("weight", None)
        if height_val is not None and weight_val is not None:
            # Use imperial units by default (inches and pounds)
            # Height is expected in inches (e.g., 70 for 5'10")
            bmi = self._calculate_bmi(height_val, weight_val, "in", "lbs")
            bmi_lnhr = self._bmi_to_lnhr(bmi)
            per_domain_ln["body"] += bmi_lnhr
            itemYears["bmi_calculated"] = bmi_lnhr / self.b

        for it in self.items:
            iid, dom = it["id"], it["domain"]
            raw = answers.get(iid, None)

            # Skip height/weight as they're used for BMI calculation
            if iid in ["height", "weight"]:
                continue

            bin_idx = _raw_to_bin(it, raw) if raw is not None else None
            lnhr = self._item_lnhr(it, bin_idx)
            per_domain_ln[dom] += lnhr
            itemYears[iid] = lnhr / self.b

        # domain caps in log space
        for dom, lnval in per_domain_ln.items():
            caps = self.domains[dom]
            per_domain_ln[dom] = max(caps["ln_cap_lo"], min(caps["ln_cap_hi"], lnval))

        lnHR_total = sum(per_domain_ln.values())
        delta_years = lnHR_total / self.b
        delta_years = max(-self.age_clamp_years, min(self.age_clamp_years, delta_years))

        domainYears = {dom: val / self.b for dom, val in per_domain_ln.items()}

        return THAResult(
            THA=chron_age_years + delta_years,
            AgeAccel=delta_years,
            domainYears=domainYears,
            itemYears=itemYears,
            algo_version=self.version,
            b=self.b,
            groups=self.groups,
        )

    def what_if(self, chron_age_years: float, answers: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
        proposed = dict(answers)
        proposed.update(changes)  # values can be raw options, numbers, or bin indices
        base = self.compute(chron_age_years, answers)
        new = self.compute(chron_age_years, proposed)
        return {"delta_years": new.AgeAccel - base.AgeAccel, "new_THA": new.THA, "old_THA": base.THA}

    def one_step_gains_months(self, answers: Dict[str, Any]) -> Dict[str, float]:
        gains: Dict[str, float] = {}
        for it in self.items:
            iid = it["id"]
            raw = answers.get(iid, None)
            if raw is None:
                gains[iid] = 0.0
                continue
            # map raw to bin; if already best, no gain
            try:
                curr = _raw_to_bin(it, raw)
            except Exception:
                gains[iid] = 0.0
                continue
            max_bin = len(it["hr"]) - 1
            if curr is None or curr >= max_bin:
                gains[iid] = 0.0
                continue
            hr_now, hr_next = it["hr"][curr], it["hr"][curr + 1]
            gain_years = (math.log(hr_now) - math.log(hr_next)) / self.b
            gains[iid] = gain_years * 12.0
        return gains

def load_config(path: str | Path) -> Dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    if yaml and str(path).endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)

# Optional CLI for quick smoke test
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compute True Health Age deterministically.")
    parser.add_argument("-c","--config", required=True)
    parser.add_argument("-a","--age", required=True, type=float)
    parser.add_argument("-n","--answers", help="JSON mapping item_id -> raw value (option string/number/bin index)")
    args = parser.parse_args()
    cfg = load_config(args.config)
    eng = THAEngine(cfg)
    # Default to middle bin for each item (variable length support)
    if args.answers:
        answers = json.loads(Path(args.answers).read_text())
    else:
        answers = {it["id"]: len(it["hr"]) // 2 for it in cfg["items"]}
    res = eng.compute(args.age, answers)
    print(json.dumps({
        "algo_version": res.algo_version,
        "b": res.b,
        "THA": round(res.THA,2),
        "AgeAccel": round(res.AgeAccel,2),
        "domainYears": {k: round(v,2) for k,v in res.domainYears.items()}
    }, indent=2))
