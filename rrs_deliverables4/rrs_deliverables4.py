#!/usr/bin/env python

#-------        Autor: Lucie Dvorakova      --------#
#-------           Login: xdvora1f          --------# 
#- Django pro generator vedeckych webovych portalu -#

import re
import sys
import urllib2
from project import *
from elasticsearch import Elasticsearch

def main():
    numProj = 0
    numProjWithDel = 0
    numDel = 0
    numDelOpen = 0
    debug = False # Kdyz true skript probehne pouze na 20ti projektech
    URLs = get_urls(debug)
    for URL in URLs:
        proj = Project(URL)
        proj.fill_data()
        numProj += 1
        numProjWithDel += proj.numProjWithDel
        numDel += proj.numDel
        numDelOpen += proj.numDelOpen
        if proj.found:
            proj.print_data()
    print "Number of projects \t%s" % numProj
    print "Number of proj. with delivarables\t%s" % numProjWithDel
    print "Number of deliverables \t%s" % numDel 
    print "Extracted deliverabels \t%s" % numDelOpen


def get_urls(debug):
    URL ="http://cordis.europa.eu/search/result_en?q=endDate=2013-10-12-2014-10-12%20AND%20contenttype=%27project%27"
    URLs = []
    page = 1
    reMap = compile_re()
    if debug:
        myURL = URL + "&p=" + str(page) + "&num=20"
        usock = urllib2.urlopen(myURL)
        print "Opening page %s - %s..." % (page, myURL)
        data = usock.read()
        print "Opened."
        usock.close() 
        URLs += re.findall(reMap['projURL'], data)


    else:      
        while 1:
            myURL = URL + "&p=" + str(page) + "&num=20"
            print "Opening page %s - %s" % (page, myURL)
            try:
                usock = urllib2.urlopen(myURL)
            except urllib2.URLError:
                sys.stderr.write("Error: URL not found. (%s)\n" % myURL)
                sys.exit(1)
            data = usock.read()
            usock.close() 
            if page == 20:
                break
            if re.search(reMap['notFound'], data):
                break
            else:
                URLs += re.findall(reMap['projURL'], data)
                page += 1 
    return URLs

def compile_re():
    reMap = {}

    reMap['notFound'] = re.compile(r'<div id="searchresult">\sNo result found</div>')
    reMap['projURL'] = re.compile(r'<span class="contenttype">\[[^>]+\]</span>\s<a href="([^"]+)">')

    return reMap
    
    

if __name__ == "__main__":
    main()
