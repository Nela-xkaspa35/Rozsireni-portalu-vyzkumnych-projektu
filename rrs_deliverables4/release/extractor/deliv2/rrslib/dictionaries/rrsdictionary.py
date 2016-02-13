#!/usr/bin/env python

"""
Module rrsdictionary represents API for dictionary-handling in RRS. We tried
(we hope successfuly) to make fast interface for searching, translating and
manipulating with large dictionaries.

The main feature of module is, that there are many compromises between memory usage,
hard-disc storage and speed of searching. The design can be for some kinds of
dictionaries not very optimized, but... it happens. (yea, it's correct, IT!).
"""

__modulename__ = "rrsdictionary"
__author__ = "Tomas Lokaj, Stanislav Heller"
__email__ = "xlokaj03@stud.fit.vutbr.cz, xhelle03@stud.fit.vutbr.cz"
__date__ = "$3-August-2010 18:15:38$"


import cPickle
import lxml.etree as lh
import re
import sys

try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")

#_______________________________________________________________________________

# Entities from rrsdb
EVENT_ACRONYMS = "event_acronym2full_name"
PROJECT_ACRONYMS = "project_acronym2title"
PROJECT_TITLES = "project_title2acronym"

# Geographic dictionaries
CITY2WOEID = "city2woeid"
WOEID2CITY = "woeid2city"
WOEID2ALTNAME = "woeid2cityaltname"
WOEID2COUNTRY = "woeid2country"
COUNTRY2CWOEID = "country2countrywoeid"
CWOEID2CITY = "countrywoeid2city"
CWOEID2COUNTRY = "countrywoeid2country"
CWOEID2CONTINENT = "countrywoeid2continent"
UNIVERSITIES = "universities"
COUNTRIES = "country2continent" # deprecated
CITIES = "city2country" # deprecated
POSTCODES = "city2postcode"

# British national corpus
BNC_UNLEMMATISED = "bnc_unlemmatised2frequency"
BNC_LEMMATISED = "bnc_lemmatised2frequency"

# Name dictionaries
NAME_FF_CZ = "firstname_female_cz2frequency"
NAME_FM_CZ = "firstname_male_cz2frequency"
NAME_FF_US = "firstname_female_us2frequency"
NAME_FM_US = "firstname_male_us2frequency"
NAME_FF_XX = "firstname_female_xx2frequency"
NAME_FM_XX = "firstname_male_xx2frequency"
NAME_SF_CZ = "surname_female_cz2frequency"
NAME_SM_CZ = "surname_male_cz2frequency"
NAME_S_US = "surname_us2frequency"

# Complementary dictionaries
NON_NAMES = "non_names"
NON_SURNAMES = "non_surnames"

#-------------------------------------------------------------------------------
# constants for dictionary arguments
CASE_SENSITIVE = 0
CASE_INSENSITIVE = 1
FIRST_UPPER = 2

NOTHING = 0
ADD = 1

RET_ORIG_TERM = True
RET_DICT_TERM = False
#-------------------------------------------------------------------------------

class RRSDictionaryError(Exception):
    pass

#-------------------------------------------------------------------------------
# end of class RRSDictionaryError
#-------------------------------------------------------------------------------


