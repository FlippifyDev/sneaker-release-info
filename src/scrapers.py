from src.scraper_sneaktorious import sneaktorious_run
from src.scraper_size import size_run

import json


scrapers = [
    (sneaktorious_run, 180),
    (size_run, 1)
]


def fetch_scrapers():
    current_run = fetch_current_run()

    scrapers_to_run = []

    for scraper_func, run_count in scrapers:
        if current_run % run_count == 0:
            scrapers_to_run.append(scraper_func)

    return scrapers_to_run



def fetch_current_run():
    with open("data/current_run.json", "r+") as file:
        count = json.load(file)["count"]

        file.seek(0)
        file.truncate()
        
        # Count increment every 2 minutes so 180 is 6 hours
        if count == 180:
            json.dump({"count": 1}, file, indent=4)
        else:
            json.dump({"count": count+1}, file, indent=4)

        return count