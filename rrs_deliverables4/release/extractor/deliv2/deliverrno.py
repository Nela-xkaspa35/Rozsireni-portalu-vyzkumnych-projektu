#!/usr/bin/env python
# -*- coding: utf-8 -*-

# deliverrno.py

# constants
EUNKNOWN = -1 # unknown error
ESTART = 100 # delimiter
EBADLINK = 101 # bad link format //module getdeliverablerecords
ENOREG = 102 # no region found //module getdeliverablerecords
ENODOC = 103 # no document on page identified as deliverable page //module getdeliverablerecords
ENOREC = 104 # no records found //module getdeliverablerecords
EXML = 105 # no input to xml //module deliverables
ESEQ = 106 # sequence not found // module getdeliverablerecords
ELNOTFOUND = 107 # no deliverable link found // module getdelivpage
EWIENORUL = 108 # no url leading to document in record // module webinfoextraction
EEND = 109

# message dictionary
_err = {
-1: 'Unknown error',
101: 'Error while searching data region: Bad link.',
102: 'Error while searching data region: Cannot find data region',
103: 'Error while recognizing data region: No documents found on deliverable page.',
104: 'Error while harvesting data records: No records found.',
105: 'Error while transforming to XML: Input dictionary not found.',
106: 'Error while harvesting data records: Cannot catch tag sequence.',
107: 'Error while searching deliverable page: Deliverable page not found.',
108: 'Error while text recognizing: No URL found in each record. Records identified as useless.'
}

def __err__(errno, *args):
    if type(errno) == int:
        try:
            msg = _err[errno]
            if len(args) == 0:
                return (-1, msg)
            else:
                return (-1, msg, " ".join(args))
        except:
            return (-2, _err[EUNKNOWN])
    elif type(errno) == str:
        return (-1, errno)
    else:
        return (-2, _err[EUNKNOWN])


