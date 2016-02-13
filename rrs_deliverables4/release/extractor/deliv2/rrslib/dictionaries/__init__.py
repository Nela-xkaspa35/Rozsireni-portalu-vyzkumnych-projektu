#!/usr/bin/env python

# init for rrs dictionaries

"""
Dictionaries in rrslib are special packages of pickled and info-xml files
used by dictionary API - rrsdictionary.py. Any other manipulation with dictionaries
out of the API frame is forbidden.

The rrslib-dictionary has mostly this architecture:
 * dict.info - XML information file containing dictionary metadata
 * keys.rrsdict - pickled list of keys
 * keys_compiled.rrsdict - compiled keys in regular expression
 * values.rrsdict - pickled list of values
 * translate_*.rrsdict - alphabecital list of pickled python-dicts {key:[values]}
"""

__all__ = ['rrsdictionary']