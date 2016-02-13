#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module improves previous scripts make_dict and make_list and creates common
library for creating rrs dictinaries.

Usage of this module is described in docstring of RRSDictionaryCreator class.
"""


__modulename__ = "rrsdictcreator"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$9-September-2010 18:21:10$"

import cPickle
import re
import os
import sys
from rrslib.others.progressbar import ProgressBar


DTYPE_LIST = 0
DTYPE_DICT = 1


class RRSDictionaryCreatorError(Exception):
    pass

#-------------------------------------------------------------------------------
# End of class RRSDictionaryCreatorError
#-------------------------------------------------------------------------------


class RRSDictionaryCreator(object):
    """
    RRSDictionaryCreator is a helper class for creating new dictinaries in
    rrslib. These dictinaries are cPickle-fashion and provide simple and quick
    API for searching in them.


    Usage (HOWTO create dictionary):
    # import this module
    from dictionaries import rrsdictcreator
    # create your own parsing function for one row of the file
    # the function has to return tuple (key, [value1, value2, ...])
    # where key is string and values is list of values (one value has to be list too!)
    def my_parse_fnc(x):
        s = x.split(" - ")
        return (s[0], map(lambda x: x.rstrip(\"\\r\\n\"), s[1:]))
    # mydict.txt contains dictionary of people (keys) and their phone numbers (values)
    try:
        dc = RRSDictionaryCreator("mydict.txt", "phonebook", DTYPE_DICT)
        dc.set_parser(my_parse_fnc)
        dc.create()
    except RRSDictionaryCreatorError, errmsg:
        sys.stderr.write(errmsg)
    """

    def __init__(self, infile, dname, dtype):
        # open file
        try:
            self.fd = open(infile, 'r')
        except IOError, e:
            raise RRSDictionaryCreatorError(e)

        # get number of lines
        self.lines = sum([1 for line in self.fd])
        self.fd.seek(0)

        # name of the dictionary
        self.name = dname

        # path to dict's directory
        self.path = dname + "/"

        # type of the dictionary = "list"/"dict"
        if dtype not in (DTYPE_LIST, DTYPE_DICT):
            raise RRSDictionaryCreatorError("Directory has to be either type" \
                       " DTYPE_LIST or DTYPE_DICT. Use these constants, please.")
        self.type = dtype

        # init object variables (keys of dict, values, etc.)
        self.keys = []
        self.values = []
        self.d = {}
        for char in "abcdefghijklmnopqrstuvwxyz":
            self.d[char] = {}
        self.d["other"] = {}

        # regexp for searching keys in text
        self.regular_expression = "(?<![a-zA-Z0-9\-])("

        # flag idicating keys in "simple" form - that means: the key doesnt
        # contain any white character (\t\n<space> etc.)
        self.simplekeys = True

        # minimal key length
        self.minkey = sys.maxint


    def _dir_create(self):
        # create directory for dict
        if not os.path.isdir(self.name):
            try:
                os.mkdir(self.name)
            except Exception, e:
                self.fd.close()
                raise RRSDictionaryCreatorError(e)
        else:
            self.fd.close()
            raise RRSDictionaryCreatorError("Directory %s already exists" % self.name)


    def _dir_delete(self):
        try:
            os.rmdir(self.name)
        except OSError:
            pass
        except Exception, e:
            self.fd.close()
            raise RRSDictionaryCreatorError(e)



    def _close_regexp(self):
        """
        Closes regular expression, compiles it and dumps it into a pickle file.
        """
        if not self.simplekeys:
            # close the regular exptression ane compile it
            self.regular_expression = self.regular_expression.rstrip("|") + ")(?![a-zA-Z0-9\-])"
            compiled = re.compile(self.regular_expression)
            # and save it
            f_compiled = open(self.path + "keys_compiled.rrsdict", "wb")
            cPickle.dump(compiled, f_compiled)
            f_compiled.close()


    def _check_if_simplekey(self, key):
        if re.search("[ \"\(\)\[\]{}\,\.\+\!\?\:\;@#\$%\^&\*]", key):
            self.simplekeys = False


    def _save_dict_files(self):
        # save keys
        f_keys = open(self.path + "keys.rrsdict", "wb")
        self.keys.sort()
        cPickle.dump(self.keys, f_keys)
        f_keys.close()

        # if we converted dictionary key->values, not list, save all values and
        # python dictionaries into pickled file
        if self.type == DTYPE_DICT:
            # save values
            f_values = open(self.path + "values.rrsdict", "wb")
            self.values.sort()
            cPickle.dump(self.values, f_values)
            f_values.close()

            # save translation dictionaries
            for k in self.d:
                f_trans = open(self.path + "translate_" + k + ".rrsdict", "wb")
                cPickle.dump(self.d[k], f_trans)
                f_trans.close()

        # create dict.info (I know, this is ugly way, but pretty easy to write...:) )
        f_info = open(self.path + "dict.info", "w")

        if self.type == DTYPE_DICT: _type = "dict"
        else: _type = "list"

        f_info.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f_info.write('<rrsdictionary>\n')
        f_info.write('    <name value=\"' + self.name + '\"/>\n')
        f_info.write('    <type value=\"' + _type + '\"/>\n')
        f_info.write('    <keysize value=\"' + str(len(self.keys)) + '\"/>\n')
        f_info.write('    <valuesize value=\"' + str(len(self.values)) + '\"/>\n')
        f_info.write('    <min-key-length value=\"' + str(self.minkey) + '\"/>\n')
        f_info.write('    <simplekeys value=\"' + str(self.simplekeys) + '\"/>\n')
        f_info.write('</rrsdictionary>\n')


    #---------------------------------------------------------------------------
    # public methods
    #---------------------------------------------------------------------------

    def parse_row(self, row):
        s = row.split("-")
        return (s[0], map(lambda x: x.rstrip("\n"), s[1:]))


    def set_parser(self, func):
        self.parse_row = func


    def create(self, showprogress=True):
        """
        Create dictionary in order of selected type, name and file. Note, that
        you have to set row-parser (method set_parser(func)) to get result you want.

        Parameter showprogress: if True, shows progressbar while creating dictionary.
        """

        p = ProgressBar('green', width=40, block='▣', empty='□')

        # create directory for this dictionary
        self._dir_create()
        # read lines
        row = self.fd.readline()
        rownum = 1
        while row:
            if showprogress and rownum % 10 == 0:
                p.render(int(101*float(rownum)/float(self.lines)), 'step %s\nCreating dictionary %s...\n' %
                         (str(int(101*float(rownum)/float(self.lines))), self.name))
            # if we are in dict
            if self.type == DTYPE_DICT:
                try:
                    key, values = self.parse_row(row)
                except Exception, e:
                    raise RRSDictionaryCreatorError("Bad parsing function. Exception: "+str(e))
                assert type(key) == str, "Key has to be type string. Probably bad parsing function used."
                assert type(values) == list, "Values have to be list. Probably bad parsing function used."
            # list otherwise
            else:
                key = row.rstrip("\r\n")

            self._check_if_simplekey(key)
            #print key, values
            if self.type == DTYPE_DICT:
                # set start char (a-z or other)
                start_char = key[0].lower()
                if not start_char.isalpha():
                    start_char = "other"

                # if key doesnt exist in dictionary yet, add it
                if not key in self.d[start_char].keys():
                    self.d[start_char][key] = values
                # if it exists, extend values
                else:
                    self.d[start_char][key].extend(values)

                # add values to global value storage
                for v in values:
                    if not v in self.values:
                        self.values.append(v)

            # add key to global key storage
            if key not in self.keys:
                self.keys.append(key)

            # handle regular expressions
            self.regular_expression += re.escape(key) + "|"

            # check minimal length of key in dictionary
            len_k = len(key)
            if len_k < self.minkey:
                self.minkey = len_k

            # read new line and start over
            row = self.fd.readline()
            rownum += 1

        self._close_regexp()
        self._save_dict_files()
        print "Successfully created RRS dictionary %s." % self.name
        return 1

#-------------------------------------------------------------------------------
# End of class RRSDictionaryCreator
#-------------------------------------------------------------------------------



if __name__ == "__main__":
    def my_parse_fnc(x):
        s = x.split(" - ")
        return (s[0], map(lambda x: x.rstrip("\r\n"), s[1:]))
    # mydict.txt contains dictionary of people (keys) and their phone numbers (values)
    try:
        dc = RRSDictionaryCreator("neprijmeni.txt", "phonebook", DTYPE_LIST)
        dc.set_parser(my_parse_fnc)
        dc.create()
    except RRSDictionaryCreatorError, errmsg:
        sys.stderr.write(str(errmsg) + "\n")

