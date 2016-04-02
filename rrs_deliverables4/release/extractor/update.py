#!/usr/bin/env python
# -*- coding: utf-8 -*-

#------------        Autori: Martin Cvicek, Lucie Dvorakova      -------------#
#----------------           Loginy: xcvice01, xdvora1f         ---------------# 
#-- Rozšíření portálu evropských výzkumných projektů o pokročilé vyhledávání -#
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
    delta = datetime.timedelta(weeks=50)
    beta = datetime.timedelta(weeks=500)
    start_time = today - delta
    update_time = today - beta
    
    for x in range(0, 3):
        findProjects(DEFAULT_PROJECT_LIST_FILENAME, BASE_URL, \
            start_time, today, "start")
        indexProjects(DEFAULT_PROJECT_LIST_FILENAME)
    '''
    findProjects(DEFAULT_PROJECT_LIST_FILENAME, BASE_URL, \
        update_time, today, "update")
    indexProjects(DEFAULT_PROJECT_LIST_FILENAME)
    '''        
if __name__ == "__main__":
    main()

