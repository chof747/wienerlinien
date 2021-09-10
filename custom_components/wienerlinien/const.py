"""Constants"""
BASE_URL = "http://www.wienerlinien.at/ogd_realtime/monitor?stopid={}"

DEPARTURES = {
    "first": {
        "key": 0,
        "name": {
            "simple": "{} first departure",
            "direction_firstnext": "{} -> {} first",
            "direction": "{} -> {}",
        },
    },
    "next": {
        "key": 1,
        "name": {
            "simple": "{} next departure",
            "direction_firstnext": "{} -> {} next",
            "direction": "{} -> {}",
        },
    },
}
