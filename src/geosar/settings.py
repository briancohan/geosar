import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
MAPBOX = os.getenv("MAPBOX")
TIMEZONE = 'America/New_York'

ASTRO_HORIZ = '-18'
NAUTI_HORIZ = '-12'
CIVIL_HORIZ = '-6'
SHINE_HORIZ = '0'

NIGHT = 'Night'
ASTRO = 'Astrological Twilight'
NAUTI = 'Nautical Twilight'
CIVIL = 'Civil Twilight'
SHINE = 'Daytime'
PLANS = 'Planning'

NIGHT_COLOR = '#01084f'
ASTRO_COLOR = '#391954'
NAUTI_COLOR = '#631e50'
CIVIL_COLOR = '#a73c5a'
SHINE_COLOR = '#ff7954'
PLANS_COLOR = '#aaaaaa'
