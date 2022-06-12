# From https://github.com/dshvadskiy/search_with_machine_learning_course/blob/main/index_products.py
import requests
from lxml import etree
from typing import Tuple
import click
import glob
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from loguru import logger
import time
import json 
from uuid import uuid1 as rand_gen

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
# logging.basicConfig(format='%(levelname)s:%(message)s')

mapping_path = '/Users/americanthinker/Training/search_fundamentals_course/opensearch/bbuy_products.json'
# NOTE: this is not a complete list of fields.  If you wish to add more, put in the appropriate XPath expression.
# TODO: is there a way to do this using XPath/XSL Functions so that we don't have to maintain a big list?
mappings = [
    "sku/text()", "sku", # SKU is the unique ID, productIds can have multiple skus
    "productId/text()", "productId",
    "name/text()", "name",
    "type/text()", "type",
    "regularPrice/text()", "regularPrice",
    "salePrice/text()", "salePrice",
    "onSale/text()", "onSale",
    "salesRankShortTerm/text()", "salesRankShortTerm",
    "salesRankMediumTerm/text()", "salesRankMediumTerm",
    "salesRankLongTerm/text()", "salesRankLongTerm",
    "bestSellingRank/text()", "bestSellingRank",
    "url/text()", "url",
    "categoryPath/*/name/text()", "categoryPath",  # Note the match all here to get the subfields
    "categoryPath/*/id/text()", "categoryPathIds",  # Note the match all here to get the subfields
    "categoryPath/category[last()]/id/text()", "categoryLeaf",
    "count(categoryPath/*/name)", "categoryPathCount",
    "customerReviewCount/text()", "customerReviewCount",
    "customerReviewAverage/text()", "customerReviewAverage",
    "inStoreAvailability/text()", "inStoreAvailability",
    "onlineAvailability/text()", "onlineAvailability",
    "releaseDate/text()", "releaseDate",
    "shortDescription/text()", "shortDescription",
    "class/text()", "class",
    "classId/text()", "classId",
    "department/text()", "department",
    "departmentId/text()", "departmentId",
    "bestBuyItemId/text()", "bestBuyItemId",
    "description/text()", "description",
    "manufacturer/text()", "manufacturer",
    "modelNumber/text()", "modelNumber",
    "image/text()", "image",
    "longDescription/text()", "longDescription",
    "longDescriptionHtml/text()", "longDescriptionHtml",
    "features/*/text()", "features"  # Note the match all here to get the subfields

]

def get_opensearch(host: str='localhost', 
                   port: int=9200, 
                   auth: Tuple[str, str]=('admin', 'admin')
                   ) -> OpenSearch:

    #### Step 2.a: Create a connection to OpenSearch
    client = OpenSearch(
    hosts=[{'host': host, 'port': port}],
    http_compress=True,  # enables gzip compression for request bodies
    http_auth=auth,
    # client_cert = client_cert_path,
    # client_key = client_key_path,
    use_ssl=False,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False)

    return client

def get_mapping(file_path: str):
    with open(file_path) as f:
        mapping = json.load(f)
        return mapping


@click.command()
@click.option('--source_dir', '-s', help='XML files source directory')
@click.option('--index_name', '-i', default="bbuy_products", help="The name of the index to write to")
def main(source_dir: str, index_name: str):
    #instantiate client
    client = get_opensearch()

    #define index mapping
    mapping = get_mapping(file_path=mapping_path)

    #create index if not already exists
    if not client.indices.exists(index_name):
        client.indices.create(index_name, body=mapping)

    # To test on a smaller set of documents, change this glob to be more restrictive than *.xml
    files = glob.glob(source_dir + "/*.xml")
    logger.info(f'All files: {files}')
    docs_indexed = 0
    tic = time.perf_counter()
    docs = []
    count = 0
    for file in files:
        logger.info(f'Processing file : {file}')
        tree = etree.parse(file)
        root = tree.getroot()
        children = root.findall("./product")
        for child in children:
            doc = {}
            for idx in range(0, len(mappings), 2):
                xpath_expr = mappings[idx]
                key = mappings[idx + 1]
                doc[key] = child.xpath(xpath_expr)
            if not 'productId' in doc or len(doc['productId']) == 0:
                continue
            #### Step 2.b: Create a valid OpenSearch Doc and bulk index 2000 docs at a time
            doc['id'] = rand_gen().hex
            count += 1
            doc['_index'] = index_name
            docs.append(doc)
            if len(docs) % 25000 == 0:
                bulk(client, docs)
                docs = []
                docs_indexed += 25000
                logger.info(f'{docs_indexed} docs indexed.')
    if docs:
        remaining_docs = len(docs)
        logger.info(f'Indexing remaining {remaining_docs} docs.')
        bulk(client, docs)
        docs_indexed += remaining_docs
    toc = time.perf_counter()
    logger.info(f'Done. Total docs: {docs_indexed}.  Total time: {((toc - tic) / 60):0.3f} mins.')
    logger.info(f'Total count: {count}')

if __name__ == "__main__":
    main()
