#! /usr/bin/python

"""
Basics of logging for RRS modules.
The sense of this module is to have uniform interface and output for logging
in Python-based RRS modules.
"""

__modulename__ = "logger"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$20.2.2011 11:31:37$"

import logging
import os.path
from rrslib.others.pattern import Singleton

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_rrs_logger(filename, logger):
    """
    Create new rrs logger.
    """
    lgr = RRSLogger(logger, logging.NOTSET)
    hdlr = logging.FileHandler(filename, 'a')
    fmt = logging.Formatter(LOG_FORMAT, None)
    hdlr.setFormatter(fmt)
    lgr.addHandler(hdlr)
    return lgr


class RRSLogger(logging.Logger):
    """
    Wrapper class for logging.Logger. Some additional stuff will be implemented
    within this class.
    """
    def log(self, lvl, msg):
        getattr(self, lvl)(msg)

#-------------------------------------------------------------------------------
# End of class RRSLogger
#-------------------------------------------------------------------------------

class RRSLogFile(object):
    """
    Abstraction of log file. This class offers all method of opened file object.
    """
    def __init__(self, filepath):
        self._fp = filepath
        self._fs = open(filepath, 'a')
        self._bound_loggers = []


    def bind_logger(self, logger):
        """
        Bind logger to the file.
        """
        self._bound_loggers.append(logger)


    def get_loggers(self):
        """
        Returns all loggers bound to this file.
        """
        return self._bound_loggers


    def __getattr__(self, attr):
        return getattr(self._fs, attr)

    def __str__(self):
        return "<RRSLogFile(filepath=\'%s\') object on %s>" % (self._fp, hex(id(self)).rstrip("L"))

    def __del__(self):
        self.close()

#-------------------------------------------------------------------------------
# End of class RRSLogFile
#-------------------------------------------------------------------------------

class RRSLogManager(Singleton):
    """
    Manager of all loggers in RRS. The manager holds information about loggers,
    opened logfiles and relationships between loggers and files.
    """

    def __init__(self):
        if '_loggers' in self.__dict__: return
        self._loggers = {}
        self._logfiles = {}


    def new_logger(self, loggername, logfilepath):
        """
        Creates new RRSLogger.
        """
        lgr = get_rrs_logger(logfilepath, loggername)
        self._loggers[loggername] = lgr
        logabspath = os.path.abspath(logfilepath)
        if logabspath not in self._logfiles:
            lf = RRSLogFile(logabspath)
            lf.bind_logger(lgr)
            self._logfiles[logabspath] = lf
        else:
            lf = self._logfiles[logabspath]
            lf.bind_logger(lgr)
        return lgr


    def use(self, logger):
        """
        Shorthand for get_logger().
        """
        return self._loggers[logger]


    def get_logger(self, logger):
        """
        Retruns logger by name.
        """
        return self._loggers[logger]


    def get_loggers_by_file(self, filepath):
        """
        Returns list of loggers bound to file @filepath.
        """
        afp = os.path.abspath(filepath)
        if not afp in self._logfiles:
            return None
        return self._logfiles[afp].get_loggers()


    def get_all_files(self):
        """
        Returns all files on which are some loggers registered.
        """
        return self._logfiles.values()


    def __del__(self):
        for f in self._logfiles.values():
            f.close()


#-------------------------------------------------------------------------------
# End of class RRSLogManager
#-------------------------------------------------------------------------------
