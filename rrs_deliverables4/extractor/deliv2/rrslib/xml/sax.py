#! /usr/bin/python

"""
This module contains support handlers for SAX-oriented XML manipulation.
Classes:
 - BufferedSAXContentHandler - simple XML handler writing into tempfile
 - SAXContentWriter - advanced sax writer with some more features (comments,
   context-holding..)
"""

__modulename__ = "sax"
__author__="Stanislav Heller"
__email__="xhelle03@stud.fit.vutbr.cz"
__date__ ="$30.1.2011 20:29:21$"


from xml.sax._exceptions import SAXException
from xml.sax import saxutils
import xml.sax.handler as saxhandler
import tempfile
from xml.sax import SAXException
import os
import sys
import StringIO
import re
import codecs

class BufferedSAXContentHandler(saxhandler.ContentHandler):
    """
    Very simple buffered SAX handler. It writes input into temporary file
    created as tempfile.TemporaryFile().
    """
    def __init__(self):
        saxhandler.ContentHandler.__init__(self)
        self._f = tempfile.TemporaryFile(mode='w+b',
                                         bufsize=-1,
                                         suffix=".tmp",
                                         prefix=".rrslib_sax_",
                                         dir="/tmp/")

    # ContentHandler methods

    def startDocument(self):
        self._f.write('<?xml version="1.0" encoding="utf-8"?>\n')

    def startElement(self, name, attrs):
        self._f.write('<' + name)
        for (name, value) in attrs.items():
            self._f.write(' %s="%s"' % (name, re.sub("\"", "&quot;", saxutils.escape(value))))
        self._f.write('>')

    def endElement(self, name):
        self._f.write('</%s>' % name)

    def characters(self, content):
        self._f.write(saxutils.escape(saxutils.escape(content)))

    def ignorableWhitespace(self, content):
        self._f.write(content)

    def processingInstruction(self, target, data):
        self._f.write('<?%s %s?>' % (target, data))


class SAXContentWriter(BufferedSAXContentHandler):
    """
    Advanced buffered SAX writer. Violating some manners of usual SAX handlers.
    Features:
     - comments
     - context-holding
     - easy endElement() with no param
     - easy endDocument()
     - printing actual content of buffer
    """
    def __init__(self, output=None):
        BufferedSAXContentHandler.__init__(self)
        self._outfile = False
        if output is not None:
            if isinstance(output, StringIO.StringIO):
                self._f = output
            elif output in (sys.stdout, sys.stderr):
                encoding = output.encoding
                if encoding is None:
                    encoding = 'utf-8'
                streamwriter = codecs.getwriter(encoding)
                self._f = streamwriter(output)
            else:
                self._f = codecs.open(output, encoding='utf-8', mode='wb')
            self._outfile = True
        self._end = False
        self._opened_elements = []
        self._empty = True
        self._started = False


    def _escape(self, s):
        s = re.sub("\"", "&quot;", saxutils.escape(s))
        return re.sub("'", "&apos;", s)


    def startElement(self, name, attrs={}):
        if self._end:
            raise SAXException("Cannot write into finished document.")
        if self._started:
            self._f.write('>')
        self._f.write('<%s' % self._escape(name))
        for (attr, value) in attrs.items():
            self._f.write(' %s="%s"' % (attr, self._escape(value)))
        self._opened_elements.append(name)
        self._empty = True
        self._started = True

    def endElement(self):
        if self._end:
            raise SAXException("Cannot write into finished document.")
        if not self._opened_elements:
            raise SAXException("Cannot close element. No elements are opened.")
        name = self._opened_elements.pop()
        if self._empty:
            self._f.write('/>')
        else:
            self._f.write('</%s>' % self._escape(name))
        self._empty = False
        self._started = False

    def characters(self, content):
        if self._started:
            self._f.write('>')
        self._f.write(saxutils.escape(content))
        self._empty = False
        self._started = False

    def ignorableWhitespace(self, content):
        if self._started:
            self._f.write('>')
        self._f.write(self._escape(content))
        self._empty = False
        self._started = False

    def comment(self, content):
        if self._started:
            self._f.write('>')
        self._f.write("<!-- %s -->\n" % content)
        self._empty = False
        self._started = False

    def getFileobj(self):
        return self._f

    def print_content(self):
        self._f.seek(0)
        print self._f.read()
        self._f.seek(0, os.SEEK_END)

    def get_opened_elements(self):
        return self._opened_elements

    def destroy(self):
        if self._outfile:
            raise SAXException("Calling destroy() is allowed only on sax handler bound to tempfile.")
        self._f.close()
        self._end = True
        self._opened_elements = []

    def endDocument(self):
        for x in range(len(self._opened_elements)):
            self.endElement()
        self._end = True
        self._f.write("\n") # add endline



#-------------------------------------------------------------------------------
# End of SAX classes
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    b = SAXContentWriter()
    b.startDocument()
    b.startElement("ahoj", {"jenda": "1"})
    b.characters("Neco uzasnyho")
    b.startElement("ukaz")
    b.endElement()
    b.startElement("asdf", {})
    b.endElement()
    b.endElement()
    b.startElement("asdf", {})
    b.startElement("asdf", {})
    b.startElement("asdf", {})
    b.endDocument()
    b.print_content()
