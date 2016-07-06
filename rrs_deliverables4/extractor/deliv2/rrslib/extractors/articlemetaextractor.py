#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ArticleMetaExtractor
"""


from citationentityextractor import CitationEntityExtractor
from documentwrapper import DocumentWrapper, TextualDocument
from rrslib.classifiers.documentinfo import DocumentInfo
from rrslib.classifiers.language import LanguageIdentifier
from rrslib.db.model import RRSKeyword, RRSContact, RRSPublication, \
    RRSPublication_type, RRSOrganization, RRSRelationshipPersonPublication, \
    RRSRelationshipPublicationCitation, \
    RRSRelationshipPublication_sectionPublication, RRSRelationshipContactPerson, \
    RRSRelationshipPublicationKeyword, RRSFile, RRSUrl, RRSRelationshipFileUrl, \
    RRSRelationshipFilePublication, RRSCitation, RRSText, RRSLanguage
from rrslib.dictionaries.rrsdictionary import RRSDictionary, NAME_FF_CZ, \
    FIRST_UPPER, NAME_FM_CZ, NAME_FF_US, NAME_FM_US, NAME_FF_XX, NAME_FM_XX, \
    COUNTRIES, CITIES, NON_SURNAMES, CASE_INSENSITIVE, NON_NAMES, NOTHING, \
    RRSDictionaryError
from rrslib.extractors.normalize import TextCleaner
from rrslib.xml.xmlconverter import Model2XMLConverter
import StringIO
import copy
import entityextractor as ee
import os
import re
import sys

__modulename__ = "articlemetaextractor"
__author__ = "Tomas Lokaj, Stanislav Heller"
__email__ = "xlokaj03@stud.fit.vutbr.cz, xhelle03@stud.fit.vutbr.cz"
__date__ = "$27-June-2010 18:32:18$"



try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")
#_______________________________________________________________________________

class DictionaryError(Exception):
    """
    """
    pass

#other
BAD_CHARS = '¤▒�'

#_______________________________________________________________________________

class MetaExtractor(object):
    """
    This class contains functions for basic metadata searching in articles.
    """
    def __init__(self):
        #patterns
        self._pat_abstract_1 = '(Abstract|ABSTRACT)'
        self._pat_abstract_2 = '(In this|This (paper|study|article|report)'
        self._pat_abstract_2 += '|IN THIS|THIS (PAPER|STUDY|ARTICLE|REPORT))'
        self._pat_abstract_end = '(!A_E!|$|\n\s*\n)'
        self._pat_keywords = 'I[nN][dD][eE][xX] ?[tT][eE][rR][mM][sS]|'
        self._pat_keywords += 'K[eE][yY] ?[wW][oO][rR][dD][sS](?: and [A-Za-z]*?)?|'
        self._pat_keywords += 'G[eE][nN][eE][rR][aA][lL] ?[tT][eE][rR][mM][sS]?'
        self.pat_months = 'janu?a?r?y?\.?|febr?u?a?r?y?\.?|marc?h?\.?|apri?l?\.?|'
        self.pat_months += 'may|june?\.?|july?\.?|augu?s?t?\.?|sept?e?m?b?e?r?\.?|'
        self.pat_months += 'octo?b?e?r?\.?|nove?m?b?e?r?\.?|dece?m?b?e?r?\.?'
        self.pat_junctions = 'the|be|a|an|anthe|of|in|at|for|from|to|into|and|or|with'
        self.pat_middle_name = '(ter|Ter|van|den|der|de|di|la|van der|von|chen|'
        self.pat_middle_name += 'van de|van den|Van|Den|Der|De|Di|La|Van der|Von|'
        self.pat_middle_name += 'Chen|Van de|Van den|el|El)'
        self.alone_name = \
            '([eE]t[. ]*?al\.?|[Ss]ons?|[Jj]r[ .,]|[Jj]unior|[eE]tc\.?)'
        self.roman_num = '(I[ .]|II[ .]|III[ .]|IV[ .]|V[ .]|VI[ .]|VII[ .]|'
        self.roman_num += 'VIII[ .]|IX[ .]|X[ .])'

        #regular expressions
        self._re_abstract_1 = re.compile(self._pat_abstract_1 + '\W+(.+?)'
                                       + self._pat_abstract_end, re.DOTALL)
        self._re_abstract_2 = re.compile(self._pat_abstract_2 + '\W+(.+?)'
                                       + self._pat_abstract_end, re.DOTALL)
        self._re_keywords_1 = re.compile('(' + self._pat_keywords
                                         + ')[-:,;. ]*?\n+(.+?)\n')
        self._re_keywords_2 = re.compile('(' + self._pat_keywords
                                         + ')[-:,;. ]+(.+?)(\n|[^0-9A-Z]\.|$)')
        self._re_meta = re.compile('(^.*)(authors?:|emails?:|editors?:)', re.I)
        self.re_published = re.compile('(^|\s)published (in|with)', re.I)
        self.re_issn = re.compile('ISSN|[0-9]{4}-[0-9]{4}')
        self.re_rep = re.compile('(^\s*[a-z]{2,} report\s*$|tech report)', re.I)
        self.re_lower_start = re.compile('^[a-z][^A-Z-\'`]')
        self.re_vol = re.compile('vol(ume)?\.? *[0-9]+', re.I)
        self.re_rev = re.compile('[Rr]evision *[0-9]+')
        self.re_inproc = \
            re.compile('in proc\.|in proceedings|proceedings of', re.I)
        self.re_no = re.compile('n(o|umber)\.? *[0-9]+', re.I)
        self.re_pages = re.compile('(pages?|p\.) [0-9]', re.I)
        self.re_etal = re.compile('et al\.?(\s|$)', re.I)
        self.re_copyright = re.compile('(^|\s)copyright(\s|$)', re.I)
        self.re_date = re.compile('(' + self.pat_months + ') .*?[0-9]{4}', re.I)
        self.re_year = re.compile('\([0-9]{4}\)')
        self.re_num = re.compile('^[0-9\s%]+$', re.DOTALL)
        self.re_noletter = re.compile('^[^a-z]+$', re.IGNORECASE)
        self.re_upper_word = re.compile('[A-Z][A-Z]+')
        self.re_lower_word = re.compile('[a-z]')
        self.re_telfax = re.compile('(tel|fax) +[+]?[0-9][-0-9 ()]', re.I)
        self.re_empty = re.compile('^\s*$', re.DOTALL)
        self.re_notitle = re.compile('\s(conference|symposium)\s', re.M | re.I)
        self.re_title = re.compile('[A-Z][A-Z]+( [A-Z][A-Z])* [0-9]{4}')
        self.re_mark = \
            re.compile('(^[^\s]+ ?(/|-[0-9]) ?[^\s]+$|[0-9]+[-:][0-9]+)')
        self.re_type = \
            re.compile('(^|\s)thesis|article|journal(\s|$)', re.I | re.DOTALL)
        self.re_organization = \
            re.compile('department of|university|school of', re.IGNORECASE)
        self.re_press = \
            re.compile('(^|[^0-9a-z])in press([^0-9a-z]|$)', re.IGNORECASE)
        self.re_domain = re.compile('.+\.[a-z]{2,3}$', re.IGNORECASE)
        self.re_zav = re.compile('^[[(].*[])]$')
        self.re_title = re.compile('^.*?T[Ii][Tt][Ll][Ee]:\s*(.+?)(\.|$)')
        self.re_authors = re.compile('^[ ,.&]*('
                    '(([A-Z][-A-Za-z\'´`]+[.,]?|' + self.pat_middle_name + 
                    '[.,]?|([A-Z]\.?-)?[A-Z]\.)[ ]+)*?'
                    '(' #Jmeno von Prijmeni
                    '(([A-Z][-A-Za-z\'´`]+)[.,]?[ ]+)'
                    '(([A-Z][-A-Za-z\'´`]+[.,]?|' + self.pat_middle_name + 
                    '[.,]?|([A-Z]\.?-)?[A-Z]\.)[ ]+)*?'
                    '(([A-Z][-A-Za-z\'´`]+)[ ]*)'
                    '|' #Prijmeni, J.
                    '(([A-Z][-A-Za-z\'´`]+[.,]?)[ ]+)'
                    '(([A-Z][-A-Za-z\'´`]+[.,]?|' + self.pat_middle_name + 
                    '[.,]?|([A-Z]\.?-)?[A-Z]\.)[ ]+)*?'
                    '((' + self.pat_middle_name
                    + '[.,]?|([A-Z]\.?-)?[A-Z][ .]?)[ ]*)+?'
                    '|' #J. von Prijmeni
                    '((' + self.pat_middle_name
                    + '[.,]?|([A-Z]\.?-)?[A-Z]\.)[ ]+)+?'
                    '(([A-Z][-A-Za-z\'´`]+[.,]?|' + self.pat_middle_name + 
                    '[.,]?|([A-Z]\.?-)?[A-Z]\.)[ ]+)*?'
                    '(([A-Z][-A-Za-z\'´`]+)[ ]*)'
                    ')'
                    '(([A-Z]v+|' + self.pat_middle_name
                    + '|([A-Z]\.?-)?[A-Z]\.)[ ]*)*?'
                    '(([., ]*(' + self.alone_name + '|'
                    + self.roman_num + ')?)*'
                    '((?<=\.) |&|[,. ]?and[,. ]|,|\.|;|$|%SEP%|\())+?'
                    '([., ]*' + self.alone_name + ')*)', re.VERBOSE)
        self.re_inc = re.compile('[^a-zA-Z]([A-Z]\.|' + self.pat_middle_name
                                 + '|' + self.alone_name + '|&)[^a-zA-Z]')
        self.re_end = re.compile('([-:,]| (' + self.pat_junctions + '))\s*\n',
                            re.IGNORECASE)
        self.re_split = \
            re.compile('^[A-Z]+( [^ a-z]+)*\n([^ a-z]+( [^ a-z]+)*\n)+')
        self.re_upper = re.compile('([A-Z][A-Z]+ ){3}')
        self.re_lower = re.compile('(^.+?) (.[^ ]?[a-z].*$)')
        self.re_by = re.compile('(^.+) by (.+?)$', re.DOTALL)
        self.re_autinline = \
            re.compile('^([A-Z][^A-Z]+( [^A-Z]+){3}.*?)([A-Z][.a-z].*)')
        self.re_word_end = re.compile(' [^A-Z]+\s*$')
        self.re_term = re.compile('(^|\s*[:,;]+)\s*(.+?)\s*([:,;]+\s*|$)')

        #Dictionaries
        try:
            self.rrsdict_locations = RRSDictionary(COUNTRIES, FIRST_UPPER)
            self.rrsdict_locations.extend(RRSDictionary(CITIES, FIRST_UPPER))
        except RRSDictionaryError:
            raise DictionaryError("Failed to load dictionaries.")


    def _is_title_impossible(self, line, check_lower=False):
        if len(line) > 300:
            return True
        elif self.re_empty.search(line) or self.re_notitle.search(line) or \
        self.re_title.search(line) or self.re_rep.search(line) or \
        self.re_issn.search(line) or self._re_meta.search(line) or \
        self.re_num.search(line)  or self.re_lower_start.search(line) or \
        self.re_telfax.search(line) or self.re_vol.search(line) or \
        self.re_no.search(line) or self.re_date.search(line) or \
        self.re_year.search(line) or self.re_pages.search(line) or \
        self.re_inproc.search(line) or self.re_type.search(line) or \
        self.re_etal.search(line) or self.re_copyright.search(line) or \
        self.re_published.search(line) or self.re_mark.search(line) or \
        self.re_organization.search(line) or self.re_press.search(line) or \
        self.re_domain.search(line) or self.re_zav.search(line) or \
        self.re_noletter.search(line) or self.re_rev.search(line):
            return True
        if check_lower and self.re_upper_word.search(line) and \
        self.re_lower_word.search(line):
            word = self.re_upper_word.search(line).group(0)
            if self.rrsdict_locations.contains_key(word):
                return True
        return False


    def find_title(self, meta_text):
        """
        This method finds article title in text.
        
        @param meta_text: part of the text containing metadata
        @type meta_text: str
        @return: returns tuple - title and the rest of the text
        @rtype: (str, str)  
        """
        title = ""
        meta_text_orig = meta_text

        while self.re_end.search(meta_text):
            meta_text = self.re_end.sub("\g<1> ", meta_text)

        #Opravi rozdeleny nazev psany velkymi pismeny
        if self.re_split.search(meta_text):
            orig_txt = self.re_split.search(meta_text).group(0)
            new_txt = orig_txt.replace("\n", " ")
            new_txt = re.sub("  +", " ", new_txt) + "\n"
            meta_text = re.sub('' + re.escape(orig_txt) + '', new_txt,
                               meta_text)

        #Ziska vsechny radky z hlavicky
        lines = meta_text.splitlines()

        #Prochazi postupne jednotlive radky a pokud v jednom najde vice moznych
        #metainformaci, tak je rozdeli
        for line in lines:
            if self._is_title_impossible(line, True):
                continue
            if self.re_upper.search(line) and self.re_lower.search(line):
                while self.re_upper.search(line) and self.re_lower.search(line):
                    new_line = self.re_lower.search(line).group(1) + "\n" \
                        + self.re_lower.search(line).group(2)
                    new_line = re.sub('(\s|\n|' + re.escape('\\') + ')+$',
                                      "", new_line)
                    meta_text = re.sub('' + re.escape(line) + '', new_line,
                                       meta_text)
                    line = self.re_lower.search(line).group(2)
            elif self.re_autinline.search(line) and \
            not self.re_word_end.search(line):
                while self.re_autinline.search(line) and \
                not self.re_word_end.search(line):
                    new_line = self.re_autinline.search(line).group(1) + "\n" \
                        + self.re_autinline.search(line).group(2)
                    new_line = re.sub('(\s|\n|' + re.escape('\\') + ')+$', "",
                                      new_line)
                    meta_text = re.sub('' + re.escape(line) + '', new_line,
                                       meta_text)
                    line = self.re_autinline.search(line).group(2)
            elif self.re_by.search(line):
                line_groups = self.re_by.search(line)
                change = False
                try:
                    if self.re_inc.search(line_groups.group(2)) and \
                    self.re_authors.search(line_groups.group(2)):
                        change = True
                except MemoryError:
                    change = True
                if change:
                    new_line = line_groups.group(1) + "\n" + line_groups.group(2)
                    new_line = re.sub('(\s|\n|' + re.escape('\\') + ')+$', "",
                                      new_line)
                    meta_text = re.sub('' + re.escape(line) + '', new_line,
                                       meta_text)

        #Znovu ziskame vsechny radky v hlavicce
        lines = meta_text.splitlines()
        possible_titles = []

        #Postupne projdeme vsechny radky a ulozime ty, ktere by mohly byt nazvem
        for line in lines:
            #Radek, ktery obsahuje text "Title:" je vyhodnocen jako nazev
            if self.re_title.search(line):
                title = self.re_title.search(line).group(2)
                if self._re_meta.search(title):
                    title = self._re_meta.search(title).group(1)
                break
            try:
                if self.re_inc.search(line) and self.re_authors.search(line):
                    continue
            except MemoryError:
                continue
            if self._is_title_impossible(line) == True:
                continue

            #Radek splnil pozadavky
            possible_titles.append(line)

        if title == "":
            title = None
            for t in possible_titles:
                title = t
                if len(t.split(" ")) <= 1:
                    continue
                break

        return (title, meta_text_orig)


    def find_abstract(self, meta_text):
        """
        This method finds article abstract in text.
        
        @param meta_text: part of the text containing metadata
        @type meta_text: str
        @return: returns tuple - abstract and the rest of the text
        @rtype: (str, str)  
        """
        abstract = None
        if self._re_abstract_1.search(meta_text):
            abstract_gr = self._re_abstract_1.search(meta_text)
            meta_text = re.sub(re.escape(abstract_gr.group(0)), "", meta_text)
            abstract = abstract_gr.group(2)
        elif self._re_abstract_2.search(meta_text):
            abstract_gr = self._re_abstract_2.search(meta_text)
            meta_text = re.sub(re.escape(abstract_gr.group(0)), "", meta_text)
            abstract = abstract_gr.group(0)

        if abstract != None:
            if re.search('[a-z]', abstract, re.I) == None:
                abstract = None
            else:
                abstract = abstract.replace("\n", " ")

        return (abstract, meta_text)

    def find_keywords(self, meta_txt):
        """
        This method finds article keywords in text.
        
        @param meta_text: part of the text containing metadata
        @type meta_text: str
        @return: returns tuple - keywords and the rest of the text
        @rtype: ([RRSKeyword], str)  
        """
        keywords = []
        keywords_text = ""
        while self._re_keywords_1.search(meta_txt) \
        or self._re_keywords_2.search(meta_txt):
            if self._re_keywords_1.search(meta_txt):
                keywords_all = self._re_keywords_1.search(meta_txt)
                keywords_text = keywords_all.group(2)
                meta_txt = re.sub(re.escape(keywords_all.group(0)), "", meta_txt)
            elif self._re_keywords_2.search(meta_txt):
                keywords_all = self._re_keywords_2.search(meta_txt)
                keywords_text = keywords_all.group(2)
                if keywords_all.group(3) != "\n":
                    keywords_text += keywords_all.group(3).replace(".", "")
                meta_txt = re.sub(re.escape(keywords_all.group(0)), "", meta_txt)

        while re.search(self._pat_keywords, keywords_text):
            keywords_text = re.sub(self._pat_keywords, ", ", keywords_text)
        if keywords_text == "":
            return (keywords, meta_txt)

        c = 1
        is_upper = False
        while self.re_term.search(keywords_text):
            term = self.re_term.search(keywords_text)
            if re.search('[A-Z]', term.group(2)):
                if not is_upper and c > 3:
                    meta_txt += " !A_E! " + keywords_text
                    break
                else:
                    is_upper = True

            keywords.append(RRSKeyword(title=term.group(2)))
            keywords_text = re.sub(re.escape(term.group(0)), "", keywords_text)
            c += 1

        return (keywords, meta_txt)



class ArticleMetaExtractor(object):
    """
    This class extracts metadata from articles.
    """

    def __init__(self, entityparams=ee.ALL):
        self.params = entityparams
        self.entity_extractor = ee.EntityExtractor()
        self.meta_extractor = MetaExtractor()
        self.cita_parser = CitationEntityExtractor(self.params)
        self.document_wrapper = DocumentWrapper()
        self.textual_document = TextualDocument()
        self.email_extractor = ee.EntityExtractor.EmailExtractor()
        self.document_info = DocumentInfo()
        self.cleaner = TextCleaner()
        self.lang_identifier = LanguageIdentifier()


    def _assign_emails(self, emails, names):
        """
        This method assigns email adresses to correct names.
        
        @param emails: list of emails
        @type emails: [RRSEmail]
        @param names: list of person names
        @type names: [RRSPerson]
        @return: list of person names with emails
        @rtype: [RRSPerson]  
        """

        names_tmp = []
        assigned_emails = []
        emails_tmp = []

        for a in names:
            names_tmp.append(a.get('full_name'))

        for r in emails:
            emails_tmp.append(r.get_localpart() + '@' + r.get_domain())

        #Zacne prirazovat, pokud je vubec extrahovany nejaky autor:
        if len(names_tmp) != 0:
            pr_names = names_tmp[:]
            pr_emails = emails_tmp[:]
            names_forms = []

            #Na zacatek prirazenych emailu vlozi pocet shodnych retezcu rovny 0
            for i in range(0, len(names_tmp)):
                assigned_emails.append("0|")

            #Upravi name autora:
            re_dot = re.compile('\.')
            re_end = re.compile(' $')
            re_start = re.compile('[^A-Za-z ]')
            re_firstname = re.compile('^([A-Z][a-z]*.*) ([A-Z][A-Za-z]*)?')
            re_surname = re.compile('([A-Z][a-z]*.*) ([A-Z][A-Za-z]*)$')
            for i in range(0, len(pr_names)):
                pr_names[i] = re_dot.sub('\. ', pr_names[i])
                pr_names[i] = re_end.sub('$', pr_names[i])
                pr_names[i] = re_start.sub("", pr_names[i])

                if names_tmp[i] == "":
                    break

                #Rozdeli name na krestni name a prsurname
                if re_firstname.search(pr_names[i]):
                    name = re_firstname.search(pr_names[i]).group(1)
                else:
                    name = pr_names[i]
                if re_surname.search(pr_names[i]):
                    surname = re_surname.search(pr_names[i]).group(2)
                else:
                    surname = pr_names[i]

                #Kazdy autor bude mit svuj seznam rezezcu:
                name = re.sub(' ', "", name)
                for k in range(0, len(surname) + 1):
                    for j in range(0, len(name) + 1):
                        names_forms.append(name[0:len(name) - j] + 
                                           surname[0:len(surname) - k])
                pr_names[i] = names_forms[:]
                names_forms = []

            #Upravi emails:
            re_at = re.compile('(.*)(@)')
            re_em_start = re.compile('[^A-Za-z]')
            for i in range(0, len(pr_emails)):
                pr_emails[i] = re_at.search(pr_emails[i]).group(1)
                pr_emails[i] = re_em_start.sub("", pr_emails[i])

            #Priradi emails ke jmenum podle nejvyssiho poctu shodnych retezcu:
            re_num = re.compile('^([0-9]+)(|)')
            i = 0

            while i < len(pr_emails):
                max_p, max_j = 0, 0
                for j in range(0, len(names_tmp)):
                    poc = 0
                    len_pr_names = len(pr_names[j])
                    for k in range(0, len_pr_names):
                        if re.search('' + re.escape(pr_names[j][k]) + '',
                                     pr_emails[i], re.IGNORECASE):
                            poc = poc + 1
                    if poc > max_p and poc > 0:
                        if int(re_num.search(assigned_emails[j]).group(1)) <= poc:
                            max_p, max_j = poc, j
                same = int(re_num.search(assigned_emails[max_j]).group(1))
                if same < max_p and len_pr_names > 0:
                    assigned_emails[max_j] = str(max_p) + "|" + str(i)
                    i = 0
                else:
                    i = i + 1

            #Upravi prirazene emaily:
            re_num_vert = re.compile("\d+\|")
            for i in range(0, len(assigned_emails)):
                assigned_emails[i] = re_num_vert.sub("", assigned_emails[i])

        for i in range(0 , len(assigned_emails)):
            if assigned_emails[i] != "":
                ei = int(assigned_emails[i])
                _rel = RRSRelationshipContactPerson()
                _rel.set_entity(RRSContact(email=emails[ei]))
                names[i].set('contact', _rel)

        return names


    def extract_data(self, document, module=None, files=[], type=None):
        """
        Output of this method is RRSPublication object with extracted data.
        
        @param document: text form of a document
        @type document: str
        @param module: module name
        @type module: str
        @param files: list of files with the document
        @type files: [RRSFile]
        @param type: type of the document
        @type type: str  
        @return: document's metadata
        @rtype: RRSPublication
        """
    
        document = self.cleaner.clean_text(document)
        #document = str(unicode(document, errors='ignore').decode('UTF-8', 'ignore'))
        #document = document.translate(None, BAD_CHARS).replace("  ", " ")

        publication = RRSPublication()
        
        #Create  publication text
        rrs_text = RRSText(content=document, length=len(document))

        #Wrap document
        textual_document = self.document_wrapper.wrap(document)
        meta_text = textual_document.get_meta()

        #Store module information into publication
        publication.set('module', module)
        
        #Get and store publication language
        lang_data = self.lang_identifier.identify(meta_text)
        lang = RRSLanguage(name=lang_data[0])
        cred = int(lang_data[1] * 2)
        if cred > 100:cred = 100
        lang.set('credibility', cred)
        publication.set('language', lang)
        
        #Get files and store them into publication
        txt_file_path = None
        pdf_file_path = None
        for f in files:
            url = f.get('url')[0].get_entities()[0]
            if re.search('\.txt$', f.get("filename")) or (f.isset('type') and f.get('type') == "txt"):
                txt_file_path = url.get('link')
                rrs_text.set('file', f)
            elif re.search('\.pdf$', f.get("filename")) or (f.isset('type') and f.get('type') == "pdf"):
                pdf_file_path = url.get('link')
            _rel = RRSRelationshipFilePublication()
            _rel.set_entity(f)
            publication.set('file', _rel)
            
        publication.set('text', rrs_text)

        #Get publication type
        if type == None and txt_file_path != None:
            type = self.document_info.get_document_type(txt_file_path, pdf_file_path)
            publication.set('type', RRSPublication_type(type=type))
        elif type != None:
            publication.set('type', RRSPublication_type(type=type))

        #Get keywords and store them into publication
        keywords = self.meta_extractor.find_keywords(meta_text)
        for keyword in keywords[0]:
            _rel = RRSRelationshipPublicationKeyword()
            _rel.set_entity(keyword)
            publication.set('keyword', _rel)
            meta_text = keywords[1]

        #Get abstract and store it into publication
        abstract = self.meta_extractor.find_abstract(meta_text)
        publication.set('abstract', abstract[0])
        meta_text = abstract[1]

        #Get title from document and store it into publication
        title = self.meta_extractor.find_title(meta_text)
        publication.set('title', title[0])
        meta_text = title[1]

        #Get emails
        emails = self.email_extractor.get_emails(meta_text)
        meta_text = self.email_extractor.get_rest()

        #Get names and assign emails and store them into publication
        names = self.entity_extractor.find_authors(meta_text)
        assigned_names = self._assign_emails(emails, names[0])
        c = 0
        for name in assigned_names:
            c += 1
            _rel = RRSRelationshipPersonPublication(author_rank=c, editor=False)
            _rel.set_entity(name)
            publication.set('person', _rel)
            #publication.set('person', name)
        meta_text = names[1]


        #Get publisher from document and store it into publication
        publisher = self.entity_extractor.find_publisher(meta_text)
        publication.set('publisher', RRSOrganization(title=publisher[0]))
        meta_text = publisher[1]


        #Get chapters from document and store them into publication
        for chpt in textual_document.get_chapters():
            _rel = RRSRelationshipPublication_sectionPublication()
            _rel.set_entity(chpt)
            publication.set("publication_section", _rel)
        
        #Get citations from document and store them into publication
        for cit in textual_document.get_citations():
            if cit == None:
                continue
            _cit = self.cita_parser.extract(cit)
            if _cit.isset('reference'):
                _cit['reference']['publication'] = publication
            _rel = RRSRelationshipPublicationCitation()
            _rel.set_entity(_cit)
            publication.set("citation", _rel)

        return publication


#-------------------------------------------------------------------------------
# end of class ArticleMetaExtractor
#-------------------------------------------------------------------------------
class TestSuite:
    def __init__(self):
        print "TestSuite for ArticleMetaExtractor"

    def _get_files_in_dir(self, directory, file_types=".*"):
        stack = [directory]
        files = []
        while stack:
            directory = stack.pop()
            try:
                for file in os.listdir(directory):
                    fullname = os.path.join(directory, file)
                    if re.search('^.*\.(' + file_types + ')$', fullname):
                        files.append(fullname)
                    if os.path.isdir(fullname) and not os.path.islink(fullname):
                        stack.append(fullname)
            except OSError:
                print "Zadana slozka neexistuje, program byl ukoncen!"
                exit()
        return files


    def test(self, dir, tb=False, remove=False, copy=True, wait=False, output_file=None):
        import traceback
        import codecs

        ok = True
        errors = []

        files = self._get_files_in_dir(dir, "txt")
        len_files = len(files)

        print "Testing AME on " + str(len_files) + " files:"

        print "\tInitializing AME......",
        sys.stdout.flush()
        try:
            ame = ArticleMetaExtractor()
            print "\t[OK]"
        except:
            print "\t[FAILED]"
            sys.stderr.write(str(sys.exc_info()))
            ok = False

        if ok:
            c = 0
            for f in files:
                c += 1
                print "\t" + str(c) + "/" + str(len_files) + "\t" + f + ".....",
                sys.stdout.flush()
                try:
                    #fileObj = codecs.open(f, "r", "utf-8")
                    #document = str(fileObj.read())
                    document = open(f, 'r').read()
                    rrsf = RRSFile()
                    _rel = RRSRelationshipFileUrl()
                    _rel.set_entity(RRSUrl(link=f))
                    rrsf.set('url', _rel)
                    fname = f.split('/')
                    fname.reverse()
                    rrsf.set('filename', fname[0])
                    rrsf.set('type', 'txt')
                    publ = ame.extract_data(document, module="publication_text_data",
                                            files=[rrsf])
                    output = StringIO.StringIO()
                    converter = Model2XMLConverter(stream=output)
                    converter.convert(publ)
                    #exit()
                    if remove:
                        os.system("rm " + f)
                    if output_file != None:
                        of = open(output_file, 'w')
                        of.write(output.getvalue())
                        of.flush()
                        of.close()
                    print "\t[OK]"
                except:
                    print "\t[FAILED]"
                    print "\t###############################################################################################"
                    sys.stdout.flush()
                    if tb:
                        traceback.print_tb(sys.exc_info()[2])
                    elif copy:
                        os.system("cp " + f + " " + "/media/Data/RRS/files/txt/ame_errors/" + str(c) + ".txt")

                    print sys.exc_info()[0], sys.exc_info()[1]
                    sys.stderr.flush()
                    print "\t###############################################################################################"
                    print
                    ok = False
                    errors.append(f)
                if wait:
                    raw_input("...continue?")
        if ok:
            print 'exiting test, everything is OK...'
        else:
            print 'exiting test, some error occured...'
            print '\nFiles with error:'
            print errors


if __name__ == '__main__':
    amets = TestSuite()
    amets.test("/media/Data/RRS/files/txt/test2/", tb=True, remove=False, wait=True, output_file="/media/Data/RRS/files/db09xml.xml")
    #amets.test("/media/Data/RRS/files/txt/test2/", tb=True, remove=False, copy=True, wait=True, output_file="/media/Data/RRS/files/db09xml.xml")
    #amets.test("/media/Data/RRS/files/txt/ame_errors", tb=True)
    #amets.test("/media/Data/RRS/publication_file_data/test/data/txt", tb=True)
    pass
