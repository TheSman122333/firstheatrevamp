"Convert estimated WBGT to classes, regional sports or screening catagories."

import json
import math
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "rules.json"


@lru_cache(maxsize=1)
def load_rules():
    with RULES_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def get_category(wbgt, rule_set, unit="C", clothing_adjustment_c=0):
    """Classify WBGT using a sports region or worker rule set.

    For example:
        sports_2
        workers_heavy_unacclimatized

    WBGT is Celsius by default.
    """

    if unit not in ("C", "F"):
        raise ValueError("Unit must be 'C' or 'F'")

    if not isinstance(wbgt, (int, float)) or isinstance(wbgt, bool) or not math.isfinite(wbgt):
        raise ValueError("WBGT MUST BE FINITE")

    if (
        not isinstance(clothing_adjustment_c, (int, float))
        or isinstance(clothing_adjustment_c, bool)
        or not math.isfinite(clothing_adjustment_c)
        or clothing_adjustment_c < 0
    ):
        raise ValueError("CLOTHING ADJUSTMENT MUST BE A POSITIVE FINITE NUMBER")

    wbgt_c = (wbgt - 32) * 5 / 9 if unit == "F" else wbgt
    rules = load_rules()

    #guidelines grouped by climate reigon
    if rule_set.startswith("sports_"):
        if clothing_adjustment_c:
            raise ValueError("CLOTHING ADJUSTMENTS ARE ONLY ALLOWED FOR WORKER RULES")

        region = rule_set.removeprefix("sports_")
        settings = rules["sports"]["regions"].get(region)

        if settings is None:
            raise ValueError(f"Unknown sports region: {region}. Choose 1, 2, or 3")

        wbgt_f = wbgt_c * 9 / 5 + 32
        category = "green"

        #each threshold active at its min
        for name, cutoff in settings["minimums"].items():
            if wbgt_f >= cutoff:
                category = name

        return {
            "category": category,
            "label": category.title(),
            "guidance": rules["sports"]["guidance"][category],
            "rule_set": rule_set,
            "source": settings["source"],
            "threshold_unit": settings["unit"],
            "reading_c": wbgt_c,
            "type": "advisory"
        }

    "Guidance depends on how acclimated and the workload"
    if rule_set.startswith("workers_"):
        name = rule_set.removeprefix("workers_")

        if name.endswith("_unacclimatized"):
            workload = name.removesuffix("_unacclimatized")
            status = "unacclimatized"
        elif name.endswith("_acclimatized"):
            workload = name.removesuffix("_acclimatized")
            status = "acclimatized"
        else:
            raise ValueError(f"Unknown worker rule set: {rule_set}")

        settings = rules["workers"]["workloads"].get(workload)

        if settings is None:
            raise ValueError(f"Unknown worker workload: {workload}")

        effective_wbgt = wbgt_c + clothing_adjustment_c
        limit = settings["limits"][status]
        reached = effective_wbgt >= limit

        return {
            "category": "review" if reached else "below_limit",
            "label": "Review heat exposure" if reached else "Below screening limit",
            "guidance": (
                "At/above the OSHA/NIOSH screening limit: assess exposure and controls."
                if reached
                else "Below this screening limit; precautions are still needed."
            ),
            "rule_set": rule_set,
            "source": settings["source"],
            "threshold_unit": settings["unit"],
            "limit_c": limit,
            "reading_c": effective_wbgt,
            "type": "screening_guidance_not_legal_limit"
        }

    raise ValueError(f"Unknown rule set: {rule_set}")


def next_category_if_close(wbgt, rule_set, unit="C"):
    """Name the next sports category when an estimate sits within the
    caution margin below that category's minimum, otherwise None.

    For example, in sports region 2 orange starts at 84.7 °F:
        84.0 °F gives "orange" (could be higher)
        82.0 °F gives None
    """

    if not rule_set.startswith("sports_"):
        raise ValueError("ONLY SPORTS RULE SETS HAVE CATEGORY CUTOFFS")

    #checks the reading and the region the same way as get_category
    current = get_category(wbgt, rule_set, unit=unit)

    sports = load_rules()["sports"]
    margin = sports.get("caution_margin_f", 1.0)
    wbgt_f = current["reading_c"] * 9 / 5 + 32

    minimums = sports["regions"][rule_set.removeprefix("sports_")]["minimums"]

    #minimums run from yellow up to black, so the first one above is next
    for name, cutoff in minimums.items():
        if cutoff > wbgt_f:
            return name if cutoff - wbgt_f <= margin + 1e-9 else None

    return None


def break_schedule(category):
    """Reminder spacing and break length for a sports heat category.

    For example, "yellow" gives {"every_minutes": 20, "break_minutes": 4}.
    """

    schedule = load_rules()["sports"]["break_schedule"].get(category)

    if schedule is None:
        raise ValueError(f"Unknown heat category: {category}")

    return schedule
