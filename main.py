import datetime
import elasticsearch
import json
import os

today = datetime.datetime.today()
host, index_agent = os.environ['ELASTICSEARCH_INDEX_URL_AGENT'].rsplit('/', 1) 
index_agent += today.strftime("%Y-%m-%d")
_, index_processor = os.environ['ELASTICSEARCH_INDEX_URL_PROCESSOR'].rsplit('/', 1)
es = elasticsearch.Elasticsearch([host])

# delete old agent index
delta = datetime.timedelta(days=int(os.environ['DAYS_HISTORY']))
end_date = today - delta
d = end_date - delta
while d <= end_date:
  print("removing old data: " + d.strftime("%Y-%m-%d"))
  d += delta
  es.indices.delete(index=index_agent + d.strftime("%Y-%m-%d"), ignore=[400, 404])


if not es.indices.exists(index=index_processor):
  print("Index %s not found, skipping the processing" % index_agent)
  quit()

page = es.search(
  index = index_agent,
  size = 100,
  scroll = '2m',
  body = {'query': {'match_all': {}}})

print("Got %d Hits:" % page['hits']['total'])

sid = page['_scroll_id']
scroll_size = page['hits']['total']

while (scroll_size > 0):
  page = es.scroll(scroll_id = sid, scroll = '2m')
  sid = page['_scroll_id']
  scroll_size = len(page['hits']['hits'])

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
        res = es.index(index=index_processor, doc_type='_doc', id=uid, body=item)
      except elasticsearch.ElasticsearchException as e:
        print(str(e))
