#!/usr/bin/env python

#-------        Autor: Lucie Dvorakova      --------#
#-------           Login: xdvora1f          --------# 
#- Django pro generator vedeckych webovych portalu -#

import re
import sys
import urllib2
import urllib
import hashlib
from elasticsearch import Elasticsearch
from datetime import datetime
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer import pdfparser
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO



class Project:
    # Objekt obsahujici potrebna data do databaze
    def __init__(self, url):
        self.url = url
        self.rcn = None
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
        self.pdf = []
        self.origPdf = None
        self.parsingPdf = None
        self.namePdf = None

        self.found = True
        self.numProjWithDel = 0
        self.numDel = 0
        self.numDelOpen = 0

        self.compile_re()


    def fill_data(self):
        # Otevirani projektu a ziskavani jeho HTML
        try:
            usock = urllib2.urlopen("http://cordis.europa.eu/" + self.url)
        except urllib2.URLError:
            sys.stderr.write("Could not open %s\n" % self.url)
            self.found = False
            return
        print "------------------------------------------------------"
        print "Opening project %s..." % self.url
        data = usock.read()
        print "Opened."
        usock.close()

        # Ziskavani cisla projektu (rcn)
        self.rcn = re.search( self.reMap['rcn'], self.url).group(1)

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

        related = re.search( self.reMap['parsingPdf'], data )
        if related:
            relatedInfoTitle = re.findall( self.reMap['relatedInfoTitle'], related.group(1) )
            print "--- %s" % relatedInfoTitle
            docAndPub = re.findall( self.reMap['relatedInfoDoc'], related.group(1) )
            docAndPubName = re.findall( self.reMap['relatedInfoDocName'], related.group(1) )
            reports = re.findall( self.reMap['relatedInfoReports'], related.group(1) )
            reportsName = re.findall( self.reMap['relatedInfoReportsName'], related.group(1) )
            if docAndPub:
                self.numProjWithDel += 1
                i = 0
                self.parsingPdf = docAndPub
                self.origPdf = docAndPub
                self.namePdf = docAndPubName
                for add in docAndPub:
                    self.numDel += 1
                    add = "http://cordis.europa.eu" + add
                    print add
                    urllib.urlretrieve (add, "./tmp.pdf")
                    try:
                        txt = self.pdfToTxt("./tmp.pdf")
                    except:
                        print "Error - Retry num. 1 "
                        try:
                            urllib.urlretrieve (add, "./tmp.pdf")
                            txt = self.pdfToTxt("./tmp.pdf")
                        except:
                            print "Error - Retry num. 2 "
                            try:
                                urllib.urlretrieve (add, "./tmp.pdf")
                                txt = self.pdfToTxt("./tmp.pdf")
                            except:
                                txt = "Error"
                                print "Unable to open pdf"
                    if txt!= None and txt!= "Error":
                        myHash = hashlib.md5()
                        myHash.update(txt)
                        numHash = int(myHash.hexdigest()[:6], 16)
                        self.pdf += [ (numHash, self.namePdf[i], add, txt) ]
                        self.numDelOpen += 1
                    print txt
                    i += 1

                
            elif reports:
                self.numProjWithDel += 1
                self.namePdf = reportsName
                self.parsingPdf = self.getPdf(reports)
                self.origPdf = reports
                

    def getPdf(self,found):
        pdfs = []
        i = 0
        for add in found:
            self.numDel += 1
            try:
                usock = urllib2.urlopen("http://cordis.europa.eu/" + add)
            except urllib2.URLError:
                sys.stderr.write("Could not open %s\n" % self.url)
                return
            dataPdf = usock.read()
            usock.close()
            add = "http://cordis.europa.eu" + re.search( self.reMap['findPdf'], dataPdf ).group(1)
            print add
            urllib.urlretrieve (add, "./tmp.pdf")
            txt = None

            try:
                txt = self.pdfToTxt("./tmp.pdf")
            except:
                print "Error - Retry num. 1 "
                try:
                     urllib.urlretrieve (add, "./tmp.pdf")
                     txt = self.pdfToTxt("./tmp.pdf")
                except:
                    print "Error - Retry num. 2 "
                    try:
                        urllib.urlretrieve (add, "./tmp.pdf")
                        txt = self.pdfToTxt("./tmp.pdf")
                    except:
                        txt = "Error"
                        print "Unable to open pdf"

            if (txt == None):
                print "Error none - Retry num. 1 "
                urllib.urlretrieve (add, "./tmp.pdf")
                txt = self.pdfToTxt("./tmp.pdf")
                if (txt == None):
                    print "Error none - Retry num. 2 "
                    urllib.urlretrieve (add, "./tmp.pdf")
                    txt = self.pdfToTxt("./tmp.pdf")
                    if (txt == None):
                        print "Unable to open pdf"


            if txt!= None and txt!= "Error":
                myHash = hashlib.md5()
                myHash.update(txt)
                numHash = int(myHash.hexdigest()[:6], 16)
                self.pdf += [( numHash, self.namePdf[i], add, txt )]
                self.numDelOpen += 1

            i += 1
            pdfs.append(txt)
            print txt
        return pdfs

    def pdfToTxt(self, path):
        rsrcMgr = PDFResourceManager()
        retStr = StringIO()
        codec = 'utf-8'
        laParams = LAParams()
        device = TextConverter(rsrcMgr, retStr, codec=codec, laparams=laParams)
        fp = file(path, 'rb')
        interpreter = PDFPageInterpreter(rsrcMgr, device)
        password = ""
        maxPages = 0
        caching = True
        pageNos=set()
        for page in PDFPage.get_pages(fp,pageNos,maxpages=maxPages,password=password,caching=caching,check_extractable=True):
            interpreter.process_page(page)
        fp.close()
        device.close()
        text = retStr.getvalue()
        retStr.close()
        return text

    # Slovnik vsech predkompilovanych regexu pro ziskavani dat z HTML jednotlivych projektu
    def compile_re(self):
        self.reMap = {}

        self.reMap['rcn'] = re.compile(r'project/rcn/([0-9]+)_en.html')
        self.reMap['title'] = re.compile(r'<h2>([^<]+)<a class="printToPdf"')
        self.reMap['getDate'] = re.compile(r'<div class="projdates">\s<b>From</b>\s?([0-9-]+)\s?<b>to</b>\s?([0-9-]+)\s?')
        self.reMap['projRef'] = re.compile(r'<b>Project reference</b>:\s?([^<]+)<br/>')
        self.reMap['fundedUnder'] = re.compile(r'<b>Funded under</b>: <a href="[^"]+">([^<]+)</a>')
        self.reMap['totalCost'] = re.compile(r'<h3>Total cost:</h3>EUR([^<]+)</div>')
        self.reMap['euCon'] = re.compile(r'<h3>EU contribution:</h3>EUR([^<]+)</div>')
        self.reMap['subProg'] = re.compile(r'<h3>Subprogramme:</h3>([^<]+)</div>')
        self.reMap['callForPropos'] = re.compile(r'<h3>Call for proposal: </h3>([^<]+)<div>')
        self.reMap['fundingScheme'] = re.compile(r'<h3>Funding scheme:</h3>([^<]+)</div>')
        self.reMap['objective'] = re.compile(r'<div class="expandable">\s<div class="tech">([\s\S]*)(?=<h2>Related information</h2>)')
        self.reMap['coordMain'] = re.compile(r'<div class="coordinator">([\s\S]*)(?=participants|id="subjects")')
        self.reMap['coordIn'] = re.compile(r'<div class="country">([^<]+)</div>')
        self.reMap['coordAdd'] = re.compile(r'<div class="optional">([^\s]+)')
        self.reMap['coord'] = re.compile(r'<div class="name">([^<]+)</div>')
        self.reMap['coordName'] = re.compile(r'<div class="contact">Administrative contact:([^<]+)<br/>')
        self.reMap['coordTel'] = re.compile(r'<br/>Tel.:([^<]+)<br/>')
        self.reMap['coordFax'] = re.compile(r'<br/>Fax:([^<]+)<br/>')
        self.reMap['subject'] = re.compile(r'<a href="/projects/result_en\.html\?q=contenttype=[^\s]+ AND sicCode/code=[^\s]+ AND language=[^"]+">([^<]+)</a>')
        self.reMap['lastUpdate'] = re.compile(r'<b>Last updated on</b>: ([^<]+)</span>')
        self.reMap['parti'] = re.compile(r'<div class="participants">([\s\S]*)(id="subjects")')
        self.reMap['participants'] = re.compile(r'<div class="name">([^<]+)</div>')
        self.reMap['removeTag'] = re.compile(r'<[^>]+>')
        self.reMap['parsingPdf'] = re.compile(r'<h2>Related information</h2>([\s\S]*)(?=<div class="coordinator">)')
        self.reMap['relatedInfoDoc'] = re.compile(r'<a href="([^.]+.[pP][dD][fF])" target="_blank">[^<]+</a>')
        self.reMap['relatedInfoDocName'] = re.compile(r'<a href="[^.]+.[pP][dD][fF]" target="_blank">([^<]+)</a>')

        self.reMap['relatedInfoReports'] = re.compile(r'<a href="(/result/rcn/[^_]+_en\.html)">')
        self.reMap['relatedInfoReportsName'] = re.compile(r'<a href="[^_]+_en\.html">([^<]+)</a>')
        self.reMap['relatedInfoTitle'] = re.compile(r'<h3 class="title">([^<]+)</h3>')
        self.reMap['findPdf'] = re.compile(r'href="(/result/rcn/[^_]+_en.pdf)">\[Print to PDF\]')
        self.reMap['removePage'] = re.compile(r'\s*Page\s[0-9]\sof\s[0-9]\s*')
        self.reMap['data'] = re.compile(r'(Funded under:\s*[^\s]*|Country:\s*[^\s]*)\s*((\s|\S)*)(?=List of Websites|Related information)')



    def print_data(self):
        # Testovaci vypis ktere honoty nalezeny
        print ("%s:" % self.rcn)
        print ("  Title: %s" % self.title)
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
        #print ("  Objective:\n\t%s" % self.objective)
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
        print ("\tPDF structure: %s" % self.pdf)

        
        es = Elasticsearch(host='ibpvm.wonderland', port=9200)
        docIndex = []
        if self.pdf:
            for doc in self.pdf:
                es.index(index="deliverables", doc_type="data", id=doc[0], body={"title": doc[1],"url": doc[2],"article": doc[3]})
                print doc[1]
                docIndex += [(doc[0])]

        
     
        es.index(index="projects", doc_type="data", id=self.rcn, body={"title": self.title,"url": self.url,"startDate": self.startDate,"endDate": self.endDate,"projRef": self.projRef, "fundedUnder": self.fundedUnder, "totalCost": self.totalCost, "euCon": self.euCon, "subProg": self.subProg, "callForPropos": self.callForPropos, "fundingScheme": self.fundingScheme, "coord": self.coord, "coordName": self.coordName, "coordAdd": self.coordAdd, "coordIn": self.coordIn, "coordTel": self.coordTel,"coordFax": self.coordFax, "participants": self.participants, "objective": self.objective, "subjects": self.subject, "lastUpdate": self.lastUpdate, "deliverablesIndex": docIndex})











        
