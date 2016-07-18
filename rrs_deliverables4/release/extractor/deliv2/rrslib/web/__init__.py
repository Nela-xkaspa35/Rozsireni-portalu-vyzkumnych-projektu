#!/usr/bin/env python

"""
Package web contains tools for manipulation with web and generally with internet.
There are modules for downloading web pages, advanced mime-handling, parsing
web pages, searching in web search engines and commont tools (url-ping etc.).
FUTURE: client-module for rrsproxy
"""

# TODO's
# for crawler, mime, tools and separsers implement uniform wrapper class
# which will use rrs-proxy

__all__ = ['crawler', 'mime', 'separsers', 'sequencewrapper', 'htmltools',
           'csstools', 'lxmlsupport']

