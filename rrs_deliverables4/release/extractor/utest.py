#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import unittest
import random
import string
import os
from common import *
from project import *
from delivs import *

TPDF = "./test_tmp.pdf"
TPDFLINK = "http://decipher-research.eu/sites/decipherdrupal/files/decipher_presentation_version_01_1.pdf"
TPROJ = "/project/rcn/97302_en.html"
TWEB = "http://decipher-research.eu/"

class TestCommon(unittest.TestCase):
    def test_Hash_Eq(self):
        w1 = "nuclear"
        w2 = "n" + "uclear"
        h1 = computeHash(w1)
        h2 = computeHash(w2)
        self.assertEqual(h1, h2)

    def test_Hash_Neq(self):
        w1 = "nuclear"
        w2 = "n" + "uclea"
        h1 = computeHash(w1)
        h2 = computeHash(w2)
        self.assertFalse(h1 == h2)

    def test_Hash_Max(self):
        for i in range(20):
            n = random.randint(1,1000)
            text = ''.join([ random.choice(string.letters) for _ in range(n) ])
            h = computeHash(text)
            self.assertTrue(h <= 16777215)

    def test_Normalize_Simple(self):
        text = r'Deliverable         with \nencoded white \n\r\tcharacters.'
        exp = r'Deliverable with encoded white characters.'
        self.assertEqual(normalize(text), exp)

    def test_Normalize_Adv1(self):
        text = r'Deliverable    <b>     with \nencoded <img src=" " />white \n\r\tcharacters</b>.'
        exp = r'Deliverable with encoded white characters.'
        self.assertEqual(normalize(text), exp)

    def test_Normalize_Adv2(self):
        text = r'Deliverable    <b>     with \nen-     coded <img src=" " />white \n\r\tchara-   cters</b>.'
        exp = r'Deliverable with encoded white characters.'
        self.assertEqual(normalize(text), exp)

    def test_Normalize_Adv3(self):
        text = r'equipment, by:\n&#149;\tDefining an unified'
        exp = r'equipment, by: Defining an unified'
        self.assertEqual(normalize(text), exp)

    def test_Normalize_Adv4(self):
        text = r'dedicated tasks. &lt;br/&gt;Virtualization technology'
        exp = r'dedicated tasks. Virtualization technology'
        self.assertEqual(normalize(text), exp)

    def test_Download(self):
        downloadFile(TPDFLINK, TPDF)
        self.assertTrue(os.path.exists(TPDF))
        os.remove(TPDF)

class TestPDF(unittest.TestCase):
    @classmethod
    def setUp(cls):
        if not os.path.exists(TPDF):
            downloadFile(TPDFLINK, TPDF)

    @classmethod
    def tearDown(cls):
        if os.path.exists(TPDF):
            os.remove(TPDF)

    def test_Pdf2Txt_Simple(self):
        text = pdf2txt(TPDF)
        self.assertTrue(text.find("Brno University of Technology") > 0)
        self.assertTrue(text.find("aaaa") == -1)

    def test_Pdf2Txt_Adv1(self):
        text = normalize(pdf2txt(TPDF))
        self.assertTrue(text.find("Brno University of Technology") > 0)
        self.assertTrue(text.find("  ") == -1)

    def test_Pdf2Txt_Adv2(self):
        text = normalize(pdf2txt(TPDF+"aaaa"))
        self.assertTrue(text == None)

class TestProject(unittest.TestCase):
    def test_Init(self):
        proj = Project(TPROJ)
        self.assertTrue(proj != None)
        self.assertEqual(proj.url, TPROJ)
        self.assertEqual(proj.rcn, "97302")
        self.assertTrue(hasattr(proj, "origWeb"))
        self.assertEqual(proj.origWeb, None)

    def test_Fill(self):
        proj = Project(TPROJ)
        proj.fillData(False)
        self.assertEqual(proj.abbr, "Decipher")
        self.assertEqual(proj.coordIn, "Ireland")
        self.assertEqual(proj.nDelivs, 4)

    def test_Delivs(self):
        (page, delivs) = findDeliverables2(TWEB)
        self.assertEqual(page, "http://decipher-research.eu/deliverables-resources")
        urls = [ deliv[1] for deliv in delivs ]
        self.assertTrue("http://decipher-research.eu/sites/decipherdrupal/files/Decipher-D8.1.3-RIA-Dissemination-Showcase.pdf" in urls)

if __name__ == "__main__":
    unittest.main(verbosity=2)
