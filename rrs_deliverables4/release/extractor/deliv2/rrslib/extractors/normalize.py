#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
This module provides method for text-cleaning and normalization into UTF-8 with
encoding unicode 0000-2014 etc.

Classes:
 - TextCleaner - cleaning text in string or unicode and encoding into UTF-8
"""
from codecs import Codec
import codecs
import re
import sys

__modulename__ = "normalize"
__author__ = "Tomas Lokaj"
__email__ = "xlokaj03@stud.fit.vutbr.cz"
__date__ = "$Date$"
__version__ = "$Revision$"



try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")


class TextCleaner(object):
    """
    This class allows opening and cleaning textual files from unappropriate
    characters.
    """

    def __init__(self):
        """
        Constructor.
        """
        # UTF-8 table at:
        # http://kellyjones.netfirms.com/webtools/ascii_utf8_table.shtml
        self._pat_bad_chars = "(" + \
            u"\u0000".encode('utf-8') + "|" + \
            u"\u0001".encode('utf-8') + "|" + \
            u"\u0002".encode('utf-8') + "|" + \
            u"\u0003".encode('utf-8') + "|" + \
            u"\u0004".encode('utf-8') + "|" + \
            u"\u0005".encode('utf-8') + "|" + \
            u"\u0006".encode('utf-8') + "|" + \
            u"\u0007".encode('utf-8') + "|" + \
            u"\u0008".encode('utf-8') + "|" + \
            u"\u000b".encode('utf-8') + "|" + \
            u"\u000c".encode('utf-8') + "|" + \
            u"\u000e".encode('utf-8') + "|" + \
            u"\u000f".encode('utf-8') + "|" + \
            u"\u0010".encode('utf-8') + "|" + \
            u"\u0011".encode('utf-8') + "|" + \
            u"\u0012".encode('utf-8') + "|" + \
            u"\u0013".encode('utf-8') + "|" + \
            u"\u0014".encode('utf-8') + "|" + \
            u"\u0015".encode('utf-8') + "|" + \
            u"\u0016".encode('utf-8') + "|" + \
            u"\u0017".encode('utf-8') + "|" + \
            u"\u0018".encode('utf-8') + "|" + \
            u"\u0019".encode('utf-8') + "|" + \
            u"\u001a".encode('utf-8') + "|" + \
            u"\u001b".encode('utf-8') + "|" + \
            u"\u001c".encode('utf-8') + "|" + \
            u"\u001e".encode('utf-8') + "|" + \
            u"\u001f".encode('utf-8') + ")"
        self._pat_quotes = "(" + \
            u"\u0027".encode('utf-8') + "|" + \
            u"\u0060".encode('utf-8') + "|" + \
            u"\u00b4".encode('utf-8') + "|" + \
            u"\u00ab".encode('utf-8') + "|" + \
            u"\u00bb".encode('utf-8') + "|" + \
            u"\u2018".encode('utf-8') + "|" + \
            u"\u2019".encode('utf-8') + "|" + \
            u"\u201a".encode('utf-8') + "|" + \
            u"\u201c".encode('utf-8') + "|" + \
            u"\u201d".encode('utf-8') + "|" + \
            u"\u201e".encode('utf-8') + "|" + \
            u"\u2032".encode('utf-8') + "|" + \
            u"\u2039".encode('utf-8') + "|" + \
            u"\u203a".encode('utf-8') + ")"
        self._pat_dashes = "(" + \
            u"\u00ac".encode('utf-8') + "|" + \
            u"\u2013".encode('utf-8') + "|" + \
            u"\u2014".encode('utf-8') + ")"
        self._re_quotes_1 = re.compile(self._pat_quotes, re.U)
        self._re_quotes_2 = re.compile("([a-z])" + u"\u0022".encode('utf-8')
                                       + "([a-z])", re.U | re.I)
        self._re_dashes_1 = re.compile(self._pat_dashes, re.U)
        self._re_dashes_2 = re.compile(unichr(226) + unichr(136) + unichr(146),
                                       re.U)
        self._re_a = re.compile("(" + unichr(192) + "|" + unichr(193) + "|"
                                + unichr(194) + "|" + unichr(195) + "|"
                                + unichr(196) + "|" + unichr(197) + ")"
                                + unichr(168), re.U)
        self._re_e = re.compile("(" + unichr(200) + "|" + unichr(201) + "|"
                                + unichr(202) + "|" + unichr(203) + ")"
                                + unichr(168), re.U)
        self._re_i = re.compile("(" + unichr(204) + "|" + unichr(205) + "|"
                                + unichr(206) + "|" + unichr(207) + ")"
                                + unichr(168), re.U)
        self._re_o = re.compile("(" + unichr(210) + "|" + unichr(211) + "|"
                                + unichr(212) + "|" + unichr(213) + "|"
                                + unichr(214) + ")" + unichr(168), re.U)
        self._re_u = re.compile("(" + unichr(217) + "|" + unichr(218) + "|"
                                + unichr(219) + "|" + unichr(220) + ")"
                                + unichr(168), re.U)
        self._re_ff = re.compile(unichr(239) + unichr(172) + unichr(128), re.U)
        self._re_fi = re.compile(unichr(239) + unichr(172) + unichr(129), re.U)
        self._re_fl = re.compile(unichr(239) + unichr(172) + unichr(130), re.U)
        self._re_ffi = re.compile(unichr(239) + unichr(172) + unichr(131), re.U)
        self._re_ffl = re.compile(unichr(239) + unichr(172) + unichr(132), re.U)
        self._re_ft = re.compile(unichr(239) + unichr(172) + unichr(133), re.U)
        self._re_st = re.compile(unichr(239) + unichr(172) + unichr(134), re.U)


    def clean_text(self, text):
        """
        This method cleans the text from unappropriate characters.

        @param text: text to be cleaned
        @type text: str
        @return: cleaned text
        @rtype: str
        """

        if not isinstance(text, unicode):
            text = text.decode("utf-8")
        #Fix ligatures
        while self._re_fi.search(text):
            text = self._re_fi.sub("fi", text)
        while self._re_ff.search(text):
            text = self._re_ff.sub("ff", text)
        while self._re_fl.search(text):
            text = self._re_fl.sub("fl", text)
        while self._re_ffl.search(text):
            text = self._re_ffl.sub("ffl", text)
        while self._re_ffi.search(text):
            text = self._re_ffi.sub("ffi", text)
        while self._re_ft.search(text):
            text = self._re_ft.sub("ft", text)
        while self._re_st.search(text):
            text = self._re_st.sub("st", text)

        #Fix umlauts
        while self._re_a.search(text):
            text = self._re_a.sub("a", text)
        while self._re_e.search(text):
            text = self._re_e.sub("e", text)
        while self._re_i.search(text):
            text = self._re_i.sub("c", text)
        while self._re_o.search(text):
            text = self._re_o.sub("o", text)
        while self._re_u.search(text):
            text = self._re_u.sub("u", text)

        #Unite quotes
        while self._re_quotes_1.search(text):
            text = self._re_quotes_1.sub('"', text)
        while self._re_quotes_2.search(text):
            text = self._re_quotes_2.sub("\g<1>'\g<2>", text)

        #Unite dashes
        while self._re_dashes_1.search(text):
            text = self._re_dashes_1.sub('-', text)
        while self._re_dashes_2.search(text):
            text = self._re_dashes_2.sub('-', text)

        #Fix unappropriate chars
        for i in [1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15, 16, 17, 18, 19,
                  20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]:
            text = text.replace(unichr(i), "")
        for i in [10, 13]:
            text = text.replace(unichr(i), "\n")

        for i in range(127, 161):
            text = text.replace(unichr(i), "")

        #Remove other unappropriate chars, which weren't fixed
        for c in text:
            try:
                unicode(chr(ord(c)))
            except ValueError:
                text = text.replace(c, "")
        return str(text)


    def read(self, ifile_path, clean=True):
        """
        This method opens and reads a textual file.

        @param ifile_path: path to file to be read
        @type ifile_path: str
        @param clean: enables cleaning process
        @type clean: bool
        @return: file content
        @rtype: str
        """
        file_obj = codecs.open(ifile_path, "r", "utf-8", errors='ignore')
        text = file_obj.read()

        if clean:
            text = self.clean_text(text)

        return str(text.encode('utf-8'))


    def read_and_save(self, ifile_path, ofile_path=None):
        """
        This method opens, reads, cleans and saves a textual file.

        @param ifile_path: path to file to be read
        @type ifile_path: str
        @param ofile_path: path to file to be saved
        @type ofile_path: str
        @return: file content
        @rtype: str
        """
        if ofile_path == None:
            ofile_path = ifile_path
        text = self.read(ifile_path, True)
        try:
            output = open(ofile_path, 'w')
            output.write(text)
            output.close()
        except IOError:
            return None

        return str(text.encode('utf-8'))

    def save_as(self, ifile_path, ofile_path=None):
        """
        This method saves a textual file.

        @param ifile_path: path to file to be read
        @type ifile_path: str
        @param ofile_path: path to file to be saved
        @type ofile_path: str
        @return: True if saving was successfull, False otherwise
        @rtype: bool

        @attention: THIS METHOD DOESN'T CLEAN TEXT!
        """
        if ofile_path == None:
            ofile_path = ifile_path
        text = self.read(ifile_path)
        try:
            output = open(ofile_path, 'w')
            output.write(text)
            output.close()
        except IOError:
            return False

        return True

#-------------------------------------------------------------------------------
# End of class TextCleaner
#-------------------------------------------------------------------------------



class Normalize(object):
    """
    This class converts titles of database elements into a normalized form
    """

    #Improved dictionary
    re_a = re.compile("(" + unichr(192) + "|" + unichr(193) + "|" + unichr(194)
                      + "|" + unichr(195) + "|" + unichr(196) + "|" + unichr(197)
                      + "|" + unichr(224) + "|" + unichr(225) + "|" + unichr(226)
                      + "|" + unichr(227) + "|" + unichr(228) + "|" + unichr(229)
                      + ")" , re.U)
    re_e = re.compile("(" + unichr(200) + "|" + unichr(201) + "|" + unichr(202)
                      + "|" + unichr(203) + "|" + unichr(232) + "|" + unichr(233)
                      + "|" + unichr(234) + "|" + unichr(235) + "|" + unichr(282)
                      + "|" + unichr(283) + ")" , re.U)
    re_i = re.compile("(" + unichr(204) + "|" + unichr(205) + "|" + unichr(206)
                      + "|" + unichr(207) + "|" + unichr(237) + "|" + unichr(238)
                      + "|" + unichr(239) + ")" , re.U)
    re_o = re.compile("(" + unichr(210) + "|" + unichr(211) + "|" + unichr(212)
                      + "|" + unichr(213) + "|" + unichr(243) + "|" + unichr(244)
                      + "|" + unichr(245) + "|" + unichr(246) + "|" + unichr(330)
                      + "|" + unichr(216) + "|" + unichr(248) + ")"  , re.U)
    re_u = re.compile("(" + unichr(217) + "|" + unichr(218) + "|" + unichr(219)
                      + "|" + unichr(220) + "|" + unichr(249) + "|" + unichr(250)
                      + "|" + unichr(251) + "|" + unichr(252) + "|" + unichr(366)
                      + "|" + unichr(367) + ")" , re.U)
    re_c = re.compile("(" + unichr(199) + "|" + unichr(231) + "|" + unichr(268)
                      + "|" + unichr(269) + ")", re.U)
    re_n = re.compile("(" + unichr(209) + "|" + unichr(241) + "|" + unichr(327)
                      + "|" + unichr(328) + ")", re.U)
    re_y = re.compile("(" + unichr(221) + "|" + unichr(255) + "|" + unichr(253)
                      + ")", re.U)
    re_s = re.compile("(" + unichr(352) + "|" + unichr(353) + ")", re.U)
    re_r = re.compile("(" + unichr(344) + "|" + unichr(345) + ")", re.U)
    re_z = re.compile("(" + unichr(381) + "|" + unichr(382) + ")", re.U)
    re_t = re.compile("(" + unichr(357) + "|" + unichr(356) + ")", re.U)
    re_d = re.compile("(" + unichr(270) + "|" + unichr(271) + ")", re.U)

    #List of words occuring in organizations
    org_replace = {"university":"univ", "univerzita":"univ", "universität":"univ",
              "universitat":"univ", "universitaire":"univ", "department":"dept",
              "département":"dept", "departement":"dept", "centre":"center",
              "laboratory":"lab", "association":"assoc", "society":"soc"}
    org_remove = ['3ao', '3at', 'a', 'aat', 'ab', 'abee', 'ad', 'adsitz', 'aemepe',
                'ag', 'akc', 'amba', 'ans', 'aps', 'as', 'asa', 'at', 'ay', 'ba',
                'bhd', 'bk', 'bl', 'bm', 'box', 'bt', 'bv', 'bvba', 'cc', 'ccbk',
                'cia', 'cic', 'co', 'commv', 'commva', 'coop', 'corp', 'cra',
                'crl', 'ctcp', 'cty', 'cvba', 'cvoa', 'da', 'dat', 'dd', 'dk',
                'dno', 'doo', 'ead', 'ebvba', 'ec', 'ee', 'eg', 'ehf', 'ehzs',
                'ei', 'eirl', 'ek', 'eood', 'epe', 'et', 'etat', 'eu', 'ev', 'fa',
                'fcp', 'fie', 'fkf', 'fop', 'gbr', 'gmbh', 'gp', 'hb', 'hf', 'huf',
                'ik', 'iks', 'inc', 'ip', 'is', 'kb', 'kd', 'kda', 'kf', 'kft',
                'kg', 'kgaa', 'kht', 'koll', 'kom', 'ks', 'kt', 'kub', 'kv', 'ky',
                'llc', 'lllp', 'llp', 'lp', 'ltd', 'ltda', 'mchj', 'mtu', 'na',
                'nl', 'nt', 'nt and sa', 'nuf', 'nv', 'nyrt', 'oao', 'obee', 'od',
                'oe', 'og', 'ohf', 'ohg', 'ok', 'ood', 'ooo', 'ou', 'oy', 'oyj',
                'partg', 'peec', 'plc', 'pllc', 'pp', 'ps', 'pt', 'pte', 'pty',
                'rhf', 'rp', 'rt', 'ry', 'sa', 'saatio', 'sab', 'sae', 'safi',
                'sapa', 'sapi', 'sarl', 'sas', 'sasu', 'sc', 'sca', 'sce', 'scoop',
                'scop', 'scra', 'scrl', 'scs', 'sd', 'sdn', 'se', 'sem', 'senc',
                'ses', 'sf', 'sgps', 'sia', 'sicaf', 'sicav', 'sl', 'sll', 'slne',
                'sm', 'sme', 'snc', 'sp', 'spa', 'spj', 'spk', 'spol', 'spp',
                'spz', 'srl', 'sro', 'ss', 'taa', 'tdv', 'the', 'tnhh', 'tov',
                'tu', 'tub', 'uab', 'ud', 'ultd', 'unltd', 'uu', 'valtion', 'vat',
                'vc', 'vof', 'vos', 'vsl', 'zao', 'zat', 'zrt', 'of', 'in']
    proj_remove = ['a', 'the']

    loca_prepos = ('of', 'the', 'de', 'am', 'nad', 'wa', 'des', 'da', 'ye', 'al',
                   'la', 'der', 'fan', 'di', 'du', 'er', 'a', 'ra', 'na', 'agus',
                   'and', 'o', 'an', 'ya', 'd')

    loca_delim = (# apostrophes
                  unichr(96), unichr(8216), unichr(39), unichr(8217), unichr(700),
                  unichr(699), unichr(1370),
                  # hyphens
                  unichr(8208), unichr(45), unichr(173), unichr(8209), unichr(8259),
                  unichr(8722),
                  # spaces
                  unichr(32), unichr(160), unichr(5760), unichr(8192), unichr(8193),
                  unichr(8194), unichr(8195), unichr(8196), unichr(8197),
                  unichr(8198), unichr(8199), unichr(8200), unichr(8201),
                  unichr(8202), unichr(8203), unichr(8204), unichr(8205),
                  unichr(8239), unichr(8287), unichr(8288), unichr(12288)
                 )


    @classmethod
    def _white_space_fix(self, txt):
        """
        Fixing of multiple whitespaces in a text.

        @param txt: text to be fixed
        @type txt: str
        @return: fixed text
        @rtype: str

        @todo: not quickest solution, but it works:)
        """
        while re.search("\s\s+", txt):
            txt = re.sub("\s\s+", " ", txt)
        txt = re.sub("^\s+", "", txt)
        txt = re.sub("\s+$", "", txt)
        return txt


    @classmethod
    def translate_national(self, txt):
        """
        Translate national chars to standard form.

        @param txt: text to be translated
        @type txt: str
        @return: translated text
        @rtype: str

        @todo: not quickest solution, but it works:)
        """
        if type(txt) is not unicode:
            txt = unicode(str(txt), encoding='utf-8')
        while Normalize.re_a.search(txt):
            txt = Normalize.re_a.sub("a", txt)
        while Normalize.re_e.search(txt):
            txt = Normalize.re_e.sub("e", txt)
        while Normalize.re_i.search(txt):
            txt = Normalize.re_i.sub("i", txt)
        while Normalize.re_o.search(txt):
            txt = Normalize.re_o.sub("o", txt)
        while Normalize.re_u.search(txt):
            txt = Normalize.re_u.sub("u", txt)
        while Normalize.re_c.search(txt):
            txt = Normalize.re_c.sub("c", txt)
        while Normalize.re_n.search(txt):
            txt = Normalize.re_n.sub("n", txt)
        while Normalize.re_y.search(txt):
            txt = Normalize.re_y.sub("y", txt)
        while Normalize.re_s.search(txt):
            txt = Normalize.re_s.sub("s", txt)
        while Normalize.re_r.search(txt):
            txt = Normalize.re_r.sub("r", txt)
        while Normalize.re_z.search(txt):
            txt = Normalize.re_z.sub("z", txt)
        while Normalize.re_t.search(txt):
            txt = Normalize.re_t.sub("t", txt)
        while Normalize.re_d.search(txt):
            txt = Normalize.re_d.sub("d", txt)
        #for letter in Normalize.tr:
            #txt = re.sub(letter, Normalize.tr[letter], txt)
        return txt


    @classmethod
    def publication(self, publ):
        """
        Normalizes publication title.

        @param publ: publication title to be normalized
        @type publ: str
        @return: normalized publication title
        @rtype: str

        @note:
        U nazvu publikaci se jedna alfanumericke ASCII lowercase znaky.
        U nazvu casopisu, sborniku (..) se jedna o cast nazvu z ktereho je
        odstratena in/the/on, proceedings, 5th/fifth, (bi)annual, (a podobne
        jako u nazvu publikace).
        """
        publ = Normalize.translate_national(publ)
        publ = re.sub("\([^\)]*\)", "", publ)
        publ = re.sub("[^a-zA-Z0-9 ]", "", publ)
        publ = re.sub("[\t\n ]+", " ", publ)
        publ = publ.rstrip(" ").lstrip(" ")
        return publ.lower()


    @classmethod
    def event(self, event):
        """
        Normalizes event title.

        @param event: event title to be normalized
        @type event: unicode
        @return: normalized event title
        @rtype: unicode
        """
        backup = event
        event = Normalize.translate_national(event)
        event = re.sub("^(in)? ?(online)? ?proc[^ ]* ?(of)? ?(the)?", "", event, re.I)
        event = re.sub(" ?[0-9]+(th|st|nd|rd)", "", event, re.I)
        years = re.findall("[0-9]+", event)
        ylist = []
        for y in years:
            yl = len(y)
            if yl == 2:
                if int(y) > 50:
                    ylist.append(int("19" + y))
                else:
                    ylist.append(int("20" + y))
            elif yl == 4:
                if int(y) > 1900 and int(y) < 2100:
                    ylist.append(int(y))
        if ylist:
            event = re.sub("[^a-zA-Z ]", "", event)
            event += " " + str(max(ylist))
        else:
            event = re.sub("[^a-zA-Z ]", "", event)
        event = re.sub("\([^\)]*\)", "", event)
        event = re.sub("^ ?[a-z]{2,10}th", "", event, re.I)
        event = re.sub("^.*(bi)?annual", "", event, re.I)
        event = re.sub("[\t\n ]+", " ", event)
        event = event.rstrip(" ").lstrip(" ")
        if event.lower() in ("workshop", "conference"):
            try:
                event = re.findall("[A-Z]{2,}", backup)
                e = ""
                for item in event:
                    if len(item) > len(e):
                        e = item
                event = e
            except:
                event = ""
        if event == "":
            event = re.sub("[^a-zA-Z ]", "", backup)
            event = event.lower()
            sp = event.split(" ")
            seqs = []
            start = 0
            end = 0
            for i, word in enumerate(sp):
                if re.search("proc\.|proceedings|[a-z]+(th|st|nd|rd)|annual| in", word, re.I):
                    seqs.append((start, end))
                    start = i
                    end = i
                else:
                    end = i
            best = None
            bestlen = 0
            for s in seqs:
                ln = s[1] - s[0]
                if ln > bestlen:
                    bestlen = ln
                    best = s
            event = " ".join(sp[best[0]:best[1] + 1])
            event = re.sub("^ ?(in)? ?(of)? ?", "", event, re.I)
        return event.lower()


    @classmethod
    def organization(self, org):
        """
        Normalizes organization title.

        @param org: organizationn title to be normalized
        @type org: unicode
        @return: normalized organization title
        @rtype: unicode
        """

        #=======================================================================
        # OrganizationExtractor should take care of this
        # capitals = re.findall("(([A-Z]{2,}\W+)+)", org)
        # cl = 0
        # for cap in capitals:
        #    l = len(cap[0].split(" "))
        #    if l > 2 and l > cl:
        #        cl = l
        #        org = cap[0]
        #=======================================================================

        org = Normalize.translate_national(org)
        org = org.lower()
        org = re.sub('\W', " ", org)
        org = org.replace("&", "and")

        for word in Normalize.org_remove:
            org = re.sub("(^|\s|$)" + re.escape(word) + "(^|\s|$)", " ", org, re.DOTALL)

        for word in Normalize.org_replace.keys():
            org = re.sub(re.escape(word), Normalize.org_replace[word] + " ", org)

        org = Normalize._white_space_fix(org)

        return org


    @classmethod
    def project(self, proj):
        """
        Normalizes project title.

        @param proj: project title to be normalized
        @type proj: unicode
        @return: normalized project title
        @rtype: unicode
        """

        proj = Normalize.translate_national(proj)

        proj = re.sub('([A-Z0-9]+-){2,}[A-Z0-9]+', "", proj)

        capitals = re.findall("(([A-Z]{2,}\W+)+)", proj)
        cl = 0
        for cap in capitals:
            l = len(cap[0].split(" "))
            if l > 2 and l > cl:
                cl = l
                proj = cap[0]

        proj = re.sub('\W', " ", proj)

        proj = proj.lower()
        proj = proj.replace("projects", "")
        proj = proj.replace("project", "")
        proj = proj.replace("&", "and")
        proj = re.sub('^\s*and', '', proj)

        for word in Normalize.proj_remove:
            proj = re.sub("(^|\s|$)" + re.escape(word) + "(^|\s|$)", " ", proj, re.DOTALL)

        if re.search('(19[0-9]{2}|20[0-9]{2})', proj):
            year = re.search('(19[0-9]{2}|20[0-9]{2})', proj).group(0)
            proj = proj.replace(year, "")
            proj += " " + year

        proj = Normalize._white_space_fix(proj)

        return proj.lower()


    @classmethod
    def to_ascii(self, s):
        s = Normalize.translate_national(s)
        return u''.join([l for l in s if ord(l) < 128])


    @classmethod
    def location(self, loc, delnum=False):
        """
        Normalizes every geographic name (cities, states, countries, etc.)
        @param loc: - string or unicode containing geograph. name for normalization
        @param delnum - if deleting numbers is needed (probably in case of city
                        and country), set this flag to True.
        @return: unicode with normalized geograph. name.
        """
        if type(loc) is not unicode:
            loc = unicode(str(loc), encoding='utf-8')
        result = u""
        chunk = u""
        for letter in loc + " ":
            if letter in Normalize.loca_delim:
                if chunk in Normalize.loca_prepos:
                    result += chunk
                else:
                    try:
                        result += chunk[0].upper()
                        result += chunk[1:]
                    except IndexError:
                        pass
                chunk = u""
                result += letter
            else:
                chunk += letter.lower()
        if delnum:
            result = re.sub("[0-9]+", "", result)
        result = result.rstrip(" ").lstrip(" ")
        if len(result) < 2:
            return None
        return result[0].upper() + result[1:]




#-------------------------------------------------------------------------------
# End of class Normalize
#-------------------------------------------------------------------------------



if __name__ == "__main__":
    loc = ["CZECH REPUBLIC", " Unitit Kinrick o Great Breetain an Northren Ireland ".lower(),
        "republic of uganda", "Usti nad Mohanem", "FRANKFURT AM MAIN",
        "Jamhuri Ya Muungano Wa Tanzania", "brno", "États-Unis d'Amérique",
        "Rìoghachd Aonaichte na Breatainn Mòire agus Èireann a Tuath", " Al Imārāt al ‘Arabīyah al Muttaḩidah",
        "987318 Curych"]
    for l in loc:
        Normalize.location(l)
        print Normalize.location(l, True)
    exit()
    projs = [
             "EuroWordNet Project",
             "Application Management Environments and Support",
             "Blue Light SE Youth Development Project",
             "Rock Eisteddfod Challenge and Mt Theo Petrol and Yuendumu Diversionary Project",
             "National Natural Science Foundation Project",
             "National Science and Technology Supporting Platform Project",
             "Development of Health Advisory Service in Organic Dairy Herds",
             "Improving welfare in organic dairy cattle",
             "Kenan Trust Family Literacy Project",
             "Text–to–Onto",
             "Alexandria Digital Library Project",
             "CARA POSTDOCTORAL MOBILITY FELLOWSHIPS IN THE HUMANITIES AND SOCIAL SCIENCES",
             "Compact disc publishing for interactive language learning",
             "Extended X-Protocol for Office-Related Technology",
             "Testing methodology for technical applications",
             "The Global Burden of Disease 2000",
             "Global Burden of Disease 2000",
             "Traffic and QOS Management for IBC",
             "Integrated Communications Management",
             "Management in a Distributed Application and Service Environment",
             "2001 Internal Land SAF",

           ]

    print "\n\n"
    l = 0
    for pp in projs:
        if len(unicode(pp, encoding='utf-8')) > l: l = len(pp)
    for p in projs:
        print p, (l - len(unicode(p, encoding='utf-8'))) * " ", " ---> ", Normalize.project(p)

    orgs = [
            "Department of Computer Science University of Maryland College Park",
            "International Institute for Mathematical Physics Boltzmanngasse",
            "Canadian Institute for Advanced Research Cosmology Program",
            "University of Alberta",
            "School of Learning & Professional Studies Queensland University of Technology",
            "Educational resources information center",
            "Stephen Pink Swedish Institute of Computer Science and Luleang",
            "University of Technology For more information about USENIX Association contact",
            "Computer Science Department University of California",
            "UNIVERSITY OF OSLO Department of Mathematics",
            "Australian Institute of Criminology",
            "School of Computer Science and Information Technology University of Nottingham",
            "University of Bia",
            "MEDmetric Corporation",
            "Department of Computing",
            "Imperial College of Science",
            "Universitat Konstanz",
            "School of Computer Science",
            "Carnegie Mellon University",
            "Audio Engineering Society",
            "National Center for Super Computing Atmospheric and Applications",
            "Department of Defense Standard Practice",
            "Department of Defense World Geodetic System",
            "Eindhoven University of Technology",
            "University College London",
            "Univ. of Bia",
            "University of Notre Dame",
            "Department of Banking",
            "University of Cologne Albertus-Magnus-Platz",
            "Irish Math. Soc. Bulletin",
            "Graduate School of Humanities",
            "School of Foreign Languages",
            "Academic Center for Computing and Media Studies",
            "edu Joseph E. Hollingsworth Department of Computer Science Indiana University Southeast",
            "Transport'end Road Research Laboratory",
            "Transportation Research Group",
            "University of Southampton",
            "Department of Computer Science",
            "Faculty of Rural and Surveying Engineering National Technical University of Athens",
            "Computer Technology Institute University of Patras BOX",
            "The Center for Plasma Edge Simulation Workflow Requirements",
            "Australian National University January",
            "California Institute of Technology",
            "Cognitive Science University of California",
            "Center for Research in Language Newsletter",
            "University of California",
            "Neurology C. University of Chicago Press",
            "Oxford University Press",
            "California Institute of Technology Pasadena",
            "Marta Kutas Department of Cognitive Science",
            "Duke University Medical Center Durham",
            "Center for Non-linear Studies",
            "Ohio State University Cognitive Science Group",
            "Carnegie-Mellon University Psychology Department",
            "Salk Institute for Biological Studies",
            "Princeton University Psychology Department",
            "California Institute of Technology",
            "University of Pittsburgh",
            "Baylor School of Medicine",
            "Smith-Kettlewell Institute of Eye Research",
            "Berkeley Vision Group",
            "University of Florida Brain Institute",
            "California Institute of Technology",
            "Institute for the Study of Man",
            "Laboratory Neuroinformatics",
            "American Physiological Society",
            "LSE Economics Department",
            "The Department of Health",
            "British Thoracic Society",
            "Institute Gustave Roussy",
            "Network Working Group Request for Comments",
            "The Internet Society",
            "Technion - Israel Institute of Technology",
            "Lawrence Livermore National Laboratory",
            "Electric Power Research Institute",
            "Society for Industrial and Applied Mathematics",
            "Bartlesville Energy Technology Center",
            "Innovative Science and Technology Office",
            "DeepLook Research Consortium",
            "Pontificia Universidad Católica de Puerto Rico",
            "Seminario Evangélico de Puerto Rico"
            ]
    print "\n\n"
    l = 0
    #for pp in orgs:
    #    if len(unicode(pp, encoding='utf-8')) > l: l = len(pp)
    #for o in orgs:
    #    print o, (l - len(unicode(o, encoding='utf-8'))) * " ", " ---> ", Normalize.organization(o)


    publ = [
    'THE FINE-GRAINED SCALABLE VIDEO CODING BASED ON MATCHING PURSUITS',
    'KP-Lab D5.8 Prototype of the Knowledge Matchmaker (V.2.0)',
    'Adaptace a integrace open-source LMS a Informačního systému Masarykovy univerzity v Brně',
    'Simulation of Queuing Systems using QS_PN_Simulation tool',
    'Joint angle and delay estimation (JADE) for multipath signals arriving at an antenna array',
    'Coding of moving pictures and associated audio for storage at up to about 1.5 Mbit/s',
    'BUT System for NIST STD 2006 - Arabic'
    ]

    event = [
    'Proc. Nat. Telecommun. Conf.',
    'IEEE Trans. Commun.',
    'Proc. SPIE: Visual Communications and Image Processing92',
    'IEEE Trans. Circuits Syst. Video Technol.',
    'IEEE Trans. Aermp. Electronic Syst.',
    'Proceedings of ICASSP',
    'IEEE Transaction on Speech and Audio Processing',
    'Proceedings of Oriental COCOSDA workshop',
    'Proc. NIST SPoken Term Detection Evaluation workshop (STD 2006)',
    'Proceedings of the Ninth International Conference on Text',
    'Proc. IEEE Workshop on Signal Processing Applications for Public Security and Forensics, 2007 (SAFE \'07)',
    'Interspeech\'2005 - Eurospeech - 9th European Conference on Speech Communication and Technology',
    '2nd Joint Workshop on Multimodal Interaction and Related Machine Learning Algorithms, Edinburgh',
    'Proceedings of the 11th Annual Conference of the International Speech Communication Association (INTERSPEECH 2010)',
    'Sborník databázové konference DATAKON 2005',
    'AMI Workshop',
    'Proceedings of NGWS2009',
    'Proceedings of 38th International Conference MOSIS\'04',
    'DuD - Datenschutz und Datensicherheit',
    'Proc. in 15th Annual Symp. Intl. on Cornput. Architecture',
    'in Proceedings of the 20th annual international ACM SIGIR conference on Research and development in information retrieval',
    'Papers presented at the 31st Annual Meeting of the International Society for General System Research.',
    'Proc. 35th Annual Meeting of the Association for Computational Linguistics and 8th Conference of Computational Linguistics',
    'Fourteenth Annual Conference, 224240. Lecture Notes in Articial Intelligence 2111',
    'Proc. of ISTs 48th Annual Conference',
    'Paper presented at the 22nd Annual ACM Conference on Research and Development in Information Retrieval',
    'of the 21st Annual Meeting of the Association for Computational Linguistics',
    'In Computational Learning Theory: Proceedings of the Fourth Annual Workshop',
    'In Proceedings of the 82nd Annual Transportation Research Board',
    'in Proceedings of the international conference on formal ontology and information systems (FOIS01)',
    'in Proceedings of the IJCAI01 workshop on ontologies and information sharing',
    'In Online proceedings of TREC-5 (1996)',
    'in Proc. IEEE Workshop HigherOrder Statistics',
    'Time Frequency and Time Scale workshop',
    '6th Int. Workshop on Temporal Representation and Reasoning (TIME)'
    ]
    print "\n\n"
    l = 0
    for pp in publ:
        if len(unicode(pp, encoding='utf-8')) > l: l = len(pp)
    for p in publ:
        print p, (l - len(unicode(p, encoding='utf-8'))) * " ", " ---> ", Normalize.publication(p)


    for pp in event:
        if len(unicode(pp, encoding='utf-8')) > l: l = len(pp)
    print "\n\n"
    for e in event:
        print e, (l - len(unicode(e, encoding='utf-8'))) * " ", " ---> ", Normalize.event(e)
