#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

# // Command()
import subprocess, threading

# // downloadFile()
import socket
import urllib2

# // computeHash()
import hashlib

# // re.sub()
import re

# // listdir()
import os

# // pdf2txt()
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer import pdfparser
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

# default timeout for web related operations
DEFAULT_TIMEOUT=30

def info(aText):
    print "Info: %s" % str(aText)

def warn(aText):
    print "WARNING: %s" % str(aText)

def err(aText):
    print "ERROR: %s" % str(aText)

def debug(aText):
    print "DEBUG: %s" % str(aText)

class Command(object):
    '''
    Objekt umoznujici spoustet libovolny prikaz v oddelenem vlakne
    s podporou timeoutu.
    '''

    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        def target():
            debug("Separate process started ...")
            try:
                self.process = subprocess.Popen(self.cmd, shell=True)
                self.process.communicate()
            except: 
                err("Error of process ...")
                self.process = None
            debug("Process finished ...")

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        i = 1
        while thread.is_alive():
            warn("Timeout reached -- terminating (%d) ..." % i)
            i += 1
            if self.process != None:
                self.process.kill()
            thread.join(2)
        if self.process != None:
            debug("Process return code: %d" % self.process.returncode)
        else:
            debug("Process finished with an error!")
        

def fetchUrl(aUrl):
    '''
    Downloads a given URL. Returns None if the download fails.
    '''

    dto = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DEFAULT_TIMEOUT)

    try:
        response = urllib2.urlopen(aUrl, timeout=DEFAULT_TIMEOUT)
        ret = response.read()
        response.close()
    except:
        warn("First retry of URL download")
        try:
            response = urllib2.urlopen(aUrl, timeout=DEFAULT_TIMEOUT)
            ret = response.read()
            response.close()
        except:
            err("Cannot download URL")
            ret = None

    return ret

def downloadFile(aUrl, aTarget):
    '''
    Downloads a file and stores it under a given name. Returns False
    if the download fails. Otherwise, returns True.
    '''

    dto = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DEFAULT_TIMEOUT)

    ret = True
    try:
        response = urllib2.urlopen(aUrl, timeout=DEFAULT_TIMEOUT)
        pdf = response.read()
        response.close()
    except:
        warn("First retry of PDF download")
        try:
            response = urllib2.urlopen(aUrl, timeout=DEFAULT_TIMEOUT)
            pdf = response.read()
            response.close()
        except:
            err("Cannot download PDF")
            ret = False

    socket.setdefaulttimeout(dto)

    if ret:
        fout = open(aTarget, "wb")
        fout.write(pdf)
        fout.close()

    return ret

def findDeliverables(aUrl):
    # Call an external command with timeout
    info("Trying to download deliverables from: %s" % aUrl)
    cmd = Command("python ./rrs_deliverables/deliverables.py -v -s -u %s" % aUrl)
    cmd.run(DEFAULT_TIMEOUT)

    # Collect found links located in an XML file
    files = os.listdir(".")
    xmls = [ x for x in files if x.lower().endswith(".xml") ]

    # Search through downloaded XML files
    links = []
    for xml in xmls:
        with open(xml, "r") as fin:
            data = fin.read()
            links += re.findall(r'<publication[^<]*<title value="([^"]*)"[^<]*<url[^<]*<link value="([^"]*)"', data)
        os.remove(xml)

    return links

def pdf2txt(path):
    '''
    Converts a given PDF to plain text in UTF8.
    '''

    try:
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
    except:
        return None

def normalize(txt):
    if txt == None:
        return None

    # remove sequences of dots and dashes
    txt = re.sub(r'\s|\.\s*\.\s*\.\s*[\.\s*]+|-\s*-\s*-\s*[-\s*]+', " ", txt)
    # remove encoded EOLs and tabs
    txt = re.sub(r'\\[ntr]', " ", txt)
    # remove xml tags
    txt = re.sub(r'<[^>]+>', "", txt)
    # remove endcoded xml tags
    txt = re.sub(r'&lt;[^&]+&gt;', "", txt)
    # remove html entities
    txt = re.sub(r'&[^ ]+;', " ", txt)
    #txt = re.sub(r'\\u(..)(..)', lambda match: (chr(int(match.group(2), 16))+chr(int(match.group(1), 16))).decode("utf-16le"), txt)
    # remove sequences of spaces
    txt = re.sub(r'\s+', " ", txt)
    # join splitted words
    txt = re.sub(r'(\w)- (\w)', r'\1\2', txt)

    return txt

def computeHash(txt):
    myHash = hashlib.md5()
    myHash.update(txt)
    numHash = int(myHash.hexdigest()[:6], 16)
    return numHash

    #txt = re.sub(r'\\u(..)(..)', lambda match: (chr(int(match.group(2), 16))+chr(int(match.group(1), 16))).decode("utf-16le"), txt)
    # remove sequences of spaces
    txt = re.sub(r'\s+', " ", txt)
    # join splitted words
    txt = re.sub(r'(\w)- (\w)', r'\1\2', txt)

    return txt

def computeHash(txt):
    myHash = hashlib.md5()
    myHash.update(txt)
    numHash = int(myHash.hexdigest()[:6], 16)
    return numHash

