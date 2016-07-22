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

@app.route("/find", methods=["GET", "POST"])
def find():
		global last_url
		last_url = request.url
		keyword=""
		# getting facets from url and query
		search_dic = {}
		# search_dic2 je promenna pro zobrazeni vybraneho filtru
		valid_specs = ["country", "programme", "subprogramme", "coordinator",
				"participant", "year"]
		#values from checkboxes
		options=[]

		if request.method == 'GET':
			search = request.args.get("search")		
			options = request.args.getlist('option[]')
			if options:
				o_split = options[0].split(',')
				options = []
				for o in o_split:
					if o: 
						options.append(o)
		
		else:
			search = request.form["search"]
			options = request.form.getlist('option[]')			
			

		#o is in the form year=2009 - we need to parse it
		if options: 
			for o in options:
				o_split = o.split('=', 1)
				# nekteri coordinator nebo participant meli uvozovky v nazvu a delalo
				# to neporadek
				val = o_split[1].replace('"', '')
				search_dic.setdefault(o_split[0], []).append(val)

		
		#get searched query
		if search and '=' in search:
			keyword = parse_keyword(search)
		elif search:
			keyword = search

		# get current page, or default to zero
		try:
			page = int(request.args.get("page", "0"))
			if page < 0:
				page = 0
		except:
			page = 0

		# build actual query for ElasticSearch 
		offset = page*ITEMS_PER_PAGE
		projects = get_project_with_keywords(keyword, \
				offset, offset+ITEMS_PER_PAGE)

		# projects2 je pro to, aby jsme mohli spocitat pocet projektu u jednotlivych
		# napr. zemich
		# projects slouzi k tomu, abychom meli vypsane i zeme, ve kterych aktualne nejsou
		# zadne projekty, protoze je vybrany nejaky filtr (napr. country:italy)
		projects2 = projects.filter(get_filter(search_dic)) 
		# getting facets
		facet = get_facets(projects, projects2)
		#projects = projects2

		# if not enought project fill with deliv + create facet of projects
		#deli_s = ''
		#deli_facet = []
		#if projects:
		#    if projects.count() < ITEMS_PER_PAGE:
		#        if search == 'projects':
		#            deli_s = get_project_with_keywords(keywords, 'deliverables', \
		#                offset, offset+ITEMS_PER_PAGE)
		#            deli_facet = deliverable_facets(deli_s)
		#            deli_s = deli_s[0:ITEMS_PER_PAGE - keyword_s.count()]
		if '=' not in search or request.method == 'POST':
			search = get_query(search_dic, keyword)
		if request.method == 'POST':
			return render_template('articles.html', s=projects2, f=facet, search=search, page=page, checkbox=options)	
		else:	
			return render_template('find.html', s=projects2, f=facet, search=search, page=page, checkbox=options)

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
def get_project_with_keywords(keyword, from_, to):
	if not keyword:        
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
	return keyword_s

# Generuje leve menu s facety na zaklade filtru facet_s
def get_facets(projects, projects2):
		listfacet = [['programme', []], ['subprogramme', []],['year', []], ['coordinator', []], ['participant', []], ['country',[]]]
		for facet in listfacet:
				facet_s = projects.facet(facet[0], filtered=True, size=20).facet_counts() #how many projects in facet without filter
				facet_s2 = projects2.facet(facet[0], filtered=True, size=20).facet_counts() #how many projects in facet with filter

				for value in facet_s[facet[0]]['terms']:
						value2 = finder(value['term'], facet_s2[facet[0]]['terms'])
						if value2 == None:
							facet[1].append([value['term'], '0 z ' + str(value['count'])])
						else:
							facet[1].append([value['term'], str(value2['count']) + ' z ' + str(value['count'])])
		#print listfacet
		return listfacet

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
		my_spec = search_dic.get(spec)
		if search_dic.get(spec):
			f = F()
			for s in my_spec:
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
	return f2

def get_query(search_dic, keyword):
	#keyword=""
	#if keywords == "":
	#	keyword = ""
	#elif '"' not in keywords:
	#	keyword_split = keywords.split(' ')
	#	for k in keyword_split:
	#		keyword += k
	#		if keyword_split[-1] != k:
	#			keyword += " OR "
	#else:
	#	keyword=keywords
	query="keyword=" + keyword
	for spec in ["country", "programme", "subprogramme", "coordinator", "participant", "year"]:
		if search_dic.get(spec):
			for s in search_dic.get(spec):
				if s:
					print s
					r = query.find(spec)
					if r != -1:
						query=query[:r+len(spec)+1] + s + "," + query[r+len(spec)+1:]
					else:
						query=query+" AND " + spec + "=" + s
					print query
	return query

#z user query dostane jen klicova slova, ze kterych odstrani prozatim AND a OR
#zatim by totiz bylo slozite v klicovych slovech michat AND a OR
def parse_keyword (keywords):
	#keyword muze aktualne vypadat treba takto:
	#keyword=young OR people AND year=2009
	#pokud jsou v keyword "", hledame o frazi
	keyword = re.search('keyword=((("([\w\s]+)"|[\w]+)(\s(OR|AND)\s)?)+)(?:(\sAND\s[\w]+=|$))', keywords)
	if keyword:
		print keyword.group(1)
		lindex = 0
		result= keyword.group(1)
		#v podstate cyklus do until " OR" nenalezeno
		while True:
			lindex = result.find(" OR", lindex)
			rindex = lindex + len(" OR")
			if lindex == -1:
				break
			else:
				result = result[:lindex] + result[rindex:]
		
		#pro pripad, ze by keyword vypadal takto, odstranime mezeru na konci:
		#search=projects AND keyword=young OR  AND year=2009
		#ostatni nepovolene kombinace nejsou mozne diky kontrole skry regex
		#if result[-1] == ' ':
		#	result = result[:len(result)-1-1]
	else:
		result= ""
	return result

if __name__ == "__main__":
	app.run(host="0.0.0.0", port = 1080, debug=True)

