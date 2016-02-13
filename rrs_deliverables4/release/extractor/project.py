#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

from common import *
from delivs import *

import re
from elasticsearch import Elasticsearch

HOST        = "localhost"
PORT        = 9200
IDXPROJ     = "xdvora1f_projects"
IDXDELIV    = "xdvora1f_deliverables"
DOCTYPE     = "data"
URL_BASE    = "http://cordis.europa.eu"

class Project:
    '''
    Objekt obsahujici potrebna data do databaze.
    '''

    def __init__(self, url):
        self.compileRe()

        self.url = url
        self.rcn = None
        self.abbr = None
        self.programme = None
        self.subprogramme = None
        self.year = None
        self.title = None
        self.startDate = None
        self.endDate = None
        self.projRef = None
        self.fundedUnder = None
        self.totalCost = None
        self.euCon = None
        self.subProg = None
        self.callForPropos = None
        self.fundingScheme = None
        self.objective = None
        self.coord = None
        self.coordIn = None
        self.coordName = None
        self.coordAdd = None
        self.coordTel = None
        self.coordFax = None
        self.subject = None
        self.lastUpdate = None
        self.participants = None
        self.partCountries = None
        self.pdf = []
        #self.origPdf = None
        #self.parsingPdf = None
        #self.namePdf = None
        self.origWeb = None
        self.delivWeb = None

        self.found = False
        self.hasDelivs = False
        self.nDelivs = 0
        self.nDelivsOk = 0
        self.nExtDelivs = 0
        self.nExtDelivsOk = 0

        # Ziskavani cisla projektu (rcn)
        self.rcn = re.search( self.reMap['rcn'], self.url).group(1)

    def fillData(self, getExternalDelivs=True):
        '''
        Otevirani projektu a ziskavani jeho HTML.
        '''

        url = URL_BASE + self.url
        info("Opening project %s ..." % self.url)
        data = fetchUrl(url)
        if data == None:
            err("Could not open %s!" % self.url)
            self.found = False
            return
        
        self.found = True

        # Ziskavani cisla projektu (rcn)
        self.rcn = re.search( self.reMap['rcn'], self.url).group(1)

        # Ziskavani zkratky
        found = re.search( self.reMap['abbr'], data )
        if found:
            self.abbr = found.group(1).strip()

        # Ziskavani nadpisu
        found = re.search( self.reMap['title'], data )
        if found:
            self.title = found.group(1).strip()

        # Ziskavani start a end dates 
        found = re.search( self.reMap['getDate'], data )
        if found:
            self.startDate = found.group(1).strip()

        if found:
            self.endDate = found.group(2).strip()

        # Ziskavani reference, contribution, cost
        found = re.search( self.reMap['projRef'], data )
        if found:
            self.projRef = found.group(1).strip()

        found = re.search( self.reMap['fundedUnder'], data )
        if found:
            self.fundedUnder = found.group(1).strip()

        found = re.search( self.reMap['totalCost'], data )
        if found:
            self.totalCost = found.group(1).replace(' ','')

        found = re.search( self.reMap['euCon'], data )
        if found:
            self.euCon = found.group(1).replace(' ','')

        # Ziskavani subprogamme a objective
        found = re.search( self.reMap['subProg'], data )
        if found:
            self.subProg = found.group(1).strip()

        found = re.search( self.reMap['callForPropos'], data )
        if found:
            self.callForPropos = found.group(1).strip()

        found = re.search( self.reMap['fundingScheme'], data )
        if found:
            self.fundingScheme = found.group(1).strip()

        found = re.search( self.reMap['objective'], data )
        if found:
            obje = found.group(1)
            self.objective = re.sub(self.reMap['removeTag'], '', obje).strip()

        #Ziskavani Coordinate info\
        coords = re.search( self.reMap['coordMain'], data )
        #print coords.group(1)
        if coords:
            found = re.search( self.reMap['coord'], coords.group(1) )
            if found:
                self.coord = found.group(1).strip()

            found = re.search( self.reMap['coordIn'], coords.group(1) )
            if found:
                self.coordIn = found.group(1).strip()

            found = re.search( self.reMap['coordAdd'], coords.group(1) )
            if found:
                self.coordAdd = found.group(1).strip()

            found = re.search( self.reMap['coordName'], coords.group(1) )
            if found:
                self.coordName = found.group(1).strip()

            found = re.search( self.reMap['coordTel'], coords.group(1) )
            if found:
                self.coordTel = found.group(1).strip()

            found = re.search( self.reMap['coordFax'], coords.group(1) )
            if found:
                self.coordFax = found.group(1).strip() 

        found = re.findall( self.reMap['subject'], data )
        if found:
            self.subject = found

        found = re.search( self.reMap['lastUpdate'], data )
        if found:
            self.lastUpdate = found.group(1).strip()

        parti = re.search( self.reMap['parti'], data )
        #print "--- %s" % parti.group(1)
        if parti:
            found = re.findall( self.reMap['participants'], parti.group(1) )
            if found:
                self.participants = found
            found = re.findall( self.reMap['partCountries'], parti.group(1) )
            if found:
                self.partCountries = found

        related = re.search( self.reMap['parsingPdf'], data )
        if related:
            # Project has a related info section
            relatedInfoTitle = re.findall( self.reMap['relatedInfoTitle'], related.group(1) )
            debug("Found relation info title: %s" % relatedInfoTitle)

            # Try to find reports first
            reports = re.findall( self.reMap['relatedInfoReports'], related.group(1) )
            reportsName = re.findall( self.reMap['relatedInfoReportsName'], related.group(1) )
            if len(reports) > 0:
                i = 0
                # Only one report is expected
                # FIXME: Is the above assumption correct???
                for deliv_url in reports:
                    pdf_html = fetchUrl(URL_BASE + deliv_url)
                    if pdf_html != None:
                        # Urcteni URL deliverable
                        pdf_url = URL_BASE + re.search(self.reMap['findPdf'], \
                            pdf_html).group(1)

                        # Stahnuti deliverable a jeho konverze
                        txt = None
                        info("Attempt to download: %s" % pdf_url)
                        if downloadFile(pdf_url, "./tmp.pdf"):
                            txt = pdf2txt("./tmp.pdf")
                            if txt != None:
                                numHash = computeHash(txt)
                                self.pdf += [( numHash, reportsName[i], pdf_url, txt )]
                                self.nDelivsOk += 1
                    i += 1
 


            # Next, try to search for Document & Publications
            docAndPub = re.findall( self.reMap['relatedInfoDoc'], related.group(1) )
            docAndPubName = re.findall( self.reMap['relatedInfoDocName'], related.group(1) )
            if len(docAndPub) > 0:
                i = 0
                for deliv_url in docAndPub:
                    pdf_url = URL_BASE + deliv_url

                    # Stahnuti deliverable a jeho konverze
                    txt = None
                    info("Attempt to download: %s" % pdf_url)
                    if downloadFile(pdf_url, "./tmp.pdf"):
                        txt = pdf2txt("./tmp.pdf")
                        if txt != None:
                            numHash = computeHash(txt)
                            self.pdf += [( numHash, docAndPubName[i], pdf_url, txt )]
                            self.nDelivsOk += 1
 
                    i += 1


            # Count downloaded deliverables
            if len(docAndPub) > 0 and len(reports) > 0:
                warn("Documents & Publications and Reports both contains some records.")
            self.nDelivs = len(reports) + len(docAndPub)

            # Finally, search for any external links
            web = re.search( self.reMap['origWeb'], related.group(1) )
            if web:
                self.origWeb = web.group(1)

                if getExternalDelivs:
                    # Use RRS Deliverables to find links to third party deliverables
                    delivs = findDeliverables2(self.origWeb)

                    nextok = 0
                    # Try to download the newly found deliverables
                    for (pdf_title, pdf_url) in delivs[1]:
                        # Stahnuti deliverable a jeho konverze
                        txt = None
                        info("Attempt to download: %s" % pdf_url)
                        if downloadFile(pdf_url, "./tmp.pdf"):
                            txt = pdf2txt("./tmp.pdf")
                            if txt != None:
                                numHash = computeHash(txt)
                                self.pdf += [( numHash, pdf_title, pdf_url, txt )]
                                nextok += 1

                    nextfound = len(delivs[1])
                    self.delivWeb = delivs[0] 
                    self.nExtDelivs = nextfound
                    self.nExtDelivsOk = nextok

        prog_done = False
        if self.fundedUnder:
            found = re.search(r'([^-]+)-(.*)', self.fundedUnder)
            if found:
                self.programme      = found.group(1).strip()
                self.subprogramme   = found.group(2).strip()
                prog_done = True
            
        if not prog_done and self.subProg:
            found = re.search(r'([^-]+)-([^-]+)', self.subProg)
            if found:
                self.programme      = found.group(1).strip()
                self.subprogramme   = found.group(2).strip()

        start = self.startDate
        if start != None and len(start) > 4:
            self.year = start[:4]

        #self.hasDelivs = self.nDelivs > 0
        #debug("aaa: %d %s)" % (self.nDelivs, self.pdf))
        #raw_input("aaa")

    def compileRe(self):
        '''
        Slovnik vsech predkompilovanych regexu pro ziskavani dat z HTML
        jednotlivych projektu.
        '''

        self.reMap = {}

        self.reMap['abbr'] = re.compile(r'<h1[^>]*>([^<]+)</h1>\s*<b>Project reference', re.M)
        self.reMap['rcn'] = re.compile(r'project/rcn/([0-9]+)_en.html')
        self.reMap['title'] = re.compile(r'<h2>([^<]+)<a class="printToPdf[^"]*"')
        self.reMap['getDate'] = re.compile(r'<div class="projdates[^"]*">\s<b>From</b>\s?([0-9-]+)\s?<b>to</b>\s?([0-9-]+)\s?')
        self.reMap['projRef'] = re.compile(r'<b>Project reference</b>:\s?([^<]+)<br/>')
        self.reMap['fundedUnder'] = re.compile(r'<b>Funded under</b>: <a href="[^"]+">([^<]+)</a>')
        self.reMap['totalCost'] = re.compile(r'<h3>Total cost:</h3>EUR([^<]+)</div>')
        self.reMap['euCon'] = re.compile(r'<h3>EU contribution:</h3>EUR([^<]+)</div>')
        self.reMap['coordIn'] = re.compile(r'<div class="country[^"]*">([^<]+)</div>')
        self.reMap['subProg'] = re.compile(r'<h3>Subprogramme:</h3>([^<]+)</div>')
        self.reMap['callForPropos'] = re.compile(r'<h3>Call for proposal: </h3>([^<]+)<div>')
        self.reMap['fundingScheme'] = re.compile(r'<h3>Funding scheme:</h3>([^<]+)</div>')
        #self.reMap['objective'] = re.compile(r'<div class="expandable[^"]*">\s<div class="tech[^"]*">([\s\S]*)(?=<h2>Related information</h2>)')
        self.reMap['objective'] = re.compile(r'<div class="tech[^"]*">([\s\S]*?)<h2')
        self.reMap['coordMain'] = re.compile(r'<div class="coordinator[^"]*">([\s\S]*)(?=participants|id="subjects")')
        self.reMap['coordAdd'] = re.compile(r'<div class="optional[^"]*">([^\s]+)')
        self.reMap['coord'] = re.compile(r'<div class="name[^"]*">([^<]+)</div>')
        self.reMap['coordName'] = re.compile(r'<div class="contact[^"]*">Administrative contact:([^<]+)<br/>')
        self.reMap['coordTel'] = re.compile(r'<br/>Tel.:([^<]+)<br/>')
        self.reMap['coordFax'] = re.compile(r'<br/>Fax:([^<]+)<br/>')
        self.reMap['subject'] = re.compile(r'<a href="/projects/result_en\.html\?q=contenttype=[^\s]+ AND sicCode/code=[^\s]+ AND language=[^"]+">([^<]+)</a>')
        self.reMap['lastUpdate'] = re.compile(r'<b>Last updated on</b>: ([^<]+)</span>')
        self.reMap['parti'] = re.compile(r'<div class="participants[^"]*">([\s\S]*)(id="subjects")')
        self.reMap['participants'] = re.compile(r'<div class="name[^"]*">([^<]+)</div>')
        self.reMap['partCountries'] = re.compile(r'<div class="country[^"]*">([^<]+)</div>')
        self.reMap['removeTag'] = re.compile(r'<[^>]+>')
        self.reMap['parsingPdf'] = re.compile(r'<h2>Related information</h2>([\s\S]*)(?=<div class="coordinator[^"]*">)')
        self.reMap['relatedInfoDoc'] = re.compile(r'<a href="([^.]+.[pP][dD][fF])" target="_blank">[^<]+</a>')
        self.reMap['relatedInfoDocName'] = re.compile(r'<a href="[^.]+.[pP][dD][fF]" target="_blank">([^<]+)</a>')

        self.reMap['relatedInfoReports'] = re.compile(r'<a href="([^_]+_en\.html)">')
        self.reMap['relatedInfoReportsName'] = re.compile(r'<a href="[^_]+_en\.html">([^<]+)</a>')
        self.reMap['relatedInfoTitle'] = re.compile(r'<h3 class="title[^"]*">([^<]+)</h3>')
        self.reMap['findPdf'] = re.compile(r'href="(/[^_]+_en.pdf)">\[Print to PDF\]')
        self.reMap['removePage'] = re.compile(r'\s*Page\s[0-9]\sof\s[0-9]\s*')
        self.reMap['origWeb'] = re.compile(r'<h3 class="title[^"]*">Multimedia</h3>\s</div>\s<div class="content[^"]*">\s<ul>\s<li>\s<a href="([^"]+)" target="_blank">([^<]+)</a>')

    def printData(self):
        '''
        Testovaci vypis, ktere hodnoty byly nalezeny.
        '''

        print ("%s:" % self.rcn)
        print ("  Title: %s" % self.title)
        print ("\tAbbreviation: %s" % self.abbr)
        print ("\tStart date: %s" % self.startDate)
        print ("\tEnd date: %s" % self.endDate)
        print ("\tProject refrence: %s" % self.projRef)
        print ("\tFunded under: %s" % self.fundedUnder)
        print ("\tTotal cost in EUR: %s" % self.totalCost)
        print ("\tEU contribution in EUR: %s" % self.euCon)
        print ("\tSubprogramme: %s" % self.subProg)
        print ("\tCall for proposal: %s" % self.callForPropos)
        print ("\tFunding scheme: %s" % self.fundingScheme)
        print ("\tParticipants: %s" % self.participants)
        print ("\tParticipants' countries: %s" % self.partCountries)
        print ("\tWeb: %s" % self.origWeb)
        print ("\tSubject: %s" % self.subject)
        print ("\tLast updated on: %s" % self.lastUpdate)
        print ("  Coordinator: %s" % self.coord)
        print ("\tName: %s" % self.coordName)
        print ("\tAddress: %s" % self.coordAdd)
        print ("\tCountry: %s" % self.coordIn)
        print ("\tTel.: %s" % self.coordTel)
        print ("\tFax: %s" % self.coordFax)
        #print ("\tPDF name: %s" % self.namePdf)
        #print ("\tPDF data: %s" % self.parsingPdf)
        if len(self.pdf) > 0:
            print ("\tPDF structure: Extracted")
        else:
            print ("\tPDF structure: Empty")

    def normalizeData(self):
        if self.objective != None:
            self.objective = normalize(self.objective)

        if self.subProg != None:
            self.subProg = normalize(self.subProg)

        if self.title != None:
            self.title = normalize(self.title)

        newpdfs = []
        for (pdf_id, pdf_title, pdf_url, pdf_article) in self.pdf:
            newpdfs += [ (pdf_id, normalize(pdf_title), pdf_url, normalize(pdf_article)) ]

        #print self.pdf
        #print newpdfs
        #raw_input("bbb")
        self.pdf = newpdfs

        return True

    def indexData(self):
        '''
        Indexace projektu.
        '''

        # Connection to ElasticSearch database
        try:
            es = Elasticsearch(host=HOST, port=PORT)
        except Exception as e:
            err("Connection to ElasticSearch cannot be established!")
            err(str(e))
            return False

        # Index project first
        project = \
        {
            "id":                   self.rcn,
            "abbr":                 self.abbr,
            "programme":            self.programme,
            "subprogramme":         self.subprogramme,
            "year":                 self.year,
            "callForPropos":        self.callForPropos,
            "coordinator":          self.coord,
            "coordAdd":             self.coordAdd,
            "coordFax":             self.coordFax,
            "country":              self.coordIn,
            "coordName":            self.coordName,
            "coordTel":             self.coordTel,
            "endDate":              self.endDate,
            "euCon":                self.euCon,
            "fundedUnder":          self.fundedUnder,
            "fundingScheme":        self.fundingScheme,
            "lastUpdate":           self.lastUpdate,
            "objective":            self.objective,
            "origWeb":              self.origWeb,
            "delivWeb":             self.delivWeb,
            "participant":          self.participants,
            "partCountry":          self.partCountries,
            "projRef":              self.projRef,
            "startDate":            self.startDate,
            "subProg":              self.subProg,
            "subjects":             self.subject,
            "title":                self.title,
            "totalCost":            self.totalCost,
            "url":                  self.url,
            "ndelivs":              self.nDelivs,
            "ndelivsok":            self.nDelivsOk,
            "nextdelivs":           self.nExtDelivs,
            "nextdelivsok":         self.nExtDelivsOk,
            "isextracted":          self.found,
            "extraInfo":            ""
        }
        try:
            es.index(index=IDXPROJ, doc_type=DOCTYPE, id=project["id"], body=project)
        except Exception as e:
            err("Project indexing ended with an error!")
            err(str(e))
            return False

        # Then, index its deliverables. Database is intentionally denormalized.
        if self.pdf:
            for pdf in self.pdf:
                doc = project.copy()
                doc["deliv_id"] = pdf[0]
                doc["deliv_title"] = pdf[1]
                doc["deliv_url"] = pdf[2]
                doc["deliv_article"] = pdf[3]
                doc["deliv_extraInfo"] = ""
                try:
                    es.index(index=IDXDELIV, doc_type=DOCTYPE, id=doc["deliv_id"], body=doc)
                except Exception as e:
                    err("Deliverable indexing ended with an error!")
                    err(str(e))
                    # Try to index remaing deliverables ...
                    #return False

        return True

    @classmethod
    def updateExtDelivs(cls, aDate1, aDate2):
        if aDate1 > aDate2:
            return

        # Connection to ElasticSearch database
        try:
            es = Elasticsearch(host=HOST, port=PORT)
        except:
            err("Connection to ElasticSearch cannot be established!")
            return

        # ranged query built from input dates
        qbody = {
                "filter" : {
                    "and" : [ 
                        { "not" : {
                            "missing" : { "field" : "origWeb" }
                        }},
                        { "range" : {
                            "startDate" : {
                                "gte" : aDate1,
                                "lte" : aDate2
                            }
                        }}
                    ]
                }
        }

        # total no. of results
        total = es.search(index=IDXPROJ, doc_type=DOCTYPE, body=qbody, size=1)
        total = int(total["hits"]["total"])
        # procced by result page by page
        for page in range(0,total,10):
            results = es.search(index=IDXPROJ, doc_type=DOCTYPE, body=qbody, from_=page, size=10)
            hits = results["hits"]["hits"]
            print "Page %d:" % page
            for hit in hits:
                proj = hit["_source"]
                web = proj["origWeb"]
                pdfs = []
                nfound = 0
                nok = 0

                # Use RRS Deliverable to find links to third party deliverables
                delivs = findDeliverables2(web)

                # Try to download the newly found deliverables
                for (pdf_title, pdf_url) in delivs[1]:
                    # Stahnuti deliverable a jeho konverze
                    txt = None
                    info("Attempt to download: %s" % pdf_url)
                    if downloadFile(pdf_url, "./tmp.pdf"):
                        txt = pdf2txt("./tmp.pdf")
                        if txt != None:
                            numHash = computeHash(txt)
                            pdfs += [( numHash, pdf_title, pdf_url, txt )]
                            nok += 1

                nfound = len(delivs[1])
                proj["delivWeb"] = delivs[0] 
                proj["nextdelivs"] = nfound
                proj["nextdelivsok"] = nok

                print proj["id"], proj["origWeb"], proj["delivWeb"], nfound, nok
                try:
                    es.index(index=IDXPROJ, doc_type=DOCTYPE, id=proj["id"], body=proj)
                except Exception as e:
                    err("Project indexing ended with an error!")
                    err(str(e))

                # Then, index its deliverables. Database is intentionally denormalized.
                if pdfs:
                    for pdf in pdfs:
                        doc = proj.copy()
                        doc["deliv_id"] = pdf[0]
                        doc["deliv_title"] = pdf[1]
                        doc["deliv_url"] = pdf[2]
                        doc["deliv_article"] = pdf[3]
                        doc["deliv_extraInfo"] = ""
                        try:
                            es.index(index=IDXDELIV, doc_type=DOCTYPE, id=doc["deliv_id"], body=doc)
                        except Exception as e:
                            err("Deliverable indexing ended with an error!")
                            err(str(e))
                            # Try to index remaing deliverables ...
                            #return False
