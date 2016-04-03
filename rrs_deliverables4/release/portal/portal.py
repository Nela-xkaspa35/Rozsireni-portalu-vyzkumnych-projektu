#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------        Autori: Martin Cvicek, Lucie Dvorakova      -------------#
#----------------           Loginy: xcvice01, xdvora1f         ---------------#
#-- Rozšíření portálu evropských výzkumných projektů o pokročilé vyhledávání -#
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import re
import sys
import math
import string
import shlex
from flask import Flask
from flask import request
from flask import render_template
from elasticsearch import Elasticsearch
from datetime import datetime
from cStringIO import StringIO
from elasticutils import get_es, F, S, MLT


HOST        = "localhost"
PORT        = 9200
IDXPROJ     = "xcvice01_projects"
IDXDELIV    = "xcvice01_deliverables"
DOCTYPE     = "data"
URL         = "http://%s:%d/" % (HOST, PORT)

ITEMS_PER_PAGE = 20
last_url = ''

es = Elasticsearch(host=HOST, port=PORT)
deliv_s = S().es(urls=[URL]).indexes(IDXDELIV).doctypes(DOCTYPE)
project_s = S().es(urls=[URL]).indexes(IDXPROJ).doctypes(DOCTYPE)

app = Flask(__name__)

@app.route("/")
def index():
    code = render_template("index.html")
    return code

@app.route("/find", methods=["GET"])
def find():
    global last_url
    last_url = request.url
    # search in project or deliverables (projects are default)
    search = request.args.get("search", "projects")
    search_pressed = request.args.get("search_pressed")
    keywords = request.args.get("keyword", "")
    # tady je ulozeno, ktere casti filtru chceme vymazat
    remove = request.args.get("remove", "")
    #if '=' not in keywords: 
    #keywords = correct_keyword(keywords, search)
    #keywords = add_spec(keywords, request.args)
    if not search_pressed:
      k = correct_query(keywords, request.args, remove)
   
    #print search
    
    # get current page, or default to zero
    try:
        page = int(request.args.get("page", "0"))
        if page < 0:
            page = 0
    except:
        page = 0
        
    
    
    # getting facets from url and query
    search_dic = {}
    # search_dic2 je promenna pro zobrazeni vybraneho filtru
    search_dic2={}
    valid_specs = ["country", "programme", "subprogramme", "coordinator",
        "participant", "year"]
    r = []
    # specification from search box is prioritized 
    if remove != "":
        r = remove.split(':')
        
    for spec in valid_specs:
        #val = q.getSpecification(spec)
        #if val:
        #    str = val.split('&')
        #    for s in str:
        #        search_dic2.setdefault(spec, []).append(s)
        #    search_dic[spec] = val.strip().lower()
        #    continue
        val = request.args.get(spec)
        # vymazani nektereho filtru - uzivatel klikl napr. na 'united kingdom x'
        if r != []:
            if spec == r[0]:
                r2 = r[1]
                search_value = r2.lower()
                val = val.replace(search_value, '')
            
        #print val
        # hodnoty z val nastrkame do search_dic2 - vypisuje vybrane filtry
        if val:
            # nekteri coordinator nebo participant meli uvozovky v nazvu a delalo
            # to neporadek
            my_val = val.replace('"', '')
            val = my_val
            str = val.split('&')
            for s in str:
                if s != "":
                    # pokud uz ve filtru hodnotu mame (napr country:united kingdom)
                    # preskocime vlozeni
                    new_s = string.capwords(s)
                    if spec in search_dic2.keys() and new_s in search_dic2.get(spec):
                        continue
                    search_dic2.setdefault(spec, []).append(new_s)
            search_dic[spec] = val.replace("+", " ").strip().lower()

    # build actual query for ElasticSearch 
    offset = page*ITEMS_PER_PAGE
    keyword_s = get_project_with_keywords(keywords, search, \
        offset, offset+ITEMS_PER_PAGE)

    # keyword_s2 je pro to, aby jsme mohli spocitat pocet projektu u jednotlivych
    # napr. zemich
    # keyword slouzi k tomu, abychom meli vypsane i zeme, ve kterych aktualne nejsou
    # zadne projekty, protoze je vybrany nejaky filtr (napr. country:italy)
    keyword_s2 = keyword_s
    if len(search_dic) > 0:
        keyword_s2 = keyword_s.filter(get_filter(search_dic))   
    user_query = get_query(search_dic, search, keywords)
    # getting facets
    facet = facets(keyword_s, keyword_s2)
    keyword_s = keyword_s2
    # getting instant show
    instan_s = ''
    if keyword_s:
        if keyword_s[0].es_meta.score > 3:
            instan_s = keyword_s
        else:
            filter_args = {"abbr": keywords}
            instan_s = keyword_s.filter(**filter_args)

    # if not enought project fill with deliv + create facet of projects
    deli_s = ''
    deli_facet = []
    if keyword_s:
        if keyword_s.count() < ITEMS_PER_PAGE:
            if search == 'projects':
                deli_s = get_project_with_keywords(keywords, 'deliverables', \
                    offset, offset+ITEMS_PER_PAGE)
                deli_facet = deliverable_facets(deli_s)
                deli_s = deli_s[0:ITEMS_PER_PAGE - keyword_s.count()]
    else:
        if search == 'projects':
            deli_s = get_project_with_keywords(keywords, 'deliverables', \
                offset, offset+ITEMS_PER_PAGE)
            deli_facet = deliverable_facets(deli_s)
            deli_s = deli_s[0:ITEMS_PER_PAGE]

    query = get_query(search_dic2, keywords, search)
    
    code = render_template('find.html', keyword=query, s=keyword_s, \
        f=facet, d=search_dic, search=search, insta=instan_s, page=page, \
        deli=deli_s, deli_facet = deli_facet, d2=search_dic2)
    return code

