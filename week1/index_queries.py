# From Dmitiriy Shvadskiy https://github.com/dshvadskiy/search_with_machine_learning_course/blob/main/index_queries.py
import click
import pandas as pd
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from loguru import logger
import json
import time

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# logging.basicConfig(format='%(levelname)s:%(message)s')
mapping_path = '/Users/americanthinker/Training/search_fundamentals_course/opensearch/bbuy_queries.json'

def get_opensearch():

    host = 'localhost'
    port = 9200
    auth = ('admin', 'admin')
    client = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_compress=True,  # enables gzip compression for request bodies
        http_auth=auth,
        # client_cert = client_cert_path,
        # client_key = client_key_path,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        #ca_certs=ca_certs_path
    )
    return client
def get_mapping(file_path: str):
    with open(file_path) as f:
        mapping = json.load(f)
        return mapping

@click.command()
@click.option('--source_file', '-s', help='source csv file', required=True)
@click.option('--index_name', '-i', default="bbuy_queries", help="The name of the index to write to")
def main(source_file: str, index_name: str):
    client = get_opensearch()

    #define index mapping
    mapping = get_mapping(file_path=mapping_path)

    #create index if not already exists
    if not client.indices.exists(index_name):
        client.indices.create(index_name, body=mapping)
        
    ds = pd.read_csv(source_file)
    #print(ds.columns)
    ds['click_time'] = pd.to_datetime(ds['click_time'])
    ds['query_time'] = pd.to_datetime(ds['query_time'])
    #print(ds.dtypes)
    docs = []
    tic = time.perf_counter()
    logger.info('Initiating indexing.')
    for idx, row in ds.iterrows():
        doc = {}
        for col in ds.columns:
            doc[col] = row[col]
        docs.append({'_index': index_name , '_source': doc})
        if idx % 1000 == 0:
            bulk(client, docs, request_timeout=60)
            logger.info(f'{idx} documents indexed')
            docs = []
    if len(docs) > 0:
        bulk(client, docs, request_timeout=60)
    toc = time.perf_counter()
    logger.info(f'Done indexing {ds.shape[0]} records. Total time: {((toc-tic)/60):0.3f} mins.')

if __name__ == "__main__":
    main()