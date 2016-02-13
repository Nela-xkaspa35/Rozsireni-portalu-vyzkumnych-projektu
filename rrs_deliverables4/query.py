#!/usr/bin/env python

#-------        Autor: Lucie Dvorakova      --------#
#-------           Login: xdvora1f          --------# 
#- Django pro generator vedeckych webovych portalu -#

from common import *

import re
import sys
from elasticsearch import Elasticsearch
from datetime import datetime
from cStringIO import StringIO
from elasticutils import get_es, S

URL = "http://ibpvm.wonderland:9200/"
INDEX_PROJ = "projects"
DOCTYPE = "data"
es = Elasticsearch(host='ibpvm.wonderland', port=9200)

#### Vyhledanani klicoveho slova v deliverables ####
'''
# Vyhledani deliverables s obsahujicim slovem
searchWord = "poorest" #Vyhledavane slovo
results = \
    es.search ( 
        index="deliverables", 
        fields="_id", 
        size="400",
        body={
            "query": {
                "match": {
                    "article": searchWord
                    }
                }
            }
        )

# Nalezeni a tisk projektu obshujici deliverables
for result in results['hits']['hits']:
    resultsProject = \
        es.search(
            index="projects", 
            size="400",
            body={
                "query": {
                    "match": {
                        "deliverablesIndex": result['_id']
                    }
                }
            }
        )

    print resultsProject['hits']['hits'][0]['_source']['title'] + "\n"
    print resultsProject['hits']['hits'][0]['_source']['subProg'] + "\n"
    print resultsProject['hits']['hits'][0]['_source']['objective'] + "\n"
'''
 #### Prace s facetama ###
searchFacet = 'coordIn' #Vyhledavany facet
basic_s = S().es(urls=[URL]).indexes(INDEX_PROJ).doctypes(DOCTYPE)
s = basic_s.facet(searchFacet).facet_counts()


for value in s[searchFacet]['terms']:
    q = basic_s.filter(coordIn = value['term'])
    for result in q:
        print result['title'] + "\n"
        print result['subProg'] + "\n"
        print result['objective'] + "\n"
    

    
    
    
