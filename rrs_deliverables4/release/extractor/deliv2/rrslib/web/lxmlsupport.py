#! /usr/bin/python

"""
Support module for lxml library. lxml provides very unpleasant iterators for
lxml.html.HtmlElement, so that for every iteration it throws different subelements
(different addresses - elem_iter1 is not elem_iter2).

This support module creates more comfortable and convenient iterator API, which
creates all subelements under one element persistent.
"""

__modulename__ = "lxmlsupport"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$3.4.2011 22:38:00$"

import types

# 3rd party lxml
from lxml.html import HtmlElement
from lxml.etree import _ElementTree

class LxmlSupportError(Exception): pass


def persist_ElementTree(elemtree):
    if type(elemtree) is not _ElementTree:
        raise LxmlSupportError("Transformed element has to be type lxml.etree._ElementTree")
    _persist_recurse(elemtree.getroot(), None)


def _persist_recurse(elem, parent):
    _persist_HtmlMixin(elem, parent)
    for child in elem.iterchildren():
        _persist_recurse(child, elem)


def _persist_HtmlMixin(elem, parent):
    # new container for children
    elem._children_container = None
    elem._parent_elem = parent
    elem.iterchildren = types.MethodType(__fake__iterchildren, elem, type(elem))
    elem.iterdescendants = types.MethodType(__fake__iterdescendants, elem, type(elem))
    elem.iter = types.MethodType(__fake__iter, elem, type(elem))
    elem.getparent = types.MethodType(__fake__getparent, elem, type(elem))
    elem.__getitem__ = types.MethodType(__fake__getitem, elem, type(elem))


def __fake__iterchildren(obj, tag=None, reversed=False):
    if obj._children_container is None:
        obj._children_container = []
        for e in HtmlElement.iterchildren(obj):
            obj._children_container.append(e)
    seq = xrange(0, len(obj._children_container))
    if reversed:
        seq = reversed(seq)
    for i in seq:
        #for e in obj._children_container:
        e = obj._children_container[i]
        if tag is not None:
            if e.tag == tag:
                yield e
        else:
            yield e

__fake__iterchildren.__name__ = "iterchildren"


def __fake__iterdescendants(obj, tag=None):
    for e in obj.iterchildren():
        if tag is not None:
            if e.tag == tag:
                yield e
        else:
            yield e
        for f in e.iterdescendants(tag):
            yield f

__fake__iterdescendants.__name__ = "iterdescendants"


def __fake__iter(e, tag=None):
    if tag is not None:
        if e.tag == tag:
            yield e
    else:
        yield e
    for f in e.iterdescendants(tag):
        yield f

__fake__iterdescendants.__name__ = "iter"


def __fake__getparent(obj):
    return obj._parent_elem

__fake__getparent.__name__ = "getparent"


def __fake__getitem(i):
    return obj._children_container[i]

__fake__getitem.__name__ = "__getitem__"
