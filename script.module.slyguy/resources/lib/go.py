import re

data = """
<ContentProtection schemeIdUri="urn:mpeg:dash:mp4protection:2011" value="cenc" cenc:default_KID="ae967c161edf4a62afab98a933bbea9c"></ContentProtection>
"""

DEFAULT_KID_PATTERN = re.compile(':default_KID="([0-9a-fA-F]{32})"')

def fix_default_kids(input_text):
    def format_kid(match):
        kid = match.group(1)
        formatted_kid = f"{kid[:8]}-{kid[8:12]}-{kid[12:16]}-{kid[16:20]}-{kid[20:]}"
        print('Dash Fix: Replaced default_KID {} -> {}'.format(kid, formatted_kid))
        return ':default_KID="{}"'.format(formatted_kid)

    replaced_text = re.sub(DEFAULT_KID_PATTERN, format_kid, input_text)
    return replaced_text

data = fix_default_kids(data)
#print(data)
