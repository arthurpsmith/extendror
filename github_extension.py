import urllib.request
import csv
import ror_data

known_extensions = {
  '03vek6s52': 'https://raw.githubusercontent.com/csgrant00/ror-extend-demo/master/examples/harvard/',
  '05rrcem69': 'https://raw.githubusercontent.com/csgrant00/ror-extend-demo/master/examples/ucdavis/',
  '04zaypm56': 'https://raw.githubusercontent.com/arthurpsmith/ror-extend-demo/master/examples/cnr_it/',
  '0447fe631': 'https://raw.githubusercontent.com/arthurpsmith/ror-extend-demo/master/examples/dod_us/',
  '01bj3aw27': 'https://raw.githubusercontent.com/arthurpsmith/ror-extend-demo/master/examples/doe_us/',
  '01hhn8329': 'https://raw.githubusercontent.com/arthurpsmith/ror-extend-demo/master/examples/maxplanck/',
  '05qrfxd25': 'https://raw.githubusercontent.com/arthurpsmith/ror-extend-demo/master/examples/ras_ru/'
}

def github_metadata(id):
    id_parts = id.split('/')
    ror_id = id_parts[0]
    ror_root_metadata = ror_data.metadata_for_ror(ror_id)
    extension = ''
    if (len(id_parts) > 1):
        extension = id_parts[1]
    orgs_metadata = {}
    if ror_id in known_extensions:
        data_source = known_extensions[ror_id]
        with urllib.request.urlopen(data_source + "orgs.csv") as orgsdata:
            orgsreader = csv.reader(orgsdata.read().decode('utf-8').split("\n"))
            for row in orgsreader:
                if (len(row) > 0) and (row[0] != 'id'):
                    orgs_metadata[row[0]] = {'id': row[0], 'name': row[1]}
                    if (len(row) > 4) and row[4] != '':
                        this_ror = row[4]
                        if this_ror.startswith('https'):
                            this_ror = this_ror[16:]
                        orgs_metadata[row[0]]['ror_id'] = this_ror
        with urllib.request.urlopen(data_source + "parents.csv") as parentsdata:
            parentsreader = csv.reader(parentsdata.read().decode('utf-8').split("\n"))
            for row in parentsreader: # should account for multiple parents properly...
                if (len(row) > 0) and (row[0] != 'id'):
                    child_id = row[0]
                    parent_id = row[1]
                    if child_id not in orgs_metadata:
                        orgs_metadata[child_id] = {'id': child_id, 'name': child_id}
                    orgs_metadata[child_id]['parent'] = parent_id
                    if parent_id not in orgs_metadata:
                        orgs_metadata[parent_id] = {'id': parent_id, 'name': parent_id,
                            'ror_id': ror_id}
                    if 'children' not in orgs_metadata[parent_id]:
                        orgs_metadata[parent_id]['children'] = []
                    orgs_metadata[parent_id]['children'].append(child_id)

    parent = ''
    children = []
    ror_self_metadata = {}
    
    if extension in orgs_metadata:
        if 'parent' in orgs_metadata[extension]:
            parent = orgs_metadata[extension]['parent']
        if 'children' in orgs_metadata[extension]:
            children = orgs_metadata[extension]['children']
        if 'ror_id' in orgs_metadata[extension]:
            ror_self_metadata = ror_data.metadata_for_ror(orgs_metadata[extension]['ror_id'])

    return {
            'ror_id': ror_id,
            'extension': extension,
            'parent': parent,
            'children': children,
            'metadata': orgs_metadata,
            'ror_root': ror_root_metadata,
            'ror_self': ror_self_metadata
    }

