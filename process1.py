import os
import json
import elasticsearch

host, index_agent = os.environ['ELASTICSEARCH_INDEX_URL_AGENT'].rsplit('/', 1)
_, index_processing = os.environ['ELASTICSEARCH_INDEX_URL_PROCESSING'].rsplit('/', 1)
es = elasticsearch.Elasticsearch([host])


res = es.search(index=index_agent, body={"query": {"match_all": {}}})
print("Got %d Hits:" % res['hits']['total'])

for hit in res['hits']['hits'][0:1]:
    for item in hit["_source"]["items"]:
        # print(json.dumps(item, indent=2))
        print(item["kind"])
        try:
            uid = item["metadata"]["uid"]
            res = es.index(index=index_processing, doc_type='_doc', id=uid, body=item)
            print(res['result'])
        except elasticsearch.ElasticsearchException as e:
            print(str(e))
