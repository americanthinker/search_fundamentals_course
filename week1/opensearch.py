from flask import g, current_app
from opensearchpy import OpenSearch
from typing import Tuple

def get_client(host: str='localhost', 
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
# Create an OpenSearch client instance and put it into Flask shared space for use by the application
def get_opensearch():
    if 'opensearch' not in g:
        #### Step 4.a:
        # Implement a client connection to OpenSearch so that the rest of the application can communicate with OpenSearch
        client = get_client()
        g.opensearch = client

    return g.opensearch
