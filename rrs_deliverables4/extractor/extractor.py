#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------        Autori: Martin Cvicek, Lucie Dvorakova      -------------#
#----------------           Loginy: xcvice01, xdvora1f         ---------------#
#-- Rozšíření portálu evropských výzkumných projektů o pokročilé vyhledávání -#
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
reMap['projURL'] = re.compile(r'<div id="project_([^"]+)"\s+class="match project')
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
    
    #base_url = aURL + "%20AND%20/project/startDate=" + \
    #    aDate1.strftime("%Y-%m-%d") + "-" + aDate2.strftime("%Y-%m-%d")
    base_url = aURL + "%20AND%20/project/startDate=2008-01-01-2016-03-05" 

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
                new_urls = []
                new_lastUpdate = []
                new_urls = re.findall(reMap['projURL'], data)             
                new_lastUpdate = re.findall(reMap['update'], data)
                project_info += zip(new_urls, new_lastUpdate)
                debug("URLS:")
                debug(new_urls)
                debug("ULAST UPDATES:")
                debug(new_lastUpdate)

        page += 1 

    return project_info

def indexProject(aURL):
    '''
    Don't understand why it is here. But we change url and this check is no more
    valid
    # Check url of a project
    rcn = re.search( reMap['rcn'], aURL)
    if rcn == None:
        return

    rcn = rcn.group(1)
    '''
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
    
    # Stahneme vsechny url a k nim last update z databaze - zabranime zbytecnemu
    # stahovani informaci navic
    es = Elasticsearch(host=HOST, port=PORT)
    result = es.search(index=IDXPROJ, body={"query" : {"match_all" : {  }}})
    nmb = result['hits']['total']
    result = es.search(index=IDXPROJ, size = nmb, body={"_source": ["url", "lastUpdate"],"query": {"match_all" : { } }})
    project_info_db = dict()
    lastUpdate_list = []
    for value in result['hits']['hits']:
        if value.has_key('_source'):
            project_info_db[value['_source']['url']] = value['_source']['lastUpdate']
    # nalezene projekty z corids klic je url a hodnota je last update date
    project_info_dct = dict(project_info)
    fmt = '%Y-%m-%d' 
    # Store URL list
    with open(aFile, "w") as fout:
        for my_url in project_info_dct.keys():
            if switch == "start":
                if my_url in project_info_db.keys():
                    info("Project with url %s is already in database" % my_url)
                else:
                    fout.write(my_url + "\n")
            else:
                if my_url in project_info_db.keys() and project_info_db[my_url] != None:
                    lastUpdate_new = project_info_dct[my_url]
                    lastUpdate_db = project_info_db[my_url]
                    slastUpdate_new = datetime.strptime(lastUpdate_new, fmt)
                    slastUpdate_db = datetime.strptime(lastUpdate_db, fmt)
                    if slastUpdate_new <= slastUpdate_db:
                        info("Project with url %s and last update date %s is already in database" % (my_url, lastUpdate_new))
                    else:
                        debug("Project with url %s and last update date %s and new last update date %s not in database" % (my_url, lastUpdate_db, lastUpdate_new))
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