class RRSDictionary(object):
    """
    This class is abstraction of dictionary in rrslib. Searching and matching is
    optimized and the format of dictionary also.

    Dictionaries are stored as pickled (cPickle) files, all keys and values are
    sorted, so searching is done by binary search. This way we boosted the speed
    of searching and reduced the complexity form o(n) to O(log2n).

    Manipulating with pickled files in other way than this class is deprecated.
    """

    def __init__(self, name, sensitivity=CASE_SENSITIVE):
        if not isinstance(sensitivity, int) or sensitivity < 0 or sensitivity > 2:
            raise RRSDictionaryError("Sensitivity has to have values CASE_SENSITIVE,"\
                                     " CASE_INSENSITIVE or FIRST_UPPER.")
        self.sensitivity = sensitivity
        __dictpath = "/".join(__file__.split("/")[:-1])
        self.name = __dictpath + "/" + name
        self._load_info()
        self.keys = None
        self.values = None
        self.dict = {}
        self.dict_added = {}
        self.keys_compiled = None
        self.extended_names = []


    def _load_info(self):
        try:
            f_info = open(self.name + "/dict.info")
        except IOError:
            raise RRSDictionaryError("rrs_library doesn't contain any dictionary"\
                                     " named " + self.name)
        tree = lh.parse(f_info)
        elem = tree.getroot()
        self.type = elem[1].get("value")
        self.keysize = int(elem[2].get("value"))
        self.valuesize = int(elem[3].get("value"))
        self.mintextlen = int(elem[4].get("value"))
        self.simplekeys = elem[5].get("value") == "True"
        f_info.close()


    def _load_keys(self):
        f_keys = open(self.name + "/keys.rrsdict", "rb")
        self.keys = cPickle.load(f_keys)
        f_keys.close()


    def _load_values(self):
        f_values = open(self.name + "/values.rrsdict", "rb")
        self.values = cPickle.load(f_values)
        f_values.close()


    def _load_translate(self, letter):
        f_trans = open(self.name + "/translate_" + letter.lower() + ".rrsdict", "rb")
        d = cPickle.load(f_trans)
        f_trans.close()
        for name in self.extended_names:
            f_trans = open(name + "/translate_" + letter.lower() + ".rrsdict", "rb")
            _n_dict = cPickle.load(f_trans)
            for key in _n_dict.keys():
                if not self._binary_search(d.keys(), key, False)[0]:
                #if not key in d.keys():
                    d[key] = _n_dict[key]
                else:
                    for val in _n_dict[key]:
                        #if not val in d[key]:
                        if not self._binary_search(d[key], val, False)[0]:
                            d[key].append(val)
            f_trans.close()
        return d


    def _load_compiled_keys(self):
        # if we are on ucs4 compiled system, we can use normal compiled re
        if self._ucs4():
            f_keys_com = open(self.name + "/keys_compiled.rrsdict", "rb")
        # if we are on ucs2, we have to use special compiled regular expression,
        # which doesnt throw OverflowError.
        else:
            f_keys_com = open(self.name + "/keys_compiled_ucs2.rrsdict", "rb")
        self.keys_compiled = cPickle.load(f_keys_com)
        f_keys_com.close()


    def _binary_search(self, l, val, is_text_search=False):
        # boost speed by filtering values shorter than minimal text length
        # returns search result and found value
        left = 0
        right = len(l)
        if right == 0:
            return False, ""
        else:
            right -= 1

        if is_text_search and len(val) < self.mintextlen:
            return False, ""
        if is_text_search and self.sensitivity == FIRST_UPPER:
            if val[0].isalpha() and  val[0].islower():
                return False, ""

        # binary search
        if is_text_search \
        and (self.sensitivity == CASE_INSENSITIVE \
        or self.sensitivity == FIRST_UPPER): val = val.lower()
        # XXX unicode string fix
        if isinstance(val, str):
            val = unicode(val, errors="replace", encoding='utf-8')

        while left <= right:
            middle = (right + left) / 2
            lm = l[middle]
            if is_text_search \
            and (self.sensitivity == CASE_INSENSITIVE \
            or self.sensitivity == FIRST_UPPER):
                if isinstance(lm, list):
                    lm = lm[0]
                lm = lm.lower()

            # XXX unicode string fix
            if isinstance(lm, str):
                lm = unicode(lm, errors="replace", encoding='utf-8')

            if lm == val:
                return True, l[middle]
            if val < lm:
                right = middle - 1
            elif val > lm:
                left = middle + 1
            else:
                return True, l[middle]
        return False, ""


    def _ucs4(self):
        if len(u'\U00010800') == 1:
            return True
        return False


    def _compile_keys(self, keys):
        regular_expression = ["(?<![a-zA-Z0-9\-])("]
        for key in keys:
            regular_expression.append(re.escape(key))
            regular_expression.append("|")
        regular_expression = "".join(regular_expression).rstrip("|") + ")"
        #compiled = None
        compiled = re.compile(regular_expression)
        return compiled

    #===========================================================================
    # def _save_dictionary(self):
    #    path = self.name + "/"
    #    # save keys
    #    f_keys = open(path + "keys.rrsdict", "wb")
    #    cPickle.dump(self.keys, f_keys)
    #    f_keys.close()
    #
    #    # save values
    #    f_values = open(path + "values.rrsdict", "wb")
    #    cPickle.dump(self.values, f_values)
    #    f_values.close()
    #
    #    f_compiled = open(path + "keys_compiled.rrsdict", "wb")
    #    cPickle.dump(self.keys_compiled, f_compiled)
    #    f_compiled.close()
    #
    #    f_compiled_ucs2 = open(path + "keys_compiled_ucs2.rrsdict", "wb")
    #    cPickle.dump(self.keys_compiled, f_compiled_ucs2)
    #    f_compiled_ucs2.close()
    #
    #    # save translation dictionaries
    #    for k in self.dict:
    #        f_trans = open(path + "translate_" + k + ".rrsdict", "wb")
    #        cPickle.dump(self.dict[k], f_trans)
    #        f_trans.close()
    #
    #    # save dict.info (I know, this is ugly way, but pretty easy to write...:) )
    #    f_info = open(path + "dict.info", "w")
    #    f_info.write('<?xml version="1.0" encoding="utf-8"?>\n')
    #    f_info.write('<rrsdictionary>\n\t')
    #    f_info.write('<name value="' + self.name + '"/>\n\t')
    #    f_info.write('<type value="' + self.type + '"/>\n\t')
    #    f_info.write('<keysize value="' + str(len(self.keys)) + '"/>\n\t')
    #    f_info.write('<valuesize value="' + str(len(self.values)) + '"/>\n\t')
    #    f_info.write('<min-key-length value="' + str(self.mintextlen) + '"/>\n\t')
    #    f_info.write('<simplekeys value="' + str(self.simplekeys) + '"/>\n')
    #    f_info.write('</rrsdictionary>')
    #===========================================================================

    #===========================================================================
    # def _load_all_translations(self):
    #    self.dict = {}
    #    for st_char in "abcdefghijklmnopqrstuvwxyz$":
    #        if not st_char.isalpha():
    #            st_char = "other"
    #        self.dict[st_char] = self._load_translate(st_char)
    #===========================================================================

    #---------------------------------------------------------------------------
    # Public methods
    #---------------------------------------------------------------------------

    def get_size_keys(self):
        return self.keysize


    def get_size_values(self):
        return self.valuesize


    def is_simplekeys(self):
        return self.simplekeys


    def get_name(self):
        return self.name


    def get_added_dict(self):
        return self.dict_added


    def get_type(self):
        return self.type


    def get_mintextlen(self):
        return self.mintextlen


    def get_keys(self):
        if self.keys is None:
            self._load_keys()
        return self.keys


    def get_values(self):
        if self.values is None:
            self._load_values()
        return self.values


    def contains_key(self, key):
        """
        Looks for a key in dictionary.
        Returns True/False.
        """
        if not isinstance(key, basestring):
            raise RRSDictionaryError("Key has to be string or unicode.")
        if self.keys is None: self._load_keys()
        return self._binary_search(self.keys, key, True)[0]


    def contains_value(self, value):
        """
        Looks for a value in distionary.
        Returns True/False.
        Dictionary has to be a 'dict' type, not 'list'.
        """
        if not isinstance(value, basestring):
            raise RRSDictionaryError("Value has to be string or unicode.")
        if self.type != "dict":
            raise RRSDictionaryError("RRSDictionary.contains_value() cannot be called "\
                                     "on list dictionaries.")
        if self.values is None: self._load_values()
        return self._binary_search(self.values, value, True)[0]


    def text_search(self, text, force_bs=False, ret=RET_ORIG_TERM):
        """
        Looks in text for terms from dictionary.
        Returns list of found terms.
        """
        # typechecking
        if not isinstance(text, basestring):
            raise RRSDictionaryError("Text has to be string or unicode.")
        if not isinstance(force_bs, bool):
            raise RRSDictionaryError("Parameter force_bs has to be True or False.")
        if not isinstance(ret, bool):
            raise RRSDictionaryError("Parameter ret has to be RET_DICT_TERM" \
                                     " or RET_ORIG_TERM.")

        # if it is loaded dictionary with basic key format (one word), search
        # in a binary way, but sadly, this doesn't work with more-word keys..
        if self.simplekeys or force_bs == True:
            # if keys not loaded yet, load it
            if self.keys is None: self._load_keys()
            # splitting into words
            t = re.sub("[\"\(\)\[\]{}\,\.\+\!\?\:\;@#\$%\^&\*]", " ", text)
            splitted = t.split(" ")
            # searching
            _buffer = []
            for w in splitted:
                res = self._binary_search(self.keys, w, True)
                if res[0]:
                    if ret:
                        _buffer.append(w)
                    else:
                        _buffer.append(res[1])
            return _buffer
        else:
            # because there are keys with more than one word in them, we have to
            # use regular expressions.
            if self.keys_compiled is None: self._load_compiled_keys()
            return self.keys_compiled.findall(text)


    def translate(self, key):
        """
        Translates key to it's values.
        Returns list of values.
        """
        if self.keys is None:
            self._load_keys()
        res = self._binary_search(self.keys, key, True)
        if not res[0]:
            return None
        else:
            key = res[1]

        if not isinstance(key, basestring):
            raise RRSDictionaryError("Key has to be string or unicode.")
        if self.type != "dict":
            raise RRSDictionaryError("RRSDictionary.translate() cannot be called "\
                                     "on list dictionaries.")
        self.st_char = key[0].lower()
        if not self.st_char in self.dict:
            if not self.st_char.isalpha():
                self.st_char = "other"
            self.dict[self.st_char] = self._load_translate(self.st_char)
            if self.st_char in self.dict_added.keys():
                for k in self.dict_added[self.st_char]:
                    #if not k in self.dict[self.st_char].keys():
                    if not self._binary_search(self.dict[self.st_char].keys(), k, False)[0]:
                        self.dict[self.st_char][k] = self.dict_added[self.st_char][k]
                    else:
                        for val in self.dict_added[self.st_char][k]:
                            if not self._binary_search(self.dict[self.st_char][k],
                            val, False)[0]:
                            #if val not in self.dict[self.st_char][k]:
                                self.dict[self.st_char][k].append(val)
        return self.dict[self.st_char][key]


    def key_startswith(self, s):
        """
        Returns list of keys which starts with specified char.
        """
        res = []
        for k in self.keys:
            if k.startswith(s): res.append(k)
        return res


    def change_sensitivity(self, sensitivity):
        """
        Changes case sensitivity of the dictionary.
        Allowed values:
            0 - CASE_SENSITIVE
            1 - CASE_INSENSITIVE
            2 - FIRST_UPPER
        Case sensitivity works only for dictionaries which containins only
        simple words.
        """
        if not isinstance(sensitivity, int) or sensitivity < 0 or sensitivity > 2:
            raise RRSDictionaryError("Sensitivity has to have values CASE_SENSITIVE,"\
                                     " CASE_INSENSITIVE or FIRST_UPPER.")
        self.sensitivity = sensitivity
    #---------------------------------------------------------------------------
    # dictionary editing and manipulation
    #---------------------------------------------------------------------------

    def extend(self, d):
        """
        Extends dictionary with another.
        Dictionaries types has to be the same - list/dict.
        """
        if not isinstance(d, RRSDictionary):
            raise RRSDictionaryError("Dictionary has to be instance of RRSDictionary.")
        if self.get_type() != d.get_type():
            raise RRSDictionaryError("Dictionaries has different types.")

        #extends keys
        if self.keys is None:
            self._load_keys()
        self.keysize = len(self.keys)
        _new_keys = []
        for key in d.get_keys():
            if not self._binary_search(self.keys, key, False)[0]:
                _new_keys.append(key)
        self.keys.extend(_new_keys)
        self.keys.sort()
        self.keysize = len(self.keys)

        if self.type == 'dict':
            self.dict = {}

            #appends dictionary names to buffer for a possible translation
            self.extended_names.append(d.get_name())

            #extends values
            if self.values is None:
                self._load_values()
            self.valuesize = len(self.values)
            _new_values = []
            for value in d.get_values():
                if not self._binary_search(self.values, value, False)[0]:
                    _new_values.append(value)
            self.values.extend(_new_values)
            self.values.sort()
            self.valuesize = len(self.values)

            #extends added dict
            _ad = d.get_added_dict()
            for st_char in _ad.keys():
                if not self._binary_search(self.dict_added.keys(), st_char, False)[0]:
                #if not st_char in self.dict_added.keys():
                    self.dict_added[st_char] = _ad[st_char]
                else:
                    for key in _ad[st_char].keys():
                        if not self._binary_search(self.dict_added[st_char].keys(),
                        key, False)[0]:
                        #if not key in self.dict_added[st_char].keys():
                            self.dict_added[st_char][key] = _ad[st_char][key]
                        else:
                            for val in _ad[st_char][key]:
                                if not self._binary_search(self.dict_added[st_char][key],
                                val, False)[0]:
                                #if val not in self.dict_added[st_char][key]:
                                    self.dict_added[st_char][key].append(val)
        #extends compiled keys and simplekey value
        if not d.is_simplekeys(): self.simplekeys = False
        if not self.simplekeys:
            self.keys_compiled = self._compile_keys(self.keys)
        else:
            self.keys_compiled = None

