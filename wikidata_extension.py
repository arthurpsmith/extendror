import re
import sys
import ror_data
from SPARQLWrapper import SPARQLWrapper, JSON
from time import sleep

# Following probably should be its own class with caching etc.
def my_get_sparql_results(queryString):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql",
        agent='extendror (https://extendror.toolforge.org) SPARQLWrapper'
    )
    sparql.setReturnFormat(JSON)
    sparql.setQuery(queryString)
    try:
        results = sparql.query().convert()
    except urllib.error.HTTPError as err:
        retry_after = None
        if err.code == 429:
            retry_after = err.headers.get("Retry-After")
        if retry_after is None:
            retry_after = 5
        sleep(retry_after)
        try:
            results = sparql.query().convert()
        except:
            results = None
    except:
        results = None
    return results

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

    qid_pattern = re.compile(r'Q\d+$')
    if extension == '':
        # Fetch all children of ror_id from Wikidata:
        sparql_query = """
SELECT DISTINCT ?parent ?item ?itemLabel WHERE {{
  ?parent wdt:P6782 '{0}' ; wdt:P355|wdt:P527 ?item .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}} ORDER BY ?itemLabel
""".format(ror_id)
        results = my_get_sparql_results(sparql_query)
        parent_item = ''
        if results:
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
        self_metadata['is_top_level'] = True
    else:
        self_metadata = wikidata_self_metadata(extension)
        self_ror_id = self_metadata['ror_id']
        if self_ror_id != '':
            ror_self_metadata = ror_data.metadata_for_ror(self_ror_id)
            if self_ror_id == ror_id:
                self_metadata['is_top_level'] = True
        # Fetch all children of extension id from Wikidata:
        query_string = """
SELECT DISTINCT ?item ?itemLabel WHERE {{
  wd:{0} wdt:P355|wdt:P527 ?item .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}} ORDER BY ?itemLabel
""".format(extension)
        results = my_get_sparql_results(query_string)
        if results:
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
    query_string = """
SELECT (count(*) as ?count) WHERE {{
  ?parent wdt:P6782 '{0}' ; (wdt:P355|wdt:P527)* wd:{1} .
}}
""".format(ror_id, qid)
    results = my_get_sparql_results(query_string)
    if results:
      for result in results['results']['bindings']:
        path_count = int(result['count']['value'])
        if (path_count > 0):
            return True
    return False


# Fetch name, parent, any ror_id, for given id
def wikidata_self_metadata(qid):
    self_metadata = {'id': qid}
    query_string = """
SELECT DISTINCT ?itemLabel ?classLabel ?ror_id ?parent ?parentLabel ?parent_ror_id  WHERE {{
  VALUES ?item {{ wd:{0} }}
  OPTIONAL {{ ?parent wdt:P355|wdt:P527 ?item }}
  OPTIONAL {{ ?parent wdt:P355|wdt:P527 ?item; wdt:P6782 ?parent_ror_id }}
  OPTIONAL {{ ?item wdt:P6782 ?ror_id }}
  OPTIONAL {{ ?item wdt:P31 ?class }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
""".format(qid)
    results = my_get_sparql_results(query_string)
    if results:
      result = results['results']['bindings'][0]
      self_metadata['name'] = result['itemLabel']['value']
      if 'ror_id' in result:
        self_metadata['ror_id'] = result['ror_id']['value']
      else:
        self_metadata['ror_id'] = ''
      classes = {}
      parents = {}
      has_ror_parent = False
      for result in results['results']['bindings']:
        if 'parent' in result:
          parent_item = result['parent']['value']
          parent_match = re.search(r'Q\d+$', parent_item)
          parent_id = None
          if parent_match:
            parent_id = parent_match.group(0)
          parent_name = result['parentLabel']['value']
          parent_ror_id = ''
          if 'parent_ror_id' in result:
            parent_ror_id = result['parent_ror_id']['value']
            has_ror_parent = True
          parents[parent_id] = {'id': parent_id, 'name': parent_name, 'ror_id': parent_ror_id}
          if 'classLabel' in result:
              classes[result['classLabel']['value']] = 1
      self_metadata['parents'] = parents.values()
      self_metadata['classes'] = classes.keys()
      self_metadata['has_ror_parent'] = has_ror_parent
    return self_metadata


# Perform a search using WDQS and wikibase EntitySearch api
def search(query):
    matches = []
    qid_pattern = re.compile(r'Q\d+$')
    query_string = """
SELECT ?item ?itemLabel ?ror_id WHERE {{
  hint:Query hint:optimizer "None" .
  SERVICE wikibase:mwapi {{
    bd:serviceParam wikibase:api "EntitySearch";
                    wikibase:endpoint "www.wikidata.org";
                    mwapi:search "{0}" ;
                    mwapi:language "en" .
      ?item wikibase:apiOutputItem mwapi:item .
  }}
  ?item (wdt:P361/wdt:P749)*/wdt:P6782 ?ror_id .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
}}
""".format(query)
    results = my_get_sparql_results(query_string)
    if results:
      for result in results['results']['bindings']:
        item = result['item']['value']
        name = result['itemLabel']['value']
        ror_id = result['ror_id']['value']
        qid_match = qid_pattern.search(item)
        if qid_match:
            qid = qid_match.group(0)
            matches.append({'id': qid, 'name': name, 'ror_id': ror_id})
    return matches
