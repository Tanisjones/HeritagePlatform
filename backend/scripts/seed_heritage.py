"""
Back-compat delegator for the legacy Riobamba seeder.

The engine lives in scripts/seed_city_engine.py and the Riobamba dataset in
data/cities/riobamba.py. The `seed_heritage` management command (a docker
entrypoint dependency) and standalone callers keep importing this module.
"""

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)

from scripts.seed_city_engine import clean_database, ensure_django  # noqa: E402,F401


def create_initial_data(*, download_remote_media: bool = True):
    from data.cities import riobamba
    from scripts.seed_city_engine import create_city_data

    create_city_data(riobamba, download_remote_media=download_remote_media)


def seed_data():
    clean_database()
    create_initial_data()
    print("Seeding complete.")


if __name__ == "__main__":
    seed_data()
