import datetime
import elasticsearch
import json
import os

today = datetime.datetime.today()
host, index_agent_raw = os.environ['ELASTICSEARCH_INDEX_URL_AGENT'].rsplit('/', 1) 
_, index_processor = os.environ['ELASTICSEARCH_INDEX_URL_PROCESSOR'].rsplit('/', 1)
es = elasticsearch.Elasticsearch([host])

def delete_index(name):
  es.indices.delete(index=name, ignore=[400, 404])
  print("Index %s removed" % name)

def process_batch(page):
  for doc in page['hits']['hits']:
    item = doc["_source"]

    # Add controller name and type in the item root level
    if 'metadata' in item:

      if 'labels' in item['metadata']:
        if 'giantswarm.io/service-type' in item['metadata']:
          continue #Dont track our pods

      if 'ownerReferences' in item['metadata']:
        if len(item['metadata']['ownerReferences']) > 0:
          if 'kind' in item['metadata']['ownerReferences'][0]:
            item['controllerKind'] = item['metadata']['ownerReferences'][0]['kind']
          if 'name' in item['metadata']['ownerReferences'][0]:
            item['controllerName'] = item['metadata']['ownerReferences'][0]['name']

    if 'kind' in item:
      try:
        uid = item["metadata"]["uid"]
        es.index(index=index_processor, doc_type='_doc', id=uid, body=item)
      except elasticsearch.ElasticsearchException as e:
        print(str(e))

# delete old agent index
d = today - datetime.timedelta(days=15)
while d <= today:
  d += datetime.timedelta(days=1)
  index_agent = index_agent_raw + d.strftime("-%Y-%m-%d")
  if not es.indices.exists(index=index_agent):
    print("Index %s not found, skipping" % index_agent)
    continue

  page = es.search(
    index = index_agent,
    size = 100,
    scroll = '2m',
    body = {'query': {'match_all': {}}})

  print("Got %d Hits:" % page['hits']['total'])

  if page['hits']['total'] <= 0:
    print("Index %s empty, skipping" % index_agent)
    delete_index(index_agent)
    continue

  sid = page['_scroll_id']
  scroll_size = page['hits']['total']

  while (scroll_size > 0):
    print("Index %s: %d items remaining to be processed" % (index_agent, scroll_size))
    process_batch(page)

    page = es.scroll(scroll_id = sid, scroll = '2m')
    sid = page['_scroll_id']
    scroll_size = len(page['hits']['hits'])

  print("Index %s processed" % index_agent)
  delete_index(index_agent)
  