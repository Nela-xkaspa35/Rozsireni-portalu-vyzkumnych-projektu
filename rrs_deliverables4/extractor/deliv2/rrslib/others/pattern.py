#! /usr/bin/python

"""
Abstract classes representing some design patterns.
"""

__modulename__ = "pattern"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$4.2.2011 9:53:58$"

import threading
import warnings
import functools
import sys


class Singleton(object):
    _single = None # Singleton instance
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        # Check to see if a __single exists already for this class
        # Compare class types instead of just looking for None so
        # that subclasses will create their own _single objects
        cls._lock.acquire()
        if cls != type(cls._single):
            cls._single = object.__new__(cls, *args)
        cls._lock.release()
        return cls._single

    def __init__(self):
        raise NotImplementedError("")

#-------------------------------------------------------------------------------
# End of class Singleton
#-------------------------------------------------------------------------------

#
# Decorators
#

## {{{ http://code.activestate.com/recipes/577452/ (r1)
class memoized(object):
    """cache the return value of a method

    This class is meant to be used as a decorator of methods. The return value
    from a given method invocation will be cached on the instance whose method
    was invoked. All arguments passed to a method decorated with memoize must
    be hashable.

    If a memoized method is invoked directly on its class the result will not
    be cached. Instead the method will be invoked like a static method:
    class Obj(object):
        @memoize
        def add_to(self, arg):
            return self + arg
    Obj.add_to(1) # not enough arguments
    Obj.add_to(1, 2) # returns 3, result is not cached
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return functools.partial(self, obj)

    def __call__(self, *args, **kw):
        try:
            obj = args[0]
        except IndexError:
            obj = self
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res

cached = memoized

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function %(funcname)s." % {
                'funcname': func.__name__,
            },
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)
    return new_func


def debugged(f):
    """
    Debugging decorator. Prints to stderr all debug info about function call.
    """
    @functools.wraps(f)
    def newf(*args, **kwds):
        print >> sys.stderr, f.func_name, args, kwds
        f_result = f(*args, **kwds)
        print >> sys.stderr, f.func_name, "returned", f_result
        return f_result
    newf.__doc__ = f.__doc__
    return newf


class lazy(object):
    """
    Make the method lazy. Once the method was called, it wouldnt call any
    """
    def __init__(self, func):
        self.func = func
        self._partial = {}

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        if not obj in self._partial:
            self._partial[obj] = functools.partial(self, obj)
            #self.func = self._partial[obj]
        return self._partial[obj]


    def __call__(self, *args, **kw):
        try:
            obj = self._partial[args[0]]
        except:
            obj = self.func
        try:
            if obj.__called:
                return None
        except AttributeError:
            obj.__called = 1
            return self.func(*args, **kw)


if __name__ == "__main__":
    class A(object):
        @lazy
        def m(self):
            print "ahoj"


    @lazy
    def f(g):
        print g

    a = A()
    b = A()
    print a.m
    print a.m
    print b.m
    print b.m

    f("ahoj")
    f("ahoj")

    print "am call"
    a.m()
    print "bm call"
    b.m()
    print "second bm call"
    b.m()