@app.route('/project/<projectid>')
def project_detail(projectid):
    global project_s
    global last_url
    
    #getting similar projects
    mlt_s = MLT(projectid, index=IDXPROJ, doctype=DOCTYPE, search_size=3)

    filter_args = {"id": projectid}
    data_s = project_s.filter(**filter_args)
    deli_s = deliv_s.filter(**filter_args)
    code = render_template('project.html', s = data_s[0], d = deli_s[0:50], url = last_url, similar=mlt_s)
    return code

@app.route('/user/')
@app.route('/user/<name>')
def user(name=None):
    return render_template('user.html', name=name)

## --------------------------------------- ##
## -------------- FUNKCE ----------------- ##
## --------------------------------------- ##
def correct_keyword(keyword, search):
  if '"' not in keyword:
    keyword_split = keyword.split(' ')
    for k in keyword_split:
      keyword += k
      if keyword_split[-1] != k:
        keyword += " OR "
  keyword="search=" + search + " AND " + "keyword=" + keyword
  return keyword

def add_spec(keywords, args):
  valid_specs = ["country", "programme", "subprogramme", "coordinator",
        "participant", "year"]
  for spec in valid_specs:
    val = args.get(spec)
    keywords += " AND " + spec + "=" + val
  return keywords
  
def correct_query(keywords, args, remove):
  valid_specs = ["country", "programme", "subprogramme", "coordinator",
        "participant", "year"]  
  r = []
  # specification from search box is prioritized 
  if remove != "":
    r = remove.split(':')
    for spec in valid_specs:
      val = args.get(spec)
      # vymazani nektereho filtru - uzivatel klikl napr. na 'united kingdom x'
      if r != []:
        if spec == r[0]:
          r2 = r[1]
          print "keywords:" + keywords
          keywords = keywords.replace(spec+"="+r2, "")
          print "keywords after r:" + keywords
      
      # hodnoty z val nastrkame do search_dic2 - vypisuje vybrane filtry
      if val:
      # nekteri coordinator nebo participant meli uvozovky v nazvu a delalo
      # to neporadek
        val = val.replace('"', '')
        str = val.split('&')
        for s in str:
          if keywords.find(spec+"="+r2) == -1:
          # pokud uz ve filtru hodnotu mame (napr country:united kingdom)
          # preskocime vlozeni
            index = keywords.find(spec + '=')
            if index != -1:
              keywords = keywords[:index] + spec + "=" + s + "OR" + keywords[index:]
            else:
              keywords+="AND " + spec + "=" + s
      print "keywords after insert:" + keywords
            
               
# Vrati filtr vsech projektu kde se nachazeji klicova slova
def get_project_with_keywords(keyword, search, from_, to):
  if search == 'projects':
    if keyword == "":        
      keyword_s = project_s.query_raw({             
        "match_all" : { }               
        })
    else:
      if '"' in keyword:
        keyword = keyword.replace('"', '')
        keyword_s = project_s.query_raw({
          "multi_match" : {
            "query" : keyword,
            "type" : "phrase",
            "fields" : [ "abbr^6","title^5", "subprogramme^3", "objective", "origWeb"]
            }    
        })
      else:
        
        keyword_s = project_s.query_raw({
          "multi_match" : {
            "query" : keyword,
            "fields" : [ "abbr^6","title^5", "subprogramme^3", "objective", "origWeb"]
            }    
        })
      keyword_s = keyword_s[from_:to]
      keyword_s = keyword_s.highlight('objective', pre_tags = ["<b>"], post_tags = ["</b>"])
  else:
    if keyword == "":
      keyword_s = deliv_s.query_raw({
        "match_all" : { }
      })
    else:
      keyword_s = deliv_s.query_raw({
        "multi_match" : {
        "query" : keyword,
        "fields" : [ "deliv_title^3", "deliv_article"],
#       "type" : "phrase"
        }
      })
    keyword_s = keyword_s[from_:to]
    keyword_s = keyword_s.highlight('deliv_article', pre_tags = ["<b>"], post_tags = ["</b>"])
  return keyword_s


