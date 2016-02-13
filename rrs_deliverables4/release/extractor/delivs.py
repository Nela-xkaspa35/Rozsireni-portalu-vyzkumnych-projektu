#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import sys
import os
import re
import urlparse

sys.path.insert(0, 'deliv2')
import deliverables 

deliv_options = {
        'debug' : False,
        'regexp' : None,
        'quiet' : False,
        'page' : False,
        'file' : False,
        'storefile' : True,
        'verbose' : True,
        'lookup_page' : False,
    }

def findDeliverables2(aUrl):
    # give the link to the rrs_deliverables2 to find the page containing deliverables
    mdeliv = deliverables.Deliverables(deliv_options, aUrl)
    page = None
    
    # stringize the found page
    try:
        deliv2_response = mdeliv.main()
        if len(mdeliv.links) > 0 and mdeliv.links[0] != -1:
            page = mdeliv.links[0]
    except Exception as e:
        print "Error occurent during deliverable extraction:"
        print e
        if mdeliv != None and hasattr(mdeliv, "links") and mdeliv.links and len(mdeliv.links) > 0 and mdeliv.links[0] != -1:
            page = mdeliv.links[0]
        else:
            page = None

    # Collect found links located in an XML file
    files = os.listdir(".")
    xmls = [ x for x in files if x.lower().endswith(".xml") ]

    # Search through downloaded XML files
    links = []
    for xml in xmls:
        with open(xml, "r") as fin:
            data = fin.read()
            relative_links = re.findall(r'<publication[^<]*<title value="([^"]*)"[^<]*<url[^<]*<link value="([^"]*)"', data)
            for (pdf_title, pdf_url) in relative_links:
                print page, pdf_url
                links.append((pdf_title, urlparse.urljoin(page, pdf_url)))
        os.remove(xml)

    return (page, links)

