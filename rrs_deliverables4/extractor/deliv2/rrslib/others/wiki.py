#! /usr/bin/python

"""
Wiki module implements API for manipulation with NLP-wiki, downloading and uploading
wiki sources and source editing. The module contains also XUnitXML2WikiConverter
which converts xunit XML format into wiki-source, so we can easily upload results
of testing (nosetests --with-xunit) on nlp-wiki

This module contains classes:
 * NLPWiki - wiki abstraction, methods for logging in, getting and saving pages/
 * WikiSource - Wiki source code with methods to edit it.
 * WikiPage - abstraction of wiki page
 * XUnitXML2WikiConverter - converter from xunit xml into wiki source code
"""


import urllib2
import lxml.html as lh
import cookielib
import lxml.etree as etree
import os.path
import datetime
import httplib


__modulename__ = "wiki"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$27.1.2011 17:51:05$"


# TODO's:
# more methods for manipulation with WikiSource


class WikiException(Exception):
    """
    Base class for all wiki exceptions.
    """
    pass

# ------------------------------------------------------------------------------
# end of class WikiException
# ------------------------------------------------------------------------------


class WikiSource(object):
    """
    WikiSource represents source code interpreted by mediawiki. Class implements
    also methods form creating the source.
    """
    def __init__(self, src=""):
        if not isinstance(src, basestring):
            raise WikiException("source code has to be type string or unicode.")
        self.src = src

    def header(self, level, hdrtext):
        if not isinstance(level, int):
            raise TypeError("Header level has to be integer")
        hdrcnt = "="*level
        self.src += hdrcnt + str(hdrtext) + hdrcnt + "\n"

    def raw_text(self, text):
        self.src += str(text)

    def newline(self):
        self.src += "<br />\n"

    def link(self, link, linktext):
        self.src += "[[%s|%s]]" % (link, linktext)

    def _list(self, l, initial):
        for item in l:
            self.src += "%s %s\n" % (initial, item)

    def ordered_list(self, content_list):
        self._list(content_list, "#")

    def unordered_list(self, content_list):
        self._list(content_list, "*")

    def table(self, matrix):
        table = '{| class="wikitable" border="1"\n'
        for row in matrix:
            table += "|-\n"
            for cell in row:
                table += "| %s\n" % cell
        table += "|}"
        self.src += table

    def code(self, code):
        self.src += "<pre>\n%s\n</pre>\n" % code

    def erase(self):
        self.src = ""

    def __str__(self):
        if self.src is None:
            return ""
        return self.src

# ------------------------------------------------------------------------------
# end of class WikiSource
# ------------------------------------------------------------------------------


class NLPWiki(object):
    """
    NLPWiki implements methods for manipulation with nlp-wiki - basic
    authentication (login), loading and saving pages and editing them.
    """
    def __init__(self, versbosity=0):
        self._verbosity = versbosity
        self._print("Initializing NLPWiki..            [ OK ]", 3)
        self._user = None
        self._password = None
        self._nlp_wiki_url = "https://merlin.fit.vutbr.cz/nlp-wiki/index.php"
        # this creates a password manager
        self._passmgr = urllib2.HTTPPasswordMgrWithDefaultRealm()


    def _print(self, msg, v):
        if self._verbosity >= v:
            print msg


    def login(self, username=None, password=None):
        """
        Log into nlp-wiki. If login wasnt successful, raises an Exception and
        print login and password data.
        @param username - login
        @param password - password to nlp-wiki
        """
        if username is None or password is None:
            raise ValueException("You have to specify your login and password to nlp-wiki.")
        self._user = username
        self._password = password
        self._passmgr.add_password(None, self._nlp_wiki_url, username, password)
        # create the AuthHandler
        self._authhandler = urllib2.HTTPBasicAuthHandler(self._passmgr)
        cj = cookielib.CookieJar()
        self._cookieproc = urllib2.HTTPCookieProcessor(cj)
        self._print("Logging in...", 1)
        # build opener and install it to urllib2 so we can use it without opener.urlopen
        self._opener = urllib2.build_opener(self._authhandler, self._cookieproc)
        try_it = urllib2.Request(self._nlp_wiki_url)
        try:
            self._opener.open(try_it)
            self._print("Logged in...                      [ OK ]", 1)
        except urllib2.URLError, e:
            raise WikiException(e)
        except httplib.HTTPException, e:
            raise WikiException(e)
        finally:
            self._print("  login was: %s" % self._user, 1)
            self._print("  password was: %s" % self._password, 1)


    def get_page(self, name):
        """
        Get wiki page by selected name.
        @return WikiPage instance with all data - page content and edit hashes.
        @param name - name of wiki page (for example "Reresearch")
        """
        query = "?title=%s&action=edit" % name
        url = self._nlp_wiki_url + query
        request = urllib2.Request(url)
        # Actually do the request, and get the response
        self._print("Downloading page %s ..." % name, 3)
        wiki_handle = self._opener.open(request)
        self._print("Done.", 3)
        # parse the tree and harvest input filend so insert into post
        tree = lh.parse(wiki_handle)
        #form = tree.find(".//form")
        inputs = tree.findall(".//input")
        textarea = tree.find(".//textarea") # "wpTextbox1"

        # Handle data to send by POST request
        tt = textarea.text
        if tt is None: tt = ""
        post_data = {"wpTextbox1" : WikiSource(tt)}
        for i in inputs:
            n = i.get("name")
            if not n.startswith("wp"):
                continue
            if n in ("wpDiff", "wpPreview", "wpWatchthis"):
                continue
            post_data[n] = i.get("value")
        w = WikiPage(name, post_data)
        w.__downloaded = True
        return w


    def _encode_multipart_formdata(self, fields):
        """
        Translate post data into form-data format.
        Fields is a sequence of (name, value) elements for regular form fields.
        @return (content_type, body) ready for httplib.HTTP instance
        @param fields - fields to insert in POST request
        """
        BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
        CRLF = '\r\n'
        L = []
        for key in fields:
            value = str(fields[key])
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return (content_type, body)


    def save_page(self, wikipage):
        """
        Save wiki page. It overwrites previous content no matter what you write
        on the page.
        @param wikipage - instance of WikiPage which has to be saved
        @return file-like handle of request
        @raises AttributeError if needed POST data are missing
        """
        self._print("Checking form-data...", 3)
        # check if it is downloaded wiki page
        if not wikipage.__downloaded:
            for key in ('wpEdittime', 'wpSave', 'wpStarttime', 'wpScrolltop',
                        'wpTextbox1', 'wpAutoSummary', 'wpSection',
                        'wpEditToken', 'wpSummary'):
                if not key in wikipage._edit_form_data:
                    raise AttributeError("Wiki page has to contain all POST data "\
                                         "needed to finish the request. Missing: %s" % key)
        content_type, body = self._encode_multipart_formdata(wikipage._edit_form_data)
        # create submitting url (form-action)
        query = "?title=%s&action=submit" % wikipage.name
        urlsubmit = self._nlp_wiki_url + query
        # create POST request with encoded body
        request = urllib2.Request(urlsubmit, body)
        # set appropriate content_type
        request.add_header('Content-Type', content_type)
        # make prev url as referer
        query = "?title=%s&action=edit" % wikipage.name
        urlref = self._nlp_wiki_url + query
        request.add_header('Referer', urlref)
        request.add_header('Content-Length', str(len(body)))
        # we are for example Google Chrome
        request.add_header('User-Agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US)'\
        ' AppleWebKit/534.10 (KHTML, like Gecko) Chrome/8.0.552.237 Safari/534.10')
        self._print("Saving wiki page %s..." % wikipage.name, 3)
        reply = self._opener.open(request)
        self._print(reply.info(), 3)
        return reply

