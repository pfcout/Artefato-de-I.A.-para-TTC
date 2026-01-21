# ==========================================================
# validate.py — SPIN Zero-Shot version (IZSC double-validation compatible)
# ==========================================================
# Original author: Lucas Schwarz
# Adaptation: SPIN Zero-Shot Project (Tele_IA, 2025)
# Purpose: Compare two independent inference rounds (double-shot)
#          and consolidate results according to selected strategy.
# ==========================================================

import random

def validate_combined_predictions(result_1: dict, result_2: dict, params: dict, strategy: str = "conservative"):
    """
    Compare two independent classification rounds (result_1 and result_2)
    and consolidate the final output based on the chosen strategy.

    Parameters
    ----------
    result_1 : dict
        Dictionary containing the first inference results (e.g., {'opening': 1, 'situation': 0, ...})
    result_2 : dict
        Dictionary containing the second inference results for the same text.
    params : dict
        Parameter dictionary returned by set_zeroshot_parameters(), containing:
            - 'valid_keys': list of active labels
            - 'label_codes': mapping for present/absent/non-coded values
    strategy : str, optional
        Strategy to combine both predictions:
            - "conservative": set 1 only if both rounds return 1
            - "optimistic":   set 1 if any round returns 1
            - "probabilistic": randomly choose between the two values

    Returns
    -------
    dict
        Dictionary containing for each label:
            - *_pred1 : value from first round
            - *_pred2 : value from second round
            - *_method : combination method used
            - <label>  : final merged value
        Plus a global key:
            - validation_conflict : 1 if any label differs between rounds, else 0
    """

    valid_keys = params.get("valid_keys", [])
    label_codes = params.get("label_codes", {"present": 1, "absent": 0})

    final = {}
    conflict_detected = False

    for key in valid_keys:
        val1 = result_1.get(key, label_codes["absent"])
        val2 = result_2.get(key, label_codes["absent"])

        # store raw predictions
        final[f"{key}_pred1"] = val1
        final[f"{key}_pred2"] = val2

        # comparison logic
        if val1 == val2:
            final[key] = val1
            final[f"{key}_method"] = "identical"
        else:
            conflict_detected = True
            if strategy == "conservative":
                final[key] = label_codes["absent"]
                final[f"{key}_method"] = "conservative"
            elif strategy == "optimistic":
                final[key] = label_codes["present"]
                final[f"{key}_method"] = "optimistic"
            elif strategy == "probabilistic":
                final[key] = random.choice([val1, val2])
                final[f"{key}_method"] = "probabilistic"
            else:
                final[key] = label_codes["absent"]
                final[f"{key}_method"] = "undefined_strategy"

    # global validation flag
    final["validation_conflict"] = 1 if conflict_detected else 0

    return final
