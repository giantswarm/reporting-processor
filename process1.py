import os
import json
import elasticsearch

host, index_agent = os.environ['ELASTICSEARCH_INDEX_URL_AGENT'].rsplit('/', 1)
_, index_processing = os.environ['ELASTICSEARCH_INDEX_URL_PROCESSING'].rsplit('/', 1)
es = elasticsearch.Elasticsearch([host])


res = es.search(index=index_agent, body={"query": {"match_all": {}}})
print("Got %d Hits:" % res['hits']['total'])

for doc in res['hits']['hits']:
  item = doc["_source"]
  if 'kind' in item:
    try:
      uid = item["metadata"]["uid"]
      res = es.index(index=index_processing, doc_type='_doc', id=item['metadata']['uid'], body=item)
      print(res['result'])
    except elasticsearch.ElasticsearchException as e:
      print(str(e))
