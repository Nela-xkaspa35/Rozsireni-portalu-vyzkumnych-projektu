#!/usr/bin/env python
# -*- coding: utf-8 -*-

# rrsregex library.
# location: rrslib/extractors/rrsregex.py

"""
This library contains multi-purpose regular expressions for identifying various
entities in text.

When importing this module, it's better to use it like module.RE, not importing
the exact regular expression, because of unspecific identifiers (the "re" at the
end isnt the most transparent identificator).

The best way to use is like this:

# import libraries
import rrsregex
import re
# some example of usage
re.search(rrsregex.IPADDRre, "192.168.0.1")

"""


__modulename__ = "rrsregex"
__author__ = "http://regexlib.com/, Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$19-June-2010 11:51:19$"


URLre = '(http|https|ftp)' \
        '\://[A-Za-z0-9\-\.]+\.[a-z]{2,3}(:[A-Za-z0-9]*)?/?' \
        '([A-Za-z0-9\-\._\?\,\'/\\\+&;%\$#\=~])*'


# IPv4 (32bit!) regex.
IPADDRre = '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9])\.'\
           '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.'\
           '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[1-9]|0)\.'\
           '(25[0-5]|2[0-4][0-9]|[0-1]{1}[0-9]{2}|[1-9]{1}[0-9]{1}|[0-9])'


# E-mail regex.
# if you are looking for system to get emails from page, look at class
# rrslib.extractors.entityextractor.EmailSearch
EMAILre = '[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~-]+)*'\
          '@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+(?:[a-zA-Z]{2}|aero|'\
          'asia|biz|cat|com|coop|edu|gov|info|int|jobs|mil|mobi|museum|name|net|org|pro|tel|travel)'


# simple regex for searching ISBN numbers.
ISBNre = '[Ii][sS][bB][nN]\x20(\d{1,5}([- ])\d{1,7}([- ])\d{1,6}([- ])(\d|X))'


if __name__ == '__main__':
    import re
    print "testing rrsregex library..."

    print "testing URL re:"
    urls = ['http://www.google.com', 'ftp:/neco.com', 'google.com', 'www.seznam.cz', \
            'http://regexlib.com/UserPatterns.aspx?authorId=a31a0874-118f-4550-933e-a7c575d149ae']
    for u in urls:
        r = re.search(URLre, u, re.I)
        if r:
            print '    ', r.group(0)


    print "testing IP re:"
    ips = ['1.1.1.1', '256.0.0.0', '255.255.255.26', '456.0.13.4', '10.0.0.1']
    for i in ips:
        r = re.search(IPADDRre, i)
        if r:
            print '    ', r.group(0)


    print 'testing EMAIL re:'
    mails = ['rahman@geekshop.mail.com', 'rahman.geek@gmail.com', 'rahman..@mail.com', 'ra@g.c']
    for m in mails:
        #print EMAILre
        r = re.search(EMAILre, m, re.I)
        if r:
            print '    ', r.group(0)


    print 'testing ISBN re:'
    isbns = ['ISBN 85-359-0277-5', 'ASBN 0-8044-2957-3', 'ISBN 645-23-4886-4', \
             'Issn 960-425-059-0', 'ISBN 468-21354-2']
    for ii in isbns:
        r = re.search(ISBNre, ii)
        if r:
            print '    ', r.group(0)


