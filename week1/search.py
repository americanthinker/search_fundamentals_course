#
# The main search hooks for the Search Flask application.
#
from flask import (
    Blueprint, redirect, render_template, request, url_for
)

from week1.opensearch import get_opensearch
from loguru import logger
bp = Blueprint('search', __name__, url_prefix='/search')


# Process the filters requested by the user and return a tuple that is appropriate for use in: the query, URLs displaying the filter and the display of the applied filters
# filters -- convert the URL GET structure into an OpenSearch filter query
# display_filters -- return an array of filters that are applied that is appropriate for display
# applied_filters -- return a String that is appropriate for inclusion in a URL as part of a query string.  This is basically the same as the input query string
def process_filters(filters_input):
    # Filters look like: &filter.name=regularPrice&regularPrice.key={{ agg.key }}&regularPrice.from={{ agg.from }}&regularPrice.to={{ agg.to }}
    filters = []
    display_filters = []  # Also create the text we will use to display the filters that are applied
    applied_filters = ""
    for filter in filters_input:
        type = request.args.get(filter + ".type")
        display_name = request.args.get(filter + ".displayName", filter)
        applied_filters += f"&filter.name={filter}&{filter}.type={type}&{filter}.displayName={display_name}"
        if type == "range":
            from_val = request.args.get(filter + ".from", None)
            to_val = request.args.get(filter + ".to", None)
            logger.info(f"from: {from_val}, to: {to_val}")
            # we need to turn the "to-from" syntax of aggregations to the "gte,lte" syntax of range filters.
            to_from = {}
            if from_val:
                to_from["gte"] = from_val
            else:
                from_val = "*"  # set it to * for display purposes, but don't use it in the query
            if to_val:
                to_from["lt"] = to_val
            else:
                to_val = "*"  # set it to * for display purposes, but don't use it in the query
            the_filter = {"range": {filter: to_from}}
            filters.append(the_filter)
            display_filters.append(f"{display_name}: {from_val} TO {to_val}")
            applied_filters += f"&{filter}.from={from_val}&{filter}.to={to_val}"
        elif type == "terms":
            field = request.args.get(filter + ".fieldName", filter)
            key = request.args.get(filter + ".key", None)
            the_filter = {"term": {field: key}}
            filters.append(the_filter)
            display_filters.append(f"{display_name}: {key}")
            applied_filters += f"&{filter}.fieldName={field}&{filter}.key={key}"
    logger.info(f"Filters: {filters}")

    return filters, display_filters, applied_filters



# Our main query route.  Accepts POST (via the Search box) and GETs via the clicks on aggregations/facets
@bp.route('/query', methods=['GET', 'POST'])
def query():
    client= get_opensearch()  # Load up our OpenSearch client from the opensearch.py file.
    index_name='full-load'
    # Put in your code to query opensearch.  Set error as appropriate.
    error = None
    user_query = None
    query_obj = None
    display_filters = None
    applied_filters = ""
    filters = None
    sort = "_score"
    sortDir = "desc"
    if request.method == 'POST':  # a query has been submitted
        user_query = request.form['query']
        if not user_query:
            user_query = "*"
        sort = request.form["sort"]
        if not sort:
            sort = "_score"
        sortDir = request.form["sortDir"]
        if not sortDir:
            sortDir = "desc"
        query_obj = create_query(user_query, [], sort, sortDir)
    elif request.method == 'GET':  # Handle the case where there is no query or just loading the page
        user_query = request.args.get("query", "*")
        filters_input = request.args.getlist("filter.name")
        sort = request.args.get("sort", sort)
        sortDir = request.args.get("sortDir", sortDir)
        if filters_input:
            (filters, display_filters, applied_filters) = process_filters(filters_input)

        query_obj = create_query(user_query, filters, sort, sortDir)
    else:
        query_obj = create_query("*", [], sort, sortDir)

    #logger.info(f"query obj: {query_obj}")
    logger.info(f'Filters: {filters}')
    #### Step 4.b.ii
    response = client.search(body=query_obj, index="full-load")# TODO: Replace me with an appropriate call to OpenSearch
    # Postprocess results here if you so desire
    #print(response)
    logger.info(f'Response: {response}')
    if error is None:
        return render_template("search_results.jinja2", query=user_query, search_response=response,
                               display_filters=display_filters, applied_filters=applied_filters,
                               sort=sort, sortDir=sortDir)
    else:
        redirect(url_for("index"))


def create_query(user_query, filters, sort="_score", sortDir="desc"):
    #logger.info(f"Query: {user_query} Filters: {filters} Sort: {sort}")
    query_obj = {
        'size': 25,
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": user_query,
                            "fields": ["name^100", "shortDescription^50", "longDescription^10"],
                            "phrase_slop": 3
                                        }
                    }
                ],
                "filter": filters
                #         },
                # "filter": {
                #         "terms": {"name": filters}
                #           }
                }},   
        "aggs": {
            "regularPrice": {
                "range": {
                        "field": "regularPrice",
                        "ranges": 
                            [
                                {"from": 0,  "to":  5,  "key": "Up to $5"},
                                {"from": 5,  "to":  20, "key": "$5-$20"},
                                {"from": 20, "to": 100, "key": "$20-$100"},
                                {"from":100, "to": 500, "key": "$100-$500"},
                                {"from":500, "key": "$500+"}
                            ]
                        }
                            },
            "department": {
                "terms": {
                    "field": "department.keyword",
                    "size": 10,
                    "min_doc_count": 0
                }
                          },
            "missing_images": {
                "missing": {"field": "image.keyword"}
                              }},
        "highlight": {
            "pre_tags" : ["<b>"],
            "post_tags" : ["</b>"],
            "fields": {
                "name": {},
                "shortDescription": {},
                "longDescription": {}
                      }
                    },
        "sort": [
            {sort: {"order": sortDir}},
            {"regularPrice": {"order": sortDir}},
            {"name.keyword": {"order": sortDir}}
                    ]
    }

    return query_obj