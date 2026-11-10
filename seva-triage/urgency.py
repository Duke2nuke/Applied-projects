"""Transparent rule-based urgency flag for seva-triage.

Urgency is NOT learned by the model. It is a short, explicit list of
phrases, so any officer can read the rules and see exactly why a
grievance was flagged high, medium or low. The lists are deliberately
narrow: health/safety risks and multi-day loss of a basic service are
high; long delays and blockages are medium; everything else is low.
"""

HIGH_PHRASES = [
    "no water for",        # multi-day loss of drinking water
    "burst",               # burst pipeline
    "sewage",              # sewage mixing with drinking water
    "contaminated",        # contaminated water
    "falling sick",        # people already ill
    "hospital",            # hospital-related failure
    "ambulance",           # ambulance needed
    "accident",            # road accident
    "outbreak",            # disease outbreak
    "dengue",              # dengue spreading
    "no medicine",         # health centre out of medicine
    "no doctor",           # no doctor available
    "no oxygen",           # oxygen supply failure
    "biting",              # stray dogs biting children
    "dangerous",           # immediate physical danger
    "may fall",            # pole / structure about to fall
    "unsafe",              # unsafe for children
    "emergency",
    "fire",
    "flood",
]

MEDIUM_PHRASES = [
    "pending for",         # application pending for months
    "delayed",             # certificate / service delayed
    "not worked for a month",
    "not worked for a week",
    "for two months",
    "for three months",
    "for four months",
    "for six months",
    "cancelled",           # service cancelled without notice
    "blocking",            # road blocked
    "blocked",             # road blocked
    "waterlogged",         # road waterlogged
    "piling up",           # garbage piling up
    "leaking",             # leaking roof / tank
    "overcrowded",         # overcrowded school bus
    "wrong",               # wrong bill / records / readings
    "faulty",              # faulty meter
    "burnt out",           # burnt-out transformer
]


def urgency(text):
    """Return 'high', 'medium' or 'low' for a grievance text."""
    lowered = text.lower()
    if any(phrase in lowered for phrase in HIGH_PHRASES):
        return "high"
    if any(phrase in lowered for phrase in MEDIUM_PHRASES):
        return "medium"
    return "low"
