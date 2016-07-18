#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import re
from project import *

# ArgumentParser class
import argparse

# datetime.strptime(), datetime.strftime()
from datetime import datetime

DEFAULT_PROJECT_LIST_FILENAME="project_urls.txt"

#globalni promenna pro prepinani mezi vyhledavvani novych projektu a update
switch = "start"
# globally used regexes
reMap = {}
reMap['notFound'] = re.compile(r'No result found')
reMap['projURL'] = re.compile(r'<span class="contenttype">\[[^>]+\]</span>[^<]+<a href="([^"]+)">')
reMap['update'] = re.compile(r'Last updated on: </b>([0-9-]+)</div>')
reMap['rcn'] = re.compile(r'project/rcn/([0-9]+)_en.html')


def getDate(aText):
    '''
    Converts text to ISO date.
    '''

    return datetime.strptime(aText, "%d/%m/%Y")

def splitByYears(aDate1, aDate2):
    '''
    Creates a list of year interval between two dates.
    '''

    if aDate1.year == aDate2.year:
        return [ (aDate1, aDate2) ]

    # First (possibly shortened) interval
    years = [ (aDate1, datetime(aDate1.year, 12, 31)) ]

    # Middle intervals
    y = aDate1.year + 1
    while y < aDate2.year:
        years += [ (datetime(y, 1, 1), datetime(y, 12, 31)) ]
        y += 1

    # Last (possibly shortened) interval
    years += [ (datetime(y, 1, 1), aDate2) ]

    return years

def getProjectURLs(aURL, aDate1, aDate2):
    '''
    Returns URL of each project that started between specified dates.
    '''
    global switch
    #base_url = aURL + "%20AND%20/project/startDate=" + \
        #aDate1.strftime("%Y-%m-%d") + "-" + aDate2.strftime("%Y-%m-%d")
    if switch == "start":
        base_url = aURL + "%20AND%20/project/startDate=2009-02-01-2009-02-28" 
    else:
        base_url = aURL + "%20AND%20/project/startDate=2009-02-01-2009-02-28"
        
    # List of projects URLs
    project_info = []

    # Pager
    page = 1

    # Fetch content of each page 
    while True:
        page_url = base_url + "&p=" + str(page) + "&num=100"
        info("Opening page %s - %s" % (page, page_url))
        data = fetchUrl(page_url)

        if data != None:
            if re.search(reMap['notFound'], data):
                break
            else:
                new_urls = re.findall(reMap['projURL'], data)
                #debug(new_urls)
                new_lastUpdate = re.findall(reMap['update'], data)
                project_info += zip(new_urls, new_lastUpdate)
                debug("URLS:")
                debug(new_urls)
                debug("ULAST UPDATES:")
                debug(new_lastUpdate)

        page += 1 

    return project_info

def indexProject(aURL):
    # Check url of a project
    rcn = re.search( reMap['rcn'], aURL)
    if rcn == None:
        return

    rcn = rcn.group(1)

    proj = Project(aURL)
    proj.fillData()
    proj.normalizeData()
    proj.printData()
    proj.indexData()

def indexProjects(aFile):
    with open(aFile, "r") as fin:
        urls = fin.readlines()

    for url in urls:
        indexProject(url.strip())

def findProjects(aFile, aBaseUrl, aFrom, aTo, my_switch):
    global switch
    switch = my_switch
    # List of project urls
    project_info = []

    # Gather URLs all projects year by year
    intervals = splitByYears(aFrom, aTo)
    for (date1, date2) in intervals:
        project_info += getProjectURLs(aBaseUrl, date1, date2)
        
    debug(project_info)
    
    es = Elasticsearch(host=HOST, port=PORT)
    result = es.search(index=IDXPROJ, body={"query" : {"match_all" : {  }}})
    nmb = result['hits']['total']
    result = es.search(index=IDXPROJ, size = nmb, body={"_source": ["url", "lastUpdate"],"query": {"match_all" : { } }})
    url_list = []
    lastUpdate_list = []
    for value in result['hits']['hits']:
        if value.has_key('_source'):
            url_list.append(value['_source']['url'])
            lastUpdate_list.append(value['_source']['lastUpdate'])
    #print url_list
    project_info_dct = dict(project_info)
        
    # Store URL list
    with open(aFile, "w") as fout:
        for my_url in project_info_dct.keys():
            if switch == "start":
                if my_url in url_list:
                    info("Project with url %s is already in database" % my_url)
                else:
                    fout.write(my_url + "\n")
            else:
                if my_url in url_list:
                    index = url_list.index(my_url)
                    lastUpdate_new = project_info_dct[my_url]
                    lastUpdate_db = lastUpdate_list[index]
                    debug ("Last update new: %s\t last update: %s" % (lastUpdate_new, lastUpdate_db))
                    if lastUpdate_new == lastUpdate_db:
                        info("Project with url %s and last update date %s is already in database" % (my_url, lastUpdate_new))
                    else:
                        fout.write(my_url + "\n")
                else:
                    fout.write(my_url + "\n")

def main():
    '''
    Crawler entry point.
    '''

    # Command line arguments
    parser = argparse.ArgumentParser(description="Extracts projects from Cordis.")
    group_me = parser.add_mutually_exclusive_group(required=True)
    group_me.add_argument('-u', '--url', nargs=1, \
        help='An URL of a page with project located at Cordis')
    group_me.add_argument("-f", "--file", nargs=1, \
        help="A file containing urls of projects to update (one per line)")
    group_me.add_argument("-e", "--ext-delivs", dest="ext", action="store_true", \
        default=False, help="Tries to find deliverables at project sites")
    parser.add_argument('-r', '--refresh-interval', nargs=2, type=getDate, \
        help='Determines date interval (dates should be formatted as DD/MM/YYYY)')
    args = parser.parse_args()

    debug(args.url)
    debug(args.refresh_interval)
    debug(args.ext)

    if args.url != None:
        findProjects(DEFAULT_PROJECT_LIST_FILENAME, args.url[0], \
            args.refresh_interval[0], args.refresh_interval[1])
        indexProjects(DEFAULT_PROJECT_LIST_FILENAME)
    elif args.file != None:
        indexProjects(args.file[0])
    elif args.ext: # (i.e., not None or False)
        Project.updateExtDelivs(args.refresh_interval[0], args.refresh_interval[1])

if __name__ == "__main__":
    main()

