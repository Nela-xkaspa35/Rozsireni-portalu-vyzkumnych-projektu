#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Documentwrapper creates abstraction layer between PDF document converted to text
and extractors. Actually, documentwrapper is a parser which returns TextualDocument
object representing parsed document.

@todo: support Unicode
"""

__modulename__ = "documentwrapper"
__author__ = "Tomas Lokaj, Jan Svoboda, Stanislav Heller"
__email__ = "xlokaj03@stud.fit.vutbr.cz, xsvobo80@stud.fit.vutbr.cz, xhelle03@stud.fit.vutbr.cz"
__date__ = "$13-October-2010 14:37:11$"

from rrslib.db.model import RRSCitation, RRSDatabaseEntityChecker, \
    RRSPublication_section, RRSReference, RRSRelationshipPublicationReference, \
    RRSRelationshipReferenceCitation
from rrslib.dictionaries.rrsdictionary import *
import re

try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")



#_______________________________________________________________________________
class TextualDocumentError(Exception):
    """
    """
    pass

class DictionaryError(Exception):
    """
    """
    pass

#-------------------------------------------------------------------------------
# End of class TextualDocumentError
#-------------------------------------------------------------------------------



class TextualDocument(object):
    """
    This represents particular parts of a textual document.
    """
    
    def __init__(self):
        self.meta = ""
        self.chapters = []
        self.citations = []
        
    def set_meta(self, val):
        """
        This functions sets the first part of document, which contains metadata.
        """
        self.meta = val

    def get_meta(self):
        """
        This function returns the part with metadata.
        """
        return self.meta
    
    def set_chapter(self, val):
        """
        This method adds found chapter. 
        """
        #RRSDatabaseEntityChecker.check_chapter(val)
        self.chapters.append(val)
    
    def get_chapters(self):
        """
        This functions returns found chapters.
        """
        return self.chapters
    
    def set_citation(self, val):
        """
        This functions add found citations.
        """ 
        #RRSDatabaseEntityChecker.check_citation(val)
        self.citations.append(val)

    def get_citations(self):
        """
        This functions returns found citations.
        """ 
        return self.citations
    
#-------------------------------------------------------------------------------
# End of class TextualDocument
#-------------------------------------------------------------------------------



class _MetaWrapper(object):
    """
    This class process publication/article/paper and looks for it's part
    which contains metadata.
    """
    
    def __init__(self):
        self._pat_first_chapter = \
            'Introduction|Acknowledgements?|Acknowledgments?|Analysis|'\
            'Background|Bibliography|Concluding [Rr]emarks|Conclusion|'\
            'Conclusion [Aa]nd [Ff]uture [Ww]ork|Conclusions|Conclusions [aA]nd'\
            ' [Ff]uture [Ww]ork|Discussion|Discussion|Evaluation|Examples?|'\
            'Experimental [Rr]esults|Experiments|Implementation|'\
            'Method|Methodology|Methods|Motivation|Overview|Preliminaries|'\
            'Previous [Ww]ork|References?|Related [wW]ork|Results?|results'\
            ' [Aa]nd [Dd]iscussion|Statistics|Summary|Tables'
        self._pat_first_chapter = "(" + self._pat_first_chapter + "|" + \
            self._pat_first_chapter.upper() + ")" 
        self.meta = ""
        self.rest = ""
        self._pat_abstract = "Abstract\W|ABSTRACT\W"
        self._re_meta1 = re.compile('((^.+?\W)(' + self._pat_abstract + ')'
                                    '\W*(.+?))(\s\s+.*$)', re.DOTALL)
        self._re_meta2 = re.compile('(^.+?\n)([^a-zA-Z]+'
                                    + self._pat_first_chapter + '.*$)',
                                    re.DOTALL)
        self._re_meta3 = re.compile('(^.+?\n)( \n \n|\s*\n\s*[0-9]+\s*\n|'
                                    '\s*\n\W*([A-Z]{2,}){2,}|\n\n)(.*$)',
                                    re.DOTALL)
        self._re_short = re.compile('(^.+?)(\W[0-9ivx]+[\s.]+'
                                    + self._pat_first_chapter + '.*$)',
                                    re.DOTALL)
        self._re_short_introduction = re.compile('(^.+?)([0-9ivx]+)?[\s.]+'
                                    'I(ntroduction|NTRODUCTION).*$',
                                    re.DOTALL)
        self._re_not_introduction = re.compile('(and|AND|to|TO)\s*I'
                                               '(ntroduction|NTRODUCTION)')

    def get_meta(self, text):
        """
        Returns string with metadata of publication/article/paper.
        
        @param text: document text
        @type text: str
        @return: string with metadata of publication/article/paper.
        @rtype: str 
        """      
        res = None
        if self._re_meta1.search(text):
            res = self._re_meta1.search(text)
        elif self._re_meta2.search(text):
            res = self._re_meta2.search(text)
        elif self._re_meta3.search(text):
            res = self._re_meta3.search(text)
        if res != None:
            self.meta = res.group(1)
            if self._re_short_introduction.search(self.meta):
                if self._re_not_introduction.search(self.meta) == None:
                    self.meta = \
                        self._re_short_introduction.search(self.meta).group(1)

        self.meta = re.sub('[0-9\s]+$', "", self.meta, re.DOTALL)
        self.rest = "\n\n\n\n\n" + re.sub(re.escape(self.meta), "", text)
        
        return self.meta        

    def get_rest(self):
        """
        Returns the rest of the text.
        
        @return: rest of the text
        @rtype: str
        """
        return self.rest


#-------------------------------------------------------------------------------
# End of class _MetaWrapper
#-------------------------------------------------------------------------------

class _ChapterWrapper(object):
    """
    This class process publication/article/paper and looks for it's chapters.
    """
   
    def __init__(self):
        
        self.rest = ""
        
        #List of roman numerals
        self._lst__roman_numerals = ["i", "ii", "iii", "iv", "v", "vi", "vii",
        "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii",
        "xviii", "xix", "xx", "xxi", "xxii", "xxiii", "xxiv", "xxv", "xxvi",
        "xxvii", "xxviii", "xxix", "xxx", "xxxi", "xxxii", "xxxiii", "xxxiv",
        "xxxv", "xxxvi", "xxxvii", "xxxviii", "xxxix", "xxxx", "xxxxi",
        "xxxxii", "xxxxiii", "xxxxiv", "xxxxv", "xxxxvi", "xxxxvii", "xxxxviii",
        "xxxxix"]
        
        #List of recent chapter names
        self._lst_recent_chapters = ['abstract', 'acknowledgements',
        'conclusion', 'acknowledgments', 'analysis', 'applications',
        'background', 'bibliography', 'concluding remarks',
        'conclusion and future work', 'discussion', 'discussion', 'evaluation',
        'conclusions', 'conclusions and future work', 'example', 'examples',
        'experimental results', 'experiments', 'implementation', 'introduction',
        'method', 'methodology', 'methods', 'motivation', 'overview',
        'preliminaries', 'previous work', 'references', 'related work',
        'result', 'results', 'results and discussion', 'statistics', 'summary',
        'tables']
        
        #List of recent chapter names which stands alone
        self._lst_recent_alone_chapters = ["references", "bibliography",
        "acknowledgments", "introduction", "conclusion", "conclusions"]
        
        #List of prepositions
        self._pat_prepositions = \
        ',|be|a|A|an|AN|An|the|THE|The|of|OF|Of|in|IN|In|at|AT|At|for|FOR|For|'\
        'from|FROM|From|to|TO|To|into|INTO|Into|and|AND|And|or|OR|Or|with|'\
        'WITH|With'
        
        #List of last words at the line
        self._lst_last_words = ["be", "is", "a", "an", "the", "of", "in", "at",
        "on", "for", "from", "to", "into", "and", "with", "by", "or", "&"]
        
        #Regular expressions
        self._re_lower = re.compile('[a-z]')
        self._re_pis = re.compile('[a-zA-Z]')
        self._re_cisla = re.compile('([0-9.]+\s+){3,}', re.DOTALL)
        self._re_math = re.compile('(([^a-zA-Z][A-Za-z] ?[-=*/] ?[0-9]|[0-9]' 
                                   '?[-=*/]|[-=*/] ?[0-9]|[A-Z]\([a-z]+\))|'
                                   '[+]|.*=\s*$)')
        self._re_tab_fig = re.compile('(Figure [0-9]+(:|\.)|Fig\. [0-9]+|'
                                      'Table [0-9]+(:|\.))')
        self._re_dot = re.compile('^.*\.\s*$', re.DOTALL)
        self._re_url = re.compile('URL[^a-z]+.*?(www\.|http://)', re.DOTALL)
        self._re_first_low = re.compile('^\s*[0-9ixv]+\.?\s+[a-z]', re.DOTALL)
        self._re_last_word = re.compile('^.*\s([^\s]+)\s*$', re.DOTALL)
        self._re_split = re.compile('(^.*?[0-9]+\.?[0-9.]*\s+.*?)'
                                    '([0-9]+\.[0-9.]*\s+.+$)', re.DOTALL)
        self._re_sub_chpt_num = re.compile('^\s*([0-9]+\.[0-9.]+).*$',
                                           re.DOTALL)
        self._re_content = re.compile('\n *(Table of Contents|CONTENTS)'
                                      ' *\n(.*$)', re.IGNORECASE | re.DOTALL)
        self._re_chpt_1 = re.compile('^\n((([0-9][0-9.]*|[IXV]+\.)\s+)?'
                                     '[^0-9]+?)[ .:]+[0-9][-0-9]*$')
        self._re_chpt_2 = re.compile('^\n((([0-9][0-9.]*|[IXV]+\.)\s+)'
                                     '[^0-9]+?)$')
        self._re_line = re.compile('(\n.+?)\n')
        self._re_symb_1 = re.compile('\n\n' + re.escape("\\") + '[A-Z][a-z]+'
                                     '\n\n', re.DOTALL)
        self._re_symb_2 = re.compile('\n' + re.escape("\\") + '[A-Z][a-z]+\n',
                                     re.DOTALL)
        self._re_ref = re.compile('^(.*\s(References|Reference|Bibliography|'
                                  'REFERENCE|REFERENCES|BIBLIOGRAPHY)\s).*?$',
                                  re.DOTALL)
        self._re_dots = re.compile('^(.+?)([.:] ?){5,}', re.DOTALL)
        self._lst_sub_chpt_nums = []

    def get_chapters(self, text):
        """
        Returns list of chapters which were found in publication.
        
        @param text: text of a document
        @type text: str
        @return: list of chapters which were found in publicatio
        @rtype: [RRSPublication_section]
        
        @todo: text positions
        """
        text_original = text
        #Promenne
        chapters, found_recent_chapters = [], []
        is_arabic_numeral, is_roman_numeral, is_alone = False, False, False
        cont1, cont2 = True, True
    
        #Oriznuti casti s pouzitou literaturou
        if self._re_ref.search(text):   
            text = self._re_ref.search(text).group(1) + "\n\n"
        #Vyjmuti symbolu z textu (napr. "\Lambda")
        text = self._remove_symbols(text)
        
        #Hledani nazvu kapitol v obsahu
        if self._re_content.search(text):
            content = "\n" + self._re_content.search(text).group(2)
            content = re.sub('^[\n\s]+', '\n', content)
            not_found = 0
            while self._re_line.search(content) and not_found < 2:
                line = self._re_line.search(content).group(1)
                if self._re_dots.search(line):
                    line = self._re_dots.search(line).group(1)
                content = re.sub('' + re.escape(line) + '', "", content)
                if cont1 and self._re_chpt_1.search(line):
                    chpt = self._re_chpt_1.search(line).group(1)
                    chapters.append({'data':chpt, 'credibility':100})
                    not_found = 0
                    cont2 = False
                elif cont2 and self._re_chpt_2.search(line):
                    chpt = self._re_chpt_2.search(line).group(1)
                    chapters.append({'data':chpt, 'credibility':100})
                    not_found = 0
                    cont1 = False
                else: not_found += 1
        #Pokud nebyly nazvy nalezeny v obsahu, budou se prochazet nazvy bezne se
        #vyskytujicich kapitol a zjisti se, jak jsou nazvy kapitol formatovany
        if len(chapters) < 3: 
            found_recent_chapters_arabic, found_recent_chapters_numeral = [], []
            for recent_chapter in self._lst_recent_chapters: 
                if self._is_introduced_arabic(recent_chapter, text):
                    #Uvozeny arabskou cislici 
                    found_recent_chapters_arabic.append(recent_chapter)
                elif self._is_introduced_roman(recent_chapter, text): 
                    #Uvozeny rimskou cislici
                    found_recent_chapters_numeral.append(recent_chapter)        
            if len(found_recent_chapters_arabic) != 0 \
            or len(found_recent_chapters_numeral) != 0:
                if len(found_recent_chapters_arabic) >= len(
                found_recent_chapters_numeral): 
                    is_arabic_numeral = True
                    found_recent_chapters = found_recent_chapters_arabic
                else:
                    is_roman_numeral = True
                    found_recent_chapters = found_recent_chapters_numeral
            else:
                is_arabic_numeral = True
                for recent_chapter in self._lst_recent_chapters:
                    if recent_chapter not in self._lst_recent_alone_chapters \
                    and self._is_introduced_not(recent_chapter, text):
                        is_arabic_numeral = False
                        is_alone = True
                        break
                    
            #Zavolani spravne extrakce
            if is_roman_numeral: 
                chapters = self._extract_roman_numerals(text)
            elif is_arabic_numeral: 
                chapters = \
                    self._extract_arabic_numerals(text, found_recent_chapters)
        
        #Pokud opravdu neni nicim uvozen
        if is_alone: 
            chapters = self._extract_alone(text)
        
        chapters = self._get_fulltext(chapters, text_original) 
        for i in range(0, len(chapters)): 
            chapters[i]["name"] = chapters[i]["name"].replace("\n", "").replace("%ZN%", "")
        return chapters

    def _extract_arabic_numerals(self, text, found_recent_chapters):
        """
        This method looks for chapters introduced by an arabic numeral.
        """
        chapters = []
        found_chapters = {}
        text_tmp = text

        is_upper, is_lower, end_dot = False, False, False
        tecka, start_i = 3, 1
      
        #Hledani formatu podle beznych nazvu kapitol a jejich ukladani do 
        #slovniku
        for recent_chapter in found_recent_chapters:
            #Zjisti, jestli je za cislici tecka
            if tecka != 1: 
                tecka = self._is_dot(recent_chapter, text)
            #Zjisti, jestli je nazev kapitoly zakoncen teckou
            end_dot = self._is_dot_end(recent_chapter, text)
          
            #Vytvori regularni vyraz, ktery zjisti cislo bezne kapitoly a zjisit
            #radkove oddeleni
            re_num_1 = re.compile('\n\n\s*(([0-9]+)\.?\s+' + str(recent_chapter)
                                  + '(\.?\s*|:.*?))\n\n', re.DOTALL | 
                                  re.IGNORECASE)
            re_num_2 = re.compile('[^\n]\n\s*(([0-9]+)\.?\s+' 
                                  + str(recent_chapter) + '(\.?\s*|:.*?))\n\n',
                                  re.DOTALL | re.IGNORECASE)
            re_num_3 = re.compile('\n\n\s*(([0-9]+)\.?\s+' + str(recent_chapter)
                                  + '(\.?\s*|:.*?))[^\n]', re.DOTALL | 
                                  re.IGNORECASE)
            re_num_4 = re.compile('[^\n]\n\s*(([0-9]+)\.?\s+' 
                                  + str(recent_chapter) + '(\.?\s*|:.*?))\n'
                                  '[^\n]', re.DOTALL | re.IGNORECASE)
          
            if re_num_1.search(text): 
                start_i, num = 1, re_num_1.search(text)
            elif re_num_2.search(text): 
                start_i, num = 2, re_num_2.search(text)
            elif re_num_3.search(text): 
                start_i, num = 3, re_num_3.search(text)
            elif re_num_4.search(text): 
                start_i, num = 4, re_num_4.search(text)
            else:
                continue
            
            #Ulozi nalezene bezne kapitoly do slovniku
            found_chapters[num.group(2)] = num.group(1)
          
            #Zjisti, jestli jsou kapitoly psany velkymi pismeny
            if str(num.group(1)).find(recent_chapter.upper()) != -1: 
                is_upper = True
            else: 
                is_lower = True
        
        #Hledani ostatnich nazvu kapitol postupne po cislech
        num, not_found = 0, 0
        while num < 200:
            #Pokud nebyl nalezen urcity pocet kapitol za sebou a zadne bezne uz
            #nezbyvaji, tak skoncime, protoze uz asi zadne dalsi v textu nejsou
            if not_found >= 3:
                if len(found_chapters.keys()) == 0: 
                    break
                else: 
                    if abs(num - int(found_chapters.keys()[0])) > 20:
                        for key in found_chapters.keys(): 
                            chapters.append({'data':found_chapters[key],
                                             'credibility':100})
                        break
            #Vytvori regularni vyraz pro podkapitoly dane kapitoly
            re_sub_chapt = re.compile('\n\s{,10}(' + str(num) + 
                                      '\.[1-9]([0-9]|\.)*[\s\n]{1,10}([A-Z]|'
                                      '[0-9]+[^\s\n])[^=+*/\n]{2,100}?)\n')  
            #Pokud je k danemu cislu nalezena bezna kapitola
            if str(num) in found_chapters.keys():
                chapters.append({'data':found_chapters[str(num)],
                                 'credibility':100})
                if re.search('^.*?' + re.escape(found_chapters[str(num)]) + 
                             '(.*$)', text, re.DOTALL | re.IGNORECASE):
                    text = str("\n" + re.search('^.*?' + 
                                re.escape(found_chapters[str(num)]) 
                                + '(.*$)', text,
                                re.DOTALL | re.IGNORECASE).group(1))
                elif re.search('^.*?' + re.escape(found_chapters[str(num)]) + 
                               '(.*$)', text_tmp, re.DOTALL | re.IGNORECASE):
                    text = str("\n" + re.search('^.*?' + 
                                re.escape(found_chapters[str(num)]) 
                                + '(.*$)', text_tmp,
                                re.DOTALL | re.IGNORECASE).group(1))
                #Hledani podkapitol
                while re_sub_chapt.search(text):
                    chapters[len(chapters) - 1]['subChpts'] = []
                    chpt = re_sub_chapt.search(text).group(1)
                    chpt = self._repair_chapter(chpt, text)
                    sub_chapter_num = \
                        self._re_sub_chpt_num.search(chpt).group(1)
                    if not self._is_chapter_wrong(chpt, end_dot) \
                    and sub_chapter_num not in self._lst_sub_chpt_nums:
                        self._lst_sub_chpt_nums.append(sub_chapter_num)
                        chapters[len(chapters) - 1]['subChpts'].append(
                            {'data':chpt.replace("\n", " "), 'credibility':70})
                        text = re.sub('' + re.escape(chpt) + '', "", text)
                    else: text = re.sub('' + re.escape(chpt) + '', "", text)
                del found_chapters[str(num)]
                num += 1
                continue
    
            elif num == 0:
                num += 1
                continue
          
            #Pokud nebyla nalezena, zkusime hledat podle danych formatu
            else:
                #Vytvoreni reularnich vyrazu podle nalezeneho formatu
                if len(found_recent_chapters): 
                    re_chapter_upper, re_chapter_lower = \
                    self._create_regular_expressions(1, num, 4, end_dot)
                else:
                    re_chapter_upper, re_chapter_lower = \
                    self._create_regular_expressions(tecka, num, start_i,
                                                     end_dot)
                #Nejprve se hledaji kapitoly psany s velkym pismenem na zacatku 
                #slova, potom s malym pismenem a potom je treba zkouset jine 
                #formaty
                if re_chapter_upper.search(text):
                    chpt = re_chapter_upper.search(text).group(2)
                elif re_chapter_lower.search(text):
                    chpt = re_chapter_lower.search(text).group(2)
                else:
                    #Zmeny poctu prazdnych radku pred a za nazvem kapitoly
                    if len(found_recent_chapters) == 0: 
                        i = 4
                    else: i = 1
                    while i <= 4:
                        if i == start_i: 
                            i += 1
                            continue
                        #Vytvoreni novych regularnich vyrazu
                        re_chapter_upper, re_chapter_lower = \
                        self._create_regular_expressions(tecka, num, i, end_dot)
                        if re_chapter_upper.search(text):
                            chpt = re_chapter_upper.search(text).group(2)
                            break
                        elif re_chapter_lower.search(text):
                            chpt = re_chapter_lower.search(text).group(2)
                            break
                        else:
                            i += 1
                            chpt = None
    
                    #Pokud nebyl nazev porad nalezen, hledame znova s ignoraci 
                    #tecky za cislici
                    if chpt == None:
                        tecka = 3
                        #Zmeny poctu prazdnych radku pred a za nazvem kapitoly
                        if len(found_recent_chapters) == 0: 
                            i = 4
                        else: i = 1
                        while i <= 4:
                            if i == start_i: 
                                i += 1
                                continue
                            #Vytvoreni novych regularnich vyrazu
                            re_chapter_upper, re_chapter_lower = \
                            self._create_regular_expressions(tecka, num, i,
                                                             end_dot)
                            if re_chapter_upper.search(text): 
                                chpt = re_chapter_upper.search(text).group(2)
                                break
                            elif re_chapter_lower.search(text):
                                chpt = re_chapter_lower.search(text).group(2)
                                break
                            else:
                                i += 1
                                chpt = None
            #Pokud porad nebyl nazev nalezen, jdeme hledat nazev dalsi kapitoly
            #v poradi
            if chpt == None:
                not_found += 1
                num += 1
                continue
          
            #Pokud nazev kapitoly nalezen byl, budeme ho upravovat
            else:
                cred = 80 - not_found * 10
                if cred < 0: 
                    cred = 0
                #Pokud jsou tam nazvy kapitoly a podkapitoly, tak se rozdeli
                if self._re_split.search(chpt):
                    chapters, text, cont = \
                    self._split_chapters(chpt, chapters, text, end_dot,
                                         is_upper, cred)     
                    if cont: 
                        continue
                else:
                    #Opravi pripadny necely nazev kapitoly
                    chpt = self._repair_chapter(chpt, text)  
                    #Pokud obsahuje nepovolene sekvence znaku, nejedna se o 
                    #nazev kapitoly
                    if self._is_chapter_wrong(chpt, end_dot):
                        text = re.sub('' + re.escape(chpt) + '', "", text)
                        continue
                    #Pokud velikosti pismen neodpovidaji vzoru, nejedna se o 
                    #nazev kapitoly
                    if is_upper and not is_lower \
                    and self._re_lower.search(chpt):
                        text = re.sub('' + re.escape(chpt) + '', "", text)
                        continue
                    chapters.append({'data':chpt, 'credibility':cred})
                    text = re.search('^.*?' + re.escape(chpt) + '(.*)$',
                                     text, re.DOTALL).group(1)
                #Hledani podkapitol dane kapitoly
                while re_sub_chapt.search(text):
                    chapters[len(chapters) - 1]['subChpts'] = []
                    chpt = re_sub_chapt.search(text).group(1)
                    #Pokud jsou tam nazvy vice podkapitol, tak se rozdeli
                    if self._re_split.search(chpt):
                        chapters, text, cont = \
                        self._split_chapters(chpt, chapters, text, end_dot,
                                             is_upper, 70)     
                        if cont: 
                            continue
                    else:
                        #Opravi pripadny necely nazev podkapitoly
                        chpt = self._repair_chapter(chpt, text)
                        #Zjisti cislo podkapitoly
                        sub_chapter_num = \
                            self._re_sub_chpt_num.search(chpt).group(1)
                        #Pokud neobsahuje nepovolene sekvence znaku a pokud 
                        #nebyla doposud nalezena podkapitola s danym cislem, tak
                        #ji povazujeme za spravnou
                        if not self._is_chapter_wrong(chpt, end_dot) \
                        and sub_chapter_num not in self._lst_sub_chpt_nums:
                            self._lst_sub_chpt_nums.append(sub_chapter_num)
                            chapters[len(chapters) - 1]['subChpts'].append(
                            {'data':chpt.replace("\n", " "), 'credibility':70})
                            text = re.sub('' + re.escape(chpt) + '', "", text)
                        else: text = re.sub('' + re.escape(chpt) + '', "", text)
                num += 1
                not_found = 0
        if len(chapters) < 3 and len(found_recent_chapters) == 0: 
            chapters = []
       
        return chapters

    def _extract_roman_numerals(self, text):
        """
        This method looks for chapters introduced by a roman numeral.
        """
        chapters, chapts = [], []
              
        #Prochazime postupne rimske cislice a hledame kapitoly
        for rom_num in self._lst__roman_numerals:
            re_chpt = re.compile('^.*?\n\s*(' + re.escape(rom_num) 
                                 + '\.?\s.*?)\s*\n', re.IGNORECASE | re.DOTALL)
            if re_chpt.search(text):
                chapter = re_chpt.search(text).group(1)
                text = re.search('^.*?' + re.escape(chapter) + '(.*)$', text,
                                 re.DOTALL).group(1)
                chapts.append({'data':chapter, 'credibility':70})
          
        return chapters

    def _extract_alone(self, text):
        """
        This method looks for not introduced chapters.
        """
        chapters = []
        is_upper, is_double_nl = False, False
        is_double_nl_s, is_double_nl_p = False, False
        
        #Zjisti, jestli jsou kapitoly psany velkymi pismeny nebo oddeleny dvema
        #radky
        for recent_chapter in self._lst_recent_chapters:    
            if recent_chapter == "references": 
                continue
            if re.search('\n\s*' + re.escape(recent_chapter.upper()) + '\s*\n',
                         text):
                is_upper = True
                break
            elif re.search('\n\n\s*' + re.escape(recent_chapter) + '\s*\n\n',
                           text, re.IGNORECASE):
                is_double_nl = True
                break
            elif re.search('\n\s*' + re.escape(recent_chapter) + '\s*\n\n',
                           text, re.IGNORECASE):
                is_double_nl_s = True
                break
            elif re.search('\n\n\s*' + re.escape(recent_chapter) + '\s*\n',
                           text, re.IGNORECASE):
                is_double_nl_p = True
                break
    
        #Vytvori spravny regularni vyraz
        if is_upper: 
            re_chapter = re.compile('\n\s*(([A-Z][A-Z]+\s+)*[A-Z][A-Z]+\s*)\n')
        elif is_double_nl: 
            re_chapter = re.compile('\n\n\s*(([A-Z]|[0-9]+[^\s.]).*?)\n\n')
        elif is_double_nl_s: 
            re_chapter = re.compile('\n\s*(([A-Z]|[0-9]+[^\s.]).*?)\n\n')
        elif is_double_nl_p: 
            re_chapter = re.compile('\n\n\s*(([A-Z]|[0-9]+[^\s.]).*?)\n')
        else:
            re_chapter = re.compile('\n\n\s*(([A-Z]|[0-9]+[^\s.]).*?)\n')
        
        #Hleda nazvy kapitol
        while re_chapter.search(text):
            chpt = re_chapter.search(text).group(1)
            text = re.sub('' + re.escape(chpt) + '', "", text)
            chpt = self._repair_chapter(chpt, text)
            if not self._is_chapter_wrong(chpt, 0): 
                chapters.append({'data':chpt, 'credibility':10})
        
        #Odstrani nazvy, ktere jsou pravdepodobně jmena a adresy z hlavicky
        for i in range(0, len(chapters)):
            if re.search('(abstract|introduction)', chapters[i]['data'],
                         re.IGNORECASE):
                for j in range(0, i): 
                    chapters.pop(0)
                break
    
        #Pokud je nalezeno podezrele moc kapitol, bylo hledani neuspesne
        if len(chapters) > 50: 
            chapters = []
    
        return chapters

    def _is_dot(self, recent_chapter, text):
        """
        This method detects dot after numeral.
        """
        if re.search('\n\s*(([0-9]+|[ixv]+)\.\s+' + str(recent_chapter) 
                     + ')\s*\.?\s*\n', text, re.DOTALL | re.IGNORECASE): 
            return 1
        else: 
            return 2

    def _is_dot_end(self, recent_chapter, text):
        """
        This method detects dot after chapter name.
        """
        if re.search('\n\s*(([0-9]+|[ixv]+)\.?\s+' + str(recent_chapter) 
                     + ')\s*\.\s*\n', text, re.DOTALL | re.IGNORECASE): 
            return True
        else: 
            return False

    def _is_chapter_wrong(self, chpt, end_dot):
        """
        This method checks chapter name.
        """
        value = False
        if not self._re_pis.search(chpt) or self._re_cisla.search(chpt) \
        or self._re_math.search(chpt) or self._re_tab_fig.search(chpt) \
        or self._re_url.search(chpt) or self._re_first_low.search(chpt): 
            value = True
        elif end_dot == 0 and self._re_dot.search(chpt): 
            value = True
        elif len(chpt) > 200: 
            value = True
        return value

    def _repair_chapter(self, chpt, text):
        """
        This method repairs incomplete name of chapter.
        """
        if re.search('^.*[,:]$', chpt, re.DOTALL):
            if re.search('' + re.escape(chpt) + '\n.+?\n', text):
                chpt = re.search('' + re.escape(chpt) + '\n.+?\n',
                                 text).group(0)
            else: return chpt
        elif self._re_last_word.search(chpt):
            last_word = self._re_last_word.search(chpt).group(1)
            if last_word.lower() in self._lst_last_words:
                if re.search('' + re.escape(chpt) + '\n.+?\n', text):
                    chpt = re.search('' + re.escape(chpt) + '\n.+?\n',
                                     text).group(0)
            else: return chpt
        return chpt

    def _is_introduced_arabic(self, recent_chapter, text):
        """
        This method finds if a chapter is introduced by an arabic numeral.
        """
        if re.search('\n\s*[0-9]+\.?\s+' + recent_chapter + '(\.?\s*|:.*?)\n',
                     text, re.DOTALL | re.IGNORECASE): return True
        return False

    def _is_introduced_roman(self, recent_chapter, text):
        """
        This method finds if a chapter is introduced by an roman numeral.
        """ 
        if re.search('\n\s*[ivx]+\.?\s+' + recent_chapter + '\.?\s*\n', text,
                     re.DOTALL | re.IGNORECASE): return True
        return False
    
    def _is_introduced_not(self, recent_chapter, text):
        """
        This method finds if a chapter is not introduced.
        """
        if re.search('\n\s*' + recent_chapter + '\s*\n', text, re.IGNORECASE): 
            return True
        return False
    
    def _remove_symbols(self, text):
        """
        This method removes symbols form a text.
        """
        if self._re_symb_1.search(text): 
            text = self._re_symb_1.sub(" ", text)
        elif self._re_symb_2.search(text): 
            text = self._re_symb_2.sub(" ", text)
        return text

    def _split_chapters(self, chpt, chapters, text, dot_end, is_upper, cred):
        """
        This method splits chapters and subchapters.
        """
        data = self._re_split.search(chpt)
        #Prvni nazev
        chpt1 = self._repair_chapter(data.group(1), text)
        if self._is_chapter_wrong(chpt1, dot_end):
            text = re.sub('' + re.escape(chpt1) + '', "", text)
            return chapters, text, True
        if is_upper and self._re_lower.search(chpt1):
            text = re.sub('' + re.escape(chpt1) + '', "", text)
            return chapters, text, True
        if self._re_sub_chpt_num.search(chpt1):
            sub_chpt_num = self._re_sub_chpt_num.search(chpt1).group(1)
            if sub_chpt_num not in self._lst_sub_chpt_nums:
                self._lst_sub_chpt_nums.append(sub_chpt_num)
                chapters.append({'data':chpt1, 'credibility':cred})    
        else:
            chapters.append({'data':chpt1, 'credibility':cred})    
        text = re.search('^.*?' + re.escape(chpt1) + '(.*)$', text,
                         re.DOTALL).group(1)
        #Druhy nazev
        chpt2 = self._repair_chapter(data.group(2), text)  
        if self._is_chapter_wrong(chpt1, dot_end):
            text = re.sub('' + re.escape(chpt1) + '', "", text)
            return chapters, text, True
        if self._re_sub_chpt_num.search(chpt2):
            sub_chpt_num = self._re_sub_chpt_num.search(chpt2).group(1)
            if sub_chpt_num not in self._lst_sub_chpt_nums:
                self._lst_sub_chpt_nums.append(sub_chpt_num)
                chapters[len(chapters) - 1]['subchpt'] = \
                [{'data':chpt2, 'credibility':70}]
            #    chapters.append({'data':chpt2,'credibility':70})
            text = re.search('^.*?' + re.escape(chpt2) + '(.*)$',
                             text, re.DOTALL).group(1)
    
        return chapters, text, False
    
    def _get_fulltext(self, chapters, text):
        """
        This method finds full content of a chapter.
        """
        re_split = re.compile('^[\s\n]*([0-9.ivxIVX]+)[\s\n]+(.*)$', re.DOTALL)
        len_chapters = len(chapters)
        if len_chapters == 0: 
            return chapters
        
        #Zkompletovani informaci o kapitole
        for i in range(0, len_chapters):
            if re_split.search(chapters[i]['data']):
                chpt_data = re_split.search(chapters[i]['data'])
                number = chpt_data.group(1)
                if re.search('([0-9]+)', number):
                    number = re.search('([0-9]+)', number).group(1)
                elif re.search('([ivxIVX]+)', number):
                    number = re.search('([ivxIVX]+)', number).group(1)
                    number = self._convert_numerals(number.capitalize())
                chapters[i]['num'] = int(number)
                chapters[i]['name'] = chpt_data.group(2)
            else:
                chapters[i]['num'] = 0
                chapters[i]['name'] = chapters[i]['data'].replace("\n", "")
            chapters[i]['data'] = \
                re.sub('\s*$', "", chapters[i]['data'], re.DOTALL)
            chapters[i]['fulltext'] = ""
            
        #Vyhledani celeho textu kapitoly
        for i in range(0, len_chapters - 1):
            if chapters[i]['num'] + 1 == chapters[i + 1]['num']:
                if re.search(re.escape(chapters[i]['data']) + '(.+?)' 
                             + re.escape(chapters[i + 1]['data']), text,
                             re.DOTALL):
                    fulltext = re.search(re.escape(chapters[i]['data']) + 
                                         '(.+?)' 
                                         + re.escape(chapters[i + 1]['data']),
                                         text, re.DOTALL)
                    chapters[i]['fulltext'] = fulltext.group(1)
                elif re.search(re.escape(chapters[i]['data']) + '\s*(.+?)\n\n',
                               text, re.DOTALL):
                    chapters[i]['fulltext'] = \
                    self._get_fulltext_short(chapters[i]['data'], text)
            elif re.search(re.escape(chapters[i]['data']) + '\s*(.+?)\n\n',
                           text, re.DOTALL):
                chapters[i]['fulltext'] = \
                self._get_fulltext_short(chapters[i]['data'], text)
          
        last_chapt = re.sub('\s', "", chapters[len_chapters - 1]['name'].lower(),
                            re.DOTALL)
        if last_chapt != "references" and last_chapt != "bibliography":
            if re.search(re.escape(chapters[len_chapters - 1]['data']) + 
                         '\s*(.+?)\n\n', text, re.DOTALL):
                chapters[len_chapters - 1]['fulltext'] = \
                self._get_fulltext_short(chapters[len_chapters - 1]['data'],
                                         text)
        for i in range(0, len(chapters)):
            if chapters[i]['fulltext'] != "":
                chapters[i]['position_from'] = text.find(chapters[i]['fulltext'])
                chapters[i]['position_to'] = chapters[i]['position_from'] + len(chapters[i]['fulltext'])
          
        return chapters
    
    def _get_fulltext_short(self, chapter, text):
        """
        This method finds shorted content of a chapter.
        """
        if re.search(re.escape(chapter) + '\s*(.+?)\.\n\n', text, re.DOTALL):
            return re.search(re.escape(chapter) + '\s*(.+?)\.\n\n', text,
                             re.DOTALL).group(1)
        elif re.search(re.escape(chapter) + '\s*(.+?)\n\n', text, re.DOTALL):
            return re.search(re.escape(chapter) + '\s*(.+?)\n\n', text,
                             re.DOTALL).group(1)
        else: 
            return ""
    
    def _convert_numerals(self, number):
        """
        This method converts an roman numeral to arabic.
        """
        if number == "I": 
            return 1
        elif number == "II": 
            return 2
        elif number == "III": 
            return 3
        elif number == "IV": 
            return 4
        elif number == "V": 
            return 5
        elif number == "VI": 
            return 6
        elif number == "VII": 
            return 7
        elif number == "VIII": 
            return 8
        elif number == "IX": 
            return 9
        elif number == "X": 
            return 10
        elif number == "XI": 
            return 11
        elif number == "XII": 
            return 12
        elif number == "XIII": 
            return 13
        elif number == "XIV": 
            return 14
        elif number == "XV": 
            return 15
        elif number == "XVI": 
            return 16
        elif number == "XVII": 
            return 17
        elif number == "XVIII": 
            return 18
        elif number == "XIX": 
            return 19
        elif number == "XX": 
            return 20
        else: 
            return 0
        
    def _create_regular_expressions(self, dot, num, level, end_dot):
        """
        This method creates regular expression according to found pattern to 
        find chapters.
        """
        if end_dot: 
            sufix = '\s*\.\s*'
        else: 
            sufix = ''
        if level == 1:
            if dot == 1:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
            elif dot == 2:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
            else:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)(([A-Z]'
                                           '[^\s\n]+?|[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
        if level == 2:
            if dot == 1:
                re_chpt_upper = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
            elif dot == 2:
                re_chpt_upper = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
            else:
                re_chpt_upper = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)(([A-Z]'
                                           '[^\s\n]+?|[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n\n')
                re_chpt_lower = re.compile('^(.|\n)*?[^\n]\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n\n')
        if level == 3:
            if dot == 1:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n[^\n]')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n[^\n]')
            elif dot == 2:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?v)' + sufix + '\n[^\n]')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n[^\n]')
            else:
                re_chpt_upper = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)(([A-Z]'
                                           '[^\s\n]+?|[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n[^\n]')
                re_chpt_lower = re.compile('^(.|\n)*?\n\n\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n[^\n]')
        if level == 4:
            if dot == 1:
                re_chpt_upper = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n+')
                re_chpt_lower = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '\.(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n+')
            elif dot == 2:
                re_chpt_upper = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '(\n\n?| +?)(([A-Z][^\s\n]+?|'
                                           '[0-9]+?[-.:stndrd]+?|' 
                                           + self._pat_prepositions 
                                           + ')\s+?)+?)' + sufix + '\n+')
                re_chpt_lower = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '(\n\n?| +?)([A-Z]|'
                                           '[0-9]+?[-.:stndrd]+?).{2,100}?)' 
                                           + sufix + '\n+')
            else:
                re_chpt_upper = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)'
                                           '(([A-Z][^\s\n]+?|[0-9]+?'
                                           '[-.:stndrd]+?|'
                                           + self._pat_prepositions + 
                                           ')\s+?)+?)' + sufix + '\n+')
                re_chpt_lower = re.compile('^(.|\n)*?\n+?\s*?(' + str(num) 
                                           + '(\.?|\.0)(\n\n?| +?)'
                                           '([A-Z]|[0-9]+?[-.:stndrd]+?)'
                                           '.{2,100}?)' + sufix + '\n+')  
        return re_chpt_upper, re_chpt_lower

    def get_rest(self):
        """
        Returns the rest of the text.
        """
        return self.rest


#-------------------------------------------------------------------------------
# End of class _ChapterWrapper
#-------------------------------------------------------------------------------

class _CitationWrapper(object):
    """
    This class process publication/article/paper and looks for it's citations.
    """
    
    def __init__(self):
        self._rest = ""
        self._citations = []
        
        #Patterms
        self._pat_middle_names = '(ter|Ter|van|den|der|da|de|di|la|van der|von'\
                                 '|chen|van de|van den|Van|Den|Der|Da|De|Di|La'\
                                 '|Van der|Von|Chen|Van de|Van den|el|El)'

        self._pat_alone_names = \
            '([eE]t[. ]*?al\.?|[Ss]ons?\W|[Jj]r[ .,]|[Jj]unior|[eE]tc\.?)'
        self._pat_name = '[A-Z][-\'Â´`a-z][-\'Â´`A-Za-z]+'
        self._pat_inc_dot = '(([A-Z][a-z]?[\.,]-? ?)+|[A-Z] ?[\.,]?)'
        self._pat_roman_numeral_dot = '(I[ .]|II[ .]|III[ .]|IV[ .]|V[ .]|'\
                                      'VI[ .]|VII[ .]|VIII[ .]|IX[ .]|X[ .])'
        self._pat_url = 'www\.[a-z0-9/\.~]+'
        self._pat_end = '(:|[0-9]|in press|\n)'
        self._pat_form_1_a = \
            '((' + self._pat_name + '( | ?, ?| ?; ?))+(!ZN!)?(' \
            + self._pat_middle_names + '|' + self._pat_inc_dot + \
            ')( |&| ?, ?| ?\.| ?; ?| ?:))'
        self._pat_form_1_b = \
            '((' + self._pat_middle_names + '|' + self._pat_inc_dot + \
            ')( | ?, ?| ?; ?)(!ZN!)?(' + self._pat_name + \
            '( |&| ?, ?| ?\.| ?; ?| ?:))+)'
        self._pat_form_2 = \
            '((' + self._pat_name + ', ?(!ZN!)?)+(' + self._pat_name + \
            ' ?)+.*?(' + self._pat_end + '))'
        self._pat_form_3 = \
            '((!ZN!)?[A-Z]{3,}(\s|,|\.|&)+[0-9]|(!ZN!)?[A-Z][a-z]+' \
            '[A-Z][a-z]*?(\s|,|\.|&)+[0-9])'
        self._pat_forms = \
            '(' + self._pat_form_1_a + '|' + self._pat_form_1_b + '|' \
            + self._pat_form_2 + '|' + self._pat_form_3 + ')'
        self._pat_roman_num_1 = 'i{1,3}|i?vi?|vi{2,3}|ix'
        self._pat_roman_num_2 = 'x{1,3}' + self._pat_roman_num_1 + '?'
        self._pat_roman_numeral = \
            '(' + self._pat_roman_num_1 + '|' + self._pat_roman_num_2 + ')'
        self._pat_quotations = '(\"|\'\'|``|Â´Â´)'
        
        #Regular expressions
        self._re_word = \
            re.compile(r'([A-Z][-\'`a-z][-\'`A-Za-z]*|[A-Z\'`-]+)',
                       re.MULTILINE)  
        self._re_clear_citation = \
            re.compile('(^( |and |\.|,|&|;|%S%)+|( |and |\.|,|&|;|%S%)+$)')
        self._re_new_line = re.compile('\n')
        self._re_multiple_white_spaces = re.compile('\s\s+')
        
        #Dictionaries
        try:
            self._rrsdict_names = RRSDictionary(NAME_FF_CZ, FIRST_UPPER)
            self._rrsdict_names.extend(RRSDictionary(NAME_FM_CZ, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_FF_US, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_FM_US, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_FF_XX, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_FM_XX, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_SF_CZ, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_SM_CZ, FIRST_UPPER))
            self._rrsdict_names.extend(RRSDictionary(NAME_S_US, FIRST_UPPER))
            
            self._rrsdict_non_names = RRSDictionary(NON_NAMES, FIRST_UPPER)
            self._rrsdict_non_names.extend(RRSDictionary(NON_SURNAMES,
                                                         FIRST_UPPER))
            
            self.rrsdict_locations = RRSDictionary(COUNTRIES, FIRST_UPPER)
            self.rrsdict_locations.extend(RRSDictionary(CITIES, FIRST_UPPER))
        except RRSDictionaryError:
            raise DictionaryError("Failed to load dictionaries.")
        
          
    def _find_bibliography_text(self, text):
        """
        This function gets the last part of articles/publications, which
        contains citations. This part is usually called "References" or 
        "Bibliography".
        """
        self._rest = text
        
        #Promenne pro zjednoduseni regularnich vyrazu:
        b = ""
        #Vyrizne vhodny text:
        pat_end = '$|\n *?\n *?\n|[Aa](ppendix|PPENDIX)|' \
                  '[Ll](ist of [Ff]igures|IST OF FIGURES)'
        reg_1 = re.compile(
          '(^.*)(\n[^\n]*?References[^A-Za-z].*?)(' + pat_end + ')',
          re.DOTALL)
        reg_2 = re.compile(
          '(^.*)(\n[^\n]*?REFERENCES[^A-Za-z].*?)(' + pat_end + ')',
          re.DOTALL)
        reg_3 = re.compile(
          '(^.*)(\n[^\n]*?Bibliography[^A-Za-z].*?)(' + pat_end + ')',
          re.DOTALL)
        reg_4 = re.compile(
          '(^.*)(\n[^\n]*?BIBLIOGRAPHY[^A-Za-z].*?)(' + pat_end + ')',
          re.DOTALL)
        reg_and = re.compile('(and|AND)\s([rR](eferences|EFERENCES)|'
                             '[Bb](ibliography|IBLIOGRAPHY))', re.IGNORECASE)
        
        if reg_1.search(text) and reg_and.search(text) == None :
            a = reg_1.search(text).group(2)
        elif reg_2.search(text) and reg_and.search(text) == None:
            a = reg_2.search(text).group(2)
        else:
            a = ""
        if reg_3.search(text) and reg_and.search(text) == None:
            c = reg_3.search(text).group(2)
        elif reg_4.search(text) and reg_and.search(text) == None:
            c = reg_4.search(text).group(2)
        else:
            c = ""
        
        lengths = \
            list(set([str(len(a)) + "a", str(len(b)) + "b", str(len(c)) + "c"]))
        lengths.sort()
      
        found = False
        for i in range(0, 3):
            if lengths[i][0] != "0":
                if lengths[i][len(lengths[i]) - 1] == "a":
                    found = True
                    text = a
                    break
                if lengths[i][len(lengths[i]) - 1] == "b":
                    found = True
                    text = b
                    break
                if lengths[i][len(lengths[i]) - 1] == "c":
                    found = True
                    text = c
                    break
        if not found:
            return ""
        
        re_rest = re.compile('(^.*?)' + re.escape(text) + '', re.DOTALL)
        if re_rest.search(self._rest):
            self._rest = re_rest.search(self._rest).group(1)
        else:
            return ""
        
        return text
        
    def _parse_citations(self, text, recurse=False):
        """
        This function separates particular citations from each other.
        """
        reg_change_1 = re.compile('[A-Z] [a-z]( [a-z])+')
        reg_change_2 = re.compile('^[\s]+')
        reg_change_3 = re.compile('  +')
        reg_space = re.compile(' ')
        reg_non_word = re.compile('[^a-zA-Z0-9,]')
        #Upravy vstupniho textu:
        if not recurse:
            text = \
                re.search('^(.*?(References?|REFERENCES?|Bibliography|BIBLIOGRAPHY)'
                          '[\n\s]*)(.*)$', text, re.DOTALL).group(3)
            text = re.sub(' \-', "-", text)
            text = re.sub('\.\s+[b-hj-z]\s+', ". ", text)

            while reg_change_1.search(text):
                with_space = reg_change_1.search(text).group(0)
                without_space = reg_space.sub("", with_space)
                text = re.sub('' + with_space + '', '' + without_space + '', text) 
            while reg_change_2.search(text):
                text = reg_change_2.sub("", text)
            while reg_change_3.search(text):
                text = reg_change_3.sub(" ", text)
      
        #Vyrizne zacatek textu referenci:
        prefix = re.search('^.{,50}', text, re.DOTALL).group(0)
        
        loop = True
        first_loop = True
        text_orig = text
        
        while loop:
            text = text_orig
            #Extrahuje _citations uvozene hranatymi zavorkami:
            if first_loop and re.search('[[].*?[]]', prefix):
                reg_square_parenthesis_1 = \
                    re.compile('(([[].*?[]]).{10,1000}?)([[])', re.DOTALL)
                reg_square_parenthesis_2 = \
                    re.compile('(([[].*?[]]).*?) .{10,1000}?\.\s*?$', re.DOTALL)
                reg_sub_hz = re.compile('^(.*?)([A-Z[[]])')
                while reg_square_parenthesis_1.search(text):
                    cit = reg_square_parenthesis_1.search(text)
                    text = re.sub('' + re.escape(cit.group(1)) + '', "", text)
                    ref_ok = reg_sub_hz.sub("\g<2>", cit.group(1), re.DOTALL)
                    if len(ref_ok) > 40 and len(ref_ok) < 1000:
                        p_space = len(reg_non_word.findall(cit.group(2)))
                        if p_space > 0:
                            if p_space < 10:
                                self._citations.append({'data':ref_ok,
                                                        'credibility':
                                                        80 - p_space * 10})  
                        else:
                            self._citations.append({'data':ref_ok,
                                                    'credibility':80})  
                if reg_square_parenthesis_2.search(text):
                    cit = reg_square_parenthesis_2.search(text)
                    if len(cit.group(0)) < 1000:
                        p_space = len(reg_non_word.findall(cit.group(2)))
                        if p_space > 0:
                            if p_space < 9:
                                self._citations.append({'data':cit.group(0),
                                    'credibility':70 - p_space * 10})  
                        else:
                            self._citations.append({'data':cit.group(0),
                                    'credibility':70})
              
            #Extrahuje reference uvozene hranatou zavorkou zprava:
            elif first_loop and re.search('(\s|^)\d+[]]', prefix, re.DOTALL):
                reg_square_parenthesis_right_1 = \
                    re.compile('(((\s|^)\d+[]]).{10,1000}?)(\d+[]])',
                               re.DOTALL)
                reg_square_parenthesis_right_2 = \
                    re.compile('(((\s|^)\d+[]]).*?) .{10,1000}?\.\s*$',
                               re.DOTALL)
                while reg_square_parenthesis_right_1.search(text):
                    cit = reg_square_parenthesis_right_1.search(text)
                    text = re.sub('' + re.escape(cit.group(1)) + '', "", text)
                    if len(cit.group(1)) > 40 and len(cit.group(1)) < 1000: 
                        p_space = len(reg_non_word.findall(cit.group(3)))
                        if p_space > 0:
                            if p_space < 9:
                                self._citations.append({'data':cit.group(1),
                                    'credibility':70 - p_space * 10})
                        else:
                            self._citations.append({'data':cit.group(1),
                                    'credibility':70})
                if reg_square_parenthesis_right_2.search(text):
                    cit = reg_square_parenthesis_right_2.search(text)
                    if len(cit.group(0)) < 1000: 
                        p_space = len(reg_non_word.findall(cit.group(3)))
                        if p_space > 0:
                            if p_space < 8:
                                self._citations.append({'data':cit.group(0),
                                    'credibility':60 - p_space * 10})
                        else:
                            self._citations.append({'data':cit.group(0),
                                'credibility':60})
              
            #Extrahuje reference uvozene rimskymi cislicemi:
            elif first_loop and re.search('^ *(' + self._pat_roman_numeral 
                                          + ' (\n|.)*?)', text, re.IGNORECASE):
                reg_roman_numeral_1 = \
                    re.compile('^ *(' + self._pat_roman_numeral 
                               + ' (\n|.){10,1000}?)'
                               '( ' + self._pat_roman_numeral + ' )',
                               re.IGNORECASE)
                reg_roman_numeral_2 = \
                    re.compile('(' + self._pat_roman_numeral 
                               + ' .{10,1000}?[^\s]{3,}\.)', re.DOTALL)
                reg_roman_numeral_3 = \
                    re.compile('(' + self._pat_roman_numeral + ' .{10,1000}?$)',
                               re.DOTALL)
                reg_roman_numeral_4 = \
                    re.compile('^ *' + self._pat_roman_numeral + ' ',
                               re.IGNORECASE)
                while reg_roman_numeral_1.search(text):    
                    cit = reg_roman_numeral_1.search(text).group(1)
                    text = re.sub('' + re.escape(cit) + '', "", text)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':70})
                if reg_roman_numeral_2.search(text):
                    cit = reg_roman_numeral_2.search(text).group(1)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':60})
                elif reg_roman_numeral_3.search(text):
                    cit = reg_roman_numeral_3.search(text).group(1)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':50})
                for i in range(len(self._citations)):
                    self._citations[i]['data'] = \
                        reg_roman_numeral_4.sub("", self._citations[i]['data'])
          
            #Extrahuje _citations uvozene cislici s teckou:
            elif first_loop and re.search('^ *[0-1]\. ', text):
                index = int(re.search('^ *([0-9])\.', text).group(1))
                reg_numeral_dot_1 = \
                    re.compile('^ *(' + str(index) + '\. .{10,1000}?)(' 
                               + str(index + 1) + '\.)', re.DOTALL)
                while reg_numeral_dot_1.search(text):
                    cit = reg_numeral_dot_1.search(text).group(1)
                    text = re.sub('' + re.escape(cit) + '', "", text)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':70})
                    index += 1
                    reg_numeral_dot_1 = \
                        re.compile('^ *(' + str(index) + '\. .*?)(' 
                                   + str(index + 1) + '\.)', re.DOTALL)
                reg_numeral_dot_2 = \
                    re.compile('(' + str(index) + '\. .*?\.\s*$)', re.DOTALL)
                if reg_numeral_dot_2.search(text):
                    cit = reg_numeral_dot_2.search(text).group(1)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':60})
        
            #Extrahuje _citations uvozene cislici v zavorkach:
            elif first_loop and re.search('^ *\([0-1]\) ', text):
                index = int(re.search('^ *\(([0-9])\)', text).group(1))
                reg_numeral_parenthesis_1 = \
                    re.compile('^ *(\(' + str(index) + '\) .{10,1000}?)(\(' 
                               + str(index + 1) + '\))', re.DOTALL)
                while reg_numeral_parenthesis_1.search(text):
                    cit = reg_numeral_parenthesis_1.search(text).group(1)
                    text = re.sub('' + re.escape(cit) + '', "", text)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':80})
                    index += 1
                    reg_numeral_parenthesis_1 = \
                        re.compile('^ *(\(' + str(index) + '\) .*?)(\(' 
                                   + str(index + 1) + '\))', re.DOTALL)
                reg_numeral_parenthesis_2 = \
                    re.compile('(\(' + str(index) + '\) .*?\.\s*$)', re.DOTALL)
                if reg_numeral_parenthesis_2.search(text):
                    cit = reg_numeral_parenthesis_2.search(text).group(1)
                    if len(cit) < 1000: 
                        self._citations.append({'data':cit, 'credibility':70})
          
            #Extrahuje pridanim znacek pred mozne pocatky referenci:
            else:
                loop = False
                #Dava znacky pred jmena:    
                rrsfound = \
                    self._rrsdict_names.text_search(text, True, RET_ORIG_TERM)
                for jmeno in rrsfound:
                    form_3 = \
                        jmeno + '( |, ?|[ ,]' + self._pat_middle_names + \
                         '[ ,]|[A-Z]\.)'
                    text = \
                        re.sub('(^|\s)(' + form_3 + '.*?)', ' !ZN!\g<2>', text,
                        re.DOTALL)
    
                #Vlozi znacku pred kazdy mozny pocatek _citations:
                reg_marks = \
                    re.compile('(^ *|\n *|[^\s]{3,}\. *|[0-9]\. *|' 
                               + self._pat_url + '[ \.]*)(' + self._pat_forms 
                               + ')', re.DOTALL)
                stop = 0
                while reg_marks.search(text) != None and stop <= 100:
                    text = reg_marks.sub('\g<1> !ZN!\g<2>', text)
                    stop += 1
          
                #Odstrani znacky od spatne oznacenych pocatku referenci:
                reg_remove_marks = \
                    re.compile('(!ZN!)+([A-Za-z]{2,})( |,|.|:|;)')
                cit_tmp = text     
    
                while True:
                    if reg_remove_marks.search(cit_tmp):
                        slovo = reg_remove_marks.search(cit_tmp).group(2)
                        if self._rrsdict_non_names.contains_key(slovo) and \
                            re.search('((!ZN!)+' + slovo + ' ?,? ? [A-Z]\.|'
                                      '[A-Z]\. ?,? ?(!ZN!)+' + slovo + ')',
                                      text) == None:
                            reg_mark_word = \
                                re.compile('(!ZN!)+(' + re.escape(slovo) + ')')
                            while reg_mark_word.search(text):
                                text = reg_mark_word.sub("\g<2>", text)
                        cit_tmp = \
                            re.sub('' + re.escape(slovo) + '', "", cit_tmp)
                    else: break
      
                reg_remove_marks = re.compile('\W[iI]n\W[ ,.]*?.*?!ZN!')
                cit_txt_tmp = text
                while reg_remove_marks.search(cit_txt_tmp):
                    txt = reg_remove_marks.search(cit_txt_tmp).group(0)
                    cit_txt_tmp = \
                        re.sub('' + re.escape(txt) + '', "", cit_txt_tmp)
                    txt2 = txt.replace("!ZN!", "")
                    text = text.replace(txt, txt2)
    
                #Upravi text na jeden radek:
                reg_dot = re.compile('\. *\n+')
                reg_space = re.compile(' {2,}')
                while reg_dot.search(text):
                    text = reg_dot.sub(". ", text)
                while reg_space.search(text):
                    text = reg_space.sub(" ", text)
                    
                #Rozdeli text podle znacek a pravidel na mozne _citations:
                text = text.replace("!ZN!", "!ZN! !ZN!")  
                tmp = re.findall(' (!ZN!)(.*?' + self._pat_end 
                                 + '.{5,}?[.0-9] *)(!ZN!)', text)
          
                #Kontroluje a upravuje mozne _citations, ktere nakonec ulozi:
                reg_cit_1 = re.compile('([^A-Za-z][. ][A-Z] ?\.|,|\sIn|\sin|'
                                       'eds?\.?\W|\() ( ?[A-Z]\. ?)*\s*$')
                reg_cit_2 = re.compile('(.*)(%SP%.*?)(' + self._pat_forms 
                                       + '.*?' + self._pat_end + '.*)')
                reg_cit_3 = re.compile('(.*?\.)(\s*' + self._pat_forms + '.*)')
                reg_cit_4 = re.compile('^(.*?)\.')
                reg_in = re.compile('^In\s+')
                reg_zn = re.compile('!ZN!')
                for i in range(0, len(tmp)):
                    cit = tmp[i][1]
                    text = re.sub('' + re.escape(cit) + '', "", text)
                    cit = reg_zn.sub("", cit) 
                    len_cit = len(self._citations)
    
                    #Pokud predchozi citace obsahuje na konci znaky v podmince,
                    # citace jeste patri k predchozi
                    if len_cit != 0 \
                    and reg_cit_1.search(self._citations[len_cit - 1]['data']):
                        self._citations[len_cit - 1]['data'] = \
                            self._citations[len_cit - 1]['data'] + " " + cit
                    #Pokud je na zacatku _citations jina _citations, ktera ma 
                    #svou cast v predesle referenci
                    elif len_cit != 0 \
                    and reg_cit_2.search(self._citations[len_cit - 1]['data']) \
                    and reg_cit_3.search(cit): 
                        tmp1 = reg_cit_2.search(self._citations[len_cit - 1]
                                                ['data'])
                        self._citations[len_cit - 1]['data'] = \
                            re.sub('' + re.escape(tmp1.group(2)) + '' 
                                   + re.escape(tmp1.group(3)) + '', "",
                                   self._citations[len_cit - 1]['data'])
                        tmp2 = reg_cit_3.search(cit)
                        self._citations.append({'data':tmp1.group(3) 
                                                + tmp2.group(1), 'credibility':
                                                self._citations[len_cit - 1]
                                                ['credibility']})
                        if len(tmp2.group(1)) < 40:
                            self._citations[len_cit]['data'] = \
                                self._citations[len_cit]['data'] \
                                + "%SP%" + tmp2.group(2)
                        else:
                            self._citations.append({'data':tmp2.group(2),
                                                    'credibility':
                                                    self._citations[len_cit - 1]
                                                    ['credibility']})
                    #Pokud je delka reference kratsi nez 40 znaku, je soucasti 
                    #predchozi reference
                    elif len_cit != 0 and len(cit) < 40:
                        self._citations[len_cit - 1]['data'] = \
                            self._citations[len_cit - 1]['data'] + " " + cit
                    #Pokud reference zacina slovem In, je soucasti predchozi
                    #reference
                    elif len_cit != 0 and reg_in.search(cit):
                        self._citations[len_cit - 1]['data'] = \
                            self._citations[len_cit - 1]['data'] + " " + cit
                    else:
                        if len(cit) < 1000 and len(cit) > 0:
                            pos = len_cit - 1
                            if pos < 0: 
                                pos = 0
                            self._citations.append({'data':cit,
                                                    'credibility':60})
    
                    #Pokud je na zacatku reference slovo charakterizujici 
                    #mesto nebo stat, patri tento pocatek k predesle referenci  
                    len_cit = len(self._citations)
                    if len_cit >= 2 \
                    and reg_cit_4.search(self._citations[len_cit - 1]['data']):
                        cit_prefix = \
                            reg_cit_4.search(self._citations[len_cit - 1]
                                             ['data'])
                        cit_prefix_split = cit_prefix.group(1)
                        cit_prefix_split = re.sub('\W', " ", cit_prefix_split)
                        cit_prefix_split = re.sub(' +', " ", cit_prefix_split)
                        cit_prefix_split = re.sub('^ +', "", cit_prefix_split)
                        cit_prefix_split = re.sub(' +$', "", cit_prefix_split)    
                        cit_prefix_split = cit_prefix_split.split(" ")
                        for word in cit_prefix_split:
                            if self.rrsdict_locations.contains_key(word):
                                self._citations[len_cit - 1]['data'] = \
                                    re.sub('^' + re.escape(cit_prefix.group(0)) 
                                           + '', "",
                                           self._citations[len_cit - 1]['data'])
                                self._citations[len_cit - 2]['data'] += \
                                    cit_prefix.group(0)        
                                break
        
                for i in range(0, len(self._citations)):
                    self._citations[i]['data'] = \
                        self._citations[i]['data'].replace("%SP%", "")
                    self._citations[i]['data'] = \
                        self._clear_citation(self._citations[i]['data'])
                        
            if len(self._citations) > 0: 
                loop = False
            first_loop = False
        
        for i in range(0, len(self._citations)):
            self._citations[i]['data'] = \
            self._citations[i]['data'].replace("\n", " ")
        for cit in self._citations:
            if re.search('^\W*$', cit['data'], re.DOTALL):
                self._citations.remove(cit)
                
        for i in range(0, len(self._citations)):
            try:
                if len(self._citations[i]['data']) > 500:
                    if not recurse:
                        data = self._citations[i]['data']
                        self._citations.pop(i)
                        i -= 1
                        self._parse_citations(data, True)
                    else:
                        self._citations[i]['data'] = self._citations[i]['data'][0:500]
            except IndexError:
                break


    def _clear_citation(self, citation):
        """
        This function clears begining and end of the citation from redundant 
        chars.
        """
        while self._re_new_line.search(citation):
            citation = self._re_new_line.sub(" ", citation)
        while self._re_multiple_white_spaces.search(citation):
            citation = self._re_multiple_white_spaces.sub(" ", citation)
        while self._re_clear_citation.search(citation):
            citation = self._re_clear_citation.sub("", citation)
        return citation  

    def get_citations(self, text):
        """
        Returns list of citations, which were found in publication.
        """
        bibliography = self._find_bibliography_text(text)
        if bibliography != "":
            self._parse_citations(bibliography)

        return self._citations    

    def get_rest(self):
        """
        Returns the rest of the text.
        """
        return self._rest


#-------------------------------------------------------------------------------
# End of class _CitationWrapper
#-------------------------------------------------------------------------------



class _ReferenceHandler(object):
    """
    This class searches for cited sentences and assigns them to correct 
    publications.
    """
    
    def __init__(self):
        self.rest = ""
        
        #Regular expressions
        self._re_clear_text = \
            re.compile('(^( |and |\.|,|&|;|%S%)+|( |and |\.|,|&|;|%S%)+$)')
        self._re_new_line = re.compile('(\n+)')
        self._re_multiple_white_spaces = re.compile('\s\s+')
        self._re_square_brackets_right = re.compile('(^\s*(.*?)[]])', re.DOTALL)
        self._re_square_brackets = re.compile('([[](.*?)[]])')
        self._re_etal = '(et ?al\.?|& ?al\.?|etc\.?)?'
        self._re_date = '\(?[0-9]{2,}[a-z]?(, ?[0-9]{2,}[a-z])?\)?'
        self._re_aut_name = re.compile('^(.+?)\(?[0-9:]')
        self._re_names_1 = \
            re.compile('([A-Z][a-z]+) (and|&) ([A-Z][a-z]+) (et|&) al\.?')    
        self._re_names_2 = re.compile('([A-Z][a-z]+) (et|&) al\.')
        self._re_names_3 = \
            re.compile('([A-Z][a-z]+) (and|&) ([A-Z][a-z]+), ?[0-9]{2,4}[a-z]?')
        self._re_not_end = \
            'viz|.\s[A-Z]|[A-Z].[A-Z]|[\W]pg|.[\W]p|.[\W]\.|[\W]cf|[\W]eg|' \
            '[\W]et|[\W]al|e\.g|etc|i\.e|[\W]pp|.[,;:.!?][,;:.!? ]|..\s'
        self._pat_quotations = '(\"|\'\'|``)'    
        self._re_sentence_low = \
            re.compile('^\s*[a-z].*?...(?<!' + self._re_not_end + 
                       ')[.?!\n]\s+(.*)$', re.DOTALL)
        self._re_quotation = re.compile('' + self._pat_quotations + '')
        self._re_sub_mark = re.compile('^.*%ZN%', re.DOTALL)
        self._re_sub = re.compile('^[.!?\s]+', re.DOTALL)
        
    def _sources_numeral_dot(self, citation_list, sources, text):
        """
        This function looks for sources which begins with numeral and dot.
        """
        for i in range(0, len(citation_list)):
            re_cis_tec = re.compile('^\s*([0-9]+)\.\s')
            if re_cis_tec.search(citation_list[i]['data']):
                num = re_cis_tec.search(citation_list[i]['data']).group(1)
                source = "[" + num + "]"
                re_source = re.compile('[[]' + num + '[-,\w]*?[]]',)
                if re_source.search(text):
                    sources.append((re_source.search(text).group(0), i))
                sources.append((source, i))
        return sources

    def _sources_square_parenthesis_right(self, citation_list, sources, text):
        """
        This function looks for sources which begins with right square 
        parenthesis.
        """
        
        for i in range(0, len(citation_list)):
            if self._re_square_brackets_right.search(citation_list[i]['data']):
                tmp = self._re_square_brackets_right.search(citation_list[i]
                                                            ['data']) 
                source = tmp.group(0)
                num = tmp.group(1)
                re_source = re.compile('^\s*([-,\w]+' + re.escape(num) + 
                                       '[-,\w]+|[-,\w]+' + re.escape(num) + 
                                       '|' + re.escape(num) + '[-,\w]+)[]]',
                                       re.DOTALL)
                if re_source.search(text):
                    sources.append((re_source.search(text).group(0), i))
                sources.append((source, i))
        return sources

    def _sources_square_parenthesis(self, citation_list, sources, text):
        """
        This function looks for sources which begins with square parenthesis.
        """
        for i in range(0, len(citation_list)):
            if self._re_square_brackets.search(citation_list[i]['data']):
                tmp = self._re_square_brackets.search(citation_list[i]['data']) 
                source = tmp.group(0)
                num = tmp.group(1)
                re_source = re.compile('[[]([-,\w]+' + re.escape(num) + 
                                       '[-,\w]+|[-,\w]+' + re.escape(num) + '|' 
                                       + re.escape(num) + '[-,\w]+)[]]')
                if re_source.search(text):
                    sources.append((re_source.search(text).group(0), i))
                sources.append((source, i))
        return sources

    def _sources_others(self, text, sources, aut):
        """
        This function looks for other sources.
        """
        text_tmp = text
        for i in range(0, len(aut)):
            pat_aut = aut[i] + ',? ?' + self._re_etal + ',? ?' + self._re_date
            re_aut = re.compile('' + pat_aut + '', re.DOTALL)
            while re_aut.search(text_tmp):
                source = re_aut.search(text_tmp).group(0)
                text_tmp = re.sub('' + re.escape(source) + '', "", text_tmp)
                sources.append((source, -1))
        text_tmp = text
        re_aut_more = \
            re.compile('by (([A-Z][a-z]+ (and|&) )*[A-Z][a-z]+ '
                       '\(?[0-9]{2,}[a-z]?\)?)')
        while re_aut_more.search(text_tmp):
            source = re_aut_more.search(text_tmp).group(1)
            text_tmp = re.sub('' + re.escape(source) + '', "", text_tmp)
            sources.append((source, -1))
        return sources, text
    
    def _clear_text(self, text):
        """
        This function clears text from white spaces and redundant characters.
        """
        while self._re_new_line.search(text):
            text = self._re_new_line.sub(" ", text)
        while self._re_multiple_white_spaces.search(text):
            text = self._re_multiple_white_spaces.sub(" ", text)
        while self._re_clear_text.search(text):
            text = self._re_clear_text.sub("", text)
        return text

    def assign(self, citation_list, text):
        """
        This main function assigns cited sentence to correct publication.
        """
        self.rest = text
        len_citations = len(citation_list)
        if len_citations == 0: 
            return citation_list
        
        for i in range(0, len_citations):
            citation_list[i]["content"] = None
        
        something_found = False
        second_round = False
        while not something_found:
            sources, aut = [], []
            #Pokud jsou reference oznaceny hranatymi zavorkami
            if not second_round  and len(citation_list) >= 3 \
             and (re.search('^\s*[[].*?[]]', citation_list[0]['data']) \
             or re.search('^\s*[[].*?[]]', citation_list[1]['data']) \
             or re.search('^\s*[[].*?[]]', citation_list[2]['data'])):
                sources = self._sources_square_parenthesis(citation_list,
                                                           sources, text)
            #Pokud jsou reference oznaceny hranatou zavorkou zprava
            elif not second_round and len(citation_list) >= 3 \
             and (re.search('^\s*.*?[]]', citation_list[0]['data']) \
             or re.search('^\s*.*?[]]', citation_list[1]['data']) \
             or re.search('^\s*.*?[]]', citation_list[2]['data'])):
                sources = self._sources_square_parenthesis_right(citation_list,
                                                                 sources, text)
            #Pokud jsou reference oznaceny cislem s teckou
            elif not second_round \
             and (re.search('^\s*[0-9]+\.\s', citation_list[0]['data'])):
                sources = self._sources_numeral_dot(citation_list, sources,
                                                    text)
            #Pokud jsou reference oznaceny hranatymi zavorkami
            elif not second_round \
             and re.search('^\s*[[].*?[]]', citation_list[0]['data']):
                sources = self._sources_square_parenthesis(citation_list,
                                                           sources, text)
            #Pokud jsou reference oznaceny hranatou zavorkou zprava
            elif not second_round \
             and re.search('^\s*.*?[]]', citation_list[0]['data']):
                sources = self._sources_square_parenthesis_right(citation_list,
                                                                 sources, text)
            #Jinak maji libovolne oznaceni
            else:
                something_found = True
                for i in range(0, len(citation_list)):
                    #Vyrizne z reference cast obsahujici jmena autoru
                    if self._re_aut_name.search(citation_list[i]['data']):
                        prefix_text = re.search('^[^A-Za-z]*(.*?)$',
                                                citation_list[i]['data'],
                                                re.DOTALL).group(1)
                        if self._re_aut_name.search(prefix_text):    
                            text_tmp = \
                                self._re_aut_name.search(prefix_text).group(1)
                        else:
                            continue
                    else: 
                        continue
                    #Najde vsechna jmena autoru z reference
                    for jmeno in re.findall('[A-Z][a-zA-Z]+', text_tmp):
                        if jmeno not in aut:
                            aut.append(jmeno) 
             
                #Prida dalsi jmena, ktere nebylo mozne najit v referencich
                text_tmp = text
                while self._re_names_1.search(text_tmp):
                    name = self._re_names_1.search(text_tmp)
                    name_1 = name.group(1)
                    name_2 = name.group(3)
                    text_tmp = \
                        re.sub('' + re.escape(name.group(0)) + '', "", text_tmp)
                    if name_1 not in aut: 
                        aut.append(name_1)
                    if name_2 not in aut: 
                        aut.append(name_2)
                while self._re_names_2.search(text_tmp):
                    name = self._re_names_2.search(text_tmp)
                    name_1 = name.group(1)
                    text_tmp = \
                        re.sub('' + re.escape(name.group(0)) + '', "", text_tmp)
                    if name_1 not in aut: 
                        aut.append(name_1)
                while self._re_names_3.search(text_tmp):
                    name = self._re_names_3.search(text_tmp)
                    name_1 = name.group(1)
                    name_2 = name.group(3)
                    text_tmp = \
                        re.sub('' + re.escape(name.group(0)) + '', "", text_tmp)
                    if name_1 not in aut: 
                        aut.append(name_1)
                    if name_2 not in aut: 
                        aut.append(name_2)
                sources, text = self._sources_others(text, sources, aut)
              
            #Pridame do textu znacky znacici moznou hranici vety
            text = re.sub('^', "%ZN%", text)
            text = re.sub('$', "%ZN%", text)
            text = \
            re.sub('(...(?<!' + self._re_not_end 
                   + ')[.?!][ \n])', "\g<1>%ZN%%ZN%", text)
            #Najdeme vsechny vety v textu
            if not second_round: 
                sentences = re.findall('%ZN%\s*(.*?)%ZN%', text, re.DOTALL)
            second_round = True  
            
            text_tmp = text
            #Prohledame vsechny sentences a zaznamename je, pokud obsahuji 
            #nejaky nalezeny zdroj
            for sentence in sentences:
                for source, ri in sources:
                    if sentence.find(source) != -1:
                        credibility = 100
                        #Upravi vetu zacinajici malym pismenem
                        if self._re_sentence_low.search(sentence):
                            credibility -= 10 
                            sentence = \
                                self._re_sentence_low.search(sentence).group(1)
                        sentence = sentence.replace("%ZN%", "")
                        count = len(re.findall('' + self._pat_quotations 
                                               + '', sentence))
                        
            
                        #Upravi vetu obsahujici necelou citaci v uvozovkach
                        if count % 2 == 1:
                            credibility -= 5
                            sentence_tmp = sentence
                            re_cit_quotation = \
                                re.compile('' + re.escape(sentence) + '.*?(' 
                                           + self._pat_quotations + '\.|\.' 
                                           + self._pat_quotations + ')',
                                           re.DOTALL)
                            if self._re_quotation.search(sentence) \
                            and re_cit_quotation.search(text_tmp):
                                credibility -= 5
                                sentence = \
                                    re_cit_quotation.search(text_tmp).group(0)
                                #Pokud by nahodou byla sentence nalezena spatne,
                                #nebudu se nic upravovat
                                if len(sentence) > 1000: 
                                    sentence = sentence_tmp
            
                        sentence = self._re_sub_mark.sub("", sentence)
                        sentence = self._re_sub.sub("", sentence)
            
                        #Jsou-li vety moc dlouhe, pokusi se je spravne zkratit
                        if len(sentence) > 1000:
                            credibility -= 10
                            re_long_1 = \
                                re.compile('^.*\n(.*' + re.escape(source) 
                                           + '.*?$)', re.DOTALL)
                            re_long_2 = \
                                re.compile('(^.*?' + re.escape(source) 
                                           + '.*?)\n.*?$', re.DOTALL)
                            if re_long_1.search(sentence):
                                sentence = re_long_1.search(sentence).group(1)
                                if len(sentence) > 1000:
                                    if re_long_2.search(sentence): 
                                        sentence = \
                                            re_long_2.search(sentence).group(1)
                            elif re_long_2.search(sentence):
                                sentence = re_long_2.search(sentence).group(1)
                                if len(sentence) > 1000:
                                    if re_long_1.search(sentence): 
                                        sentence = \
                                            re_long_1.search(sentence).group(1)
                            if len(sentence) > 1000: 
                                break
            
                        if len(sentence) > 40:
                            if ri != -1:
                                something_found = True
                                citation_list[ri]['content'] = \
                                    (self._clear_text(sentence), int((credibility 
                                     + citation_list[ri]["credibility"]) / 2))
                                    
                                self.rest = \
                                    re.sub(re.escape(sentence), "", text)
                            else:
                                for i in range(0, len(citation_list)):
                                    if citation_list[i]['content'] != None:
                                        continue
                                    if self._re_aut_name.search(citation_list[i]
                                                                ['data']):
                                        prefix_text = \
                                            re.search('^[^A-Za-z]*(.*?)$',
                                                      citation_list[i]['data'],
                                                      re.DOTALL).group(1)
                                        if self._re_aut_name.search(prefix_text):
                                            prefix = \
                                                self._re_aut_name.search(
                                                             prefix_text).group(1)
                                            names = re.findall('([A-Z][a-zA-Z]+)',
                                                               source)
                                            
                                            for name in names:
                                                if re.search(name, prefix,
                                                             re.IGNORECASE):
                                                    citation_list[i]['content'] = \
                                                        (self._clear_text(sentence),
                                                         int((credibility 
                                                         + citation_list[ri]["credibility"]) 
                                                         / 2) - 10)
                                                    break
        return citation_list

    def get_rest(self):
        """
        Returns the rest of the text.
        """
        return self.rest


#-------------------------------------------------------------------------------
# End of class _ReferenceHandler
#-------------------------------------------------------------------------------


class DocumentWrapper(object):
    """
    This class separates document to it's particular parts - head, chapters and
    references.
    """
    
    def __init__(self):
        self.original_text = ""
        self.rest = ""
        self.meta = ""
        self.chapters = []
        self.citations = []
    
    def _handle_meta(self, text):
        mw = _MetaWrapper()
        self.meta = mw.get_meta(text)
        self.rest = mw.get_rest()
    
    def _handle_citations(self, text):
        cw = _CitationWrapper()
        self.citations = cw.get_citations(text)
        self.rest = cw.get_rest()

    def _handle_references(self, citation_list, text):
        rh = _ReferenceHandler()
        self.citations = rh.assign(citation_list, text)
        self.rest = rh.get_rest()
        
    def _handle_chapters(self, text):
        chw = _ChapterWrapper()
        self.chapters = chw.get_chapters(text)
        self.rest = chw.get_rest()

    def wrap(self, text):
        # Tato metoda bude ridit celou extrakci, musime vybrat spravne poradi
        # extrakce jednotlivych casti a vyuzivat metod get_rest() privatnich 
        # wrapovacich trid.    
        
        # Tady se konvertuji vsechny stringy (citace, kapitoly apod.) na 
        #objekty, ulozi se do instance TextualDocumentu.
        td = TextualDocument()
        
        self.original_text = text
        self.rest = text

        self._handle_meta(self.rest)
        td.set_meta(self.meta)
        
        self._handle_citations(self.rest)
        self._handle_references(self.citations, self.rest)
        self.rest = self.rest.replace("%ZN%", "")
        self._handle_chapters(self.rest)
        
        for chpt in self.chapters:
            chapter = RRSPublication_section()
            chapter.set("title", chpt["name"])
            if chpt["fulltext"] != "":
                chapter.set('text_position_from', chpt["position_from"])
                chapter.set('text_position_to', chpt["position_to"]) 
            #chapter.set("content", chpt["fulltext"])
            chapter.set("credibility", chpt["credibility"])
            if chpt["num"] != 0:
                chapter.set("number", chpt["num"])
            td.set_chapter(chapter)
        
        for cit in self.citations:
            citation = RRSCitation()
            if cit["content"] != None:
                citation.set("credibility", cit["content"][1])
                citation.set("content", cit["content"][0])
            else:
                citation.set("credibility", 50)
            _ref = RRSReference(content=cit["data"])
            _ref.set('credibility', cit["credibility"])
            _rel2 = RRSRelationshipPublicationReference()
            #===================================================================
            # if "publication" in cit:
            #    _rel2.set_entity(cit["publication"])
            #    _ref.set("referenced_publication", _rel2)
            #===================================================================
            citation.set("reference", _ref)
            td.set_citation(citation)
                
        return td
#-------------------------------------------------------------------------------
# End of class DocumentWrapper
#-------------------------------------------------------------------------------


class _DocumentWrapperTestSuite(object):
    def __init__(self):
        pass 
    
if __name__ == '__main__':
    f = '/media/Data/Skola/FIT/prace/NLP/clanky/converted/21a05ccefa2d83f865c644002c64b8dad6904c97.txt'
    f2 = 'media/Data/Skola/FIT/prace/NLP/clanky/converted/21a6e3c7dc0637d25566704dd490c8a1cf135e4c.txt'
    docw = DocumentWrapper()
    st = open(f, 'r')
    rr = docw.wrap(st.read())
    print rr.get_meta()
    print rr.get_citations()
    print rr.get_chapters()
    
