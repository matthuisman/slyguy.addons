REGION_ALL = 'all'
REGIONS = ['Sydney', 'Melbourne', 'Brisbane', 'Perth', 'Adelaide', 'Darwin', 'Hobart', 'Canberra', REGION_ALL]
DATA_URL = 'https://i.mjh.nz/au/{region}/tv.json.gz'
EPG_URL = 'https://i.mjh.nz/au/{region}/epg.xml.gz'

ALL = 0
FREEVIEW_ONLY = 1
FAST_ONLY = 2
CHANNEL_MODES = [ALL, FREEVIEW_ONLY, FAST_ONLY]