# Generuje leve menu s facety na zaklade filtru facet_s
def facets(keyword_s, keyword_s2):
    listfacet = [['programme', []], ['subprogramme', []],['year', []], ['coordinator', []], ['participant', []], ['country',[]]]
    for facet in listfacet:
        facet_s = keyword_s.facet(facet[0], filtered=True, size=20).facet_counts()
        facet_s2 = keyword_s2.facet(facet[0], filtered=True, size=20).facet_counts()
        for value in facet_s[facet[0]]['terms']:
            value2 = finder(value['term'], facet_s2[facet[0]]['terms'])
            if value2 == None:
              facet[1].append([value['term'], '0 z ' + str(value['count'])])
            else:
              facet[1].append([value['term'], str(value2['count']) + ' z ' + str(value['count'])])
    #print listfacet
    return listfacet

# finding projects with deliverables
def deliverable_facets(deli_s):
    deli_facet = []
    deli_facet_s = deli_s.facet("id", filtered=True, size=100).facet_counts()
    for item in deli_facet_s['id']['terms']:
        filter_args = {"id": item['term']}
        tmp_s = deli_s.filter(**filter_args)
        deli_facet.append([item['term'],tmp_s[0]['abbr']])
    return deli_facet

# K nalezeni hodnoty v poli listu + vraceni hodnoty
def finder(element, array):  
    #print array    
    for x in array:
        if element in x['term']:
            return x
    return None

# Sestavi filtr, ktery je slozeny z or (mezi jednotlivymi polozkami v menu) a 
# and (mezi hlavnimi nadpisy menu)
# return - vraci instanci objekt typu F
def get_filter(search_dic):
    main_filter = []
    for spec in ["country", "programme", "subprogramme", "coordinator",
    "participant", "year"]:
        if search_dic.get(spec):
            spec2 = search_dic.get(spec).split('&')
            f = F()
            for s in spec2:
                if s != "":
                # Bohuzel to nejde resit jinak nez 'switch' cyklem - neumime
                # dostat hodnotu spec pro filter F - spec je jiz povazovano 
                # za retezec
                    if spec == "country":
                        f |= F(country=s)
                    elif spec == "programme":
                        f |= F(programme=s)
                    elif spec == "subprogramme":
                        f |= F(subprogramme=s)
                    elif spec == "coordinator":
                        f |= F(coordinator=s)
                    elif spec == "participant":
                        f |= F(participant=s)
                    elif spec == "year":
                        f |= F(year=s)
            main_filter.append(f)
    f2 = F()
    for f in main_filter:
        f2 &= f
    # print f2
    return f2

# Pokud byl filtr zadan klikanim, musime to prevest do textove podoby     
def get_query(search_dic, search, keyword):
    user_query = ""
    keyword_validation = re.search('keyword=("([\w\s]+)"|(([\w]+)(\s(OR|AND)\s)?)+)(\sAND\s[\w]+=|$)', query)
    if not keyword_validation:
      keyword=""
    else:
      if '"' not in keyword and ' ' in keyword:
        keyword=""
        
    query = "search=" + search + " AND keyword=" + keyword
    if user_query != "": 
        user_query = query + " AND " + user_query
    else:
        user_query = query
    return user_query

def parse_user_query (query):
  search = re.search('search=(projects|deliverables)', query)      
  print query
  keyword = re.search('keyword=("([\w\s]+)"|(([\w]+)(\s(OR|AND)\s)?)+)(\sAND\s[\w]+=|$)', query)
  if search:
    print search.group(1)
  if keyword:
    print keyword.group(1)
    
def get_query(search_dic2, keywords, search):
  keyword=""
  if '"' not in keywords:
    keyword_split = keywords.split(' ')
    for k in keyword_split:
      keyword += k
      if keyword_split[-1] != k:
        keyword += " OR "
  query="search=" + search + " AND keyword=" + keyword
  for spec in ["country", "programme", "subprogramme", "coordinator",
    "participant", "year"]:
        if search_dic2.get(spec):
            query=query+"AND "
            spec2 = search_dic.get(spec).split('&')
            for s in spec2:
                if s != "":
                  r = query.find(spec)
                  if r != -1:
                    query=query[:r+len(spec)+1] + s + "," + query[r+len(spec)+1:]
                  else:
                    query=query+"AND " + spec + "=" + s
  return query  

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 1080, debug=True)

