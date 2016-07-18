#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module contains tool for checking credibility of converstion pdf -> text
processed by pdftotext utility.
"""

__modulename__ = "pdf2textcredibility"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$4-August-2010 15:13:10$"
__version__ = "$0.10.9.20$"

import re
import os
import subprocess
import tempfile
from rrslib.dictionaries.rrsdictionary import *

# ------------------------------------------------------------------------------
# TESTING:
# ------------------------------------------------------------------------------
# SPECIFICITY:
# tested on 717 samples, 15 of them had credibility < 50. All of them were
# true negative, so the algorithm has about 100% specificity (95% in real maybe).
# SENSITIVITY:
# because of large amount of samples, I tested only that samples, which had
# crediblity 50-70. Above 70 it's pretty sure, that the result is correct.
# All of samples in range 50-70 were OK (too much code inside, two-language
# version of article etc.). So I belive that sensitivity is about 90-95%...
# ------------------------------------------------------------------------------

class PDF2TextCredibility(object):
    """
    This tool checks the credibility of conversion from pdf to text using
    pdftotext tool.

    NOTE: conversion accepts utf-8 non-breaking space (\\xc2\\xa0) and counts it
    as normal space (\\x20). Without this feature were some of pdf's which
    were converted OK identifyed as badly converted (credibility < 10).
    """
    def __init__(self, wppc=80):
       if wppc == 0:
           raise AttributeError("Word per page count cannot be zero.")
       self.info = {}
       self.bnc_dict = RRSDictionary("bnc_unlemmatised2frequency", CASE_INSENSITIVE)
       self.splitted = []
       self.wppc = wppc


    def _split_into_words(self):
        self.text = re.sub("[@!\^#$%&_\*\(\)\=\[\]{}\:\"\\<>\`;\/\+\,\.\']", " ", self.text)
        self.text = re.sub("([ \t\x0c\x0a]+)|(\xc2\xa0)", " ", self.text)
        self.splitted = self.text.split(" ")
        self.cleaned = []
        for word in self.splitted:
            if len(word) < 3:
                continue
            if not re.search("[a-z]{3,}", word, re.I):
                continue
            self.cleaned.append(word.lstrip("-. ").rstrip(" .-").lower())
        del self.splitted


    def _check_words(self):
        self.ok = 0
        self.bad = 0
        #print self.cleaned
        for word in self.cleaned:
            if self.bnc_dict.contains_key(word):
                self.ok +=1
            else:
                self.bad += 1


    def _calculate_credibility(self):
        pages = self.pdfinfo[1]['Pages']
        ratio = 1.0
        words_per_page = float(self.ok)/float(pages)
        # self.wppc is 60 by default
        if words_per_page < self.wppc:
            ratio = float(words_per_page)/float(self.wppc)
        #print self.ok, self.bad, ratio
        _all = float(self.ok+self.bad)
        del self.cleaned
        if _all == 0:
            return 0
        return int((float(self.ok)/_all)*ratio*100)


    def _get_info(self, f):
        """
        Returns tuple (infocode, info_dict) where infocode is return code, which
        return pdfinfo utility and info_dict are parsed data from pdfinfo output.
        0      No error.
        1      Error opening a PDF file.
        2      Error opening an output file.
        3      Error related to PDF permissions.
        99     Other error.
        """
        tmp = tempfile.TemporaryFile(suffix='', prefix='tmp')
        devnull = open("/dev/null")
        infocode = subprocess.call(["pdfinfo", f], stdout=tmp, stderr=devnull)
        devnull.close()
        tmp.seek(0)
        pdfinfo = tmp.read()
        tmp.seek(0, os.SEEK_END)
        tmp.close()
        if infocode != 0:
            return (infocode, None)
        d = {}
        rows = pdfinfo.split("\n")
        for r in rows:
            sp = r.split(":")
            key = sp[0]
            value = ":".join(sp[1:]).lstrip(" \t")
            if key == '': continue
            d[key] = value
        return (infocode, d)


    def get_credibility(self, text_file_path, pdf_file_path):
        """
        Returns credibility (integer 0-100) of successfull conversion from pdf
        to text. The threshold is considered to be 50 - below 50 it is badly
        converted (in most cases) and above 50 it's OK.
        """
        txtfileobj = open(text_file_path, 'r')
        self.text = txtfileobj.read()
        txtfileobj.close()
        self.pdfinfo = self._get_info(pdf_file_path)
        if self.pdfinfo[0] != 0:
            return int(0)
        self._split_into_words()
        self._check_words()
        return self._calculate_credibility()



#-------------------------------------------------------------------------------
# end of clas PDF2TextCredibility
#-------------------------------------------------------------------------------


