#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module mime creates interface for handling MIME types, especially content-type,
which is the most important for web-extractors in RRS and for downloading in general.
"""


__modulename__ = "mime"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$31-May-2010 9:48:01$"


from urlparse import urlsplit
from urlparse import urlparse
import httplib
import threading
import thread
import re
import mimetypes


# import MAX_THREADS constant
from crawler import MAX_THREADS

mime_types_map_exclusive = {'mny': 'application/x-msmoney',
'rtf': 'application/rtf', 'scd': 'application/x-msschedule',
'gz': 'application/x-gzip', 'sct': 'text/scriptlet',
'pko': 'application/ynd.ms-pkipko', 'lsx': 'video/x-la-asf',
'wrl': 'x-world/x-vrml', 'wri': 'application/x-mswrite',
'fif': 'application/fractals', 'wma': 'audio/x-ms-wma',
'clp': 'application/x-msclip', 'wmf': 'application/x-msmetafile',
'sst': 'application/vnd.ms-pkicertstore', 'p10': 'application/pkcs10',
'lzh': 'application/octet-stream', 'cer': 'application/x-x509-ca-cert',
'mpp': 'application/vnd.ms-project', 'hqx': 'application/mac-binhex40',
'xlm': 'application/vnd.ms-excel', 'trm': 'application/x-msterminal',
'bas': 'text/plain', 'crt': 'application/x-x509-ca-cert',
'xlc': 'application/vnd.ms-excel', 'xla': 'application/vnd.ms-excel',
'evy': 'application/envoy', 'crd': 'application/x-mscardfile',
'stm': 'text/html', 'xlw': 'application/vnd.ms-excel',
'xlt': 'application/vnd.ms-excel', 'crl': 'application/pkix-crl',
'jfif': 'image/pipeg', 'pmw': 'application/x-perfmon',
'htc': 'text/x-component', 'pmr': 'application/x-perfmon',
'mdb': 'application/x-msaccess', 'hlp': 'application/winhlp',
'htt': 'text/webviewhtml', 'pma': 'application/x-perfmon',
'pmc': 'application/x-perfmon', 'pml': 'application/x-perfmon',
'rmi': 'audio/mid', 'uls': 'text/iuls', 'ico': 'image/x-icon',
'xof': 'x-world/x-vrml', 'dms': 'application/octet-stream',
'asr': 'video/x-ms-asf', 'asp': 'text/html', 'cmx': 'image/x-cmx',
'pub': 'application/x-mspublisher', 'asf': 'video/x-ms-asf',
'dcr': 'application/x-director', 'wdb': 'application/vnd.ms-works',
'm3u': 'audio/x-mpegurl', 'isp': 'application/x-internet-signup',
'mvb': 'application/x-msmediaview', 'cod': 'image/cis-cod',
'xul': 'application/vnd.mozilla.xul+xml', 'lsf': 'video/x-la-asf',
'acx': 'application/internet-property-stream', 'tgz': 'application/x-compressed',
'dir': 'application/x-director', 'm13': 'application/x-msmediaview',
'm14': 'application/x-msmediaview', 'hta': 'application/hta',
'setpay': 'application/set-payment-initiation', 'svg': 'image/svg+xml',
'setreg': 'application/set-registration-initiation', 'xaf': 'x-world/x-vrml',
'ogg': 'application/ogg', 'ins': 'application/x-internet-signup',
'iii': 'application/x-iphone', 'asx': 'video/x-ms-asf',
'stl': 'application/vnd.ms-pkistl', 'aspx': 'text/html',
'der': 'application/x-x509-ca-cert', 'flr': 'x-world/x-vrml',
'cat': 'application/vnd.ms-pkiseccat', 'pot,': 'application/vnd.ms-powerpoint',
'spl': 'application/futuresplash', 'z': 'application/x-compress',
'prf': 'application/pics-rules', 'p7r': 'application/x-pkcs7-certreqresp',
'p7s': 'application/x-pkcs7-signature', 'dxr': 'application/x-director',
'mpv2': 'video/mpeg', 'p7b': 'application/x-pkcs7-certificates',
'wks': 'application/vnd.ms-works', 'spc': 'application/x-pkcs7-certificates',
'wrz': 'x-world/x-vrml', 'shtml': 'text/html', 'p7m': 'application/x-pkcs7-mime',
'sit': 'application/x-stuffit', 'mid': 'audio/mid', '323': 'text/h323',
'xhtml': 'application/xhtml+xml', 'csv': 'text/csv',
'wcm': 'application/vnd.ms-works', 'vrml': 'x-world/x-vrml',
'wps': 'application/vnd.ms-works', 'jsp': 'text/javascript',
'php': 'application/x-httpd-php', 'class': 'application/octet-stream',
'axs': 'application/olescript', 'lha': 'application/octet-stream'}



class MIMEError(Exception):
    def __init__(self, msg=None, url=None):
        self.msg = msg
        self.url = url

    def __str__(self):
        if self.url is None:
            return "%s" % self.msg
        return "%s occured on %s" % (self.msg, self.url)

# ------------------------------------------------------------------------------
# end of class MIMEError
# ------------------------------------------------------------------------------

class GetContentTypeThread(threading.Thread):
    """
    Mime handler thread.
    """
    def __init__(self, url):
        # invoke thread constructor
        threading.Thread.__init__(self)

        # init url
        self.url = url
        self._http()

        # result
        self.content_type = None


    def _http(self):
        if self.url.startswith("www."):
            self.url = "http://" + self.url


    def suffix2mime(self, suff):
        """
        Function mapping suffix of file to content-type header
        """
        if suff in mime_types_map_exclusive:
            return mime_types_map_exclusive[suff]
        return None


    def run(self):
        """
        Returns MIME content-type
        """
        u = urlparse(self.url)
        if u.query == '':
            suffix = re.search(r'(?<=\.)[^/\.]+$', u.path)
        else:
            suffix = False
        # if got suffix, return content-type mapped in mime_types_map_exclusive dictionary
        # or in mimetypes.types_map
        if suffix:
            self.content_type, encoding = mimetypes.guess_type(self.url, strict=False)
            if self.content_type is None:
                self.content_type = self.suffix2mime(suffix.group(0))
        # if url has not any suffix i.e.: http://www.universityc.com/~jim-barkley/
        # ask server for mime (HEAD request)
        else:
            self.content_type = self._ask_server()


    def _ask_server(self):
        """
        Ask server for file type
        """
        spliturl = urlsplit(self.url)
        # make HEAD request
        try:
            conn = httplib.HTTPConnection(spliturl[1])
        except:
            return None
        try:
            conn.request("HEAD", "/" + spliturl[2] + "?" + spliturl[3])
        except:
            return None
        try:
            header = conn.getresponse()
        except:
            return None
        # try to get the suffix from the content-disposition header field
        cont_disp = header.msg.getheader('Content-Disposition')
        if cont_disp is not None and "filename=" in cont_disp:
            try:
                sp = cont_disp.split("filename=")
                content_type, encoding = mimetypes.guess_type(sp[1], strict=False)
                if content_type is not None:
                    return content_type
                suffix = re.search(r'(?<=\.)[^/\.]+$', sp[1])
                _type = self.suffix2mime(suffix.group(0))
                if _type is not None:
                    return _type
            except:
                pass
        # get header message but return only MIME type
        return header.msg.gettype()


    def __getresult__(self):
        """
        Get result
        """
        if self.content_type != None: return self.content_type
        else: return False


# ------------------------------------------------------------------------------
# end of class GetContentTypeThread
# ------------------------------------------------------------------------------

class MIMEHandler:
    def __init__(self):
        self.ctthreads = [] # threads
        self.ctlist = {} # results


    def __getresult(self):
        """
        Get result and delete self.ctthreads
        """
        if len(self.ctlist) == 0:
            return None
        l = self.ctlist
        self.ctlist = {}
        del self.ctthreads[:]
        return l


    def start(self, url_list):
        """
        Start threads to retrieve content-types of urls from url_list
        """
        if not getattr(url_list, '__iter__', False) or isinstance(url_list, basestring):
            raise MIMEError(msg="Parameter url_list has to be type list, tuple or set")
        for url in url_list:
            thrd = GetContentTypeThread(url)
            # keep a list all threads
            self.ctthreads.append(thrd)
            thrd.name = url

            while 1:
                # reduce max threads to 30
                if threading.activeCount() > MAX_THREADS:
                    time.sleep(2)
                    continue
                try:
                    thrd.start()
                    break
                except thread.error:
                    # wait for end of some thread
                    time.sleep(2)

        # wait for all threads to finish
        for th in self.ctthreads:
            th.join()
            self.ctlist[th.name] = th.__getresult__()

        return self.__getresult()

# ------------------------------------------------------------------------------
# end of class MIMEhandler
# ------------------------------------------------------------------------------

# XXX for backward compatibility
MIMEhandler = MIMEHandler
