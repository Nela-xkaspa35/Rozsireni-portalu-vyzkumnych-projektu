#!/usr/bin/env python 
# -*- coding: utf-8 -*-

## deliverables debugging class

import sys, re, unicodedata

class DeliverableDebugger():
    """To set debug flag false start with an -O option"""
    def __init__(self, verbose=False, debug=False):
        self.__verbose__ = verbose
        self.__debug     = debug
        
        # set error messages
        self._errv = "cannot decode verbose message."
        self._errd = "cannot decode debug info."
        
        # checking data types
        if not type(self.__verbose__) == bool:
            raise ValueError("Verbose flag has to be boolean.")
            

    def _format(self, data):
        # endcode
        encode_flag = False
        for chset in ('iso-8859-2', 'cp1250', 'iso-8859-1', 'utf-16'):
            try:
                data = data.decode(chset).encode('utf-8')
                encode_flag = True
                break
            except:
                continue
        # normalize
        if encode_flag:
            data = unicode(data, 'utf-8')
            data = unicodedata.normalize('NFKD', data)
        return data

    # all messages are printed to standard error stream stderr
    """ verbose - used for listing common process states """
    def verbose(self, msg):
        if self.__verbose__ == True:
            try:
                sys.stderr.write(self._format(msg)+'\n')
                sys.stderr.flush()
            except:
                sys.stderr.write(self._errv+'\n')


    """ debug - listing detailed process states """
    def debug(self, msg):
        if self.__debug == True:
            try:
                sys.stderr.write("Debug message:    "+self._format(msg)+'\n')
                sys.stderr.flush()
            except:
                sys.stderr.write(self._errd+'\n')
# end of class DeliverableDebug

if __name__ == '__main__':
    debugger = DeliverableDebugger(verbose = True,debug = True)
    __verbose = debugger.verbose
    
