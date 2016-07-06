#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

from extractor import *
import datetime

BASE_URL = "http://cordis.europa.eu/projects/result_en?q=programme/code=%27FP7%27%20AND%20contenttype=%27project%27"
DEFAULT_PROJECT_LIST_FILENAME="project_urls.txt"

def main():
    '''
    Update script entry point.
    '''
    today = datetime.datetime.today()
    delta = datetime.timedelta(weeks=10)
    beta = datetime.timedelta(weeks=1000)
    start_time = today - delta
    update_time = today - beta
    '''
    for i in [1, 2, 3]:
        findProjects(DEFAULT_PROJECT_LIST_FILENAME, BASE_URL, \
          start_time, today, "start")
        indexProjects(DEFAULT_PROJECT_LIST_FILENAME)
    '''

    findProjects(DEFAULT_PROJECT_LIST_FILENAME, BASE_URL, \
        update_time, today)
    indexProjects(DEFAULT_PROJECT_LIST_FILENAME)

if __name__ == "__main__":
    main()

