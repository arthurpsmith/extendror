import re
import ror_data
from SPARQLWrapper import SPARQLWrapper, JSON

def wikidata_metadata(id):
    id_parts = id.split('/')
    ror_id = id_parts[0]
    ror_root_metadata = ror_data.metadata_for_ror(ror_id)
    extension = ''
    if (len(id_parts) > 1):
        extension = id_parts[1]
    if not verify_wikidata_relation(ror_id, extension):
        return {'ror_id': ror_id, 'extension': extension, 'error': 'Unrelated'}
    children = []
    self_metadata = {}
    ror_self_metadata = {}

    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    qid_pattern = re.compile(r'Q\d+$')
    if extension == '':
        # Fetch all children of ror_id from Wikidata:
        sparql.setQuery("""
SELECT DISTINCT ?parent ?item ?itemLabel WHERE {{
  ?parent wdt:P6782 '{0}' ; wdt:P355|wdt:P527 ?item .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}} ORDER BY ?itemLabel
""".format(ror_id))
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        parent_item = ''
        for result in results['results']['bindings']:
            item = result['item']['value']
            parent_item = result['parent']['value']
            name = result['itemLabel']['value']
            qid_match = qid_pattern.search(item)
            if qid_match:
                qid = qid_match.group(0)
                children.append({'id': qid, 'name': name})
        qid_match = qid_pattern.search(parent_item)
        if qid_match:
            extension = qid_match.group(0)
            self_metadata = wikidata_self_metadata(extension)
            ror_self_metadata = ror_root_metadata
    else:
        self_metadata = wikidata_self_metadata(extension)
        self_ror_id = self_metadata['ror_id']
        if self_ror_id != '':
            ror_self_metadata = ror_data.metadata_for_ror(self_ror_id)
        # Fetch all children of extension id from Wikidata:
        sparql.setQuery("""
SELECT DISTINCT ?item ?itemLabel WHERE {{
  wd:{0} wdt:P355|wdt:P527 ?item .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}} ORDER BY ?itemLabel
""".format(extension))
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        for result in results['results']['bindings']:
            item = result['item']['value']
            name = result['itemLabel']['value']
            qid_match = qid_pattern.search(item)
            if qid_match:
                qid = qid_match.group(0)
                children.append({'id': qid, 'name': name})

    return {
            'ror_id': ror_id,
            'extension': extension,
            'metadata': self_metadata,
            'ror_self': ror_self_metadata,
            'children': children,
            'ror_root': ror_root_metadata
    }


# Verify there is a path from parent to child found:
def verify_wikidata_relation(ror_id, qid):
    if qid == '':
        return True
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery("""
SELECT (count(*) as ?count) WHERE {{
  ?parent wdt:P6782 '{0}' ; (wdt:P355|wdt:P527)* wd:{1} .
}}
""".format(ror_id, qid))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    for result in results['results']['bindings']:
        path_count = int(result['count']['value'])
        if (path_count > 0):
            return True
    return False


# Fetch name, parent, any ror_id, for given id
def wikidata_self_metadata(qid):
    self_metadata = {'id': qid}
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery("""
SELECT DISTINCT ?itemLabel ?ror_id ?parent ?parentLabel ?parent_ror_id  WHERE {{
  VALUES ?item {{ wd:{0} }}
  OPTIONAL {{ ?parent wdt:P355|wdt:P527 ?item }}
  OPTIONAL {{ ?parent wdt:P355|wdt:P527 ?item; wdt:P6782 ?parent_ror_id }}
  OPTIONAL {{ ?item wdt:P6782 ?ror_id }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
""".format(qid))
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    result = results['results']['bindings'][0]
    self_metadata['name'] = result['itemLabel']['value']
    if 'ror_id' in result:
      self_metadata['ror_id'] = result['ror_id']['value']
    else:
      self_metadata['ror_id'] = ''
    if 'parent' in result:
      parent_item = result['parent']['value']
      parent_match = re.search(r'Q\d+$', parent_item)
      if parent_match:
          self_metadata['parent_id'] = parent_match.group(0)
      else:
          self_metadata['parent_id'] = None
      self_metadata['parent_name'] = result['parentLabel']['value']
      if 'parent_ror_id' in result:
          self_metadata['parent_ror_id'] = result['parent_ror_id']['value']
      else:
          self_metadata['parent_ror_id'] = ''
    return self_metadata
