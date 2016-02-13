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

BASE_URL = "http://cordis.europa.eu/projects/result_en?q=programme/code=%27FP7%27%20AND%20contenttype=%27project%27"
DEFAULT_PROJECT_LIST_FILENAME="project_urls.txt"

# globally used regexes
reMap = {}
reMap['notFound'] = re.compile(r'No result found')
reMap['projURL'] = re.compile(r'<span class="contenttype">\[[^>]+\]</span>[^<]+<a href="([^"]+)">')
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
 
    base_url = aURL + "%20AND%20/project/startDate=" + \
        aDate1.strftime("%Y-%m-%d") + "-" + aDate2.strftime("%Y-%m-%d")

    # List of projects URLs
    urls = []

    # Pager
    page = 1

    # Fetch content of each page 
    while True:
        page_url = base_url + "&p=" + str(page) + "&num=20"
        info("Opening page %s - %s" % (page, page_url))
        data = fetchUrl(page_url)

        if data != None:
            if re.search(reMap['notFound'], data):
                break
            else:
                new_urls = re.findall(reMap['projURL'], data)
                urls += new_urls
                debug(new_urls)

        page += 1 

    return urls

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

def findProjects(aFile, aBaseUrl, aFrom, aTo):
     # List of project urls
    urls = []

    # Gather URLs all projects year by year
    intervals = splitByYears(aFrom, aTo)
    for (date1, date2) in intervals:
        urls += getProjectURLs(aBaseUrl, date1, date2)

    # Store URL list
    with open(aFile, "w") as fout:
        for url in urls:
            fout.write(url + "\n")

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