#===============================================================================
#
#    def extend_persist(self, d):
#        self.extend(d)
#        self._load_all_translations()
#        self._save_dictionary()
#===============================================================================


#===============================================================================
#    def delete(self, key):
#        if not isinstance(key, basestring):
#            raise RRSDictionaryError("Key has to be string or unicode.")
#
#        if self.keys is None:
#            self._load_keys()
#        self.keysize = len(self.keys)
#
#        if not self._binary_search(self.keys, key, 0, self.keysize - 1, False):
#            return False
#
#        self.keys.remove(key)
#        self.keysize = self.keysize - 1
#
#        if self.type == "dict":
#            if self.values is None:
#                self._load_values()
#            self.valuesize = len(self.values)
#            val = self.translate(key)
#            if val != None:
#                self.values.remove(val)
#                self.valuesize = self.valuesize - 1
#
#            self._load_all_translations()
#            st_char = key[0].lower()
#            if not st_char.isalpha():
#                st_char = "other"
#            if st_char in self.dict:
#                del self.dict[st_char][key]
#        return True
#
#
#    def delete_persist(self, key):
#        if not self.delete(key):
#            return False
#        self._save_dictionary()
#        return True
#===============================================================================


    def add(self, key, values, behaviour):
        """
        Adds new key and it's values to dictionary.
        If dictionary type is 'list', values are irrelevant.
        Parameter 'behaviour' has values:
            1 - ADD: if key exists, add new values (in case of 'dict')
            0 - NOTHING: if key exists, do nothing
        """

        if not isinstance(key, basestring):
            raise RRSDictionaryError("Key has to be string or unicode.")
        if behaviour != ADD and behaviour != NOTHING:
            raise RRSDictionaryError("Behaviour value has to be ADD or NOTHING.")

        if self.keys is None:
            self._load_keys()
        self.keysize = len(self.keys)

        #check if still simplekeys:
        if re.search("[ \"\(\)\[\]{}\,\.\+\!\?:]", key):
            self.simplekeys = False

        #adds to dict
        if self.type == "dict":
            if not isinstance(values, (basestring, list)):
                raise RRSDictionaryError("Values has to be either string, unicode or list of them.")

            #adds keys
            if self._binary_search(self.keys, key, False)[0]:
                if behaviour == NOTHING: return
            else:
                self.keys.append(key)
                self.keys.sort()
                self.keysize += 1

            #adds values
            if self.values is None:
                self._load_values()
            self.valuesize = len(self.values)
            if type(values) != type([]):
                values = [values]
            for value in values:
                if not self._binary_search(self.values, value, False)[0]:
                    self.values.append(value)
                    self.valuesize += 1
                    self.values.sort()

            #adds relations to dict
            st_char = key[0].lower()
            if not st_char.isalpha():
                st_char = "other"
            if not self._binary_search(self.dict_added.keys(), st_char, False)[0]:
            #if not st_char in self.dict_added.keys():
                self.dict_added[st_char] = {key:values}
            else:
                if not self._binary_search(self.dict_added[st_char].keys(), key, False)[0]:
                #if not key in self.dict_added[st_char].keys():
                    self.dict_added[st_char] = {key:values}
                else:
                    for val in values:
                        if not self._binary_search(self.dict_added[st_char][key],
                        val, False)[0]:
                        #if val not in self.dict_added[st_char][key]:
                            self.dict_added[st_char][key].append(val)

        #adds to list
        elif self.type == "list":
            #adds keys
            if self._binary_search(self.keys, key, False)[0]:
                if behaviour == NOTHING: return
            else:
                self.keys.append(key)
                self.keys.sort()
                self.keysize += 1
        self.dict = {}

        #recompile regular expression if it's necessary
        if not self.simplekeys:
            self.keys_compiled = self._compile_keys(self.keys)
        else:
            self.keys_compiled = None



#-------------------------------------------------------------------------------
# end of class RRSDictionary
#-------------------------------------------------------------------------------

if __name__ == '__main__':
    d = RRSDictionary(CITIES)
    s = ["ahojs", "cau"]
    print d._binary_search(s, "ahoj", False)[0]
    pass
