#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import unittest
from query import *

class TestQuery(unittest.TestCase):
    def test_SimpleQuery(self):
        q = Query("nuclear")
        self.assertTrue("nuclear" in q.keywords)

    def test_ComplexQueries(self): 
        q = Query('nuclear programme:fp7 country:"Czech Republic" "subprogramme":PEOPLE')
        self.assertTrue("nuclear" in q.keywords)
        self.assertEqual(q.specifications["programme"], "fp7")
        self.assertEqual(q.specifications["country"], "Czech Republic")
        self.assertEqual(q.specifications["subprogramme"], "PEOPLE")

    def test_TrickyQueries(self):
        #lex = QueryLexer()
        #print lex.tokenize('nucle\\:ar bbb')
        #par = QueryParser()
        #print par.parse('nucle\\:ar bbb')

        q = Query('coordIn\\:ar coordIn:ar bbb\\:')
        print q.keywords
        print q.specifications

        q = Query('nuclear country:"France"')
        print q.keywords
        print q.specifications

       
        #self.assertTrue('nucle"ar' in q.keywords)
        #q = Query('nucle"ar')
        #print q.keywords

if __name__ == "__main__":
    unittest.main()
