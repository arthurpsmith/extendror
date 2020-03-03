import json
import urllib.request

ror_api_prefix = 'https://api.ror.org/organizations/ror.org/'

def metadata_for_ror(ror_id):
    metadata = {}
    with urllib.request.urlopen(ror_api_prefix + ror_id) as ror_api:
        metadata = json.load(ror_api)
    return metadata