# ------------------------------------------------------------------------------
# end of class NLPWiki
# ------------------------------------------------------------------------------


class WikiPage(object):
    """
    Abstraction of wiki page and it's content.

    If you want to edit some page, you have to gain edit data (edit hash etc.)
    at first, so the procedure is:
    1. download te wiki page using NLPWiki.get_page()
    2. do some stuff in the source (editing, eraising..) - WikiPage.get_source()
    3. insert new source int the page - WikiPage.set_source()
    4. upload page on wiki: NLPWiki.save_page()
    """
    def __init__(self, name,  post_data):
        self.name = name
        self._edit_form_data = post_data
        self.__downloaded = False


    def get_source(self):
        """
        Returns wiki source code from the page.
        """
        return self._edit_form_data["wpTextbox1"]


    def set_source(self, src, minor_edit=False):
        """
        @param src instance of WikiSource
        @param minor_edit - is this minor edit on the page?
        """
        if not isinstance (src, WikiSource):
            raise TypeError("Source has to be type WikiSource.")
        self._edit_form_data["wpTextbox1"] = src
        if minor_edit:
            self._edit_form_data['wpMinoredit'] = '1'
        else:
            self._edit_form_data['wpMinoredit'] = '0'

# ------------------------------------------------------------------------------
# end of class WikiPage
# ------------------------------------------------------------------------------


class XUnitXML2WikiConverter(object):
    """
    This converter translates XML

    TODO: THIS CLASS HAS TO BE ENLARGED. IT DOESN'T HANDLE EVERY TYPE OF XUNIT XML!
    """
    def __init__(self):
        self.etree = None
        self.wikisource = WikiSource()


    def _get_tag_params(self, paramlist, tag):
        paramval = []
        for x in paramlist:
            if tag.get(x) is not None:
                paramval.append(x+": "+tag.get(x))
        return paramval


    def _parse_xml(self):
        testsuite = self.etree.getroot()
        self.wikisource.header(2, testsuite.get("name"))
        suiteparams = ("tests", "errors", "failures", "time", "skip")
        self.wikisource.unordered_list(self._get_tag_params(suiteparams, testsuite))
        for testcase in testsuite.iterchildren():
            self.wikisource.newline()
            self.wikisource.header(3, testcase.get("classname"))
            self.wikisource.unordered_list(self._get_tag_params(("name", "time"), testcase))
            try:
                self.wikisource.header(4, testcase[0].get("type"))
                self.wikisource.unordered_list(self._get_tag_params(["message"], testcase[0]))
                self.wikisource.code(testcase[0].text)
            except: pass


    def _parse_folder_name(self, path_to_file):
        path = os.path.dirname(path_to_file)
        folder = path.split("/")[-1]
        timestamp, branch = folder.split("_")
        branch = branch.split(".")[0]
        timestamp = str(datetime.datetime.fromtimestamp(float(timestamp)))

        self.wikisource.erase()
        self.wikisource.header(1, "Rrs_library test output")
        self.wikisource.unordered_list(["repository: rrslib.git",
                                        "branch: "+branch,
                                        "time: "+timestamp])
        self.wikisource.newline()


    def convert(self, xunitfile):
        """
        Converts XML in xunit format into wikipedia source code which can be
        uploaded to nlp-wiki.
        @param xunitfile - path to xml file to be converted
        @return instance of WikiSource
        """
        self._parse_folder_name(xunitfile)
        fh = open(xunitfile, 'r')
        self.etree = etree.parse(fh)
        fh.close()
        self._parse_xml()
        return self.wikisource

# ------------------------------------------------------------------------------
# end of class XUnitXML2WikiConverter
# ------------------------------------------------------------------------------
