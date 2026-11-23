"""Daytime adaptation shared by the village builder and individual shop installers."""

RESIDENTIAL_PLOTS = ('07', '08')

TAVERN_DAYLIGHT = {
    'exposure_compensation': 2.0,
    'additional_dark_adaptation_stops': 4.0,
    'entrance_transition_cm': 60.0,
    'shadow_contrast': 0.5,
}

RESIDENTIAL_DAYLIGHT = {
    'exposure_compensation': 1.7,
    'additional_dark_adaptation_stops': 3.4,
    'entrance_transition_cm': 75.0,
    'shadow_contrast': 0.5,
}

SHOP_DAYLIGHT = {
    '01': TAVERN_DAYLIGHT,       # Blacksmith forge and loft
    '03': RESIDENTIAL_DAYLIGHT,  # Apothecary and upstairs living space
    '04': RESIDENTIAL_DAYLIGHT,  # Enclosed carpenter's loft
    '05': TAVERN_DAYLIGHT,       # Stone windmill tower
    '06': {**RESIDENTIAL_DAYLIGHT, 'exposure_compensation': .55},  # Lit sales counter
    '09': RESIDENTIAL_DAYLIGHT,  # Gunshop
}


def apply_daylight(room, settings):
    for name, value in settings.items():
        room.set_editor_property(name, value)
