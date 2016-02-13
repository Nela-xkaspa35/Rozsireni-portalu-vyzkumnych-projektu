#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Entityextractor is a library which provides interface for recognizing and extracting
named entities from text.
"""
from lxml import etree
from rrslib.db.model import *
from rrslib.dictionaries.rrsdictionary import *
from rrslib.xml.xmlconverter import Model2XMLConverter
from rrsregex import ISBNre, URLre
import StringIO
import os
import re
import string

__modulename__ = "entityextractor"
__author__ = "Tomas Lokaj, Stanislav Heller, Jan Svoboda, Petr Holasek"
__email__ = "xlokaj03@stud.fit.vutbr.cz, xhelle03@stud.fit.vutbr.cz, "\
            "xsvobo80@stud.fit.vutbr.cz, xholas02@stud.fit.vutbr.cz"
__date__ = "$27-Mar-2010 17:23:12$"
__version__ = "$0.10.9.20$"



try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")



#_______________________________________________________________________________


# entityextractor constants
TITLE = int("0x00000001", 0)
BOOKTITLE = int("0x00000002", 0)
PUBLISHER = int("0x00000004", 0)
PUBLISHED_DATE = int("0x00000008", 0)
AUTHOR = int("0x00000010", 0)
EDITOR = int("0x00000020", 0)
EMAIL = int("0x00000030", 0)
EVENT = int("0x00000040", 0)
ORGANIZATION = int("0x00000080", 0)
LOCATION = int("0x00000100", 0)
ISBN = int("0x00000200", 0)
ISSN = int("0x00000400", 0)
PAGES = int("0x00000800", 0)
VOLUME = int("0x00001000", 0)
TO_APPEAR = int("0x00002000", 0)
SUBMITTED = int("0x00003000", 0)
TELEPHONE = int("0x00004000", 0)
FAX = int("0x00008000", 0)
PROJECT = int("0x00010000", 0)
URL = int("0x00020000", 0)

# all params together
ALL = int("0xffffffff", 0)

# dictionary mapping entity constants to methods
ENTITY2METHOD = { TITLE: 'find_title',
                  BOOKTITLE: 'find_booktitle',
                  PUBLISHER:'find_publisher',
                  PUBLISHED_DATE: 'find_published_date',
                  AUTHOR: 'find_authors',
                  EDITOR: 'find_editors',
                  EMAIL: 'find_email',
                  EVENT: 'find_event',
                  ORGANIZATION: 'find_organization',
                  LOCATION: 'find_location',
                  ISBN: 'find_isbn',
                  ISSN: 'find_issn',
                  PAGES: 'find_pages',
                  VOLUME: 'find_volume',
                  TO_APPEAR: 'find_to_appear',
                  SUBMITTED: 'find_submitted',
                  TELEPHONE: 'find_telephone',
                  FAX: 'find_fax',
                  PROJECT: 'find_project',
                  URL: 'find_url'
                }

# dictionary mapping methods to entity constants
METHOD2ENTITY = { 'find_title':TITLE,
                  'find_booktitle':BOOKTITLE,
                  'find_publisher':PUBLISHER,
                  'find_published_date':PUBLISHED_DATE,
                  'find_authors':AUTHOR,
                  'find_editors':EDITOR,
                  'find_email': EMAIL,
                  'find_event':EVENT,
                  'find_organization':ORGANIZATION,
                  'find_location':LOCATION,
                  'find_isbn':ISBN,
                  'find_issn':ISSN,
                  'find_pages':PAGES,
                  'find_volume':VOLUME,
                  'find_to_appear':TO_APPEAR,
                  'find_submitted':SUBMITTED,
                  'find_telephone':TELEPHONE,
                  'find_fax':FAX,
                  'find_project':PROJECT,
                  'find_url':URL
                 }


#-------------------------------------------------------------------------------


class _EntityExtractorComponent(object):
    """
    Parent class of all extractor components.
    """
    def __init__(self):
        self.rest = None

    def get_rest(self):
        """
        Returns the rest of the text without extracted information.
        """
        return self.rest

#-------------------------------------------------------------------------------
# end of class _EntityExtractorComponent
#-------------------------------------------------------------------------------



class EntityExtractor(object):
    """
    This class impelments all functionalities below (NameExtractor, EventExtractor...)
    to get effective system for recognizing named entities.

    Singleton.
    """
    __single = None # Singleton instance

    def __new__(classtype, *args, **kwargs):
        # Check to see if a __single exists already for this class
        # Compare class types instead of just looking for None so
        # that subclasses will create their own __single objects
        if classtype != type(classtype.__single):
            classtype.__single = object.__new__(classtype, *args)
        return classtype.__single


    def __init__(self):
        self.mail_e = EntityExtractor.EmailExtractor()
        self.loca_e = EntityExtractor.GeographicLocationExtractor()
        self.name_e = EntityExtractor.NameExtractor()
        self.email_e = EntityExtractor.EmailExtractor
        self.even_e = EntityExtractor.EventExtractor()
        self.date_e = EntityExtractor.DateExtractor()
        self.orga_e = EntityExtractor.OrganizationExtractor()
        self.tele_e = EntityExtractor.TelephoneNumberExtractor()
        self.proj_e = EntityExtractor.ProjectExtractor()


    class ProjectExtractor(_EntityExtractorComponent):
        """
        This class extracts project names from text.
        """

        def __init__(self):
            _EntityExtractorComponent.__init__(self)
            self._rrsdict_acronyms = RRSDictionary(PROJECT_ACRONYMS, CASE_INSENSITIVE)
            self._rrsdict_titles = RRSDictionary(PROJECT_TITLES, CASE_INSENSITIVE)
            self._rrsdict_locations = RRSDictionary(COUNTRIES, CASE_INSENSITIVE)
            self._rrsdict_locations.extend(RRSDictionary(CITIES, CASE_INSENSITIVE))

            self.org_e = EntityExtractor.OrganizationExtractor()
            self.rest = ""
            self._acronyms = []

            self._acronym_blacklist = ['UNIVERSITY', 'PURPOSE', 'BACKGROUND',
                                       'BATHYMETRIC', 'SURVEY', 'ACCURACY',
                                       'STANDARDS', 'ABSTRACT', 'ABSTRACTS',
                                       'INTRDUCTION', 'IMPLEMENTATION', 'EXPERIMENTS',
                                       'CONCLUSIONS', 'SUPERVISOR', 'SUPERVISING' ]

            self._pat_project = \
                "((research|RESEARCH|Research|\w*-?sponsored|\w*-?SPONSORED) )?"\
                "(projects?|Projects?|PROJECTS?)"
            self._pat_quotes = "(" + u"\u00b4".encode('utf - 8') + "|" \
                + u"\u00a8".encode('utf - 8') + "|" + u"\u201c".encode('utf - 8') \
                + "|" + u"\u201d".encode('utf - 8') + "|" + u"\u2018".encode('utf - 8') \
                + "|" + u"\u2019".encode('utf - 8') + "|" + u"\u201a".encode('utf - 8') \
                + "|" + u"\u201e".encode('utf - 8') + "|" + u"\u02dd".encode('utf - 8') \
                + ")"
            self._pat_prefix = ('(The\s+|the\s+|THE\s+|,\s*|:\s*|\(\s*|;\s*|-\s*)')
            self._re_project_quotes = re.compile("(" + self._pat_project + "\s*"
                                                + self._pat_quotes + "\s*([A-Z].{3,100}?)"
                                                + self._pat_quotes + ")\W", re.DOTALL)
            self._re_acronym = re.compile('\(?([A-Z]{2,})\)? ' + self._pat_project + '|'
                                         + self._pat_project + " \(?([A-Z]{2,})\)?")
            self._re_the_project_1 = re.compile('(' + self._pat_prefix + 
                                                '([A-Zao0-9][-–a-zA-Z0-9\']+\s+)+'
                                                + self._pat_project + ')\W', re.DOTALL)
            self._re_the_project_2 = re.compile('(' + self._pat_prefix + self._pat_project
                                                + " ([A-Z]\w+) (\(.+?\)|[-A-Z0-9/]+))")

        def _search_with_the(self, text):
            """
            Finds project written like:
                The Hellenic Cadastre Project
                the ALT project
                the project CUTE (Clean Urban Transport for Europe)
            """
            projects = []
            initial_credibility = 50

            #First search
            potential_projects = self._re_the_project_1.findall(text)
            for p in potential_projects:
                if re.search('research|sponsored', p[2], re.I) or p[2][0].islower():
                    continue
                credibility = initial_credibility
                proj = RRSProject()
                title = None
                if p[1][0].isupper() and p[5][0].isupper():
                    title = p[0]
                    credibility += 20
                else:
                    title = p[0]
                    if not p[1][0].isupper():
                        title = re.sub("^" + self._pat_prefix, "", title, re.I)
                        credibility -= 10
                    if not p[5][0].isupper():
                        title = re.sub("\s+" + self._pat_project + "$", "",
                                       title, re.IGNORECASE)
                        credibility -= 10
                proj.set('title', title)
                proj.set('credibility', credibility)
                projects.append(proj)
                text = re.sub(re.escape(p[0]), "", text)
                self._rest = text

            #Second search
            potential_projects = self._re_the_project_2.findall(text)
            for p in potential_projects:
                credibility = initial_credibility + 20
                proj = RRSProject()
                if len(p[5]) > len(p[6]):
                    title = p[5]
                    acronym = p[6]
                else:
                    title = p[6]
                    acronym = p[5]

                if len(re.findall('([0-9])', title)) >= \
                len(re.findall('([a-zA-Z])', title)):
                    proj.set('ref_code', title)
                    title = None
                elif len(re.findall('([0-9])', acronym)) >= \
                len(re.findall('([a-zA-Z])', acronym)):
                    proj.set('ref_code', acronym)
                    acronym = None

                proj.set('title', title)
                proj.set('acronym', acronym)
                proj.set('credibility', credibility)
                projects.append(proj)
                text = re.sub(re.escape(p[0]), "", text)
                self._rest = text

            return projects

        def _search_with_quotes(self, text):
            """
            Finds project written like:
                Project "Development of Health Advisory Service in Organic Dairy Herds"
                project "Performance-based regulation for distribution utilities"
            """
            projects = []
            initial_credibility = 30

            potential_projects = self._re_project_quotes.findall(text)

            for p in potential_projects:
                credibility = initial_credibility
                proj = RRSProject(title=p[5])
                if p[3][0].isupper():
                    credibility += 20
                proj.set('credibility', credibility)
                projects.append(proj)
                text = re.sub(re.escape(p[0]), "", text)
                self._rest = text

            return projects

        def _search_with_acronyms(self, text):
            """
            Looks for potential acronyms.
            """
            initial_credibility = 10
            potential_acronyms = self._re_acronym.findall(text)
            acronyms = []
            projects = []

            for acr in potential_acronyms:
                if acr[0] != "":
                    acr = acr[0]
                else:
                    acr = acr[1]
                if len(acr) <= 2:
                    continue
                if acr in self._acronym_blacklist:
                    continue
                if self._rrsdict_locations.contains_key(acr):
                    continue
                if acr in acronyms:
                    continue
                acronyms.append(acr)

            for acronym in acronyms:
                credibility = initial_credibility
                title = None
                if text.find("(" + acronym + ")") != -1:
                    credibility += 20
                ls = acronym[0]
                le = acronym[len(acronym) - 1]
                pat_title_start = "\("
                pat_title_end = "\)"

                pat_title = pat_title_start + "?" + ls + "\w[^.]*?" + le + "\w+"\
                    + pat_title_end + "?"

                re_title_start = re.compile(pat_title_start)
                re_title_end = re.compile(pat_title_end)
                re_title_1 = re.compile("^.*(" + pat_title + ")\s*\(?"
                                        + re.escape(acronym) + "\)?\s*"
                                        + self._pat_project, re.DOTALL)
                re_title_2 = re.compile(self._pat_project + "\s*\(?"
                                        + re.escape(acronym) + "\)?\s*("
                                        + pat_title + ").*$", re.DOTALL)

                if re_title_1.search(text):
                    title = re_title_1.search(text).group(1)
                    credibility += 20
                elif re_title_2.search(text):
                    title = re_title_2.search(text).group(1)
                    credibility += 20

                if title != None:
                    title = re_title_start.sub("", title)
                    title = re_title_end.sub("", title)
                    if len(title) > 100 \
                    or len(self.org_e.extract_organizations(title)) != 0:
                        title = None
                        acronym = None

                if acronym != None:
                    project = RRSProject(acronym=acronym, title=title)
                    project.set('credibility', credibility)
                    projects.append(project)

            return projects


        def _complete_project_data(self, projects):
            """
            This method completes founded data about project and recalculates
            it's credibility.
            """
            completed_projects = []
            completed_acronyms = {}
            completed_titles = {}

            for project in projects:
                title = project.get('title')
                acronym = project.get('acronym')
                credibility = project.get('credibility')

                #Switch title and acronym
                if acronym == None:
                    if re.search('^[A-Z]+$', title):
                        acronym = title
                        title = None

                if acronym != None:
                    #Look to dictionary for an acronym
                    if self._rrsdict_acronyms.contains_key(acronym):
                        credibility += 20
                        if title == None:
                            titles = self._rrsdict_acronyms.translate(acronym)
                            for t in titles:
                                if isinstance(t, list):
                                    t = t[0]
                                if len(titles) == 1 or re.search(re.escape(t),
                                   text, re.IGNORECASE | re.DOTALL) != None:
                                    title = t
                                    if len(title.split(" ")) > 1:
                                        credibility += 20
                                    else:
                                        credibility += 10
                                    break
                else:
                    if title != None:
                        #Look to dictionary for a title
                        if self._rrsdict_titles.contains_key(title):
                            credibility += 20
                            acronyms = self._rrsdict_titles.translate(title)
                            for a in acronyms:
                                if isinstance(a, list):
                                    a = a[0]
                                if len(acronyms) == 1 or re.search("\W"
                                   + re.escape(a) + "\W", text, re.IGNORECASE
                                   | re.DOTALL) != None:
                                    acronym = a
                                    credibility += 10
                                    break

                if credibility > 100:
                    credibility = 100

                project.set('title', title)
                project.set('acronym', acronym)
                project.set('credibility', credibility)

                if acronym == None:
                    if title not in completed_titles.keys():
                        completed_titles[str(title)] = project
                    elif completed_titles[str(title)].get('credibility') < credibility:
                        credibility = project.get('credibility') + 5
                        if credibility > 100:
                            credibility = 100
                        project.set('credibility', project.get('credibility') + 5)
                        completed_titles[str(title)] = project
                elif acronym not in completed_acronyms.keys():
                    completed_acronyms[acronym] = [project]
                else:
                    completed_acronyms[acronym].append(project)

            for acronym in completed_acronyms.keys():
                if len(completed_acronyms[acronym]) == 1:
                    project = completed_acronyms[acronym][0]
                    if str(project.get('title')) in completed_titles.keys():
                        completed_titles.pop(str(project.get('title')))
                    completed_projects.append(project)
                else:
                    titles = {}
                    for project in completed_acronyms[acronym]:
                        if str(project.get('title')) not in titles.keys() \
                        or project.get('credibility') > \
                        titles[str(project.get('title'))][0]:
                            titles[str(project.get('title'))] = \
                                (project.get('credibility'), project)
                            if str(project.get('title')) in completed_titles.keys():
                                completed_titles.pop(str(project.get('title')))

                    for title in titles.keys():
                        completed_projects.append(titles[title][1])

            for project in completed_titles.values():
                if project.get('credibility') > 100:
                    project.set('credibility', 100)
                completed_projects.append(project)

            return completed_projects


        def extract_projects(self, text):
            """
            This method looks for project names in text.
            """

            projects = []
            projects.extend(self._search_with_quotes(text))
            projects.extend(self._search_with_the(text))
            projects.extend(self._search_with_acronyms(text))

            projects = self._complete_project_data(projects)

            return projects



    class EmailExtractor(_EntityExtractorComponent):
        """
        Searching e-mails on page.
        Many of the e-mails on pages are crypted, so this class is able to handle some
        kinds of them. All of the used methods aren't case sensitive (it can handle
        both: lowercase and uppercase). To enumerate possible methods of e - mail - crypting:

            - john.black@gmail.com - normal way of e - mail string
            - john.black (at) gmail.com - (at) hack
            - john.black(at - sign)gmail.com - (at - sign) hack
            - john.black & #64;gmail.com  -  &#64; HTML entity
            - john (dot) black@gmail (dot) com - (dot) hack
            - john.black < img source = "php.gen()" /> gmail.com - img hack
            - {alice, bob, cecilia}@gmail.com - multi - mail format

        and all combinations of them.
        """
        def __init__(self):
            _EntityExtractorComponent.__init__(self)
            self.html = ""
            self._user_pattern = "[A-Z0-9!#$%&\'\*\+/\=\?\^_`\|~\._\-]+ ?"
            self._host_pattern = " ?[A-Z0-9\.\-]+\.[A-Z]{2,4} ?"
            self._user_pat_dot = "(?:[A-Z0-9_%\-]+ ?\(? ?DOT ?\)? ?)+[A-Z0-9_%\-]+"
            self._host_pat_dot = " ?(?:[A-Z0-9\-]+ ?\(? ?DOT ?\)? ?)+[a-z]{2,4} ?"
            self._multi_host_pattern = "\{[A-Z0-9!#$%&\'\*\+/\=\?\^_`\|~\._\-, ]+\}" + \
                                       "@[A-Z0-9\.\-]+\.[A-Z]{2,4}"
            self._imgmark = "&&IMG&&" #

            self._mailmarks = ("@", # common form
                               "&#64;", # HTML entity
                               "\(?[aA][Tt]-[Ss][Ii][gG][Nn]\)?", # at-sign hack
                               "[( ]{1,2}[aA][Tt][ )]{1,2}", # (at) hack
                               self._imgmark)                        # img hack


        def _format(self):
            """
            Converts all found mails to common form of e - mail.
            """
            for pat in self._mailmarks:
                self.mails = map(lambda x: re.sub(pat, "@", x), self.mails)
            self.mails = map(lambda f: re.sub("\(?[ ]?[dD][Oo][Tt][ ]?\)?", ".", f), self.mails)
            mm = map(lambda x: re.sub("[ ]+", "", x), self.mails)
            # delete duplicate mails
            self._result_mails = []
            for m in mm:
                dupl = False
                for compare in mm:
                    if m in compare and m is not compare:
                       dupl = True
                       break
                if not dupl:
                    try:
                        self._result_mails.append(RRSEmail(email=m))
                    except RRSDatabaseValueError:
                        pass
            return self._result_mails


        def _get_all_mails(self):
            """
            Harvests all possible e - mail addresses from html page.
            """
            # substitute images to non-tagged string
            # because image between two strings could be potentially img with zavinac
            markup_text = re.sub("<img[^>]+>", self._imgmark, self.txt)

            # get e-mail from mailto:
            self.mails.extend(re.findall(r"(?<=mailto:)" + self._user_pattern + "@" + \
                              self._host_pattern, markup_text, re.I))

            # clean html from all tags (because of crypting mail string by many tags
            # like: <span>john</span><a>@</a><span>gmail.</span><div>com</div> )
            pure_text = re.sub("<[^>]+>", " ", markup_text)
            pure_text = re.sub("[" + string.whitespace + "]+", " ", pure_text)
            # try to catch all possibe emails
            for m in self._mailmarks:
                self.mails.extend(re.findall(r"" + self._user_pattern + m + \
                                             self._host_pattern, pure_text, re.I))
                self.mails.extend(re.findall(r"" + self._user_pat_dot + m + \
                                             self._host_pat_dot, pure_text, re.I))
                self.mails.extend(re.findall(r"" + self._user_pat_dot + m + \
                                             self._host_pattern, pure_text, re.I))
                self.mails.extend(re.findall(r"" + self._user_pattern + m + \
                                             self._host_pat_dot, pure_text, re.I))

            # delete mails from text
            for em in self.mails:
                pure_text = re.sub(re.escape(em), "", pure_text)

            # get multimail format e-mail addresses: {jimmy,john,anette}@fit.vutbr.cz
            _multi = re.findall(self._multi_host_pattern, pure_text, re.I)

            # delete found emails from text
            for em in _multi:
                pure_text = re.sub(re.escape(em), "", pure_text)

            for mmail in _multi:
                hosts, domain = mmail.split("@")
                hosts = re.sub("[\{\}]", "", hosts)
                spl_hosts = hosts.split(",")
                for h in spl_hosts:
                    self.mails.append(h + "@" + domain)
            self.rest = pure_text


        def _find(self):
            self.mails = []
            self._get_all_mails()
            return self._format()


        def get_html_emails(self, elemtree):
            """
            Main method for searching on HTML pages.
            """
            self.txt = etree.tostring(elemtree)
            return self._find()


        def get_emails(self, text):
            """
            Main method for searching in text.
            """
            self.txt = text
            return self._find()

    #---------------------------------------------------------------------------
    # end of class EmailSearch
    #---------------------------------------------------------------------------


    class GeographicLocationExtractor(_EntityExtractorComponent):
        """
        This class is ment to be an extractor of geographical locations. It recognizes
        cities and countries all over the world. Using geographical ontology
        searches for all missing data in an inteligent way: when only city was
        recognized, it finds also a region, country and continent, where the city
        is located.
        -----
        Sadly, there's no algorithm to recognize country of cities, which are located
        in more than one country. This algorithm should be based on frequency of
        appearance (of city or phrase) in text or on best-known-first algorithm,
        but we dont have data about size of city (inhibitants, km-square, ...).
        -----
        We hope, that one day there in RRS will be implemented real geographical
        onotology and this class became useless.
        """

        def __init__(self):
            """
            GeographicLocationExtractor constructor.
            """
            _EntityExtractorComponent.__init__(self)

            self.city2woeid = RRSDictionary(CITY2WOEID, CASE_INSENSITIVE)
            self.woeid2city = RRSDictionary(WOEID2CITY, CASE_INSENSITIVE)
            self.woeid2cityaltname = RRSDictionary(WOEID2ALTNAME, CASE_INSENSITIVE)
            self.woeid2country = RRSDictionary(WOEID2COUNTRY, CASE_INSENSITIVE)
            self.country2countrywoeid = RRSDictionary(COUNTRY2CWOEID, CASE_INSENSITIVE)
            self.countrywoeid2city = RRSDictionary(CWOEID2CITY, CASE_INSENSITIVE)
            self.countrywoeid2country = RRSDictionary(CWOEID2COUNTRY, CASE_INSENSITIVE)
            self.countrywoeid2continent = RRSDictionary(CWOEID2CONTINENT, CASE_INSENSITIVE)
            self.city2postcode = RRSDictionary(POSTCODES, CASE_INSENSITIVE)


        class TemporaryGeographicalOntology(object):
            """
            This class represents temporary geographical ontology, which is used
            for more accurate specification of location in case that only some
            part of location is recognized.

            Class TemporaryGeographicalOntology contains only one classmethod,
            go_up_in_hierarchy(), which represents the whole process of searching
            in ontology.
            """
 
            @classmethod
            def go_up_in_hierarchy(self, objname, objname_type, city2woeid,
                                   woeid2city, woeid2cityaltname, woeid2country,
                                   country2countrywoeid, countrywoeid2country,
                                   countrywoeid2continent, search_altnames=False):
                """
                Methods takes two parameters - objname and objname_type.
                Method searches all data above param in hierarchy
                city - woeid - city altnames - country - country_altnames - country_woeid - continent.
                """

                h = {'city': None, 'city_woeid': None, 'city_altnames': None,
                     'country' : None, 'country_altnames': None,
                     'country_woeid': None, 'continent': None}
                if objname is None: return h

                if objname_type == 'city':
                    h['city'] = objname
                    city_woeids = city2woeid.translate(objname)
                    if city_woeids:
                        woeid = city_woeids[len(city_woeids) - 1]
                        h['city_woeid'] = woeid
                        
                        # xlokaj03: this is not necessary, altnames are not 
                        # in db yet, search_altnames is always false
                        if search_altnames:
                            city_altnames = woeid2cityaltname.translate(woeid)
                            h['city_altnames'] = city_altnames
                            
                        countries = woeid2country.translate(woeid)
                        if countries:
                            h['country'] = countries[0]
                            country_woeids = country2countrywoeid.translate(countries[0])
                            if country_woeids:
                                h['country_woeid'] = country_woeids[0]
                                continents = countrywoeid2continent.translate(country_woeids[0])
                                if continents:
                                    h['continent'] = continents[0]
                                    
                                # xlokaj03: this is not necessary, altnames are not 
                                # in db yet, search_altnames is always false    
                                if search_altnames:
                                    country_altnames = countrywoeid2country.translate(country_woeids[0])
                                    if len(country_altnames) > 1:
                                        h['country_altnames'] = country_altnames
                                        
                elif objname_type == 'woeid':
                    h['city_woeid'] = objname
                    cities = woeid2city.translate(objname)
                    if cities:
                        h['city'] = cities[0]
                        
                    # xlokaj03: this is not necessary, altnames are not 
                    # in db yet, search_altnames is always false  
                    if search_altnames:
                        city_altnames = woeid2cityaltname.translate(objname)
                        h['city_altnames'] = city_altnames
                    countries = woeid2country.translate(objname)
                    
                    if countries:
                        h['country'] = countries[0]
                        country_woeids = country2countrywoeid.translate(countries[0])
                        if country_woeids:
                            h['country_woeid'] = country_woeids[0]
                            continents = countrywoeid2continent.translate(country_woeids[0])
                            if continents:
                                h['continent'] = continents[0]
                                
                            # xlokaj03: this is not necessary, altnames are not 
                            # in db yet, search_altnames is always false  
                            if search_altnames:
                                country_altnames = countrywoeid2country.translate(country_woeids[0])
                                if len(country_altnames) > 1:
                                    h['country_altnames'] = country_altnames
                                    
                elif objname_type == 'country':
                    h['country'] = objname
                    country_woeids = country2countrywoeid.translate(objname)
                    if country_woeids:
                        h['country_woeid'] = country_woeids[0]
                        continents = countrywoeid2continent.translate(country_woeids[0])
                        if continents:
                            h['continent'] = continents[0]
                            
                        # xlokaj03: this is not necessary, altnames are not 
                        # in db yet, search_altnames is always false  
                        if search_altnames:
                            country_altnames = countrywoeid2country.translate(country_woeids[0])
                            if len(country_altnames) > 1:
                                h['country_altnames'] = country_altnames
                                
                elif objname_type == 'cwoeid':
                    h['country_woeid'] = objname
                    countries = countrywoeid2country.translate(objname)
                    if countries:
                        h['country'] = countries[0]
                    continents = countrywoeid2continent.translate(objname)
                    if continents:
                        h['continent'] = continents[0]
                        
                    # xlokaj03: this is not necessary, altnames are not 
                    # in db yet, search_altnames is always false  
                    if search_altnames:
                        country_altnames = countrywoeid2country.translate(objname)
                        if len(country_altnames) > 1:
                            h['country_altnames'] = country_altnames
                return h


        def find_street(self, text):
            """
            Tries to find a street in text.
            """
            iterate = 1
            street = None
            is_digit = 0

            text_tmp = string.lower(text)

            while iterate == 1:        # endless cycle (but it will iterate only once because terminations)
                ind = string.find(text_tmp, ' street')
                if ind != -1:
                    last_ind = ind + 7
                    break
                ind = string.find(text_tmp, ' avenue')
                if ind != -1:
                    last_ind = ind + 7
                    break
                ind = string.find(text_tmp, ' road')
                if ind != -1:
                    last_ind = ind + 5
                    break
                ind = string.find(text_tmp, ' broadway')
                if ind != -1:
                    last_ind = ind + 9
                    break
                ind = string.find(text_tmp, ' way')
                if ind != -1:
                    last_ind = ind + 4
                    break
                break

            if ind > -1: # a hit!
                for first_ind in range(ind - 1, -1, -1):   #index of number of the street
                    sample = text[first_ind]
                    if is_digit == 0:
                        if sample.isdigit() == True:     # find first digit searching from the end
                            is_digit = 1
                    else:                                # find last digit searching from the end
                        if sample.isdigit() == True:
                            is_digit = 1
                        else:
                            first_ind += 1
                            break
                if is_digit == 1: # some digit was found - success
                    street = text[first_ind:last_ind]

            return street


        def extract_address(self, text, city, city2postcode):
            """
            Tries to find an address in text for the city given as param.
            """
            # make regular expression
            codesList = city2postcode.translate(city)
            pcodes = None
            if codesList:
                pcodes = "(?:"
                for c in codesList:
                    pcodes += c + "|"
                pcodes = pcodes.rstrip("|") + ")"

            # if there were some post codes for this city, try to search address using them
            if (pcodes):
                address = re.search(r"([\d/-]+ (?:[A-Z]|\d+[\.snrt])[\w\. ]*|(?:[A-Z]|\d+[\.snrt])[\w\. ]" \
                    r"*? [\d/-]+)[, ] ?" + pcodes, text, re.UNICODE)
                if(address):
                    return address.group(1)
            # if nothing was found or there weren't any pcodes for this city, try another search pattern
            address = self.find_street(text)
            if(address):
                return address
            return None


        def extract_locations(self, text, search_altnames=False):
            """
            Recognizes locations (cities, countries etc.) and using geo ontology
            gets date from higher level - when city was found, finds appropriate
            country and continent for that city.
            """
            # invalid cities and states (so far) - can be changed at any time
            # NOTE! - any new invalid cities must be capitalized to make wanted effect
            invalid_cities = ('University', 'Of', 'For', 'Data', 'Research', 'In',
                              'College', 'Center', 'And', 'De', 'Usa', 'At', 'Del',
                              'As', 'Section', 'Japan', 'Di', 'We', 'Boulevard',
                              'Vii', 'Mars', 'Theme', 'West', 'Dan', 'Dept', 'Sri',
                              'Institute', 'General', 'To', 'February', 'School',
                              'Dutch', 'National', 'Cirl', 'Mobile', 'Vladimir',
                              'California', 'Media', 'Street', 'Republic');

            iterate = 1
            tokens = string.split(text, None)
            for token_index in range(len(tokens)):
                tokens[token_index] = string.capitalize(tokens[token_index])
            text = string.join(tokens, " ") # whole text is now "capitalized"
            cities = self.city2woeid.text_search(text, force_bs=False, ret=RET_ORIG_TERM)
            _res = []
            self.rest = text
            onto = EntityExtractor.GeographicLocationExtractor.TemporaryGeographicalOntology
            while(iterate == 1): # endless cycle - but it's stopped always during first iteration
                if cities:
                    for c in cities:
                        if c.__str__() not in invalid_cities:
                            backcheck_hit = 0 # used in "city in country" backcheck control
                            credibility = 61 # implicite credibility for "city" is 61
                            l = RRSLocation()
                            loc = onto.go_up_in_hierarchy(c, 'city', self.city2woeid,
                                    self.woeid2city, self.woeid2cityaltname,
                                    self.woeid2country, self.country2countrywoeid,
                                    self.countrywoeid2country, self.countrywoeid2continent,
                                    search_altnames)
                            #for attr in ('city', 'city_altnames', 'country', 'country_altnames', 'continent'):
                            for attr in ('city', 'country', 'continent'):
                                l.set(attr, loc[attr], strict=False)
                            if 'city_woeid' in loc and loc['city_woeid'] is not None:
                                l.set('woeid', int(loc['city_woeid']))
                            elif 'country_woeid' in loc and loc['country_woeid'] is not None:
                                l.set('woeid', int(loc['country_woeid']))
                            _res.append(l)

                            # xlokaj03: this is not necessary, altnames are not 
                            # in db yet, search_altnames is always false 
                            if search_altnames:
                                if loc['city_altnames'] is None:
                                    credibility -= 1
                                else:
                                    credibility += 2

                            # NOTE xlokaj03 - is this check nessessary?
                            # double - check the country
                            countries = self.country2countrywoeid.text_search(text,
                                              force_bs=False, ret=RET_ORIG_TERM)
                            if countries:
                                if loc['country'] in countries:
                                    credibility += 15
                                else:
                                    for country_tmp in countries:
                                        cwoeid_tmp = self.country2countrywoeid.translate(country_tmp)
                                        cities_tmp = self.countrywoeid2city.translate(cwoeid_tmp[0])
                                        if cities_tmp != None:
                                            if loc['city'] in cities_tmp:
                                                backcheck_hit = 1
                                                break
                                    if backcheck_hit == 1:
                                        credibility += 15
                                    else: # country in text doesn't belong to city that was found
                                        credibility -= 37
                                    loc = onto.go_up_in_hierarchy(countries[0],
                                        'country', self.city2woeid, self.woeid2city,
                                        self.woeid2cityaltname, self.woeid2country,
                                        self.country2countrywoeid, self.countrywoeid2country,
                                        self.countrywoeid2continent, search_altnames)
                                    
                                    # xlokaj03: this is not necessary, altnames are not 
                                    # in db yet, search_altnames is always false
                                    if search_altnames:
                                        for attr in ('country', 'country_altnames', 'continent'):
                                            l.set(attr, loc[attr], strict=False)
                                    else:
                                        for attr in ('country', 'continent'):
                                            l.set(attr, loc[attr], strict=False)
                                    if 'country_woeid' in loc and loc['country_woeid'] is not None:
                                        l.set('woeid', int(loc['country_woeid']))
                                    self.rest = re.sub(re.escape(countries[0]) + "[,\. ]?", "", self.rest)

                            # try to find an address for this city
                            addr = self.extract_address(text, c, self.city2postcode)
                            if(addr):
                                credibility += 7
                                l.set("address", addr)
                                self.rest = re.sub(re.escape(addr) + "[,\. ]?", "", self.rest)
                            else:
                                credibility -= 2

                            self.rest = re.sub(re.escape(c) + "[,\. ]?", "", self.rest)

                            # credibility
                            l.set('credibility', credibility)

                    break # end the endless cycle

                countries = self.country2countrywoeid.text_search(text, force_bs=False, ret=RET_ORIG_TERM)
                if countries:
                    for c in countries:
                        credibility = 40 # implicite credibility for "country" is 61
                        l = RRSLocation()
                        loc = onto.go_up_in_hierarchy(c, 'country', self.city2woeid,
                            self.woeid2city, self.woeid2cityaltname, self.woeid2country,
                            self.country2countrywoeid, self.countrywoeid2country,
                            self.countrywoeid2continent, search_altnames)
                        
                        # xlokaj03: this is not necessary, altnames are not 
                        # in db yet, search_altnames is always false 
                        if search_altnames:
                            for attr in ('country', 'country_altnames', 'continent'):
                                l.set(attr, loc[attr], strict=False)
                        else:
                            for attr in ('country', 'continent'):
                                l.set(attr, loc[attr], strict=False)
                        
                        if 'country_woeid' in loc and loc['country_woeid'] is not None:
                            l.set('woeid', int(loc['country_woeid']))
                        _res.append(l)
                        self.rest = re.sub(re.escape(c) + "[,\. ]?", "", self.rest)

                         # try to find an address
                        addr = self.extract_address(text, c, self.city2postcode)
                        if(addr):
                            credibility += 7
                            l.set("address", addr)
                            self.rest = re.sub(re.escape(addr) + "[,\. ]?", "", self.rest)
                        else:
                            credibility -= 2

                        self.rest = re.sub(re.escape(c) + "[,\. ]?", "", self.rest)

                        # credibility
                        l.set('credibility', credibility)

                    break # end the endless cycle

                break

            if _res: return _res
            return None


    #---------------------------------------------------------------------------
    # end of class GeographicLocationExtractor
    #---------------------------------------------------------------------------

    class NameExtractor(_EntityExtractorComponent):
        """
        This class is ment to be an extractor of firstnames and surnames in input.

        It uses dictionaries from folder "dictionaries".
        Extracted names will be names with the greatest appearance frequency

        @todo:
        Decoding functions = deprecated
        Performance issue : string concatenation
                            for loops
        Compute credibility before removing in get rest
        Nationality decode
        Add exceptions
        Wiki;)
        Improve pylint score
        """
        def __init__(self):
            _EntityExtractorComponent.__init__(self)
            self.persons = []
            # Loaded dictionaries
            self._firstnames = []
            self._surnames = []
            self._toerase = []
            self._antinames = None
            self._example = RRSPerson()
            # Compiles regexps
            self.__REsname_pref = '(?:O\'|Mc|Mac|van |von )?'
            self.__REletters = '[A-Za-z\xa0-\xff]'
            self.__REetal = '(?:[\s]+[Ee][Tt] [Aa][Ll][\.]?)?'
            self.__REfnames = '[A-Z]' + self.__REletters + '{1,}'
            self.__REsnames = '[A-Z]' + self.__REletters + '{1,}(?:-[A-Z]' + \
                self.__REletters + '{1,})?'
            self.__REinit = '[A-Z]\.'

            self.__RE_Snm = re.compile('(?P<last>' + self.__REsname_pref
                                       + self.__REsnames + ')' + self.__REetal
                                       + '\s*,?\s*(?P<first>' + self.__REinit
                                       + ')\s*(?P<middle>' + self.__REinit
                                       + '(?:\s*' + self.__REinit + ')*)?',
                                       re.M)
            self.__RE_nmS = re.compile('(?P<first>' + self.__REinit
                                       + ')\s*(?P<middle>' + self.__REinit
                                       + '(?:\s*' + self.__REinit
                                       + ')*)?\s+(?P<last>'
                                       + self.__REsname_pref + self.__REsnames
                                       + ')' + self.__REetal, re.M)
            self.__RE_NMS = re.compile('(?P<first>' + self.__REfnames
                                       + ')\s+(?P<middle>' + self.__REfnames
                                       + ')?\s*(?P<last>' + self.__REsname_pref
                                       + self.__REsnames + ')', re.M)
            self.__RE_NmS = re.compile('(?P<first>' + self.__REfnames
                                       + ')\s*(?P<middle>' + self.__REinit
                                       + '(?:\s*' + self.__REinit
                                       + ')*)\s+(?P<last>' + self.__REsname_pref
                                       + self.__REsnames + ')' + self.__REetal,
                                       re.M)
            self.__RE_SN = re.compile('(?P<last>' + self.__REsname_pref
                                       + self.__REsnames + ')' + self.__REetal
                                       + '\s*,\s*(?P<first>' + self.__REfnames
                                       + ')', re.M)
            self.init_dicts()

        def init_dicts(self):
            """
            Load dictionaries into the memory
            """
            self._firstnames.append(RRSDictionary(NAME_FF_CZ, CASE_INSENSITIVE))
            self._firstnames.append(RRSDictionary(NAME_FM_CZ, CASE_INSENSITIVE))
            self._firstnames.append(RRSDictionary(NAME_FF_US, CASE_INSENSITIVE))
            self._firstnames.append(RRSDictionary(NAME_FM_US, CASE_INSENSITIVE))
            self._firstnames.append(RRSDictionary(NAME_FF_XX, CASE_INSENSITIVE))
            self._firstnames.append(RRSDictionary(NAME_FM_XX, CASE_INSENSITIVE))
            self._surnames.append(RRSDictionary(NAME_SF_CZ, CASE_INSENSITIVE))
            self._surnames.append(RRSDictionary(NAME_SM_CZ, CASE_INSENSITIVE))
            self._surnames.append(RRSDictionary(NAME_S_US, CASE_INSENSITIVE))
            self._antinames = RRSDictionary(NON_NAMES, CASE_INSENSITIVE)

        def is_firstname(self, word):
            """
            Compare word with dictionaries
            """
            for x in self._firstnames:
                if x.contains_key(word):
                    return True
            return None

        def is_surname(self, word):
            """
            Compare word with dictionaries
            """
            for x in self._surnames:
                if x.contains_key(word):
                    return True
            return None

        def is_antiname(self, word):
            """
            Compare word with anti-names dict
            """
            if self._antinames.contains_key(word):
                return True
            else:
                return None

        def fill_name(self, person):
            """
            Set "name" attribut of RRSPerson, if full name exists
            """
            if person.get('first_name') and person.get('last_name'):
                full = person.get('first_name')
                if person.get('middle_name'):
                    full = full + " " + person.get('middle_name')
                full = full + " " + person.get('last_name')
                person.set('full_name', full)

        def scan_types(self, text):
            """
            Recognize types of citations in text;
            Returns list of extract functions to apply
            """
            # Prefers initials types
            __match_dict = {}
            __func_list = []
            __match_dict[self.extract_Snm] = 0
            __match_dict[self.extract_nmS] = 0
            __match_dict[self.extract_NMS] = 0
            __match_dict[self.extract_NmS] = 0
            __match_dict[self.extract_Snm] = len(self.__RE_Snm.findall(text))
            __match_dict[self.extract_nmS] = len(self.__RE_nmS.findall(text))
            __match_dict[self.extract_NMS] = len(self.__RE_NMS.findall(text))
            __match_dict[self.extract_NmS] = len(self.__RE_NmS.findall(text))
            __match_dict[self.extract_SN] = len(self.__RE_SN.findall(text))

            if __match_dict[self.extract_Snm] or __match_dict[self.extract_nmS]:
                if __match_dict[self.extract_Snm] >= __match_dict[self.extract_nmS]:
                    __func_list.append(self.extract_Snm)
                    __func_list.append(self.extract_NmS)
                    __func_list.append(self.extract_nmS)
                else:
                    __func_list.append(self.extract_NmS)
                    __func_list.append(self.extract_nmS)
                    __func_list.append(self.extract_Snm)
            else:
                __func_list.append(self.extract_NMS)
                __func_list.append(self.extract_SN)

            return __func_list

        #Extract functions extract_<type>:

        def extract_Snm(self, text, list):
            # Search for: Surname, N. M.
            n_s = self.__RE_Snm.finditer(text)
            for match in n_s:
                if self.is_antiname(match.group('last')):
                    continue
                new_person = RRSPerson()
                new_person.set('first_name', match.group("first"))
                new_person.set('middle_name', match.group("middle"))
                new_person.set('last_name', match.group("last"))
                new_person.set('original', match.group(0).replace("\n", " "))
                if self.is_surname(match.group("last")):
                    new_person.set('credibility', 80)
                else:
                    new_person.set('credibility', 50)
                self._toerase.append(text[match.start():match.end()])
                list.append(new_person)
            for name in self._toerase:
                text = re.sub(name, "", text)
            self._toerase = []
            return text

        def extract_SN(self, text, list):
            # Search for: Surname, Name
            n_s = self.__RE_SN.finditer(text)
            for match in n_s:
                if self.is_antiname(match.group('last')):
                    continue
                new_person = RRSPerson()
                new_person.set('first_name', match.group("first"))
                new_person.set('last_name', match.group("last"))
                new_person.set('original', match.group(0).replace("\n", " "))
                if self.is_surname(match.group("last")):
                    new_person.set('credibility', 80)
                else:
                    new_person.set('credibility', 50)
                self._toerase.append(text[match.start():match.end()])
                list.append(new_person)
            for name in self._toerase:
                text = re.sub(name, "", text)
            self._toerase = []
            return text 

        def extract_nmS(self, text, list):
            # Search for: N. M. Surname
            n_s = self.__RE_nmS.finditer(text)
            for match in n_s:
                # Main condition
                if self.is_antiname(match.group('last')):
                    continue
                new_person = RRSPerson()
                new_person.set('first_name', match.group('first'))
                new_person.set('middle_name', match.group('middle'))
                new_person.set('last_name', match.group('last'))
                new_person.set('original', match.group(0).replace("\n", " "))
                if self.is_surname(match.group('last')):
                    new_person.set('credibility', 80)
                else:
                    new_person.set('credibility', 50)
                self._toerase.append(text[match.start():match.end()])
                list.append(new_person)
            for name in self._toerase:
                text = re.sub(name, "", text)
            self._toerase = []
            return text

        def extract_NMS(self, text, list):
            # Search for: Name Middle Surname
            n_s = self.__RE_NMS.finditer(text)
            for match in n_s:
                # Main condition
                if self.is_antiname(match.group('first')) or \
                    self.is_antiname(match.group('last')):
                    continue
                new_person = RRSPerson()
                new_person.set('first_name', match.group('first'))
                new_person.set('middle_name', match.group('middle'))
                new_person.set('last_name', match.group('last'))
                new_person.set('original', match.group(0).replace("\n", " "))
                if self.is_firstname(match.group('first')) and \
                    self.is_surname(match.group('last')):
                    if match.group('middle'):
                        if self.is_firstname(match.group('middle')) or \
                            self.is_surname(match.group('middle')):
                            new_person.set('credibility', 90)
                        else:
                            new_person.set('credibility', 75)
                    else:
                        new_person.set('credibility', 60)

                ##########################################################
                # reversed order of names: bugfixed in release 0.10.9.20
                elif self.is_surname(match.group('first')) or \
                    self.is_firstname(match.group('last')):
                    new_person.set('first_name', match.group('last'))
                    new_person.set('last_name', match.group('first'))
                    if match.group('middle'):
                        new_person.set('credibility', 75)
                    else:
                        new_person.set('credibility', 60)
                ##########################################################

                else:
                    if self.is_firstname(match.group('first')) or \
                        self.is_surname(match.group('last')):
                        new_person.set('credibility', 60)
                    else:
                        new_person.set('credibility', 50)
                self._toerase.append(text[match.start():match.end()])
                list.append(new_person)
            for name in self._toerase:
                text = re.sub(name, "", text)
            self._toerase = []
            return text

        def extract_NmS(self, text, list):
            # Search for: Name M. Surname
            n_s = self.__RE_NmS.finditer(text)
            for match in n_s:
                if self.is_antiname(match.group('last')) or \
                    self.is_antiname(match.group('first')):
                    continue
                new_person = RRSPerson()
                new_person.set('first_name', match.group('first'))
                new_person.set('middle_name', match.group('middle'))
                new_person.set('last_name', match.group('last'))
                new_person.set('original', match.group(0).replace("\n", " "))
                if self.is_surname(match.group('last')) and \
                    self.is_firstname(match.group('first')):
                    new_person.set('credibility', 75)
                else:
                    if self.is_surname(match.group('last')):
                        new_person.set('credibility', 60)
                    else:
                        new_person.set('credibility', 40)
                self._toerase.append(text[match.start():match.end()])
                list.append(new_person)
            for name in self._toerase:
                text = re.sub(name, "", text)
            self._toerase = []
            return text

        def main_extract(self, text):
            """
            Extract firstname, surname, sex and nationality of person from text.

            @return: Returns tuple of list of RRSPerson objects and rest of text

            @todo: 3-level credibility - result is average
            """
            __person_list = []
            __scan_list = []

            __scan_list = self.scan_types(text)
            for func in __scan_list:
                text = func(text, __person_list)

            for person in __person_list:
                self.fill_name(person)
            return __person_list, text


        def extract_persons(self, text):
            """
            Return list of extracted persons
            """
            persons, self.rest = self.main_extract(text)
            return persons

    #---------------------------------------------------------------------------
    # end of class NameExtractor
    #---------------------------------------------------------------------------


    class EventExtractor(_EntityExtractorComponent):
        """
        Extracts events information from plain text
        """

        # helper strings
        strEvents = "award|ceremony|competition|concert|conference|course|"\
                    "congress|colloquium|discussion|exhibition|fair|forum|"\
                    "launch|lecture|meeting|open day|screening|seminar|"\
                    "symposium|webinar|workshop"
        strEventsAbr = "conf\.|crs\.|colloq\.|lch\.|lnch\.|mtg\.|soc\.|wksh\.|"
        strPubls = "conference|incollection|inproceedings|mastersthesis|"\
                   "phdthesis|proceedings|techreport|unpublished|reports?|papers?"
        strPublsAbr = "conf\.|proc\.|unp\.|rpt\."
        strContinents = "World|Asian?|African?|(?:North|South)? ?American?|"\
                        "Antarctican?|European?|Australian?"
        strNations = "National|International|Intern\.|Int\.|Nat\.|Natl\."
        strPreps = "about|as|at|by|for|from|in|of|on|to"
        strNum = "(?:\d{0,2}(?:1st|2nd|3rd|[04-9]th)|first|second|third|(?:four|"\
                 "fif|six|seven|eigh|nin|ten|eleven|twelf|thir)(?:teen)?th)"
        strYear = "(?:[12]\d{3}|\'\d{2})"
        strBigComp = "ACM|IEEE"
        strAniv = "Annual|Anniversary|Jubilee"
        strBLWords = "compute(?:s|ed)|requir(?:es?|ing|ed)?|see(?:n)?|allow(?:s"\
                     "|ed|ing)|repeat(?:ing|ed|s)?|referr(?:ed|ing|s)?|contain("\
                     "?:s|ing|ed)?|consider(?:s|ing|ed)?|show(?:s|ing|n)?|let|"\
                     "flow(?:ing|s|n)?|mention(?:ed|ing)?|use(?:ed|s)?|combine("\
                     "?:s|ed|ing)?|go(?:es|ing)|went|that|this|he|she|them|his"\
                     "|her|their|we|is|are|was|were|will|would|can|could|shall|"\
                     "should|had|has|have|get|got|which|where|what|while|when"

        # regular expressions
        reNumNatEvn = re.compile(r"((?:" + strNum + r"|" + strYear + r") (?:" + \
                                 strAniv + r")?[ \w\-\(\)\&]*?(?:" + strNations + \
                                 r"|" + strContinents + r") ?(?:" + strAniv + \
                                 r")? ?(?:" + strEventsAbr + strEvents + 
                                 r")[\s\-\(\)\!\.\,\?\&].*?)(?:\n|\\n|!|,|\?)", \
                                 re.IGNORECASE)

        reNumOrNatEvn = re.compile(r"((?:(?:" + strNum + r"|" + strYear + r")|(?:" + \
                                   strNations + r"|" + strContinents + r")) (?:" + \
                                   strAniv + r")?[ \w\-\(\)\&]*?(?:" + strEventsAbr + \
                                   strEvents + 
                                   r")[\s\-\(\)\!\.\,\?\&].*?)(?:\n|\\n|!|,|\?)", \
                                   re.IGNORECASE)
        reEvnNumOrNat = re.compile(r"((?:" + strAniv + r")? ?(?:" + strEventsAbr + \
                                   strEvents + 
                                   r") (?:(?:" + strNum + r"|" + strYear + r")|(?:" + \
                                   strNations + r"|" + strContinents + \
                                   r"))[\s\-\(\)\!\.\,\?\&].*?)(?:\n|\\n|!|,|\?)", \
                                   re.IGNORECASE)
        reAcrEvn = None
        rePublAcr = None
        reCheckBlackList = re.compile(r" (?:" + strBLWords + r") ", re.IGNORECASE)

        

        _filesPath = ""

        def __init__(self):
            """
            Class constructor
            """
            _EntityExtractorComponent.__init__(self)
            self.eventdict = RRSDictionary(EVENT_ACRONYMS, CASE_INSENSITIVE)


        def _guess_type(self, title):
            _type = "conference"
            for t in ('award', 'ceremony', 'competition', 'concert', 'conference',
                      'convention',
                      'course', 'defense', 'discussion', 'exhibition',
                      'fair', 'forum', 'launch', 'lecture', 'meeting', 'open day',
                      'screening', 'seminar', 'social', 'symposium', 'webinar',
                      'workshop'):
                if re.search(t, title, re.I):
                    return t


        def extract_events(self, plainText="", bRoughSearch=True):
            """
            Get the events from a plain text
            """
            if(not plainText):
                return None

            resLst = []
            #===================================================================
            #xlokaj03: New acronym search with dictionary
            #===================================================================
            acronyms = self.eventdict.text_search(plainText, ret=RET_DICT_TERM)
            for acronym in acronyms:
                if(self.reCheckBlackList.search(acronym)):
                    continue
                title = self.eventdict.translate(acronym)
                if isinstance(title, list):
                    title = title[0]
                if re.search(re.escape(title), plainText, re.IGNORECASE):
                    resLst.append({"Event":title,
                                   "Credibility":100, "Acronym":acronym})
                    plainText = re.sub(re.escape(title), "", plainText, re.IGNORECASE)
                else:
                    resLst.append({"Event":title,
                                   "Credibility":80, "Acronym":acronym})
                plainText = re.sub(re.escape(acronym), "", plainText, re.IGNORECASE)
                
            #===================================================================
            #===================================================================
            
            # try to find some events using prepared REs
            # 1st pattern
            e = self #EntityExtractor.EventExtractor
            searchRes = e.reNumNatEvn.findall(plainText)
            for rec in searchRes:
                if(not e.reCheckBlackList.search(rec)):
                    resLst.append({"Event":rec, "Credibility":80, "Acronym":None})
                    plainText = plainText.replace(rec, "")
            # 2nd pattern
            searchRes = e.reNumOrNatEvn.findall(plainText)
            for rec in searchRes:
                if(not e.reCheckBlackList.search(rec)):
                    resLst.append({"Event":rec, "Credibility":70, "Acronym":None})
                    plainText = plainText.replace(rec, "")
            # 3rd pattern
            searchRes = e.reEvnNumOrNat.findall(plainText)
            for rec in searchRes:
                if(not e.reCheckBlackList.search(rec)):
                    resLst.append({"Event":rec, "Credibility":70, "Acronym":None})
                    plainText = plainText.replace(rec, "")

#===============================================================================
# xlokaj03: this may be redundant, because it allways adds just the acronym
# found in dictionary. Same result should be achieved by the text_search() 
# method from dictionary - see above
#===============================================================================
#            # if previous searching wasn't successful, try another two patterns
#            # load list of acronyms from file and prepare it for inserting into RE
#            # get list of the acronyms from file
#            if(not resLst):
#                strAcrs = "[A-Za-z]{2,13}"
# 
#                # XXXRe: These two are working, just not searching plain acronyms
#                # XXXRe: (plain acronyms - see rought testing part)
#                # create 1st pattern
#                reAcrEvn = re.compile(r"((?:\\n|\s|\()(?:" + strAcrs + r"|" + \
#                                      e.strBigComp + r")(?: |\)|\'\d{2}).*?(?:" + \
#                                      e.strEventsAbr + e.strEvents + r").*?)(?:"\
#                                      "\n|\\n|!|,|\?)")
#                # create 2nd pattern
#                # is this working?? XXX
#                rePublAcr = re.compile(r"(?:" + e.strPubls + r"|" + e.strPublsAbr + \
#                                       r")(.*?[ \(](?:" + strAcrs + ")(?: |\)|"\
#                                       "\'\d{2}).*?)(?:\n|\\n|!|,|\?)")
#                # 1st pattern
#                searchRes = reAcrEvn.findall(plainText)
#                for rec in searchRes:
#                    rec = rec.lstrip(" ")
#                    if(not e.reCheckBlackList.search(rec)) and self.eventdict.contains_key(rec):
#                        resLst.append({"Event":title, "Credibility":60, "Acronym":rec})
#                        plainText = plainText.replace(rec, "")
# 
#                # 2nd pattern
#                searchRes = rePublAcr.findall(plainText)
#                for rec in searchRes:
#                    rec = rec.lstrip(" ")
#                    if(not e.reCheckBlackList.search(rec)) and self.eventdict.contains_key(rec):
#                        resLst.append({"Event":rec, "Credibility":60, "Acronym":None})
#                        plainText = plainText.replace(rec, "")
#                #!!! ROUGH TESTING PART !!!#
#                # if there are still no results, check for rought searching option
#                # if the rough searching is turned on, search according to only acronyms
#                # slightly modified, now working good, so rough testing is turned on as default
#                if(not resLst and bRoughSearch):
#                    # create RE for searching the acronyms
#                    reAcrsOnly = re.compile(r"(?:\\n|\s|\()(" + strAcrs + \
#                                          r")(?: |\)|\'\d{2})?(?:\n|\\n|!|,|\?)")
#                    # apply the pattern
#                    searchRes = reAcrsOnly.findall(plainText)
#                    for rec in searchRes:
#                        if not self.reCheckBlackList.search(rec) and self.eventdict.contains_key(rec):
#                            #print self.eventdict.contains_key(rec), rec
#                            #print self.eventdict.translate(rec)
#                            credibility = 50
#                            if(len(rec) < 3):
#                                credibility = 30
#                            try:
#                                resLst.append({"Event":self.eventdict.translate(rec),
#                                               "Credibility":credibility,
#                                               "Acronym":rec})
#                                plainText = plainText.replace(rec, "")
#                            except(KeyError):
#                                continue
#                #!!! ROUGH TESTING PART !!!#
#===============================================================================

            # save remaining text
            self.rest = plainText

            # end of searching, return the results
            events = []
            for event in resLst:
                rrse = RRSEvent(title=event['Event'])
                rrse.set('credibility', event['Credibility'])
                rrse.set('acronym', event['Acronym'])
                # guess type
                _type = RRSEvent_type()
                _type.set('type', self._guess_type(event['Event']))
                rrse.set('type', _type)
                events.append(rrse)
            return events

    #---------------------------------------------------------------------------
    # end of class EventExtractor
    #---------------------------------------------------------------------------


    class OrganizationExtractor(_EntityExtractorComponent):
        """
        Searching for organizations in references.
        This class looks for universities, faculties, departments, academies,
        institutes, colleges, offices, bureaus, centers, laboratories,
        associations, groups, councils, societies, consortiums and associations.

        Examples:
            Technion - Israel Institute of Technology
            Lawrence Livermore National Laboratory
            Electric Power Research Institute
            Society for Industrial and Applied Mathematics
            Bartlesville Energy Technology Center
            Innovative Science and Technology Office
            DeepLook Research Consortium
        """

        def __init__(self):
            self.organizations = []
            self._buffer_organization_type = {}
            self._buffer_organization_credibility = {}
            self.rest = ""
            self.work_text = ""

            #Dictionaries
            self._rrsdict_universities = RRSDictionary(UNIVERSITIES,
                                                            CASE_INSENSITIVE)
            self.significant_words_and_actions = {
                "university":self._university, "univ":self._university,
                "univerzita":self._university, "universität":self._university,
                "universitat":self._university, "universitaire":self._university,
                "academy":self._academy, "academica":self._academica,
                "faculty":self._faculty, "fakulta":self._faculty,
                "fakultät":self._faculty, "fakultat":self._faculty,
                "faculté":self._faculty, "faculte":self._faculty,
                "department":self._department, "dept":self._department,
                "département":self._department, "departement":self._department,
                "oddělení":self._department, "abteilung":self._department,
                "school":self._school, "institute":self._institute,
                "college":self._college, "center":self._center,
                "centre":self._center, "laboratory":self._laboratory,
                "lab":self._laboratory, "group":self._group,
                "council":self._council, "office":self._office,
                "corporation":self._corporation, "bureau":self._bureau,
                "association":self._association, "assoc":self._association,
                "consortium":self._consortium, "society":self._society,
                "soc":self._society, "agency":self._agency,
            }
            self._common_organizations_shortcuts = [
                'acm', 'acm', 'adsl', 'appn', 'ati', 'atsc', 'aiim', 'mfj', 'atis',
                'ieee', 'acis', 'ansi', 'arpa', 'asedie', 'aui', 'aace', 'aaim',
                'aect', 'ais', 'ami', 'apts', 'aip', 'apiiq', 'aimia', 'csiro',
                'aitec', 'bacug', 'bbbo', 'bsia', 'betech', 'bsa', 'www', 'cais',
                'canarie', 'cdma', 'cedar', 'ctr', 'cait', 'cicc', 'circit',
                'cict', 'ceto', 'cbi', 'ciec', 'cnidr', 'cauce', 'cix', 'cgda',
                'ciac', 'csi', 'ciesin', 'cea', 'cordis', 'cenic', 'xiwt',
                'darpa', 'darpa', 'ec', 'dma', 'dda', 'ddn', 'disa', 'atm', 'dfn',
                'davic', 'dstc', 'dsdm', 'ecma', 'edi', 'epri', 'edac', 'eia',
                'ema', 'epic', 'eg', 'earn', 'echo', 'ecis', 'ecoga', 'eema',
                'emf', 'ero', 'ercim', 'eto', 'etf', 'ewos', 'fcc', 'fstc',
                'first', 'igd', 'fsf', 'frc', 'gam', 'ggf', 'gmd', 'gr', 'ai',
                'hippi', 'api', 'hpcc', 'html', 'iana', 'iath', 'idom', 'ieee',
                'iepg', 'ietf', 'iitf', 'icca', 'os', 'ics', 'ittc', 'iisp',
                'isaca', 'issa', 'itaa', 'itac', 'iti', 'itsma', 'da', 'inria',
                'icard', 'icot', 'fokus', 'iams', 'interacta', 'idsa', 'imat',
                'isa', 'iac', 'iasted', 'icia', 'icma', 'icsi', 'iec', 'iec',
                'iics', 'imia', 'iso', 'irex', 'its', 'itu', 'iab', 'icann',
                'em', 'iahc', 'irtf', 'isp', 'isoc', 'nic', 'iops', 'ip', 'isdn',
                'isoc', 'jate', 'jpnic', 'jnns', 'jtc', 'nap', 'mcnc', 'mfa',
                'mmcf', 'mmta', 'sig', 'nab', 'nacse', 'nastd', 'ncsa', 'ncet',
                'netc', 'niiip', 'nipc', 'nist', 'isdn', 'nmaa', 'nttc', 'ntia',
                'ntonc', 'nbx', 'nthp', 'nanog', 'npac', 'nwcet', 'ora', 'oclc',
                'gl', 'opa', 'oetc', 'ptc', 'pci', 'pdes', 'pfir', 'popai', 'pasc',
                'pitac', 'psg', 'race', 'rare', 'rsac', 'ftk', 'rccs', 'ripe',
                'nt', 'scra', 'share', 'sv', 'sldram', 'slonet', 'smart', 'smds',
                'sea', 'stc', 'sampe', 'scte', 'smpte', 'spi', 'spa', 'stpi',
                'sonet', 'spie', 'ssa', 'ste', 'snia', 'surf', 'tcif', 'tia',
                'teletech', 'isdn', 'tno', 'tra', 'trust', 'tsan', 'unibel',
                'ulis', 'usc', 'usenix', 'vhdl', 'sig', 'vrml', 'wab', 'tafe',
                'wap', 'waria', 'mc', 'witsa', 'wia', 'wro'
            ]
            self._common_organizations_words = [
                "international", "forum", "information", "group", "systems",
                "network", "research", "internet", "european", "national",
                "computer", "telecommunications", "technology", "software",
                "alliance", "science", "computer", "applied", "physics", "phasical",
                "mathematics", "mathematical", "american", "education", "science",
                "sciences", "computing"
            ]

            #Patterns
            self._pat_word_1 = "(([A-Z]\.)+|[(][A-Z]{2,}[)]|[-'A-Za-z&/]+)"
            self._pat_word_2 = "(([A-Z]\.)+|[A-Z][a-z]{1,7}\.|[(][A-Z]{2,}[)]|[-'A-Za-z&/]+)"
            self._pat_separator = "[\s,;:.]"
            self._pat_markers_sub = "#START_MARK#\g<1>#END_MARK#"
            self._pat_forbidden_words = '(meeting|seminar|symposium|conference|'\
                                        'journal|press|proc\.|proceedings|before'\
                                        '|when|while|is|review)'
            self._pat_forbidden_prefix = '(at|by|on|in|of the|with the)'
            self._pat_prefix_to_remove = '((at|by|on) the)'
            self._pat_report = '((technical|research) report|tech\.? report|tech'\
                               '\.? rep\.?|(technical|research) rep\.?|(?<!tech'\
                               'nical )report|(?<!research )report)'

            #Regular expressions
            self._re_organization = re.compile('^.*?(#START_MARK#.+?#END_MARK#)')
            self._re_join_organization = re.compile('#END_MARK#(\W+)#START_MARK#',
                                                    re.DOTALL)
            self._re_words_and_separators = re.compile('([a-z]+?)(\W+|$)',
                                                       re.DOTALL)
            self._re_forbidden_words = re.compile('(^|\W)'
                                                  + self._pat_forbidden_words
                                                  + '(\W|$)', re.IGNORECASE)
            self._re_relation = re.compile('^(.+?)' + self._pat_separator
                                           + '*?#RELATION_MARK#'
                                           + self._pat_separator + '*?(.+)$')
            self._re_report = re.compile('(?<!' + self._pat_separator + ')(\s*'
                                         + self._pat_report + ')', re.IGNORECASE)
            self._re_remove_prefix = re.compile(self._pat_prefix_to_remove,
                                                re.IGNORECASE)
            self._re_shortcut = re.compile('[(][A-Z]{2,5}[)]')
            self._re_shorted_organization = \
                re.compile('univ\.|dept\.|assoc\.|soc\.', re.IGNORECASE)
            self._re_lower_word = re.compile('^[a-z].*?$')
            self._re_multiple_whitespace = re.compile('\s\s+', re.DOTALL)


        def _group(self, reference):
            """
            Finds organizations containing phrase 'group'.
            """
            _pat_group = '([Gg][Rr][Oo][Uu][Pp])'
            return self._find_organization(_pat_group, reference)


        def _university(self, reference):
            """
            Finds organizations containing phrases 'university' or 'univ.'
            or 'univerzita' or 'universität' or 'universitaire'.
            """
            _pat_university = '('
            _pat_university += '[Uu][Nn][Ii][Vv][Ee][Rr][Ss][Ii][Tt][Yy]'
            _pat_university += '|[Uu][Nn][Ii][Vv]\.'
            _pat_university += '|[Uu][Nn][Ii][Vv][Ee][Rr][Zz][Ii][Tt][Aa]'
            _pat_university += '|[Uu][Nn][Ii][Vv][Ee][Rr][Ss][Ii][Tt][ÄäAa][Tt]'
            _pat_university += '|[Uu][Nn][Ii][Vv][Ee][Rr][Ss][Ii][Tt][Aa][Ii][Rr][Ee]'
            _pat_university += ')'
            return self._find_organization(_pat_university, reference)


        def _department(self, reference):
            """
            Finds organizations containing phrases 'department' or 'dept\.
            or 'oddělení' or 'département' or 'abteilung'.
            """
            _pat_department = '('
            _pat_department += '[Dd][Ee][Pp][Aa][Rr][Tt][Mm][Ee][Nn][Tt]'
            _pat_department += '|[Dd][Ee][Pp][Tt]\.'
            _pat_department += '|[Oo][Dd][Dd][ĚěEe][Ll][Ee][Nn][ÍíIi]'
            _pat_department += '|[Dd][EeÉé][Pp][Aa][Rr][Tt][Ee][Mm][Ee][Nn][Tt]'
            _pat_department += '|[Aa][Bb][Tt][Ee][Ii][Ll][Uu][Nn][Gg]'
            _pat_department += ')'
            return self._find_organization(_pat_department, reference)


        def _faculty(self, reference):
            """
            Finds organizations containing phrases 'faculty' or 'fakulta'
            of 'fakultät' or 'faculté'.
            """
            _pat_faculty = '('
            _pat_faculty += '[Ff][Aa][Cc][Uu][Ll][Tt][Yy]'
            _pat_faculty += '|[Ff][Aa][Kk][Uu][Ll][Tt][Aa]'
            _pat_faculty += '|[Ff][Aa][Kk][Uu][Ll][Tt][ÄäAa][Tt]'
            _pat_faculty += '|[Ff][Aa][Cc][Uu][Ll][Tt][ÉéEe]'
            _pat_faculty += ')'
            return self._find_organization(_pat_faculty, reference)


        def _school(self, reference):
            """
            Finds organizations containing phrase 'school'.
            """
            _pat_school = '([Ss][Cc][Hh][Oo][Oo][Ll])'
            return self._find_organization(_pat_school, reference)


        def _institute(self, reference):
            """
            Finds organizations containing phrase 'institute'.
            """
            _pat_institute = '([Ii][Nn][Ss][Tt][Ii][Tt][Uu][Tt][Ee])'
            return self._find_organization(_pat_institute, reference)


        def _corporation(self, reference):
            """
            Finds organizations containing phrase 'corporation'.
            """
            _pat_corporation = '([Cc][Oo][Rr][Pp][Oo][Rr][Aa][Tt][Ii][Oo][Nn])'
            return self._find_organization(_pat_corporation, reference)


        def _center(self, reference):
            """
            Finds organizations containing phrases 'center' or 'centre'.
            """
            _pat_center = '([Cc][Ee][Nn][Tt]([Ee][Rr]|[Rr][Ee]))'
            return self._find_organization(_pat_center, reference)


        def _laboratory(self, reference):
            """
            Finds organizations containing phrases 'laboratory' or 'lab.'.
            """
            _pat_laboratory = '('
            _pat_laboratory += '[Ll][Aa][Bb][Oo][Rr][Aa][Tt][Oo][Rr][Yy]'
            _pat_laboratory += '|[Ll][Aa][Bb]\.'
            _pat_laboratory += ')'
            return self._find_organization(_pat_laboratory, reference)


        def _council(self, reference):
            """
            Finds organizations containing phrase 'council'.
            """
            _pat_council = '([Cc][Oo][Uu][Nn][Cc][Ii][Ll])'
            return self._find_organization(_pat_council, reference)


        def _college(self, reference):
            """
            Finds organizations containing phrase 'college'.
            """
            _pat_college = '([Cc][Oo][Ll][Ll][Ee][Gg][Ee])'
            return self._find_organization(_pat_college, reference)


        def _academy(self, reference):
            """
            Finds organizations containing phrase 'academy'.
            """
            _pat_academy = '([Aa][Cc][Aa][Dd][Ee][Mm][Yy])'
            return self._find_organization(_pat_academy, reference)


        def _academica(self, reference):
            """
            Finds organizations containing phrase 'academica'.
            """
            _pat_academica = '([Aa][Cc][Aa][Dd][Ee][Mm][Ii][Cc][Aa])'
            return self._find_organization(_pat_academica, reference)


        def _society(self, reference):
            """
            Finds organizations containing phrase 'society' or 'soc.'.
            """
            _pat_society = '('
            _pat_society += '[Ss][Oo][Cc][Ii][Ee][Tt][Yy]'
            _pat_society += '|[Ss][Oo][Cc]\.'
            _pat_society += ')'
            return self._find_organization(_pat_society, reference)


        def _agency(self, reference):
            """
            Finds organizations containing phrase 'agency'.
            """
            _pat_agency = '([Aa][Gg][Ee][Nn][Cc][Yy])'
            return self._find_organization(_pat_agency, reference)


        def _consortium(self, reference):
            """
            Finds organizations containing phrase 'consortium'.
            """
            _pat_consortium = '([Cc][Oo][Nn][Ss][Oo][Rr][Tt][Ii][Uu][Mm])'
            return self._find_organization(_pat_consortium, reference)


        def _office(self, reference):
            """
            Finds organizations containing phrase 'office'.
            """
            _pat_office = '([Oo][Ff][Ff][Ii][Cc][Ee])'
            return self._find_organization(_pat_office, reference)


        def _bureau(self, reference):
            """
            Finds organizations containing phrase 'bureau'.
            """
            _pat_bureau = '([Bb][Uu][Rr][Ee][Aa][Uu])'
            return self._find_organization(_pat_bureau, reference)


        def _association(self, reference):
            """
            Finds organizations containing phrases 'association' or 'assoc.'.
            """
            _pat_association = '('
            _pat_association += '[Aa][Ss][Ss][Oo][Tt][Ii][Aa][Tt][Ii][Oo][Nn]'
            _pat_association += '|[Aa][Ss][Ss][Oo][Cc]\.'
            _pat_association += ')'
            return self._find_organization(_pat_association, reference)


        def _find_organization(self, pattern_organization, reference):
            """
            This method looks for organization specified in pattern.
            """
            if self._re_shorted_organization.search(reference):
                #Organization is in shorted form (univ., dept...)
                pattern_1 = re.compile('((' + self._pat_word_2 + ' )*'
                                       + pattern_organization + '( '
                                       + self._pat_word_2 + ')+)')
                pattern_2 = re.compile('((' + self._pat_word_2 + ' )+'
                                       + pattern_organization + '( '
                                       + self._pat_word_2 + ')*)')
            else:
                pattern_1 = re.compile('((' + self._pat_word_1 + ' )*'
                                       + pattern_organization + '( '
                                       + self._pat_word_1 + ')+)')
                pattern_2 = re.compile('((' + self._pat_word_1 + ' )+'
                                       + pattern_organization + '( '
                                       + self._pat_word_1 + ')*)')

            if pattern_1.search(reference):
                if self._check_organization(pattern_1.search(reference).group(1)):
                    self.work_text = pattern_1.sub(self._pat_markers_sub,
                                                   self.work_text)
                    return True
            if pattern_2.search(reference):
                if self._check_organization(pattern_2.search(reference).group(1)):
                    self.work_text = pattern_2.sub(self._pat_markers_sub,
                                                   self.work_text)
                    return True
            return False


        def _check_organization(self, organization_title):
            """
            This method checks the organization and returns False if it's not
            correct.
            """
            if self._calculate_credibility(organization_title) < 10:
                #Too low credibility
                return False
            for s_word in self.significant_words_and_actions.keys():
                if re.search('(^|\W)' + self._pat_forbidden_words + '\W+.*?'
                             + s_word, organization_title, re.IGNORECASE):
                    return False
                if re.search(s_word + '\W+.*?' + self._pat_forbidden_words
                             + '(\W|$)', organization_title, re.IGNORECASE):
                    return False
            for s_word in self.significant_words_and_actions.keys():
                if re.search('(^|\W)' + self._pat_forbidden_prefix
                             + '(\s.+?\s|\s)+' + s_word, organization_title,
                             re.IGNORECASE):
                    return False
            return True


        def _repair_text(self, text):
            """
            This method changes an original text into a suitable form.
            """
            while self._re_multiple_whitespace.search(text):
                text = self._re_multiple_whitespace.sub(" ", text)
            while self._re_remove_prefix.search(text):
                text = self._re_remove_prefix.sub(",", text)
            text = self._re_report.sub(",\g<1>", text)
            return text


        def _remove_marks(self, text):
            """
            This method removes markers from a text.
            """
            text = text.replace('#START_MARK#', "")
            text = text.replace("#END_MARK#", "")
            text = text.replace("#RELATION_MARK#", "")
            return text


        def _fix_marks(self, text):
            """
            This method fixes markers in a text.
            """
            while re.search('(#START_MARK#){2,}', text):
                text = re.sub('(#START_MARK#){2,}', '#START_MARK#', text)
            while re.search('(#END_MARK#){2,}', text):
                text = re.sub('(#END_MARK#){2,}', '#END_MARK#', text)
            return text


        def _get_organization_type(self, organization_title):
            """
            This method returns type of the organization.
            """
            if organization_title in self._buffer_organization_type.keys():
                return self._buffer_organization_type[organization_title]
            for s_word in self.significant_words_and_actions.keys():
                if re.search(s_word, organization_title, re.IGNORECASE):
                    if s_word == "univ" or s_word == "univerzita" or \
                        s_word == "universität" or s_word == "universitat" or \
                        s_word == "universitaire":
                        s_word = "university"
                    elif s_word == "dept" or s_word == "oddělení" or \
                        s_word == "oddeleni" or s_word == "département" or \
                        s_word == "departement" or s_word == "abteilung":
                            s_word = "department"
                    elif s_word == "fakulta" or s_word == "fakultät" or \
                        s_word == "fakultat" or s_word == "faculté" or \
                        s_word == "faculte":
                            s_word = "faculty"
                    elif s_word == "soc":
                        s_word = "society"
                    elif s_word == "assoc":
                        s_word = "association"
                    elif s_word == "centre":
                        s_word = "center"
                    elif s_word == "lab":
                        s_word = "laboratory"
                    self._buffer_organization_type[organization_title] = s_word
                    return s_word
            return "unknown"


        def _get_RRSOrganization_type(self, organization_title):
            """
            This method returns type used in rrs_library of the organization.
            """
            type = self._get_organization_type(organization_title)
            if type == "university":
                return RRSOrganization_type(type="university")
            elif type == "faculty":
                return RRSOrganization_type(type="faculty")
            elif type == "department":
                return RRSOrganization_type(type="department")
            elif type == "group":
                return RRSOrganization_type(type="research group")
            else:
                return RRSOrganization_type(type="misc")


        def _calculate_credibility(self, organization_title):
            """
            This method calculates credibility of an organization title.
            """
            if organization_title in self._buffer_organization_credibility.keys():
                credibility = self._buffer_organization_credibility[organization_title]
            else:
                credibility = 0
                #fix not needed anymore
                #organization_title = re.sub('[^-\w\'/äëïöüáéíóúǎě()]', " ",
                #                            organization_title, re.IGNORECASE)
                organization_title = re.sub('[^-\w\'/()]', " ",
                                            organization_title, re.IGNORECASE)
                organization_title = re.sub('\s\s+', " ", organization_title,
                                            re.DOTALL)
                organization_title = re.sub('^\s+', "", organization_title,
                                            re.DOTALL)
                organization_title = re.sub('\s+$', "", organization_title,
                                            re.DOTALL)
                words = organization_title.split(" ")
                for word in words:
                    word_lower = word.lower().replace("(", "").replace(")", "")
                    if self._re_shortcut.search(word):
                        credibility += 100
                    elif word_lower in self._common_organizations_shortcuts:
                        credibility += 100
                    elif word_lower in self.significant_words_and_actions.keys():
                        credibility += 100
                    elif word_lower in self._common_organizations_words:
                        credibility += 50
                    else:
                        credibility += 25
                    if self._re_lower_word.search(word):
                        credibility -= 50
                credibility = int(float(credibility) / len(words))
                if credibility < 0: credibility = 0
            return credibility


        def _set_organization_attributes(self, rrs_organization, organization_title,
                                         type=None, cred=None):
            """
            This method sets the main RRSOrganization attributes.
            """
            rrs_organization.set("title", organization_title)
            if type == None:
                rrs_organization.set("type", self._get_RRSOrganization_type(organization_title))
            else:
                rrs_organization.set("type", type)    
            if cred == None:
                rrs_organization.set("credibility", self._calculate_credibility(organization_title))
            else:
                rrs_organization.set("credibility", cred)
            return rrs_organization


        def _analyze_relations(self, organization_titles):
            """
            This method compares two organizations and decides which one is
            parent and child organization.
            """
            first_organization = {"title": organization_titles.group(1)}
            second_organization = {"title": organization_titles.group(2)}
            first_organization["type"] = \
                self._get_organization_type(first_organization["title"])
            second_organization["type"] = \
                self._get_organization_type(second_organization["title"])

            if first_organization["type"] == "university":
                if second_organization["type"] == "faculty" or \
                    second_organization["type"] == "department" or  \
                    second_organization["type"] == "institute" or \
                    second_organization["type"] == "center" or \
                    second_organization["type"] == "laboratory" or \
                    second_organization["type"] == "unit":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "university":
                if first_organization["type"] == "faculty" or \
                    first_organization["type"] == "department" or  \
                    first_organization["type"] == "institute" or  \
                    first_organization["type"] == "center" or \
                    first_organization["type"] == "laboratory" or \
                    first_organization["type"] == "unit":
                    return {"parent":second_organization, "child":first_organization}
            if first_organization["type"] == "faculty":
                if second_organization["type"] == "department" or \
                    second_organization["type"] == "laboratory":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "faculty":
                if first_organization["type"] == "department" or \
                    first_organization["type"] == "laboratory":
                    return {"parent":second_organization, "child":first_organization}
            if first_organization["type"] == "laboratory":
                if second_organization["type"] == "department":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "laboratory":
                if first_organization["type"] == "department":
                    return {"parent":second_organization, "child":first_organization}
            if first_organization["type"] == "academy":
                if second_organization["type"] == "institute":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "academy":
                if first_organization["type"] == "institute":
                    return {"parent":second_organization, "child":first_organization}
            if first_organization["type"] == "academica":
                if second_organization["type"] == "institute":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "academica":
                if first_organization["type"] == "institute":
                    return {"parent":second_organization, "child":first_organization}
            if first_organization["type"] == "institute":
                if second_organization["type"] == "laboratory":
                    return {"parent":first_organization, "child":second_organization}
            if second_organization["type"] == "institute":
                if first_organization["type"] == "laboratory":
                    return {"parent":second_organization, "child":first_organization}
            return None


        def _find_relations(self, text, parent):
            """
            This method looks for relations beetween organizations.
            """
            titles = self._re_relation.search(text)
            analyzed_titles = self._analyze_relations(titles)
            if analyzed_titles == None:
                #Only one organization
                rrs_organization_1 = RRSOrganization(id=None, title=None)
                title = self._remove_marks(titles.group(1))
                rrs_organization_1 = \
                    self._set_organization_attributes(rrs_organization_1, title)
                if parent == None:
                    self.organizations.append(rrs_organization_1)
                #db09 fix
                #else: parent.set("organizations", rrs_organization_1)
                else:
                    rrs_organization_1.set("parent", parent)
                rrs_organization_2 = RRSOrganization(id=None, title=None)
                title = self._remove_marks(titles.group(2))
                rrs_organization_2 = \
                    self._set_organization_attributes(rrs_organization_2, title)
                if parent == None:
                    self.organizations.append(rrs_organization_2)
                #db09 fix
                #else: parent.set("organizations", rrs_organization_2)
                else: rrs_organization_2.set("parent", parent)
            else:
                parent_organization = RRSOrganization(id=None, title=None)
                title = self._remove_marks(analyzed_titles["parent"]["title"])
                parent_organization = \
                    self._set_organization_attributes(parent_organization, title)
                child_organization = RRSOrganization(id=None, title=None)
                if self._re_relation.search(analyzed_titles["child"]["title"]):
                    self._find_relations(analyzed_titles["child"]["title"],
                                         parent_organization)
                else:
                    title = self._remove_marks(analyzed_titles["child"]["title"])
                    child_organization = \
                        self._set_organization_attributes(child_organization, title)
                    #db09 fix
                    #parent_organization.set("organizations", child_organization)
                    child_organization.set("parent", parent_organization)
                if parent == None:
                    self.organizations.append(parent_organization)
                #db09 fix
                #else: parent.set("organizations", parent_organization)
                else:
                    parent_organization.set("parent", parent)


        def extract_organizations(self, text):
            """
            Main method - looks for an information about organizations in reference
            text and returns list of found organizations.
            
            @param text: text
            @type text: string
            @return: found organizations
            @rtype: [RRSOrganizations]  
            """
            
            self.organizations = []
            result = False
            text_low = text.lower()
            words_and_separators = self._re_words_and_separators.findall(text_low)
            self.rest = text
            text = self._repair_text(text)
            self.work_text = text

            for word_and_separator in words_and_separators:
                word = word_and_separator[0]
                if word in self.significant_words_and_actions.keys():
                    if self.significant_words_and_actions.get(word)(text):
                        result = True

            self.work_text = self._fix_marks(self.work_text)

            while self._re_join_organization.search(self.work_text):
                self.work_text = \
                    self._re_join_organization.sub("\g<1>#RELATION_MARK#",
                                                   self.work_text)
                    
            #University search with dictionary
            univs = self._rrsdict_universities.text_search(self.work_text,
                                                           force_bs=False,
                                                           ret=RET_ORIG_TERM)
            for univ in univs:
                self.work_text = re.sub(re.escape(univ), "", self.work_text)
                if re.search(self._pat_separator + '+\s*' + re.escape(univ),
                             self.rest):
                    self.rest = re.sub(self._pat_separator + '+\s*' 
                                           + re.escape(univ), "", self.rest)
                elif re.search(re.escape(univ) + '\s*' + self._pat_separator 
                               + '+', self.rest):
                    self.rest = re.sub(re.escape(univ) + '\s*' 
                                       + self._pat_separator + '+', "", self.rest)
                rrs_organization = RRSOrganization(id=None, title=None)
                rrs_organization = self._set_organization_attributes(rrs_organization,
                                              univ, cred=100,
                                              type=RRSOrganization_type(type="university"))
                self.organizations.append(rrs_organization)
                
            #Other searches
            if not result:
                while self._re_organization.search(self.work_text):
                    marked_organization = \
                        self._re_organization.search(self.work_text).group(1)
                    organization = self._remove_marks(marked_organization)
                    self.work_text = re.sub(re.escape(marked_organization), "",
                                            self.work_text)
                    if re.search(self._pat_separator + '+\s*'
                                 + re.escape(organization), self.rest):
                        self.rest = re.sub(self._pat_separator + '+\s*'
                                           + re.escape(organization), "",
                                           self.rest)
                    elif re.search(re.escape(organization) + '\s*'
                                   + self._pat_separator + '+', self.rest):
                        self.rest = re.sub(re.escape(organization) + '\s*'
                                           + self._pat_separator + '+', "",
                                           self.rest)
                    #Multiple organization in relations:
                    if self._re_relation.search(marked_organization):
                        self._find_relations(marked_organization, None)
                    #Only one organization
                    else:
                        rrs_organization = RRSOrganization(id=None, title=None)
                        rrs_organization = \
                            self._set_organization_attributes(rrs_organization,
                                              self._remove_marks(organization))
                        self.organizations.append(rrs_organization)

            self._buffer_organization_type = {}
            self._buffer_organization_credibility = {}
            return self.organizations


    #---------------------------------------------------------------------------
    # end of class OrganizationExtractor
    #---------------------------------------------------------------------------


    class DateExtractor(_EntityExtractorComponent):
        """
        Extracts date and time from plain text.
        """
        # helper strings
        strMonths = "January|February|March|April|May|June|July|August|September"\
                    "|October|November|December"
        strMonthsShort = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
        # not used yet
        strDays = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
        # not used yet
        strDaysShort = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"
        # has the | character to be easily connected into RE
        strTimeZonesEu = "BST|CEDT|CEST|CET|EEDT|EEST|EET|GMT|IST|MESZ|MEZ|UTC|"\
                         "WEDT|WEST|WET|"
        # has the | character to be easily connected into RE
        strTimeZonesAu = "ACDT|ACST|AEDT|AEST|AWST|CDT|CST|CXT|EDT|EST|NFT|WST|"
        strTimeZonesAm = "ADT|AKDT|AKST|AST|HAA|HAC|HADT|HAE|HAP|HAR|HAST|HAT|"\
                         "HAY|HNA|HNC|HNE|HNP|HNR|HNT|HNY|MDT|MST|NDT|NST|PDT|PST"
        # regular expressions
        # year only
        #reYearOnly = re.compile(r"\b(?:\d+ ?BC|AD ?[012]?\d{1,3}|[012]?\d{1,3}"\
        #                        " ?AD|[12]\d{3})\b", re.IGNORECASE | re.DOTALL)
        reYearOnly = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b",
                                re.IGNORECASE | re.DOTALL)
        # month only
        #reYearMonth = re.compile(r"\b(?:" + strMonths + r"|" + strMonthsShort + \
        #                         r")\b[,-/]? ?\b(?:\d+ ?BC|A?D? ?[012]?\d{1,3}|" +\
        #                         "[012]?\d{1,3} ?A?D?|[12]\d{1,3})\b", re.IGNORECASE | re.DOTALL)
        reYearMonth = re.compile(r"\b(?:" + strMonths + r"|" + strMonthsShort + \
                                 r")\b[,-/]? ?\b(?:19\d{2}|20\d{2}|2100)\b", \
                                 re.IGNORECASE | re.DOTALL)
        # dd mm yyyy format
        reNumDDMMYYYY = re.compile(r"\b(?:[012]?\d|3[01])\b\. ?\b(?:0?\d|1[012])"\
                                   "\b\. ?\b(?:19\d{2}|20\d{2}|2100)\b", \
                                   re.IGNORECASE | re.DOTALL)
        reNumDDMMYYYY2 = re.compile(r"\b(?:[012]?\d|3[01])\b\- ?\b(?:0?\d|1[012])"\
                                    "\b\- ?\b(?:19\d{2}|20\d{2}|2100)\b", \
                                    re.IGNORECASE | re.DOTALL)
        reNumDDMMYYYY3 = re.compile(r"\b(?:[012]?\d|3[01])\b/ ?\b(?:0?\d|1[012])"\
                                    "\b/ ?\b(?:19\d{2}|20\d{2}|2100)\b", \
                                    re.IGNORECASE | re.DOTALL)
        reWorDDMMYYYY = re.compile(r"\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)\b\.?"\
                                    " ?\b(?:" + strMonths + r"|" + strMonthsShort + r")"\
                                    "\b[\.,]? ?\b(?:19\d{2}|20\d{2}|2100)\b",
                                    re.IGNORECASE | re.DOTALL)
        reWorDDMMYYYY2 = re.compile(r"\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)\b\-\b"\
                                    "(?:" + strMonths + r"|" + strMonthsShort + r")\b"\
                                    "\-\b(?:19\d{2}|20\d{2}|2100)\b",
                                    re.IGNORECASE | re.DOTALL)
        # yyyy mm dd format
        reNumYYYYMMDD = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b\. ?"\
                                    "\b(?:0?\d|1[012])\b\. ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b",
                                    re.IGNORECASE | re.DOTALL)
        reNumYYYYMMDD2 = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b\- ?"\
                                    "\b(?:0?\d|1[012])\b\- ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b",
                                    re.IGNORECASE | re.DOTALL)
        reNumYYYYMMDD3 = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b/ ?"\
                                    "\b(?:0?\d|1[012])\b/ ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b",
                                    re.IGNORECASE | re.DOTALL)
        reWorYYYYMMDD = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b,? ?\b(?:" + strMonths + \
                                     r"|" + strMonthsShort + r")\b,? ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b\.?",
                                    re.IGNORECASE | re.DOTALL)
        reWorYYYYMMDD2 = re.compile(r"\b(?:19\d{2}|20\d{2}|2100)\b\-\b(?:" + strMonths + \
                                     r"|" + strMonthsShort + r")\b\-\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b\.?",
                                    re.IGNORECASE | re.DOTALL)
        # mm dd yyyy format
        reNumMMDDYYYY = re.compile(r"\b(?:0?\d|1[012])\b\. ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b\. ?\b(?:19\d{2}|"\
                                    "20\d{2}|2100)\b", re.IGNORECASE | re.DOTALL)
        reNumMMDDYYYY2 = re.compile(r"\b(?:0?\d|1[012])\b\- ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b\- ?\b(?:19\d{2}|"\
                                    "20\d{2}|2100)\b", re.IGNORECASE | re.DOTALL)
        reNumMMDDYYYY3 = re.compile(r"\b(?:0?\d|1[012])\b/ ?\b(?:1st|2nd|3rd|"\
                                    "[012]?\dt?h?|3[01]t?h?)\b/ ?\b(?:19\d{2}|"\
                                    "20\d{2}|2100)\b", re.IGNORECASE | re.DOTALL)
        reWorMMDDYYYY = re.compile(r"\b(?:" + strMonths + r"|" + strMonthsShort + \
                                     r")\b,? ?\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                                    "\b[\.,]? ?\b(?:19\d{2}|20\d{2}|2100)\b",
                                    re.IGNORECASE | re.DOTALL)
        reWorMMDDYYYY2 = re.compile(r"\b(?:" + strMonths + r"|" + strMonthsShort + \
                                     r")\b\-\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                                    "\b\-\b(?:19\d{2}|20\d{2}|2100)\b",
                                    re.IGNORECASE | re.DOTALL)
        # time AM/PM
        reTimeAMPM = re.compile(r"(?:(?:\bPM\b|\bAM\b|p\.m\.|a\.m\.) \b"\
                                    "(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b|\b"\
                                    "(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b (?:\bPM\b|"\
                                    "\bAM\b|p\.m\.|a\.m\.))", re.IGNORECASE | re.DOTALL)
        # time 24 hour
        reTime24 = re.compile(r"(?:\s|\\n)((?:[01]?\d|2[0123]):[0-5]\d(?::[0-5]\d"\
                                    "(?:\.\d+)?)?)(?:[\+\-]\b[012]?\d:\d{2}\b| ?(?:Z|" + \
                                    strTimeZonesEu + strTimeZonesAu + strTimeZonesAm + r")"\
                                    "\b)?", re.IGNORECASE | re.DOTALL)
        # date and time together
        # date & AM/PM time
        reDateTimeAMPM = re.compile(r"(?:0?\d|1[012])\b/ ?\b(?:1st|2nd|3rd|[012]?\dt?h?|"\
                                    "3[01]t?h?)\b/ ?\b(?:19\d{2}|20\d{2}|2100)[ T]?(?:(?:\bPM\b|\bAM\b|"\
                                    "p\.m\.|a\.m\.) \b(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b|"\
                                    "\b(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b (?:\bPM\b|"\
                                    "\bAM\b|p\.m\.|a\.m\.))", re.IGNORECASE | re.DOTALL)
        # date & 24 hour time
        reDateTime24 = re.compile(r"(?:19\d{2}|20\d{2}|2100)\b\- ?\b(?:0?\d|1[012])\b\- ?\b"\
                                    "(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)[ T]?(?:(?:[01]?\d|"\
                                    "2[0123]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)(?:[\+\-]\b[012]?\d:\d{2}\b|"\
                                    " (?:Z|" + strTimeZonesEu + strTimeZonesAu + strTimeZonesAm + \
                                    r")\b)?", re.IGNORECASE | re.DOTALL)

        _filesPath = ""
        _remText = ""
        _resList = []

        def __init__(self):
            _EntityExtractorComponent.__init__(self)


        def month_word_to_num(self, monthWord=None):
            """
            Converts month word representation into numeric one
            """
            if(not monthWord):
                return int(0)

            # create list of month word representations
            lstMonths = ["jan", "january", "feb", "february", "mar", "march", \
                         "apr", "april", "may", "may", "jun", "june", "jul", \
                         "july", "aug", "august", "sep", "september", "oct", \
                         "october", "nov", "november", "dec", "december"]
            # look for monthWord in lstMonths
            monthNum = None
            # first try to convert string into int
            try:
                monthNum = int(monthWord)
            # if there's an error try to convert month word representations into numbers
            except(ValueError):
                try:
                    monthNum = int(lstMonths.index(monthWord) / 2) + 1
                # if there's an error again, this is probably not a month
                except(ValueError):
                    monthNum = None
            return monthNum



        def day_word_to_num(self, dayWord=None):
            """
            Converts day word representation into numeric one
            """
            dayNum = None
            # first try to convert string into int
            try:
                dayNum = int(dayWord)
            # if there's an error try to convert day word representations into numbers
            except(ValueError):
                try:
                    dayNum = int(re.search("\d+", dayWord).group())
                # if there's an error again, this is probably not a day
                except(ValueError):
                    dayNum = None
            return dayNum



        def extract_dates(self, plText="", mode=3):
            """
            Extracts dates from a plain text
                mode = 0 ... try to extract only dates containing just year
                mode = 1 ... try to extract only dates containing just month and year
                mode = 2 ... try to extract only dates containing just day, month and year
                mode >= 3 ... try to extract dates in all formats
            """
            # test for the file name
            if(not plText):
                return

            outDict = {}
            self._resList = []
            # process dates containing just year
            if(mode == 0):
                # use RE on the prepared document
                outDict["Years"] = self.reYearOnly.findall(plText)
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["Years"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    self._resList.append(RRSDateTime(year=int(rec)))
            # process dates containing just month and year
            elif(mode == 1):
                # use RE on the prepared document
                outDict["MonthsYears"] = self.reYearMonth.findall(plText)
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["MonthsYears"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[1]),
                                 month=self.month_word_to_num(parts[0].lower())))
            # process dates containing just day, month and year
            elif(mode == 2):
                # use RE on the prepared document
                # first get all dd mm yyyy formats
                outDict["DDMMYYYY"] = self.reNumDDMMYYYY.findall(plText)
                outDict["DDMMYYYY"].extend(self.reNumDDMMYYYY2.findall(plText))
                outDict["DDMMYYYY"].extend(self.reNumDDMMYYYY3.findall(plText))
                outDict["DDMMYYYY"].extend(self.reWorDDMMYYYY.findall(plText))
                outDict["DDMMYYYY"].extend(self.reWorDDMMYYYY2.findall(plText))
                # remove found dates from the text to avoid finding them again
                for rec in outDict["DDMMYYYY"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[2]), \
                                         month=self.month_word_to_num(parts[1].lower()), \
                                         day=self.day_word_to_num(parts[0].lower())))
                # then all yyyy mm dd formats
                outDict["YYYYMMDD"] = self.reNumYYYYMMDD.findall(plText)
                outDict["YYYYMMDD"].extend(self.reNumYYYYMMDD2.findall(plText))
                outDict["YYYYMMDD"].extend(self.reNumYYYYMMDD3.findall(plText))
                outDict["YYYYMMDD"].extend(self.reWorYYYYMMDD.findall(plText))
                outDict["YYYYMMDD"].extend(self.reWorYYYYMMDD2.findall(plText))
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["YYYYMMDD"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[0]), \
                                         month=self.month_word_to_num(parts[1].lower()), \
                                         day=self.day_word_to_num(parts[2].lower())))
                # finally get all mm dd yyyy formats
                outDict["MMDDYYYY"] = self.reNumMMDDYYYY.findall(plText)
                outDict["MMDDYYYY"].extend(self.reNumMMDDYYYY2.findall(plText))
                outDict["MMDDYYYY"].extend(self.reNumMMDDYYYY3.findall(plText))
                outDict["MMDDYYYY"].extend(self.reWorMMDDYYYY.findall(plText))
                outDict["MMDDYYYY"].extend(self.reWorMMDDYYYY2.findall(plText))
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["MMDDYYYY"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[2]), \
                                         month=self.month_word_to_num(parts[0].lower()), \
                                         day=self.day_word_to_num(parts[1].lower())))
            # process every date
            else:
                # first get all dd mm yyyy formats
                outDict["DDMMYYYY"] = self.reNumDDMMYYYY.findall(plText)
                outDict["DDMMYYYY"].extend(self.reNumDDMMYYYY2.findall(plText))
                outDict["DDMMYYYY"].extend(self.reNumDDMMYYYY3.findall(plText))
                outDict["DDMMYYYY"].extend(self.reWorDDMMYYYY.findall(plText))
                outDict["DDMMYYYY"].extend(self.reWorDDMMYYYY2.findall(plText))
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["DDMMYYYY"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[2]), \
                                         month=self.month_word_to_num(parts[1].lower()), \
                                         day=self.day_word_to_num(parts[0].lower())))
                # then all yyyy mm dd formats
                outDict["YYYYMMDD"] = self.reNumYYYYMMDD.findall(plText)
                outDict["YYYYMMDD"].extend(self.reNumYYYYMMDD2.findall(plText))
                outDict["YYYYMMDD"].extend(self.reNumYYYYMMDD3.findall(plText))
                outDict["YYYYMMDD"].extend(self.reWorYYYYMMDD.findall(plText))
                outDict["YYYYMMDD"].extend(self.reWorYYYYMMDD2.findall(plText))
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["YYYYMMDD"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[0]), \
                                         month=self.month_word_to_num(parts[1].lower()), \
                                         day=self.day_word_to_num(parts[2].lower())))
                # finally get all mm dd yyyy formats
                outDict["MMDDYYYY"] = self.reNumMMDDYYYY.findall(plText)
                outDict["MMDDYYYY"].extend(self.reNumMMDDYYYY2.findall(plText))
                outDict["MMDDYYYY"].extend(self.reNumMMDDYYYY3.findall(plText))
                outDict["MMDDYYYY"].extend(self.reWorMMDDYYYY.findall(plText))
                outDict["MMDDYYYY"].extend(self.reWorMMDDYYYY2.findall(plText))
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["MMDDYYYY"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[2]), \
                                         month=self.month_word_to_num(parts[0].lower()), \
                                         day=self.day_word_to_num(parts[1].lower())))
                # get all month and year formats
                outDict["MonthsYears"] = self.reYearMonth.findall(plText)
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["MonthsYears"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\,\.\-\/\: ]", rec)))
                    self._resList.append(RRSDateTime(year=int(parts[1]), \
                                         month=self.month_word_to_num(parts[0].lower())))
                # get all only year formats
                outDict["Years"] = self.reYearOnly.findall(plText)
                # remove found dates from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["Years"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    self._resList.append(RRSDateTime(year=int(rec)))
            # save remaining text
            self.rest = plText
            return self._resList



        def extract_times(self, plText="", mode=2):
            """
            Extracts time from plain texts
                mode = 0 ... try to extract time in AM/PM format
                mode = 1 ... try to extract time in 24 hour format
                mode >= 2 ... try to extract time in all formats
            """
            # test for the file name
            if(not plText):
                return

            outDict = {}
            self._resList = []
            # process times in AM/PM format
            if(mode == 0):
                # get all AM/PM times
                outDict["AMPM"] = self.reTimeAMPM.findall(plText)
                # remove found times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["AMPM"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # find out whether it is AM or PM
                    ampmInfo = re.search("(PM|AM|p\.m\.|a\.m\.)", rec, flags=re.I).group()
                    theTime = rec.replace(ampmInfo, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(ampmInfo == 'PM' or ampmInfo == 'p.m.'):
                        if(len(parts) == 2):
                            self._resList.append(RRSDateTime(hour=(int(parts[0]) + \
                                                 12), minute=int(parts[1])))
                        elif(len(parts) > 2):
                               self._resList.append(RRSDateTime(hour=(int(parts[0]) + \
                                                    12), minute=int(parts[1]), \
                                                    second=int(parts[2])))
                    else:
                        if(len(parts) == 2):
                            self._resList.append(RRSDateTime(hour=int(parts[0]), \
                                                 minute=int(parts[1])))
                        elif(len(parts) > 2):
                               self._resList.append(RRSDateTime(hour=int(parts[0]), \
                                                    minute=int(parts[1]), \
                                                    second=int(parts[2])))
            # process times in 24 hours format
            elif(mode == 1):
                # get all 24 hours times
                outDict["time24"] = self.reTime24.findall(plText)
                # remove found times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["time24"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\.\-\+\: ]", rec)))
                    if(len(parts) == 2):
                        self._resList.append(RRSDateTime(hour=int(parts[0]), \
                                                         minute=int(parts[1])))
                    elif(len(parts) > 2):
                        self._resList.append(RRSDateTime(hour=int(parts[0]), \
                                                         minute=int(parts[1]), \
                                                         second=int(parts[2])))
            # process times in all formats
            else:
                # get all AM/PM times
                outDict["AMPM"] = self.reTimeAMPM.findall(plText)
                # remove found times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["AMPM"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # find out whether it is AM or PM
                    ampmInfo = re.search("(PM|AM|p\.m\.|a\.m\.)", rec, flags=re.I).group()
                    theTime = rec.replace(ampmInfo, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(ampmInfo == 'PM' or ampmInfo == 'p.m.'):
                        if(len(parts) == 2):
                            self._resList.append(RRSDateTime(hour=(int(parts[0]) + 12), \
                                minute=int(parts[1])))
                        elif(len(parts) > 2):
                               self._resList.append(RRSDateTime(hour=(int(parts[0]) + 12), \
                                minute=int(parts[1]), second=int(parts[2])))
                    else:
                        if(len(parts) == 2):
                            self._resList.append(RRSDateTime(hour=int(parts[0]), minute=\
                                 int(parts[1])))
                        elif(len(parts) > 2):
                               self._resList.append(RRSDateTime(hour=int(parts[0]), minute=\
                                 int(parts[1]), second=int(parts[2])))
                # get all 24 hours times
                outDict["time24"] = self.reTime24.findall(str(plText))
                # remove found times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["time24"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    parts = list(filter(None, re.split(r"[\.\-\+\: ]", rec)))
                    if(len(parts) == 2):
                        self._resList.append(RRSDateTime(hour=int(parts[0]), minute=\
                             int(parts[1])))
                    elif(len(parts) > 2):
                        self._resList.append(RRSDateTime(hour=int(parts[0]), minute=\
                             int(parts[1]), second=int(parts[2])))
            # save remaining text
            self.rest = plText
            return self._resList



        def extract_datestimes(self, plText="", mode=2):
            """Extracts whole date time formats from plain text
                mode = 0 ... process dates with AM/PM times only
                mode = 1 ... process dates with 24 hour times only
                mode >= 2 ... process dates with times in all formats"""
            # test for the plain text
            if(not plText):
                return

            outDict = {}
            self._resList = []
            # proces dates with AM/PM time formats
            if(mode == 0):
                # get all date and AM/PM times
                outDict["DateTimeAMPM"] = self.reDateTimeAMPM.findall(plText)
                # remove found date times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["DateTimeAMPM"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    # first extract date part
                    theDate = re.search(r"\b(?:0?\d|1[012])\b/ ?\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                        "\b/ ?\b(?:[12]\d{1,3})", rec, flags=re.IGNORECASE).group()
                    dateParts = list(filter(None, re.split(r"[\,\.\-\/\: ]", theDate)))
                    # then extract time part
                    theTime = re.search(r"(?:(?:\bPM\b|\bAM\b|p\.m\.|a\.m\.) \b(?:[01]?\d:[0-5]\d(?::[0-5]\d"\
                        "(?:\.\d+)?)?)\b|\b(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b (?:\bPM\b|\bAM\b|p\.m\.|a\.m\.))"\
                        , rec, flags=re.IGNORECASE).group()
                    # find out whether it is AM or PM
                    ampmInfo = re.search("(PM|AM|p\.m\.|a\.m\.)", theTime, flags=re.IGNORECASE).group()
                    theTime = theTime.replace(ampmInfo, "")
                    # save it to the RrsDateTime format
                    timeParts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(ampmInfo == 'PM' or ampmInfo == 'p.m.'):
                        if(len(timeParts) == 2):
                            self._resList.append(RRSDateTime(year=int(dateParts[2]), month=\
                                self.month_word_to_num(dateParts[0].lower()), day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=(int(timeParts[0]) + 12), minute=int(timeParts[1])))
                        elif(len(timeParts) > 2):
                               self._resList.append(RRSDateTime(year=int(dateParts[2]), month=\
                                self.month_word_to_num(dateParts[0].lower()), day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=(int(timeParts[0]) + 12), minute=int(timeParts[1]), second=int(timeParts[2])))
                    else:
                        if(len(timeParts) == 2):
                            self._resList.append(RRSDateTime(year=int(dateParts[2]), month=\
                                self.month_word_to_num(dateParts[0].lower()), day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=int(timeParts[0]), minute=int(timeParts[1])))
                        elif(len(timeParts) > 2):
                               self._resList.append(RRSDateTime(year=int(dateParts[2]), month=\
                                self.month_word_to_num(dateParts[0].lower()), day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=int(timeParts[0]), minute=int(timeParts[1]), second=int(timeParts[2])))
            # process dates with 24 hour time formats
            elif(mode == 1):
                # get all date and 24 hour times
                outDict["DateTime24"] = self.reDateTime24.findall(plText)
                # remove found date times from the text to avoid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["DateTime24"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    # first extract date part
                    theDate = re.search(r"\b(?:[12]\d{1,3})\b\- ?\b(?:0?\d|1[012])\b\- ?\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                        , rec, flags=re.IGNORECASE).group()
                    dateParts = list(filter(None, re.split(r"[\,\.\-\/\: ]", theDate)))
                    # then extract time part
                    theTime = re.search(r"(?:(?:[01]?\d|2[0123]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)"\
                    "(?:[\+\-]\b[012]?\d:\d{2}\b| ?(?:Z|" + strTimeZonesEu + strTimeZonesAu + \
                        strTimeZonesAm + r")\b)?", rec, flags=re.IGNORECASE).group()
                    timeParts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(len(timeParts) == 2):
                        self._resList.append(RRSDateTime(year=int(dateParts[0]), month=\
                            self.month_word_to_num(dateParts[1].lower()), day=self.day_word_to_num(dateParts[2].lower()), \
                            hour=int(timeParts[0]), minute=int(timeParts[1])))
                    elif(len(timeParts) > 2):
                        self._resList.append(RRSDateTime(year=int(dateParts[0]), month=\
                            self.month_word_to_num(dateParts[1].lower()), day=self.day_word_to_num(dateParts[2].lower()), \
                            hour=int(timeParts[0]), minute=int(timeParts[1]), second=int(timeParts[2])))
            # process dates with all time formats
            else:
                # get all date time formats
                # get all date and AM/PM times
                outDict["DateTimeAMPM"] = self.reDateTimeAMPM.findall(plText)
                # remove found date times from the text to avid finding them again
                for rec in outDict["DateTimeAMPM"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    # first extract date part
                    theDate = re.search(r"\b(?:0?\d|1[012])\b/ ?\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                        "\b/ ?\b(?:[12]\d{1,3})", rec, flags=re.IGNORECASE).group()
                    dateParts = list(filter(None, re.split(r"[\,\.\-\/\: ]", theDate)))
                    # then extract time part
                    theTime = re.search(r"(?:(?:\bPM\b|\bAM\b|p\.m\.|a\.m\.) \b(?:[01]?\d:[0-5]\d(?::[0-5]\d"\
                        "(?:\.\d+)?)?)\b|\b(?:[01]?\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)\b (?:\bPM\b|\bAM\b|p\.m\.|a\.m\.))"\
                        , rec, flags=re.IGNORECASE).group()
                    # find out whether it is AM or PM
                    ampmInfo = re.search("(PM|AM|p\.m\.|a\.m\.)", theTime, flags=re.IGNORECASE).group()
                    theTime = theTime.replace(ampmInfo, "")
                    # save it to the RrsDateTime format
                    timeParts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(ampmInfo == 'PM' or ampmInfo == 'p.m.'):
                        if(len(timeParts) == 2):
                            self._resList.append(RRSDateTime(year=int(dateParts[2]), \
                                 month=self.month_word_to_num(dateParts[0].lower()), \
                                 day=self.day_word_to_num(dateParts[1].lower()), hour=(int(timeParts[0]) + 12), \
                                 minute=int(timeParts[1])))
                        elif(len(timeParts) > 2):
                               self._resList.append(RRSDateTime(year=int(dateParts[2]), \
                                month=self.month_word_to_num(dateParts[0].lower()), \
                                day=self.day_word_to_num(dateParts[1].lower()), hour=(int(timeParts[0]) + 12), \
                                minute=int(timeParts[1]), second=int(timeParts[2])))
                    else:
                        if(len(timeParts) == 2):
                            self._resList.append(RRSDateTime(year=int(dateParts[2]), \
                                month=self.month_word_to_num(dateParts[0].lower()), \
                                day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=int(timeParts[0]), minute=int(timeParts[1])))
                        elif(len(timeParts) > 2):
                               self._resList.append(RRSDateTime(year=int(dateParts[2]), \
                                month=self.month_word_to_num(dateParts[0].lower()), \
                                day=self.day_word_to_num(dateParts[1].lower()), \
                                hour=int(timeParts[0]), minute=int(timeParts[1]), second=int(timeParts[2])))
                # get all date and 24 hour times
                outDict["DateTime24"] = self.reDateTime24.findall(plText)
                # remove found date times from the text to avid finding them again
                # also save results to rrsdatetime format
                for rec in outDict["DateTime24"]:
                    # remove it from plain text
                    plText = plText.replace(rec, "")
                    # save it to the RrsDateTime format
                    # first extract date part
                    theDate = re.search(r"\b(?:[12]\d{1,3})\b\- ?\b(?:0?\d|1[012])\b\- ?\b(?:1st|2nd|3rd|[012]?\dt?h?|3[01]t?h?)"\
                        , rec, flags=re.IGNORECASE).group()
                    dateParts = list(filter(None, re.split(r"[\,\.\-\/\: ]", theDate)))
                    # then extract time part
                    theTime = re.search(r"(?:(?:[01]?\d|2[0123]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?)"\
                        "(?:[\+\-]\b[012]?\d:\d{2}\b| ?(?:Z|" + strTimeZonesEu + strTimeZonesAu + strTimeZonesAm + r")\b)?"\
                        , rec, flags=re.IGNORECASE).group()
                    timeParts = list(filter(None, re.split(r"[\.\-\+\: ]", theTime)))
                    if(len(timeParts) == 2):
                        self._resList.append(RRSDateTime(year=int(dateParts[0]), \
                            month=self.month_word_to_num(dateParts[1].lower()), \
                            day=self.day_word_to_num(dateParts[2].lower()), \
                            hour=int(timeParts[0]), minute=int(timeParts[1])))
                    elif(len(timeParts) > 2):
                        self._resList.append(RRSDateTime(year=int(dateParts[0]), \
                            month=self.month_word_to_num(dateParts[1].lower()), \
                            day=self.day_word_to_num(dateParts[2].lower()), \
                            hour=int(timeParts[0]), minute=int(timeParts[1]), second=int(timeParts[2])))
            # save remaining text
            self.rest = plText
            return self._resList

    #---------------------------------------------------------------------------
    # end of class DateExtractor
    #---------------------------------------------------------------------------


    class TelephoneNumberExtractor(_EntityExtractorComponent):
        """
        Searching for telephone numbers in plain text.
        """

        # prefix to country dictionary
        prefix2country = {
        '+672': 'Norfolk Island', '+673': 'Brunei', '+670': 'Timor-Leste',
        '+676': 'Tonga', '+88213': 'EMSAT (Mobile Satellite service)',
        '+674': 'Nauru', '+675': 'Papua New Guinea', '+678': 'Vanuatu',
        '+679': 'Fiji', '+27': 'South Africa', '+677': 'Solomon Islands',
        '+1 784': 'Saint Vincent and the Grenadines', '+1 787': 'Puerto Rico',
        '+5399': 'Guantanamo Bay', '+48': 'Poland', '+49': 'Germany',
        '+968': 'Oman', '+966': 'Saudi Arabia', '+45': 'Denmark', '+964': 'Iraq',
        '+965': 'Kuwait', '+962': 'Jordan', '+960': 'Maldives',
        '+808': 'International Shared Cost Service (ISCS)', '+43': 'Austria',
        '+250': 'Rwanda', '+251': 'Ethiopia', '+252': 'Somalia', '+253': 'Djibouti',
        '+254': 'Kenya', '+255': 'Zanzibar', '+256': 'Uganda', '+257': 'Burundi',
        '+258': 'Mozambique', '+378': 'San Marino', '+299': 'Greenland',
        '+1 340': 'U.S. Virgin Islands', '+91': 'India', '+377': 'Monaco',
        '+376': 'Andorra', '+375': 'Belarus', '+374': 'Armenia', '+373': 'Moldova',
        '+372': 'Estonia', '+371': 'Latvia', '+370': 'Lithuania', '+92': 'Pakistan',
        '+31': 'Netherlands', '+30': 'Greece', '+870': 'Inmarsat SNAC',
        '+90': 'Turkey', '+971': 'United Arab Emirates', '+241': 'Gabon',
        '+970': 'Palestinian Territory', '+973': 'Bahrain', '+972': 'Israel',
        '+975': 'Bhutan', '+974': 'Qatar', '+977': 'Nepal', '+976': 'Mongolia',
        '+243': 'Congo - Kinshasa', '+242': 'Congo - Brazzaville',
        '+240': 'Equatorial Guinea', '+247': 'Ascension', '+246': 'Diego Garcia',
        '+245': 'Guinea-Bissau', '+244': 'Angola', '+382': 'Montenegro',
        '+249': 'Sudan', '+248': 'Seychelles', '+996': 'Kyrgyzstan',
        '+995': 'Georgia', '+994': 'Azerbaijan', '+993': 'Turkmenistan',
        '+992': 'Tajikistan', '+878': 'Universal Personal Telecommunications (UPT)',
        '+998': 'Uzbekistan', '+66': 'Thailand', '+64': 'New Zealand',
        '+65': 'Singapore', '+62': 'Indonesia', '+63': 'Philippines',
        '+60': 'Malaysia', '+61': 'Cocos-Keeling Islands', '+967': 'Yemen',
        '+800': 'International Freephone Service', '+1 684': 'American Samoa',
        '+1 441': 'Bermuda', '+886': 'Taiwan', '+218': 'Libya', '+680': 'Palau',
        '+216': 'Tunisia', '+212': 'Morocco', '+213': 'Algeria', '+504': 'Honduras',
        '+599': 'Sint Maarten', '+297': 'Aruba', '+359': 'Bulgaria',
        '+358': 'Finland', '+93': 'Afghanistan', '+592': 'Guyana',
        '+357': 'Cyprus', '+590': 'Saint Martin', '+298': 'Faroe Islands',
        '+596': 'Martinique', '+353': 'Ireland', '+594': 'French Guiana',
        '+690': 'Tokelau', '+691': 'Micronesia', '+692': 'Marshall Islands',
        '+1 284': 'British Virgin Islands', '+598': 'Uruguay', '+855': 'Cambodia',
        '+852': 'Hong Kong SAR China', '+853': 'Macau SAR China',
        '+850': 'North Korea', '+501': 'Belize', '+1': 'United States',
        '+500': 'South Georgia and the South Sandwich Islands', '+503': 'El Salvador',
        '+505': 'Nicaragua', '+506': 'Costa Rica', '+507': 'Panama',
        '+261': 'Madagascar', '+509': 'Haiti', '+263': 'Zimbabwe',
        '+262': u'R\xe9union', '+265': 'Malawi', '+264': 'Namibia',
        '+267': 'Botswana', '+291': 'Eritrea', '+1 264': 'Anguilla',
        '+47': 'Norway', '+40': 'Romania', '+963': 'Syria', '+1 268': 'Barbuda',
        '+423': 'Liechtenstein', '+593': 'Ecuador', '+1 868': 'Trinidad and Tobago',
        '+1 869': 'Saint Kitts and Nevis', '+41': 'Switzerland', '+354': 'Iceland',
        '+81': 'Japan', '+82': 'South Korea', '+961': 'Lebanon', '+84': 'Vietnam',
        '+591': 'Bolivia', '+86': 'China', '+421': 'Slovakia', '+683': 'Niue',
        '+682': 'Cook Islands', '+681': 'Wallis and Futuna', '+356': 'Malta',
        '+687': 'New Caledonia', '+686': 'Kiribati', '+685': 'Samoa',
        '+7 840': 'Abkhazia', '+689': 'French Polynesia', '+688': 'Tuvalu',
        '+355': 'Albania', '+350': 'Gibraltar', '+290': 'Saint Helena',
        '+95': 'Myanmar', '+44': 'United Kingdom', '+352': 'Luxembourg',
        '+1 664': 'Montserrat', '+238': 'Cape Verde', '+232': 'Sierra Leone',
        '+239': u'S\xe3o Tom\xe9 and Pr\xedncipe', '+233': 'Ghana',
        '+230': 'Mauritius', '+231': 'Liberia', '+236': 'Central African Republic',
        '+237': 'Cameroon', '+234': 'Nigeria', '+235': 'Chad', '+266': 'Lesotho',
        '+1 876': 'Jamaica', '+34': 'Spain', '+36': 'Hungary',
        '+1 345': 'Cayman Islands', '+8818': 'Globalstar (Mobile Satellite Service)',
        '+33': 'France', '+32': 'Belgium', '+39': 'Italy', '+595': 'Paraguay',
        '+8816': 'Iridium (Mobile Satellite service)', '+46': 'Sweden',
        '+8812': 'Ellipso (Mobile Satellite service)', '+856': 'Laos',
        '+8810': 'ICO Global (Mobile Satellite Service)', '+7 6': 'Kazakhstan',
        '+1 671': 'Guam', '+1 670': 'Northern Mariana Islands', '+98': 'Iran',
        '+1 649': 'Turks and Caicos Islands', '+1 242': 'Bahamas',
        '+88216': 'Thuraya (Mobile Satellite service)', '+1 246': 'Barbados',
        '+1 758': 'Saint Lucia', '+269': 'Comoros', '+1 473': 'Grenada',
        '+1 808': 'Wake Island', '+1 809': 'Dominican Republic', '+20': 'Egypt',
        '+268': 'Swaziland', '+502': 'Guatemala', '+597': 'Suriname',
        '+39 066': 'Vatican', '+420': 'Czech Republic', '+1 767': 'Dominica',
        '+7': 'Russia', '+221': 'Senegal', '+222': 'Mauritania',
        '+881': 'Global Mobile Satellite System (GMSS)', '+880': 'Bangladesh',
        '+508': 'Saint Pierre and Miquelon', '+260': 'Zambia', '+94': 'Sri Lanka',
        '+58': 'Venezuela', '+57': 'Colombia', '+56': 'Easter Island',
        '+55': 'Brazil', '+54': 'Argentina', '+53': 'Cuba', '+52': 'Mexico',
        '+51': 'Peru', '+225': 'Ivory Coast', '+224': 'Guinea', '+227': 'Niger',
        '+226': 'Burkina Faso', '+351': 'Portugal', '+220': 'Gambia', '+223': 'Mali',
        '+389': 'Macedonia', '+386': 'Slovenia', '+387': 'Bosnia and Herzegovina',
        '+385': 'Croatia', '+229': 'Benin', '+228': 'Togo', '+380':
        'Ukraine', '+381': 'Serbia'}

        country2prefix = {'Canada': '+1', 'East Timor': '+670',
        'Turkmenistan': '+993', 'Saint Helena': '+290', 'Zanzibar': '+255',
        'Vatican': '+39 066', 'Lithuania': '+370', 'Cambodia': '+855',
        'Switzerland': '+41', 'Ethiopia': '+251', 'Aruba': '+297',
        'Micronesia': '+691', 'Wallis and Futuna': '+681', 'Argentina': '+54',
        'Bolivia': '+591', 'Cameroon': '+237', 'Burkina Faso': '+226',
        'Swaziland': '+268', 'Bahrain': '+973', 'Saudi Arabia': '+966',
        'Rwanda': '+250', 'Togo': '+228', 'Japan': '+81', 'Cape Verde': '+238',
        'Northern Mariana Islands': '+1 670', 'Slovenia': '+386',
        'Guatemala': '+502', 'Bosnia and Herzegovina': '+387', 'Kuwait': '+965',
        'Cuba (Guantanamo Bay)': '+5399', 'Guantanamo Bay': '+5399',
        'Dominica': '+1 767', 'Liberia': '+231', 'French Antilles': '+596',
        'Jamaica': '+1 876', 'Oman': '+968', 'Tanzania': '+255',
        'Martinique': '+596', 'Christmas Island': '+61', 'French Guiana': '+594',
        'Congo, Dem. Rep. of (Zaire)': '+243', 'Monaco': '+377',
        'Chatham Island (New Zealand)': '+64', 'New Zealand': '+64',
        'Yemen': '+967', 'Macau SAR China': '+853', 'Andorra': '+376',
        'Albania': '+355', 'Samoa': '+685', 'Norfolk Island': '+672',
        'Kazakhstan': '+7 6', 'Guam': '+1 671', 'India': '+91', 'Tunisia': '+216',
        'Azerbaijan': '+994', 'Universal Personal Telecommunications (UPT)': '+878',
        'Lesotho': '+266', 'Midway Island': '+1 808', 'United Arab Emirates': '+971',
        'Kenya': '+254', 'South Korea': '+82', 'Hong Kong SAR China': '+852',
        'Turkey': '+90', 'Afghanistan': '+93', 'Mauritania': '+222',
        'International Shared Cost Service (ISCS)': '+808', 'Bangladesh': '+880',
        'Solomon Islands': '+677', 'Turks and Caicos Islands': '+1 649',
        'Saint Lucia': '+1 758', 'San Marino': '+378', 'Kyrgyzstan': '+996',
        'Cocos-Keeling Islands': '+61', 'France': '+33', 'Bermuda': '+1 441',
        'Slovakia': '+421', 'Somalia': '+252', 'Peru': '+51', 'Laos': '+856',
        'Nauru': '+674', 'Seychelles': '+248', 'Norway': '+47', 'Malawi': '+265',
        'Cook Islands': '+682', 'Abkhazia': '+7 840', 'Cuba': '+53',
        'Montenegro': '+382', 'Saint Kitts and Nevis': '+1 869', 'China': '+86',
        'Ellipso (Mobile Satellite service)': '+8812', 'Mayotte': '+262',
        'Armenia': '+374', 'Easter Island': '+56', 'Inmarsat SNAC': '+870',
        'Saint Vincent and the Grenadines': '+1 784', 'Ukraine': '+380',
        'Dominican Republic': '+1 809', 'Mongolia': '+976', 'Ghana': '+233',
        'Tonga': '+676', 'Finland': '+358', 'Libya': '+218', 'Uganda': '+256',
        'Cayman Islands': '+1 345', 'Central African Republic': '+236',
        'Mauritius': '+230', 'Ascension': '+247', 'Liechtenstein': '+423',
        'Belarus': '+375', 'British Virgin Islands': '+1 284', 'Mali': '+223',
        'Saint Pierre and Miquelon': '+508', 'Russia': '+7', 'Bulgaria': '+359',
        'United States': '+1', 'Romania': '+40', 'Angola': '+244',
        'Thuraya (Mobile Satellite service)': '+88216', 'Chad': '+235',
        'South Africa': '+27', 'Tokelau': '+690', 'Cyprus': '+357',
        'South Georgia and the South Sandwich Islands': '+500', 'Niger': '+227',
        'Sweden': '+46', 'Qatar': '+974', 'El Salvador': '+503', 'Austria': '+43',
        'Vietnam': '+84', 'Mozambique': '+258', 'Hungary': '+36',
        'Brazil': '+55', 'Netherlands': '+31', 'Falkland Islands': '+500',
        'Faroe Islands': '+298', 'Guinea': '+224', 'Panama': '+507',
        'Guyana': '+592', 'Costa Rica': '+506', 'Luxembourg': '+352',
        'American Samoa': '+1 684', 'Bahamas': '+1 242', 'Gibraltar': '+350',
        'Ivory Coast': '+225', 'Pakistan': '+92', 'Palau': '+680',
        'Nigeria': '+234', 'Ecuador': '+593', 'Czech Republic': '+420',
        'Brunei': '+673', 'Australia': '+61', 'Iran': '+98', 'Algeria': '+213',
        'Australian External Territories': '+672', 'Tuvalu': '+688',
        'Congo - Kinshasa': '+243', 'Gambia': '+220', 'Jordan': '+962',
        'Sudan': '+249', 'Marshall Islands': '+692', 'Chile': '+56',
        'Puerto Rico': '+1 787', 'Belgium': '+32', 'Kiribati': '+686',
        'Haiti': '+509', 'Belize': '+501', 'Sierra Leone': '+232',
        'Georgia': '+995', 'Denmark': '+45', 'Philippines': '+63',
        'Tajikistan': '+992', 'Moldova': '+373', 'Morocco': '+212',
        'Croatia': '+385', 'French Polynesia': '+689', 'Guinea-Bissau': '+245',
        'Thailand': '+66', 'Namibia': '+264', 'Grenada': '+1 473',
        'Congo - Brazzaville': '+242', 'U.S. Virgin Islands': '+1 340',
        'Iraq': '+964', 'Portugal': '+351', 'Estonia': '+372', 'Uruguay': '+598',
        'Mexico': '+52', 'Lebanon': '+961', 'Uzbekistan': '+998',
        'Djibouti': '+253', 'Greenland': '+299', 'Antigua and Barbuda': '+1 268',
        'Spain': '+34', 'Colombia': '+57', 'Burundi': '+257', 'Taiwan': '+886',
        'Fiji': '+679', u'R\xe9union': '+262', 'Barbados': '+1 246',
        'Madagascar': '+261', 'Italy': '+39', 'Bhutan': '+975', 'Zambia': '+260',
        'Iridium (Mobile Satellite service)': '+8816', 'Nepal': '+977',
        'Barbuda': '+1 268', 'Malta': '+356', 'Maldives': '+960',
        u'S\xe3o Tom\xe9 and Pr\xedncipe': '+239', 'Suriname': '+597',
        'International Freephone Service': '+800', 'Anguilla': '+1 264',
        'Venezuela': '+58', 'Netherlands Antilles': '+599', 'Niue': '+683',
        'United Kingdom': '+44', 'Israel': '+972', 'Wake Island': '+1 808',
        'EMSAT (Mobile Satellite service)': '+88213', 'Indonesia': '+62',
        'Malaysia': '+60', 'Iceland': '+354', 'Senegal': '+221',
        'Papua New Guinea': '+675', 'Gabon': '+241', 'Nevis': '+1 869',
        'Trinidad and Tobago': '+1 868', 'Zimbabwe': '+263', 'Germany': '+49',
        'Diego Garcia': '+246', 'Benin': '+229', 'Saint Martin': '+590',
        'ICO Global (Mobile Satellite Service)': '+8810', 'Poland': '+48',
        'Eritrea': '+291', 'Ireland': '+353', 'Palestinian Territory': '+970',
        u'Saint Barth\xe9lemy': '+590', 'British Indian Ocean Territory': '+246',
        'Montserrat': '+1 664', 'New Caledonia': '+687', 'Macedonia': '+389',
        'North Korea': '+850', 'Sri Lanka': '+94', 'Latvia': '+371',
        'Global Mobile Satellite System (GMSS)': '+881', 'Syria': '+963',
        'Guadeloupe': '+590', 'Sint Maarten': '+599', 'Vanuatu': '+678',
        'Honduras': '+504', 'Myanmar': '+95', 'Equatorial Guinea': '+240',
        'Egypt': '+20', 'Nicaragua': '+505', 'Singapore': '+65', 'Serbia': '+381',
        'Botswana': '+267', 'Timor-Leste': '+670', 'Congo': '+242',
        'Greece': '+30', 'Paraguay': '+595', u'Cura\xe7ao': '+599',
        'Globalstar (Mobile Satellite Service)': '+8818', 'Comoros': '+269'}

        def __init__(self):
            _EntityExtractorComponent.__init__(self)
            # patterns
            self.phone_num = "((\+|(00))?(\(?[0-9]{1,5}\)?)? ?[0-9 \-\.]{9,}[0-9])"
            # these are here because one day here will be credibilty. The numbers
            # wich were found with these regexps, will have higher credibility
            # (of course)
            self.phone_specific1 = "phone\:?[ \t]*" + self.phone_num
            self.phone_specific2 = "tel(ephone)?\.?\:?[ \t]*" + self.phone_num
            # fax
            self.fax_specific = "(fax\.?\:?[ \t]*)" + self.phone_num
            # common form of telephone
            self.phone_fax_common = "(?:(phone\:?[ \t]*)|(tel(ephone)?\.?\:?[ \t]*))?" \
                                    + self.phone_num

        def extract_phone_numbers(self, text, fax=False):
            # FIXME do not accept ISBN nubers!!
            if not fax:
                m = re.findall(self.phone_fax_common, text)
            else:
                m = re.findall(self.fax_specific, text)
            l = []
            self.rest = text
            for phone in m:
                specif, num, pref = 1, 3, 6
                if fax:
                    specif, num, pref = 0, 1, 4
                tel = phone[num].lstrip(' ').rstrip(' ').replace(".", " ")
                # delete found numbers from text
                self.rest = re.sub(re.escape(phone[specif] + phone[num]) + "[, ]*", "", self.rest)
                prefix = re.sub("[\(\)]+", "", phone[pref])
                if prefix and "+" + prefix in \
                    EntityExtractor.TelephoneNumberExtractor.prefix2country:
                    nationality = \
                    EntityExtractor.TelephoneNumberExtractor.prefix2country["+" + prefix]
                    l.append((tel, nationality))
                else:
                    l.append((tel, None))
            return l


    #---------------------------------------------------------------------------
    # end of class TelephoneNumberExtractor
    #---------------------------------------------------------------------------


    #---------------------------------------------------------------------------
    # Public methods of EntityExtractor
    #---------------------------------------------------------------------------

    def find_title(self, text):
        """
        Find title of publication or paper in citation or reference.

        This method doesnt work for searching publication titles in free text
        or on web pages.

        This method needs to be fixed.
        """
        def _blacklist(chunks):
            _res = []
            for ch in chunks:
                ch = ch.lstrip(" \t")
                if not re.search("(?:" + _blacklisted + ")(?![a-z]+)", ch, re.I):
                    # if there are more numerical characters, than allowed
                    # (4x lesser than alpha-characters), skip it
                    if len(re.findall("[0-9]", ch)) * 5 > len(re.findall("[a-zA-Z ]", ch)):
                        continue
                    # if starts with unallowed preposition, skip it
                    if re.search("^(and|in|[a-zA-Z]\.|like|of)", ch):
                        continue
                    _res.append(ch)
            return _res

        def _get_longest(title_list):
            longest = None
            l = 0
            for t in title_list:
                if len(t) > l:
                    l = len(t)
                    longest = t
            return longest

        def _title_cleaning(title):
            t = title.rstrip(" ,.").lstrip(" .,")
            t = re.sub("quot;", "", t)
            t = re.sub("[ \t]+", " ", t)
            t = re.sub("[,\.][ ]+[a-zA-Z]$", "", t)
            return t

        _blacklisted = 'proceedings|conference|incollection|' \
                       'award|ceremony|concert|course|congress|exhibition|fair|' \
                       'lecture|meeting|seminar|symposium|webinar|' \
                       'workshop|journal|published|chapter'
        dots = re.findall("\.", text)
        commas = re.findall("\,", text)
        # try to catch format of reference
        if len(dots) > len(commas):
            chunks = re.findall("[a-z0-9 ]{3}[^\"\'\.]{16,200}\.?\,?", text, re.I)
        else:
            chunks = re.findall("[a-z0-9 ]{3}[^\"\'\,]{16,200}\.?\,?", text, re.I)
        # blacklist found chunks
        _res = _blacklist(chunks)
        # if not found, try another pattern
        if not _res:
            chunks = re.findall("[ a-z0-9\:\-]{19,200}", text, re.I)
            _res = _blacklist(chunks)
        title = _get_longest(_res)
        if title is not None:
            t = _title_cleaning(title)
            return (t, re.sub(re.escape(title), "", text))
        return (None, text)


    def find_booktitle(self, text):
        """
        Finds title of book or journal, of which the main extracted publication
        is a part.
        """
        dots = re.findall("\.", text)
        commas = re.findall("\,", text)
        # try to catch format of reference
        if len(dots) > len(commas):
            chunks = re.findall("[a-z0-9 ]{3}[^\"\'\.]{16,200}\.?\,?", text, re.I)
        else:
            chunks = re.findall("[a-z0-9 ]{3}[^\"\'\,]{16,200}\.?\,?", text, re.I)
        _blacklisted = '(?:proceedings|conference|university|' \
                       'award|ceremony|concert|course|congress|exhibition|fair|' \
                       'meeting|seminar|symposium|webinar|' \
                       'workshop|department|faculty|published|chapter)(?![a-z]+)'
        _booktitle = ('(?:journal|book)')
        for ch in chunks:
            if not re.search(_blacklisted, ch, re.I):
                if re.search(_booktitle, ch, re.I):
                    return (ch.lstrip(" ,.").rstrip(",. "), re.sub(re.escape(ch), "", text))
        return (None, text)


    def find_publisher(self, text):
        """
        Finds name of publisher, which published the paper or publication.
        """
        m = re.search("publishe((d by)|(r))[^\.\,]+,?.?", text, re.I)
        if m:
            publisher = re.sub("publishe((d by)|(r\:?))", "", m.group(0))
            return (publisher.lstrip(" ").rstrip(",. "), re.sub(re.escape(m.group(0)), "", text))
        m2 = re.search("[^\.,]+ press", text, re.I)
        if m2:
            publisher = m2.group(0)
            return (publisher.lstrip(" ").rstrip(",. "), re.sub(re.escape(publisher), "", text))
        return (None, text)



    def find_published_date(self, text):
        """
        Find date, when paper or publication was published.
        """
        return (self.date_e.extract_dates(text), self.date_e.get_rest())


    def find_authors(self, text):
        """
        Find names of authors of publication (all names, that arent in 'editors'
        section), which is found in text.
        """
        return (self.name_e.extract_persons(text), self.name_e.get_rest())


    def find_editors(self, text):
        """
        Find all editors
        
        @attention: This method sometimes stucks!
        @todo: This method has to be fixed! 
        """
        __person_list = []
        return (__person_list, text)
    
        REback = re.compile('((?![A-Z])\.|[^:;])+(?P<edmark>(editors|Eds)[;\.\)]{1})', re.M)
        match = re.search(REback, text)
        if match:
            editor_s = text[match.start():match.end()]
            __person_list.extend(self.name_e.extract_persons(editor_s))
            text = text[:match.start()] + self.name_e.get_rest() + text[match.end():]
            text = text.replace(match.group('edmark'), "")
            return (__person_list, text)
        REfor = re.compile('(?P<edmark>edited by|editors|ed\.)((?![A-Z])\.|[^:;])+', re.M)
        match = re.search(REfor, text)
        if match:
            editor_s = text[match.start():match.end()]
            __person_list.extend(self.name_e.extract_persons(editor_s))
            text = text[:match.start()] + self.name_e.get_rest() + text[match.end():]
            text = text.replace(match.group('edmark'), "")
        return (__person_list, text)
    
    
    def find_email(self, text):
        """
        Finds email adresses in text.
        """
        return (self.email_e.get_emails(text), self.email_e.get_rest())


    def find_event(self, text):
        """
        Find event (conference, workshop, seminar, lecture..etc) in text.
        """
        return (self.even_e.extract_events(text), self.even_e.get_rest())


    def find_organization(self, text):
        """
        Find organization (university, research lab/center, faculty, department)
        in text.
        """
        return (self.orga_e.extract_organizations(text), self.orga_e.get_rest())


    def find_location(self, text):
        """
        Find location (city, address, country).
        """
        return (self.loca_e.extract_locations(text), self.loca_e.get_rest())


    def find_project(self, text):
        """
        Find projects in text.
        """
        return (self.proj_e.extract_projects(text), text)


    def find_isbn(self, text):
        """
        Find International Serial Book Number (ISBN).
        """
        m = re.search(ISBNre + ",? ?", text)
        if m and m.group(0):
            return (m.group(1), re.sub(re.escape(m.group(0)), "", text))
        return (None, text)


    def find_issn(self, text):
        """
        Find International Standard Serial Number.  (ISBN).
        ISSN numbers are assigned by the ISSN national Centres coordinated in
        a network. All ISSN are accessible via the ISSN Register. The ISSN is
        not "just another administrative number". The ISSN should be as basic
        a part of a serial as the title.

        - As a standard numeric identification code, the ISSN is eminently
          suitable for computer use in fulfilling the need for file update and
          linkage, retrieval and transmittal of data.
        - As a human readable code, the ISSN also results in accurate citing of
          serials by scholars, researchers, information scientists and librarians.
        - In libraries, the ISSN is used for identifying titles, ordering and
          checking in, claiming serials, interlibrary-loan, union catalog reporting etc.
        - ISSN is a fundamental tool for efficient document delivery. ISSN
          provides a useful and economical method of communication between
          publishers and suppliers, making trade distribution systems faster
          and more efficient, in particular through the use of bar-coding and
          EDI (electronic data interchange).
        """
        reFindIssn = re.compile(r"(?<!p\.)(?<!pages)\s?(\d{4}\-\d{3}[0-9xX])", \
                                re.IGNORECASE)
        resIssnList = []
        remText = text
        # use prepared RE to search ISSN in plain text
        for rec in reFindIssn.findall(text):
            # remove the '-' sign from the middle of ISSN
            tmp = rec.replace('-', "")
            # check each record found in the text using the verification equation
            refN = 8
            vCode = 0
            try:
                # create control sum
                for char in tmp:
                    if(refN == 1 and char.upper() == 'X'):
                        vCode += 10
                    else:
                        vCode += refN * int(char)
                    refN -= 1
                # compute control sum modulo 11, the result has to be 0
                vCode %= 11
            except(TypeError):
                # if there's an type error exception, probably we're computing
                # control sum of something unexpected, so it's not an ISSN number
                vCode = -1
            # if it is an ISSN number(vCode is 0), remove it from the plain text
            # and add it to the resulting array
            if(vCode == 0):
                remText = remText.replace(rec, "")
                resIssnList.append(rec)
        # return (issn, remText)
        # !!! Now it's designed to return ISSN numbers list because in some documents,
        # 2 and more ISSN numbers were found !!!
        return (resIssnList, remText)


    def find_pages(self, text):
        """
        Recongnizing page count.
        """
        m = re.search('((?:pages|p\.|pp\.?|s\.)|(?<=[^\-\d]))\s*(?P<p1>\d+) ?-+ '\
                      '?(?P<p2>\d*)(?![\d\-]),? ?', text, re.I)
        if m and m.group('p1'):
            if m.group('p2'):
                if m.group('p1') < m.group('p2'):
                    pg = int(m.group('p2')) - int(m.group('p1'))
                else:
                    pg = int(m.group('p1')) - int(m.group('p2'))
                return (pg, re.sub(re.escape(m.group(0)), "", text))
            else:
                return (int(m.group('p1')), re.sub(re.escape(m.group(0)), "", text))
        return (None, text)


    def find_volume(self, text):
        """
        Find 'vol., volume, num. or number' in text.
        """
        m = re.search('((vol(?:\.|ume))|(num(?:\.|ber)))\s+(?P<vol>\d+),? ?', text, re.I)
        if m and m.group('vol'):
            return (int(m.group('vol')), re.sub(re.escape(m.group(0)), "", text))
        return (None, text)


    def find_to_appear(self, text):
        """
        Find terms 'to appear', nebo 'forth.' - forthcoming in text.
        """
        #=======================================================================
        # m = re.search('((\()?(to appear|accepted|submitted(\sfor publication)?' + 
        #              '|soumis|forth\.)(?(2)\)))', text, re.I)
        #=======================================================================
        m = re.search('((\()?(to appear|accepted|soumis|forth\.)(?(2)\)))',
                      text, re.I)
        if m:
            return (True, re.sub(re.escape(m.group(0)), "", text))
        return (None, text)
    
    
    def find_submitted(self, text):
        """
        Find term 'submitted' - forthcoming in text.
        """
        m = re.search('((\()?(submitted(\sfor publication)?)(?(2)\)))',
                      text, re.I)
        if m:
            return (True, re.sub(re.escape(m.group(0)), "", text))
        return (None, text)


    def find_telephone(self, text):
        """
        Finds telephone number in text and adds country by prefix of tel.num.
        """
        return (self.tele_e.extract_phone_numbers(text, fax=False), self.tele_e.get_rest())


    def find_fax(self, text):
        """
        Finds fax in text and adds country by prefix of fax num.
        """
        return (self.tele_e.extract_phone_numbers(text, fax=True), self.tele_e.get_rest())


    def find_url(self, text):
        """
        Find urls in text and returns list of them.
        """
        #urls_txt = re.findall("https?\://[a-z0-9%\./\+_&;#=~\,]+", text, re.I)
        urls_txt = re.findall("(" + URLre + ")", text, re.I)
        urls = []
        for u in urls_txt:
            url = u[0].rstrip(".,")
            urls.append(RRSUrl(link=url))
            text = re.sub(re.escape(url), "", text)
        if urls:
            return (urls, text)
        return (None, text)


#-------------------------------------------------------------------------------
# end of class EntityExtractor
#-------------------------------------------------------------------------------


################################################################################
# MAIN
################################################################################

# Main. Testing.
def get_files_in_dir(directory, file_types=".*"):
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

class NameFilter:
    """
    This class should check found names and filter those that are probably wrong
    
    @author: xlokaj03
    @attention: under construction
    @todo: almost everything :P
    """
    def __init__(self):
        pass
    
    def filter(self, name):
        if re.search("IEEE", name):
            return name
        else: return None
        

if __name__ == "__main__":
    
    text = "Asian Conference on Intelligent Information and Database Systems (ACIIDS)"
    ee = EntityExtractor.EventExtractor()
    events = ee.extract_events(text)
    print events[0]
    exit()
    
    
    text = "Karl von Bahnhoff  wrote about ...."
    
    ee = EntityExtractor.NameExtractor()
    persons = ee.extract_persons(text)
    print persons[0]
    exit()
    
    text = open("/media/Data/RRS/antijmena/delete", 'r').readlines()
    nf = NameFilter()
    for name in text:
        if nf.filter(name) != None: print name
        #print ee.find_authors(n[1])
    
    
    exit()
    
    text = "http://regexlib.com/Search.aspx?k=URL"
    ee = EntityExtractor()
    url = ee.find_url(text)
    print url[0][0].get('link')
    print url[1]
    
    exit()
    
    
    text = "West Liberty State College, Boston, USA. Washington D.C., This paper was published on ,Faculty of Information Technology, VUT, Brno, Czech Republic. bla bla New York City, USA"
    orge = EntityExtractor.OrganizationExtractor()
    o = orge.extract_organizations(text)
    print o[0]
    exit()
    
    
    
    
    print "Init",
    sys.stdout.flush()
    start_t = time.time()
    gle = EntityExtractor.GeographicLocationExtractor()
    stop_t = time.time()
    print stop_t - start_t
    
    print "Extracting",
    sys.stdout.flush()
    start_t = time.time()
    locations = gle.extract_locations(text[0])
    stop_t = time.time()
    total_t = stop_t - start_t
    print total_t
    for x in locations:
        print x
    print "Extraction time:\t" + str(total_t)
        

    exit()
    
    
    ex = EntityExtractor.ProjectExtractor()

    proj = []

    for f in get_files_in_dir("/media/Data/RRS/files/txt/projects"):
        print f
        text = open(f, 'r').read()
        text = re.sub('R[eE][fF][eE][rR][eE][nN][cC][eE][sS]?\W.*?$', "", text, re.DOTALL)
        for p in ex.extract_projects(text):
            output = StringIO.StringIO()
            converter = Model2XMLConverter(stream=output)
            converter.convert(p)
            print output.getvalue()

        print "#################################################################"
