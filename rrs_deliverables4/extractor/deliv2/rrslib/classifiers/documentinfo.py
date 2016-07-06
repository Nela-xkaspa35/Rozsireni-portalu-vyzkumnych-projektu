#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module documentinfo acts as a document classifier (tries to set correct type of
publication) and also as tuned pdfinfo unix utility.

THIS MODULE NEEDS TO BE IMPROVED AND TESTED!
"""

__modulename__ = "documentinfo"
__author__ = "Tomas Lokaj"
__email__ = "xlokaj03@stud.fit.vutbr.cz"
__date__ = "$9-September-2010 18:21:10$"


################################################################################
#Imports
################################################################################
from rrslib.dictionaries.rrsdictionary import EVENT_ACRONYMS, CASE_SENSITIVE, \
    RRSDictionary, RET_ORIG_TERM
import commands
import re
import sys

try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")
################################################################################
#End of imports
################################################################################

#Document types
PRESENTATION = "presentation"
POSTER = "poster"
ARTICLE = "article"
INPROCEEDINGS = "inproceedings"
UNPUBLISHED = "unpublished"
PHDTHESIS = "phdthesis"
MASTERTHESIS = "masterthesis"
TECHREPORT = "techreport"
MISC = "misc"


################################################################################
#Class DocumentEvaluator
################################################################################
class DocumentInfo(object):
    """
    This class collects information about PDF documents.
    """

    def __init__(self):
        self.pat_month = "january|february|march|april|may|june|july|august|"
        self.pat_month += "september|october|november|december|jan\.?|feb\.?|"
        self.pat_month += "mar\.?|apr\.?|jun\.?|jul\.?|aug\.?|sept?\.?|oct\.?|"
        self.pat_month += "nov\.?|dec\.?"
        self.pat_date = "(" + self.pat_month + \
                        " ([_0-9]+\.? )*)(19[0-9]{2}|2[0123][0-9]{2})"
        self.kws_unpublished = {"introduction":50, "abstract":50,
                                "related work":50}
        self.kws_article = {"(vol\.?|volume)\s*[0-9]+":20, self.pat_date:20,
                            "(pages?|pp?\.?)\s*[-0-9]+(?!\))":20,
                            "(number|no\.?)\s*[_0-9]+":20,
                            "copyright":20, "all rights reserved":20,
                            "journal":20, "is published":20, "published in":20,
                            "first published":20, "in press":20,
                            "introduction":50, "abstract":50,
                            "related work":50, self._find_events:50,
                            self._find_events_2:20}
        self.kws_techreport = {"this report":200, "tech[a-z]+ report":200,
                               "summary report":100, "is (a )?report":80}
        self.kws_phdthesis = {"supervisor":100, "this thesis":200,
                              "dissertation":200, "Ph\.?D thesis":200}
        self.kws_masterthesis = {"supervisor":100, "this thesis":200,
                                 "master thesis":200, "master\W?s thesis":200}
        self.types = {UNPUBLISHED:self.kws_unpublished, ARTICLE:self.kws_article,
                      PHDTHESIS:self.kws_phdthesis,
                      MASTERTHESIS:self.kws_masterthesis,
                      TECHREPORT:self.kws_techreport}

        self.re_proceedings = re.compile('\W(proceedings|conference)\W', re.DOTALL)
        self.re_ms_powerpoint = re.compile('powerpoint', re.IGNORECASE)
        self.re_oo_impress = re.compile('impress', re.IGNORECASE)
        self.re_pages = re.compile('Pages:\s*([0-9]+)')

        self.pat_chapters = "R(eferences|EFERENCES)"
        self.re_chapters = re.compile('(^.*\W)(' + self.pat_chapters + ')\W',
                                      re.DOTALL)

        #Proceedings articles patterns and RE
        self.pat_time = "[0-2]?[0-9]:[0-9][0-9]"
        self.pat_toc_page = "(\.\s*){2,}[0-9]+\n"
        self.pat_pagesep = "(\s*\n\n\s*|\s*-\s*\n\n|\n\n\s*-\s*)"
        self.pat_roman_nums = self.pat_pagesep + \
             "(XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)" + \
            self.pat_pagesep
        self.pat_page_end_strict = "(" + self.pat_pagesep + "[0-9]+" + \
            self.pat_pagesep + "|\npage [0-9]+\n|\.[0-9]+" + \
                self.pat_pagesep + ")"
        self.pat_page_end = "(" + self.pat_pagesep + "[0-9]+" + \
            self.pat_pagesep + "|\npage [0-9]+\n|\.[0-9]+\n\n|\n\n)"
        self.re_proceedings_prefix_strict = \
            re.compile("(^.+((" + self.pat_time + "|" + self.pat_toc_page + \
                       ").*" + self.pat_page_end_strict + "|" + \
                       self.pat_roman_nums + "))", re.DOTALL | re.IGNORECASE)
        self.re_proceedings_prefix = \
            re.compile("(^.+((" + self.pat_time + "|" + self.pat_toc_page + \
                       ").*" + self.pat_page_end + "|" + self.pat_roman_nums + \
                       "))", re.DOTALL | re.IGNORECASE)
        self.re_abstract = \
            re.compile("(^.+?)\n(abstract|references)(\W[^.\n]*)?\n",
                       re.DOTALL | re.IGNORECASE)
        self.re_proceedings = re.compile("(^.+?\Wproceedings\W.*?\n\n)",
                                         re.DOTALL | re.IGNORECASE)
        
        self.re_multi_strict = \
            re.compile('(^.{5000,}?\nR[Ee][Ff][Ee][Rr][Ee][Nn][Cc][Ee][Ss]\W*\n.+?' + \
                       self.pat_page_end_strict + ')', re.DOTALL)
        self.re_previous_1 = \
            re.compile('(^\s*([A-Z]\.|[A-Z]\w+[,. ]+[A-Z]\.|' + \
                       '[^\n]+?[(.,]\s*[0-9]{4}\s*[.),][^\n]+?\n|' + \
                       '[^a-zA-Z]|[a-z]|[A-Z]\w*?\.?\n|[^\n]*\Weds\W).*?' + \
                       self.pat_page_end + ')', re.DOTALL)
        self.re_previous_2 = \
            re.compile('^\s*(Introduction|INTRODUCTION|Appendix|APPENDIX|' + \
                       'Table\W+[0-9]|TABLE\W+[0-9]|Figure\W+[0-9]|' + \
                       'FIGURE\W+[0-9]|Section\W+[0-9]|SECTION\W+[0-9])',
                       re.DOTALL)


        self.rrsdict_events = RRSDictionary(EVENT_ACRONYMS, CASE_SENSITIVE)


    def _find_events(self, text):
        events = self.rrsdict_events.text_search(text, False, RET_ORIG_TERM)
        if len(events) > 0:
            return True
        else:
            return False


    def _find_events_2(self, text):
        if re.search("[0-9A-Z]+(/[0-9A-Z]+)+", text):
            return True
        else:
            return False


    def _is_proceedings(self, text):
        if self.re_proceedings.search(text):
            return True
        else:
            return False


    def _is_presentation(self, pdfinfo):
        if self.re_ms_powerpoint.search(pdfinfo):
            return True
        else:
            return False


    def _is_poster(self, pdfinfo):
        if self.re_pages.search(pdfinfo):
            pnum = int(self.re_pages.search(pdfinfo).group(1))
            if pnum == 1:
                return True
            else:
                return False
        else:
            return False


    def _shrink_text(self, text):
        if self.re_chapters.search(text):
            text = self.re_chapters.search(text).group(1)
        return text


    def get_pdfinfo(self, pdf_file_path):
        """
        Returns pdf metadata using pdfinfo program.
        """
        return commands.getoutput('pdfinfo ' + pdf_file_path)


    def get_document_type(self, text_file_path, pdf_file_path=None):
        """
        Main method.
        Returns type of specified document.
        """
        if pdf_file_path != None:
            pdfinfo = self.get_pdfinfo(pdf_file_path)
            if self._is_presentation(pdfinfo):
                return PRESENTATION
            elif self._is_poster(pdfinfo):
                return POSTER

        text_full = open(text_file_path, 'r').read()
        offset = 5000

        text_orig = text_full[0:offset]
        text_orig = self._shrink_text(text_orig)
        text = text_orig.lower()

        points = {}
        for type in self.types.keys():
            points[type] = [0, 0]
            for kw in self.types[type].keys():
                if isinstance(kw, str):
                    if re.search("(^|\W)" + kw + "(\W|$)", text, re.DOTALL):
                        points[type][0] += int(self.types[type][kw])
                        points[type][1] += 1
                else:
                    if kw(text_orig):
                        points[type][0] += int(self.types[type][kw])
                        points[type][1] += 1

        final_type = (MISC, 0)

        for type in points.keys():
            score = points[type][0]
            if score > final_type[1]:
                final_type = (type, points[type][0])

        if final_type[0] == ARTICLE and points[UNPUBLISHED][0] != 0:
            if final_type[1] - points[UNPUBLISHED][0] <= 20:
                final_type = (UNPUBLISHED, points[UNPUBLISHED][0])

        if final_type[0] == ARTICLE or final_type[0] == UNPUBLISHED:
            if self._is_proceedings(text):
                final_type = (INPROCEEDINGS, final_type[1])

        return final_type[0]
    
    def get_articles(self, text):
        """
        In case of proceedings, this method returns list of contained articles.
        """
        articles = []
        
        if self.re_abstract.search(text):
            reduced_text = self.re_abstract.search(text).group(1)
        else:
            reduced_text = text

        if self.re_proceedings_prefix_strict.search(reduced_text):
            groups = self.re_proceedings_prefix_strict.search(reduced_text)
            text = re.sub(re.escape(groups.group(1)), "", text)
        elif self.re_proceedings_prefix.search(reduced_text):
            groups = self.re_proceedings_prefix.search(reduced_text)
            text = re.sub(re.escape(groups.group(1)), "", text)
        elif self.re_proceedings.search(reduced_text):
            groups = self.re_proceedings.search(reduced_text)
            text = re.sub(re.escape(groups.group(1)), "", text)
        
        while self.re_multi_strict.search(text):
            article = self.re_multi_strict.search(text).group(1)
            text = re.sub(re.escape(article), "", text)
            while self.re_previous_1.search(article):
                previous = self.re_previous_1.search(article).group(1)
                article = re.sub(re.escape(previous), "", article)
                if len(articles) > 0:
                    articles[len(articles) - 1] += "\n" + previous
            if self.re_previous_2.search(article)and len(articles) > 0:
                articles[len(articles) - 1] += "\n\n" + article
            else:
                articles.append(article)

        if len(articles) == 1:
            articles = []
        return articles
################################################################################
#End of class DocumentInfo
################################################################################

if __name__ == '__main__':
    DI = DocumentInfo()
    fileno = "01"
    text_file_path = "/media/Data/RRS/files/multi_articles/txt/" + str(fileno) + ".txt"
    pdf_file_path = "/media/Data/RRS/files/multi_articles/pdf/" + str(fileno) + ".pdf"
    text = open(text_file_path, 'r').read()
    #print DI.get_pdfinfo(pdf_file_path)
    #print DI.get_document_type(text_file_path, pdf_file_path)
    articles = DI.get_articles(text)
    for article in articles:
        print "------------------------------------------------------------"
        print article[0:500]
        print "------------------------------------------------------------\n\n"
            
