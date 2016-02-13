#!/usr/bin/python

"""
This module provides database abstraction layer for easier manipulation with
SQL-queries and for querying database.
"""

__modulename__ = "dbal"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$3.2.2011 21:44:29$"


from rrslib.others.pattern import Singleton
from rrslib.db.model import _RRSDatabaseEntity, __tables__, RRSDateTime, \
                            RRSEmail, _RRSDbEntityRelationship
from rrslib.others.logger import RRSLogManager
import model
import psycopg2
import psycopg2.extras
import re
import traceback
import StringIO
import datetime
import random
import string

# register UNICODE in psycopg2
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

# Constants for selects and joins
ALL         = "*"
CROSS       = "CROSS JOIN"
INNER       = "INNER JOIN"
NATURAL     = "NATURAL JOIN"
OUTER       = "OUTER JOIN"
LEFT        = "LEFT JOIN"
RIGHT       = "RIGHT JOIN"
LEFT_OUTER  = "LEFT OUTER JOIN"
RIGHT_OUTER = "RIGHT OUTER JOIN"
FULL_OUTER  = "FULL OUTER JOIN"

ASCENDING = "ASC"
DESCENDING = "DESC"


class DatabaseError(Exception): pass
"""
General database exception. Raise it if some problem with database or connection
occurs.
"""

#-------------------------------------------------------------------------------
# End of class DatabaseError
#-------------------------------------------------------------------------------

NO_LOGS = 0
STAT_LOG = 1
EXEC_LOG = 2
SELE_LOG = 3


class _PostgreSQLDbLogger(object):
    """
    Wrapper class of logger for postgresql database. This is a different kind of
    logger with some additional methods.
    """
    def __init__(self, logfile, level=3):
        """
        Log gevel:
         - 0 No logs
         - 1 Only database status messag log
         - 2 Status message log and executive (UPDATE, DELETE and INSERT) log
         - 3 status, executive and select log
        """
        self.level = level
        if self.level < STAT_LOG: return
        if logfile is None:
            raise ValueError("Name of logfile has to be type string or unicode, not Nonetype.")
        self.manager = RRSLogManager()
        h = str(random.randint(1,1000))
        self.pg_db_sele = "postgresql_db_sele" + h
        self.pg_db_exec = "postgresql_db_exec" + h
        self.pg_db_stat = "postgresql_db_stat" + h
        if level >= SELE_LOG:
            log_select = "%s.db.sele.log" % logfile
            self.select_logger = self.manager.new_logger(self.pg_db_sele, log_select)
        if level >= EXEC_LOG:
            log_exec = "%s.db.exec.log" % logfile
            self.exec_logger = self.manager.new_logger(self.pg_db_exec, log_exec)
        if level >= STAT_LOG:
            log_stat = "%s.db.stat.log" % logfile
            self.stat_logger = self.manager.new_logger(self.pg_db_stat, log_stat)


    def log_query(self, q, success=True):
        """
        Log some postgresql query.
        """
        if self.level < STAT_LOG: return
        if re.search("^SELECT", q, re.I):
            if self.level < SELE_LOG: return
            if success:
                self.select_logger.info("SQL: %s" % q)
            else:
                self.log_traceback(self.pg_db_sele, "error", "SQL failed:")
        elif re.search("^(INSERT|DELETE|UPDATE|LOCK|COMMIT|BEGIN)", q, re.I):
            if self.level < EXEC_LOG: return
            if success:
                self.exec_logger.info("SQL: %s" % q)
            else:
                self.log_traceback(self.pg_db_exec, "error", "SQL failed:")
        else:
            if success:
                self.stat_logger.info("Unrecognized SQL query: %s" % q)
            else:
                self.log_traceback(self.pg_db_stat, "error", "SQL failed:")

    def log_connection(self, param=None, success=True):
        """
        Log connection messages.
        """
        if self.level < STAT_LOG: return
        if success:
            (dbname, host, user, password, encoding) = param
            self.stat_logger.info("Connected to database: '%s' on host: '%s' as "\
                                  "user: '%s' with password: '%s'" % (dbname,
                                  host, user, password))
            self.stat_logger.info("Connection encoding is: %s" % encoding)
        else:
            self.log_traceback(self.pg_db_stat, "critical", "Connection failed:")

    def log_schema_chg(self, schema):
        if self.level < STAT_LOG: return
        self.stat_logger.info("Setting database schema '%s'" % schema)

    def log_encoding_chg(self, encoding):
        if self.level < STAT_LOG: return
        self.stat_logger.info("Changed connection encoding to %s" % encoding)

    def log_traceback(self, logname, loglevel, msg):
        """
        The message will be prepended to the traceback.
        """
        if self.level < STAT_LOG: return
        io = StringIO.StringIO()
        traceback.print_exc(limit=None, file=io)
        io.seek(0)
        self.manager.use(logname).log(loglevel, "%s\n%s" % (msg, io.read()))

    def log_status(self, loglevel, msg):
        if self.level < STAT_LOG: return
        self.stat_logger.log(loglevel, msg)

    def log_exec(self, loglevel, msg):
        if self.level < EXEC_LOG: return
        self.exec_logger.log(loglevel, msg)

#-------------------------------------------------------------------------------
# End of class _PostgreSQLDbLogger
#-------------------------------------------------------------------------------


class PostgreSQLDatabase(Singleton):
    """
    General postgreSQL database. This class uses psycopg2 engine.
    The class has singleton behaviour.
    """
    logger = None
    connection = None

    def __init__(self, logfile=None, loglevel=NO_LOGS):
        if self.logger is not None:
            return
        self.logger = _PostgreSQLDbLogger(logfile, loglevel)


    def connect(self, host, dbname, user, password):
        if self.logger is not None:
            self.logger.log_status('info', "Initializing connection to PostgreSQL database...")
        try:
            self.connection = psycopg2.connect(host=host,
                                               database=dbname,
                                               user=user,
                                               password=password)
            self.logger.log_connection((host, dbname, user, password, self.connection.encoding), True)
        except:
            self.logger.log_connection(None, False)
            raise
        self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self._command = None


    def is_connected(self):
        return self.connection is not None


    def set_schema(self, schema):
        self.schema = schema
        self.logger.log_schema_chg(schema)


    def query(self, command):
        """
        Perform SQL query. This method has to be optimized as much as possible.
        See http://initd.org/psycopg/docs/faq.html#best-practices.
        """
        self._command = command
        try:
            self.cursor.execute(command)
            self.logger.log_query(command, True)
        except Exception:
            self.logger.log_query(command, False)
            raise


    def set_client_encoding(self, encoding):
        """
        Set client encoding defined on the database connection.
        """
        self.connection.set_client_encoding(encoding)
        self.logger.log_encoding_chg(encoding)


    def last_query(self):
        """
        Returns last executed command.
        """
        return self._command


    def fetch_all(self):
        """
        Fetch all returned rows by last SELECT.
        """
        return self.cursor.fetchall()


    def fetch_one(self):
        """
        Fetch one (next) returned row by last SELECT.
        """
        return self.cursor.fetchone()


    def refresh(self):
        """
        Setting new cursors and holding data in memory is kind of magic which
        has to be processed here.
        """
        self.cursor.close()
        self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


    def procedure(self, procname, params):
        """
        Performs database procedure. Doesnt return anything.
        """
        self.cursor.callproc(procname, params)


    def lock(self, table, mode):
        cmmd = "LOCK TABLE %s.%s IN %s MODE" % (self.schema, table, mode)
        self.cursor.execute(cmmd)
        self.logger.log_query(cmmd, True)


    def start_transaction(self):
        self.cursor.execute("BEGIN WORK;")
        self.logger.log_query("BEGIN WORK;", True)


    def end_transaction(self):
        self.cursor.execute("COMMIT WORK;")
        self.logger.log_query("COMMIT WORK;", True)
        

    def get_last_id(self, table):
        """
        Returns last inserted row's id.
        """
        if self.schema is None:
            raise DatabaseError("Cannot retrieve last inserted row's ID: schema not set.")
        try:
            self.cursor.execute("SELECT currval('%s.%s_id_seq');" % (self.schema, table))
            return self.cursor.fetchone()[0]
        except Exception:
            return None


    def get_row_count(self):
        """
        Returns count of afected rows by SELECT, UPDATE or INSERT statement.
        """
        return self.cursor.rowcount


#-------------------------------------------------------------------------------
# End of class PostgreeSQLDatabase
#-------------------------------------------------------------------------------


class BaseSQLQuery(object): pass
"""
This is base class of all query-like classes. There's nothing implemented but
is serves as a backup for implementation some specialities or workarounds within
these classes.
"""

#-------------------------------------------------------------------------------
# End of class BaseSQLQuery
#-------------------------------------------------------------------------------


class FluentSQLQueryError(Exception): pass
"""
Exception for all errors withing FluentSQLQuery class.
"""

#-------------------------------------------------------------------------------
# End of class FluentSQLQueryError
#-------------------------------------------------------------------------------



class FluentSQLQuery(BaseSQLQuery):
    """
    FluentSQLQuery provides API for postgresql-query manipulation.
    This class is inspired by David Grundl's dibi::DibiFluent class from
    dibi abstraction layer (PHP).

    Not supported:
    - Nested SELECT
    - Aliases (AS clause)
    Not implemented yet:
    - JOIN (inner, outer, cross, natural)
    """

    masks = {
    'SELECT' : ('SELECT', 'FROM', 'WHERE', 'GROUP BY',
                'HAVING', 'ORDER BY', 'LIMIT', 'OFFSET'),
    'UPDATE' : ('UPDATE', 'SET', 'WHERE', 'RETURNING'),
    'INSERT' : ('INSERT', 'INTO', 'VALUES', 'SELECT', 'RETURNING'),
    'DELETE' : ('DELETE', 'FROM', 'WHERE', 'ORDER BY', 'LIMIT', 'RETURNING')
    }

    def __init__(self, sql=""):
        self._const = sql != ""
        self._sql = self._unicode(sql)
        self._clauses = {}
        self._type = None
        self._id = None
        self._count = None
        self._rrsdb = None
        self._where = False
        self._force_delete = False


    def __call__(self):
        # here will be called singleton instance of database
        # and commited all changes.
        self._dbinit()
        # compile the query
        self._compile()
        # erase LAST_ROW_ID and count
        self._id, self._count = None, None
        # check if it is delete statement
        # WARNING: if query contains unsafe operation (deleting or truncating
        # whole table), check force_delete flag and if we aren't forcing DELETE
        # smt, raise exception
        if self._is_unsafe_delete() and not self._force_delete:
            raise FluentSQLQueryError("Forbidden operation: DELETE on whole table."\
                                " Call force_delete() to force this operation.")
        # perform query
        self._rrsdb.query(self._sql)
        # if query was INSERT-like, save the last ID.
        # this is done because after a few statements the user can perform another
        # insert and this ID would be lost. So if it was saved now, we are safe
        # get it every time (before change of this query of course).
        self._retrieve_last_id()
        # save count of produced/affected rows.
        # XXX does it work for DELETE statement?
        self._count = self._rrsdb.get_row_count()


    def _unicode(self, val):
        if type(val) == unicode:
            return val
        elif type(val) == str:
            return unicode(val, encoding='utf-8')
        else:
            return unicode(str(val), encoding='utf-8')


    def _retrieve_last_id(self):
        if re.search("^INSERT INTO ", self._sql, re.I):
            try:
                table = re.search("(?<=insert into )[^ ]+(?= )", self._sql, re.I).group(0)
            except:
                self._id = None
            if "." in table:
                table = table.split(".")[-1]
            try:
                self._id = self._rrsdb.get_last_id(table)
            except psycopg2.ProgrammingError:
                self._id = None


    def _dbinit(self):
        self._rrsdb = PostgreSQLDatabase()


    def _is_unsafe_delete(self):
        if re.search("^DELETE", self._sql, re.I):
            if re.search("WHERE", self._sql, re.I):
                return False
            elif re.search("LIMIT", self._sql, re.I):
                return False
            return True
        return False


    def _compile(self):
        # warning! If user adds his own sql command in constructor, database
        # schema will be ommited!
        # FIXME parse command and add schema if not added!!!!!!
        if self._const: return
        # clean sql buffer
        self._sql = unicode('')
        # init database to get schema
        if self._rrsdb is None:
            self._dbinit()
        try:
            schema = self._rrsdb.schema
        except:
            schema = None

        # if type is None, the command wasnt created with methods but
        # it was created with string parameter in constructor, so it has no
        # sense to continue in compiling
        if self._type == None:
            return

        # construct command from clauses
        for clause in self.masks[self._type]:
            if clause in self._clauses:
                clparam = self._clauses[clause]
                self._sql += clause + " "
                # in these clauses are table names as params

                if clause in ("FROM", "INTO", "UPDATE"):
                    if isinstance(clparam, (list, tuple, set)):
                        # if we have list of tables, add schema to them
                        # if tablename contains schema, don't do anything
                        tables = ""
                        for table in clparam:
                            if schema is not None and not table.startswith(schema):
                                table = schema + "." + table
                            tables += table + ", "
                        tables = tables.rstrip(", ")
                        self._sql += self._unicode(tables) + " "
                    else:
                        if schema is not None and not clparam.startswith(schema):
                            clparam = schema + "." + clparam
                        self._sql += self._unicode(clparam) + " "
                    if clause ==  "INTO":
                        vals = self._clauses["VALUES"]
                        self._keys = set()
                        for v in vals:
                            self._keys |= set(v.keys())
                        self._sql += "(" + self._unicode(", ".join(list(self._keys))) + ") "

                elif clause == "WHERE":
                    # TODO add brackets to statements

                    for item in clparam:
                        if type(item) is tuple:
                            lside, val, column = item
                            self._sql += self._unicode(lside)
                            if column:
                                self._sql += self._unicode(val) + " "
                            else:
                                val = re.sub("'", "\\'", self._unicode(val)) # fixing ' problem
                                self._sql += "'" + self._unicode(val) + "' "
                        else:
                            # logical AND, OR
                            self._sql += item + " "

                    if 'WHERECOL'in self._clauses:
                        for item in self._clauses['WHERECOL']:
                            if type(item) is tuple:
                                lside, val = item
                                self._sql += self._unicode(lside)
                                val = re.sub("'", "\\'", self._unicode(val)) # fixing ' problem

                            else:
                                # logical AND, OR
                                self._sql += item + " "


                elif clause in ("SELECT", "ORDER BY", "RETURNING", "GROUP BY"):
                    if clause == "SELECT":
                        # in select clause we have to process DISTINCT first
                        if "DISTINCT ON" in self._clauses:
                            self._sql += "DISTINCT ON ("
                            dist_param = self._clauses["DISTINCT ON"]
                            if isinstance(dist_param, (list, tuple, set)):
                                self._sql += self._unicode(", ".join(list(dist_param))) + " "
                            else:
                                self._sql += self._unicode(dist_param) + " "
                            self._sql = self._sql.rstrip(" ") + ") "
                    if isinstance(clparam, (list, tuple, set)):
                        self._sql += self._unicode(", ".join(list(clparam))) + " "
                    else:
                        self._sql += self._unicode(clparam) + " "
                    if clause == "ORDER BY":
                        self._sql += self._clauses["ORDER BY TYPE"] + " "

                elif clause in ("LIMIT", "OFFSET"):
                    self._sql += self._unicode(clparam) + " "

                elif clause == "VALUES":
                    for values in clparam:
                        # values is a dictionary with {"attr":"value}
                        self._sql += "("
                        for k in list(self._keys):
                            if k in values:
                                val = re.sub("'", "\\'", self._unicode(values[k])) # fixing ' problem
                                self._sql += "'" + self._unicode(val) + "', "
                            else:
                                self._sql += "DEFAULT, " # XXX DEFAULT OR NULL?
                        self._sql = self._sql.rstrip(", ")
                        self._sql += "), "
                    self._sql = self._sql.rstrip(", ")

                elif clause == "SET":
                    for attr in clparam:
                        value = self._unicode(clparam[attr])
                        if value in ("DEFAULT", "NULL", "NOW"):
                            self._sql += self._unicode(attr) + "="+ value + ", "
                        elif value.startswith("+="):
                            value = value.lstrip("+=")
                            self._sql += self._unicode(attr) + "=" + self._unicode(attr) + "+" + value + ", "
                        elif value.startswith("-="):
                            value = value.lstrip("-=")
                            self._sql += self._unicode(attr) + "=" + self._unicode(attr) + "-" + value + ", "
                        else:
                            val = re.sub("'", "\\'", self._unicode(value)) # fixing ' problem
                            self._sql += self._unicode(attr) + "='" + self._unicode(val) + "', "
                    self._sql = self._sql.rstrip(", ") + " "

                else:
                    if clparam is not None:
                        self._sql += self._unicode(clparam) + " "

        self._sql = self._sql.rstrip(" ")


    def _statement(self, param, stmt, errormsg):
        if isinstance(param, basestring):
            self._clauses[stmt] = param
        elif getattr(param, '__iter__', False):
            self._clauses[stmt] = tuple(param)
        else:
            raise FluentSQLQueryError(errormsg)
        return self


    def id(self):
        """
        Returns last inserted row's ID. This works only if last performed
        command was INSERT. Returns None otherwise.

        This works only if ID column of table is type SERIAL or INTEGER with
        applied nextval() function.
        """
        return self._id


    def count(self):
        """
        Returns number of rows that the last query-call produced (for DQL
        statements like SELECT) or affected (for DML statements like UPDATE
        or INSERT).

        This method has nothing to do with COUNT(*) statement.
        """
        return self._count


    def fetch_one(self):
        """
        Fetch the next row of a query result set, returning a single tuple,
        or None when no more data is available.
        """
        return self._rrsdb.cursor.fetchone()


    def fetch_all(self):
        """
        Fetch all (remaining) rows of a query result, returning them as a list
        of tuples. An empty list is returned if there is no more record to fetch.
        """
        return self._rrsdb.cursor.fetchall()


    def sql(self):
        """
        Returns compiled SQL query as a string.
        """
        self._compile()
        if self._sql == "":
            raise FluentSQLQueryError("Empty SQL command.")
        return self._sql

    # ----------------------- STATEMENTS AND CLAUSES -----------------------

    def select(self, cols):
        """
        Invoke SELECT statement.
        @param cols - type: iterable or string - columns to select.
        call: select(["apple", "pineapple"]) or select("apple")

        SELECT retrieves rows from a table or view.
        """
        if self._type is None:
            self._type = "SELECT"
        return self._statement(cols, "SELECT", "Parameter of select statement "\
                              "has to be string or iterable (list, tuple, set)")

    def distinct(self, cols):
        """
        Set <<DISTINCT>> part of SELECT statement.

        If DISTINCT is specified, all duplicate rows are removed from the result
        set (one row is kept from each group of duplicates).
        """
        return self._statement(cols, "DISTINCT ON", "Parameter of DISTINCT statement "\
                              "has to be string or iterable (list, tuple, set)")


    def from_table(self, tables):
        """
        Set <<FROM>> part of SELECT statement.
        """
        return self._statement(tables, "FROM", "Parameter of FROM statement has"\
                              " to be string or iterable  (list, tuple, set)")


    def where(self, lside, param, column=False):
        """
        Set WHERE clause for SELECT, UPDATE or DELETE statement.
        """
        if self._where:
            raise FluentSQLQueryError("Cannot call WHERE twice in a row with no"\
            " logical operator in the middle. Call and_() or or_() method first.")
        self._clauses['WHERE'] = [(lside,param,column)]
        self._where = True
        return self


    def and_(self, lside, param, column=False):
        """
        Add next part of WHERE statement connected with logical AND.
        """
        if not self._where:
            raise FluentSQLQueryError("Error in SELECT statement: cannot call AND before calling WHERE")
        self._clauses['WHERE'].extend(["AND", (lside,param,column)])
        return self


    def or_(self, lside, param, column=False):
        """
        Add next part of WHERE statement connected with logical OR.
        """
        if not self._where:
            raise FluentSQLQueryError("Error in SELECT statement: cannot call OR before calling WHERE")
        self._clauses['WHERE'].extend(["OR", (lside,param,column)])
        return self


    def group_by(self, cols):
        """
        Set <<GROUP BY>> part of SELECT statement.

        GROUP BY will condense into a single row all selected rows that share
        the same values for the grouped columns.
        """
        return self._statement(cols, "GROUP BY", "Parameter of GROUP BY statement"\
                             " has to be string or iterable (list, tuple, set)")


    def having(self, condition):
        """
        Set <<HAVING>> part of SELECT statement.

        HAVING eliminates group rows that do not satisfy the condition.
        """
        self._clauses['HAVING'] = condition
        return self


    def order_by(self, cols, type="ASC"):
        """
        Set <<ORDER BY>> part of SELECT statement.
        @param type: string - asc or desc.
        """
        self._clauses["ORDER BY TYPE"] = type
        return self._statement(cols, "ORDER BY", "Parameter of ORDER BY statement"\
                             " has to be string or iterable (list, tuple, set)")


    def limit(self, limit):
        """
        Set <<LIMIT>> part of SELECT statement.
        """
        self._clauses['LIMIT'] = limit
        return self


    def offset(self, offset):
        """
        Set <<OFFSET>> part of SELECT statement.
        """
        self._clauses['OFFSET'] = offset
        return self


    def insert(self, table, values={}):
        """
        Invoke INSERT statement.

        This method supports multiple INSERTs. Just apply it more times
        on one query and then call the query. Processing of the multiple INSERT
        inserts DEFAULT value into columns which were created by union of all
        columns of inserted rows but which aren't present in the extact row.
        For example:

        query.insert("person", {"first_name": "Adam", "last_name": "Sklenar", "born":1967})

        query.insert("person", {"first_name": "Jiri", "middle_name": "Miroslav", "last_name": "Zapolsky"})

        will be interpreted as:

        INSERT INTO person (first_name, middle_name, last_name, born)
                    VALUES ('Adam', DEFAULT, 'Sklenar', 1967),
                           ('Jiri', 'Miroslav', 'Zapolsky', DEFAULT);
        """
        if self._type is None:
            self._type = "INSERT"
        self._clauses['INSERT'] = None
        if "INTO" not in self._clauses:
            self._clauses['INTO'] = table
        # otherwise INTO is present in self._clauses
        elif self._clauses['INTO'] != table:
            raise FluentSQLQueryError("Cannot insert into multiple tables in one query. Create more queries.")
        # add values
        if "VALUES" not in self._clauses:
            self._clauses['VALUES'] = [values]
        else:
            self._clauses['VALUES'].append(values)
        return self


    def update(self, table, values={}):
        """
        Invoke UPDATE ... SET ... statement.

        If there is a need to increment or decrement some value, add into
        dictionary this acronyme:
        {"money":"+=1000"} will be interpreted as 'money = money + 1000'
        or
        {"money":"-=1000"} will be interpreted as 'money = money - 1000'

        Default or null value could be added like this:
        {"money":"DEFAULT"} will be interpreted as 'money = DEFAULT'
        and null value:
        {"money":"NULL"} will be interpreted as 'money = NULL'
        """
        if self._type is None:
            self._type = "UPDATE"
        self._clauses['UPDATE'] = table
        self._clauses['SET'] = values
        return self


    def delete(self, table, force=False):
        """
        Invoke DELETE FROM statement.
        Table is a string representing table from which have to be rows deleted.

        If parameter force is set (True), the processing of query accepts
        command to delete (truncate) the whole table. Otherwise, the query to
        truncate table is  never processed.
        """
        if not isinstance(table, basestring):
            raise FluentSQLQueryError("Parameter table in DELETE statement has"\
                                      " to be string or unicode.")
        if self._type is None:
            self._type = "DELETE"
        self._clauses['DELETE'] = None
        self._clauses['FROM'] = table
        self._force_delete = force


    def join(self, type_const, table):
        """
        Not implemented yet.
        """
        raise NotImplementedError()
        if type_const not in (CROSS, INNER, NATURAL, OUTER, LEFT, RIGHT,
                              LEFT_OUTER, RIGHT_OUTER, FULL_OUTER):
            raise FluentSQLQueryError("Wrong type of JOIN.")


    def on(self, expression):
        """
        Not implemented yet.
        """
        raise NotImplementedError()


    def fulltext_search(self, lang, columns, query):
        """
        This creates the WHERE statement with fulltext search to_tsvector() and
        to_tsquery().
        The result is something like:
        WHERE to_tsvector(column1 || ' ' || column2) @@ to_tsquery('your query')
        """
        if isinstance(columns, (tuple, list)):
            columns = map(lambda x: "coalesce(%s,'')" % x, columns)
            cols = " || ' ' || ".join(columns)
            if lang is None:
                self.where("to_tsvector(%s) @@ " % cols, \
                           "to_tsquery('%s')" % query, True)
            else:
                self.where("to_tsvector('%s', %s)" % (lang, cols), \
                           "to_tsquery('%s', '%s')" % (lang, query), True)
        elif isinstance(columns, basestring):
            if lang is None:
                self.where("to_tsvector(%s) @@ " % columns, \
                           "to_tsquery('%s')" % query, True)
            else:
                self.where("to_tsvector('%s', %s)" % (lang, columns), \
                           "to_tsquery('%s', '%s')" % (lang, query), True)
        else:
            raise FluentSQLQueryError("Vector_tables has to be type tuple, list,"\
                                      " string or unicode")


    def returning(self, cols):
        """
        Add clause RETURNING at the end of the SQL command.

        Forces db to return (when fetching data) columns selected by @param cols
        which is either string (one column) or tuple|list|set of strings
        representing columns.
        """
        return self._statement(cols, "RETURNING", "Parameter of RETURNING clause"\
                             " has to be string or iterable (list, tuple, set)")


    def get_db(self):
        """
        Returns instance of PostgreSQLDatabase on which is the query object
        connected.
        """
        return self._rrsdb


    def cleanup(self):
        """
        Clean up the object, set all variables to default.
        This method supports reusability of object.
        """
        self._sql = unicode('')
        self._const = False
        self._clauses = {}
        self._type = None
        self._id = None
        self._count = None
        self._keys = None
        self._where = False
        self._force_delete = False


    def force_delete(self):
        """
        Force DELETE statement without protection against truncating table.

        Be aware from using this method: keep in mind, that there's no UNDO
        if database has no extern backup.
        """
        self._force_delete = True


    def __str__(self):
        if self._sql == "":
            return "<Uncompiled FluentSQLQuery query in %s>" % str(hex(id(self))).rstrip("L")
        return "<Compiled FluentSQLQuery query: \"%s\">" % self._sql


#-------------------------------------------------------------------------------
# End of class FluentSQLQuery
#-------------------------------------------------------------------------------

RRSDB_MISSING = 10
RRSDB_OVERWRITE = 11
RRSDB_CREDIBILITY = 12
RRSDB_BESTCHOICE = 13


class RRSDatabase(Singleton):
    """
    The most upper layer in abstraction scale. This class represents RRS database,
    exactly the schema 'data'. Methods of this class allows to manipulate with
    data in database. Take care of it!
    """
    def __init__(self, logfile=None, schema='data', logs=SELE_LOG):
        self._db = PostgreSQLDatabase(logfile, logs)
        if not self._db.is_connected():
            self._db.connect(host="localhost",
                             dbname="reresearch",
                             user="reresearch",
                             password="lPPb5Wat4rPSMhtc")
            self._db.set_schema(schema)
        self._table_to_class_map = {}
        self._map_table_to_class()

    #-----------------+
    # support methods |
    #-----------------+

    def _map_table_to_class(self):
        for item in dir(model):
            if not item.startswith("RRS"):
                continue
            cls = getattr(model, item)
            if not issubclass(cls, _RRSDatabaseEntity):
                if not issubclass(cls, model._RRSDbEntityRelationship):
                    continue
            self._table_to_class_map[cls._table_name] = cls


    def _update_meta(self, id, module, table, credibility):
        q = FluentSQLQuery()
        meta_table = table + "_meta"
        if "_" in table:
            meta_table = table + "__meta"
        entity_id_name = table + "_id"
        q.select("id").from_table("module").where("module_name=", module).limit(1)
        q()
        fetched_data = q.fetch_one()
        if fetched_data is None:
            raise DatabaseError("No such RRS module: %s" % module)
        meta_id = fetched_data[0] # id of module
        q.cleanup()
        d = {entity_id_name: id,
             "module_id": meta_id}
        if credibility is not None:
            d["credibility"] = credibility
        q.insert(meta_table, d)
        q()


    def _get_meta_table(self, obj):
        meta_tbl = obj._table_name
        if "_" in obj._table_name:
            return meta_tbl + "__meta"
        return meta_tbl + "_meta"


    def _unicode(self, string):
        if isinstance(string, unicode):
            return string
        return unicode(str(string), encoding='utf-8')


    #----------------+
    # public methods |
    #----------------+

    # Universal methods - oriented to all entities, usually manipulation with
    # records in table - loading, storing, updating or connecting them.
    # Params of these methods are often objects - object is ment to be instance
    # of subclass of _RRSDatabaseEntity (thus class mapped to table in db),
    # it means object is instance of RRS*** class.

    def __contains__(self, item):
        return self.contains(item) is not None


    def contains(self, item):
        """
        If item is in database, method returns it's ID, None otherwise.
        @param item can be either:
        - tuple ('table.colum', value). This means, that method will search for
          value in table and column specified by first item (string) in tuple.
        - RRSDatabaseEntity object.
        """
        self._db.refresh()
        q = FluentSQLQuery()
        if type(item) is tuple:
            attr, val = item
            table, column = attr.split(".")
            q.select("id").from_table(table).where("%s=" % column, val)
            q()
            if q.count():
                return q.fetch_all()
            return None
        elif isinstance(item, _RRSDatabaseEntity):
            table = item._table_name
            q.cleanup()
            if "id" in item:
                q.select("id").from_table(table).where("id=", item['id'])
                q()
                if q.count():
                    return q.fetch_all()
            return None
        else:
            raise TypeError("Item withing 'in' statement has to be type "\
                        "tuple or instance of subclass of _RRSDatabaseEntity.")


    def insert(self, obj, source_module):
        """
        Insert object into database. Inserted are only own-attributes, which are
        not NULL. Metainformation about inserted record are stored into appropriate
        '***_meta' table.
        @param obj - inserted object representing one row in table
        @param source_module - string representing name of module which produced
               this output. This param is userd to update metadata tables.
        @return the same object with assigned ID of inserted row.
        """
        if not isinstance(obj, _RRSDatabaseEntity):
            raise TypeError("Inserted object has to be instance of subclass of _RRSDatabaseEntity")
        tbl = obj._table_name
        q = FluentSQLQuery()
        if obj.empty(exc=['id']):
            raise DatabaseError("Cannot insert empty object. Object %s at %s was empty." %
                                (obj._table_name, str(hex(id(obj)))))
        sql_values = {}
        for attr in obj:
            if obj[attr] is None: continue
            if type(obj[attr]) is list: continue
            if attr in ("id", "module", "credibility"): continue
            if attr == "type" and obj._table_name != 'file': continue
            if isinstance(obj[attr], _RRSDatabaseEntity):
                db_attr = None
                if "_" in attr: # has a role
                    sp = attr.split("_")
                    if sp[0] in __tables__: # organization_grants
                        db_attr = "%s_id_%s" % (sp[0], sp[1])
                    elif sp[1] in __tables__: #source_url
                        db_attr = "%s_id" % attr
                    else:
                        pass
                else:
                    db_attr = "%s_id" % attr
                if obj[attr]['id'] is None: continue
                sql_values[db_attr] = obj[attr]['id']
            else:
                sql_values[attr] = unicode(obj[attr])
        self._db.start_transaction()
        self._db.lock(tbl, "EXCLUSIVE")
        q.insert(tbl, sql_values)
        try:
            q()
        except:
            self._db.connection.rollback()
            self._db.end_transaction()
            raise
        _id = q.id() # id of inserted record
        if _id is None:
            # if wrong sequence name, try to get the id by values
            q.cleanup()
            q.select("id").from_table(tbl)
            for attr in sql_values:
                try:
                    q.where("%s=" % attr, sql_values[attr])
                except FluentSQLQueryError:
                    q.and_("%s=" % attr, sql_values[attr])
            q()
            if q.count() == 1:
                _id = q.fetch_one()[0]
            else:
                self._db.end_transaction()
                raise DatabaseError("Cannot retrieve last inserted ID from sequence."\
                                    " The sequence name is probably invalid.")
        self._db.end_transaction()
        q.cleanup()
        if tbl not in ("geoplanet",):
            self._update_meta(_id, source_module, tbl, obj['credibility'])
        obj['id'] = int(_id)
        self._db.refresh() # set new cursor to free memory
        return obj


    def load(self, type_ident, id):
        """
        Load row from database. Table is determined by type_ident -class or table
        (see params) and row is determined by ID (@param id).
        @param type_ident: Type identifier - class or table name
        @param id: id of row we wanna fetch
        Raises exception when type_ident is neither class representin database entity
        or string containing name of table.

        This method loads only own attributes into object. No foreign keys are
        handled at all.
        """
        table = None
        obj = None
        if type(type_ident) == type and issubclass(type_ident, _RRSDatabaseEntity): # class
            obj = type_ident()
            table = obj._table_name
        elif type_ident in __tables__: # table name
            if type_ident.endswith("_meta"):
                raise TypeError("Parameter type_ident has to be type class "\
                                    "identifying entity or table name of entity.")
            # find the appropriate class
            table = type_ident
            try:
                obj = self._table_to_class_map[table]() # instantiate class
            except KeyError:
                raise Warning("Class not found. There has to be a class like this: %s" % table)
        else:
            raise TypeError("Parameter type_ident has to be type class "\
                                "identifying entity or table name if entity.")
        q = FluentSQLQuery()
        q.select("*").from_table(table).where("id=", id)
        q()
        d = dict(q.fetch_one())
        # set own attributes only
        for attr in d:
            if d[attr] is None:
                continue
            if attr not in obj.__types__:
                if not attr.endswith("id"):
                    # load also attributes which might be from different version of db
                    # set their type as _UnknownType
                    obj.set(attr, d[attr], strict=False)
                continue
            type_ = obj.__types__[attr]
            if type_ is basestring:
                obj[attr] = d[attr]
            elif type(d[attr]) in (datetime.date, datetime.datetime):
                dt = RRSDateTime()
                dt.parse_isoformat(d[attr].isoformat())
                obj[attr] = dt
            elif type_ == RRSEmail:
                obj[attr] = RRSEmail(d[attr])
            else:
                obj[attr] = (type_)(d[attr])
        self._db.refresh()
        return obj


    def update(self, id, obj, behaviour=RRSDB_MISSING):
        """
        Update row in table. Row is represented by ID and new data are stored in
        object (@param obj). Behaviour of update is determined by param behaviour.
        @param behaviour can be one of (constants):
        - RRSDB_MISSING - Inserts only missing columns (which are NULL)
        - RRSDB_OVERWRITE - Overwrite all columns
        - RRSDB_CREDIBILITY - If inserted object has assigned credibility, method
          compares it with credibility of database object and chooses data with
          higher crediblity and stores it into database. If inserted object doesn't
          contain credibility, method doesn't do anything and returns False.
        - RRSDB_BESTCHOICE - combination of previous methods. This is pure magic.
          It is supposed to be the best choice, but who knows...

        @returns True if the record was changed (if anything was updated).
        @returns False if not (in case, that input data weren't of better quality
        or behaviour did not allow update).
        """
        # TODO update meta table entry if the record was updated
        if not isinstance(obj, _RRSDatabaseEntity):
            raise TypeError("Updated object has to be instance of subclass of _RRSDatabaseEntity")
        if not isinstance(id, int):
            raise DatabaseError("ID has to be type integer.")
        q = FluentSQLQuery()
        db_obj = None
        #self._db.start_transaction()
        #self._db.lock(obj._table_name, "SHARE")
        if behaviour == RRSDB_MISSING:
            db_obj = self.load(obj.__class__, id)
            _updated = False
            for attr in db_obj:
                if not attr in obj: continue
                if type(obj[attr]) is list:
                    continue
                if db_obj[attr] is None:
                    db_obj[attr] = obj[attr]
                    _updated = True
                else:
                    if "id" in attr: continue # do not erase any ID!
                    setattr(db_obj, attr, None) # avoid overwriting the data
            if not _updated:
                #self._db.end_transaction()
                return False
        elif behaviour == RRSDB_OVERWRITE:
            db_obj = self.load(obj.__class__, id)
            for attr in db_obj:
                if type(obj[attr]) is list:
                    continue
                if unicode(db_obj[attr]) == unicode(obj[attr]) and attr != 'id':
                    setattr(db_obj, attr, None) # avoid re-writing the same data
                else:
                    if obj[attr] is None:
                        setattr(db_obj, attr, None)
                    else:
                        db_obj[attr] = obj[attr]
        elif behaviour == RRSDB_CREDIBILITY:
            if 'credibility' in obj:
                meta = self.get_meta(db_obj)
                if meta['credibility'] is None or meta['credibility'] < obj['credibility']:
                    db_obj = self.load(obj.__class__, id)
                    for attr in db_obj:
                        if type(obj[attr]) is list:
                            continue
                        if db_obj[attr] == obj[attr] and attr != 'id':
                            setattr(db_obj, attr, None) # avoid re-writing the same data
                        else:
                            db_obj[attr] = obj[attr]
                else:
                    #self._db.end_transaction()
                    return False
            else:
                #self._db.end_transaction()
                return False
        elif behaviour == RRSDB_BESTCHOICE:
            #self._db.end_transaction()
            raise NotImplementedError()
        else:
            #self._db.end_transaction()
            raise ValueError("Parameter behaviour has to be one of "\
            "(RRSDB_MISSING, RRSDB_OVERWRITE, RRSDB_CREDIBILITY, RRSDB_BESTCHOICE)")

        sql_values = {} # storage of real updated data
        for attr in db_obj:
            if db_obj[attr] is None: continue
            if type(db_obj[attr]) is list: continue
            if attr in ("id", "type", "module", "credibility"): continue
            if isinstance(db_obj[attr], _RRSDatabaseEntity):
                db_attr = None
                if "_" in attr: # has a role
                    sp = attr.split("_")
                    if sp[0] in __tables__: # organization_grants
                        db_attr = "%s_id_%s" % (sp[0], sp[1])
                    elif sp[1] in __tables__: #source_url
                        db_attr = "%s_id" % attr
                else:
                    db_attr = "%s_id" % attr
                if db_obj[attr]['id'] is None: continue
                sql_values[db_attr] = db_obj[attr]['id']
            else:
                sql_values[attr] = self._unicode(db_obj[attr])
        # skip if no data to update
        if not sql_values:
            #self._db.end_transaction()
            return False
        # se update query
        q.update(db_obj._table_name, sql_values).where("id=", db_obj['id'])
        # perform query
        q()
        #self._db.end_transaction()
        return True


    def relationship(self, attr, rel_obj):
        """
        Inserts relation between two objects.
        This relation is represented by junction table which represents
        N:N on 1:N relationship.

        @param attr - string representing name of attribute in which was this
                      relationship object stored.
        @param rel_obj - the relationship object. This has to be instance of
                        RRSRelationship*** class.
        @return True if relationship was created, False if relationship exists.
        """
        if rel_obj._parent['id'] is None:
            raise DatabaseError("All objects of relationship %s have to be "\
                                "stored to database." % rel_obj._table_name)

        q = FluentSQLQuery()
        #self._db.start_transaction()
        # if the relationship is type 1:N
        if rel_obj._fake_table:
            # parent ID will be stored the row on which side is cardinality N
            parent_id = rel_obj._parent['id']
            #for obj in rel_obj._entities:
            #    self._db.lock(obj._table_name, "SHARE")
            for obj in rel_obj._entities:
                if obj['id'] is None:
                    #self._db.end_transaction()
                    raise DatabaseError("All objects of relationship %s have to be "\
                    "stored to database. Failed on %s.id" % (rel_obj._table_name, obj._table_name))

                q.cleanup()
                # find out, which attribute was it
                if "_" in attr:
                    if attr not in __tables__: # relationship has a role
                        spl = attr.split("_") # reference, reference
                        role, ent = spl[0], spl[1]
                        #role, ent, _ = attr.split("_") # reference, reference
                        suff = "_" + rel_obj._parent._table_name
                        objattrs = [x for x in obj]
                        if role + suff in objattrs:
                            id_attrname = role + suff +  + "_id"
                            q.update(obj._table_name, {id_attrname: parent_id}).where("id=", obj['id'])
                            q()
                        elif role + "d" + suff in objattrs:
                            id_attrname = role + "d" + suff + "_id"
                            q.update(obj._table_name, {id_attrname: parent_id}).where("id=", obj['id'])
                            q()
                        else:
                            raise RuntimeError("Unknown error. This shouldn't really happen. Ever. :)"\
                            " If it does, check the attribute %s in table %s for correct name." %
                            (attr, obj._table_name))
                        continue
                id_attrname = rel_obj._parent._table_name + "_id"
                # FIXME here it is everytime updated - but what if the relationship exists??
                q.update(obj._table_name, {id_attrname: parent_id}).where("id=", obj['id'])
                q()
            #self._db.end_transaction()
            return True
        # relationship is N:N
        d = {rel_obj._parent._table_name + "_id" : rel_obj._parent['id']}
        for obj in rel_obj._entities:
            if obj['id'] is None:
                #self._db.end_transaction()
                raise DatabaseError("All objects of relationship %s have to be "\
                "stored to database. Failed on %s.id" % (rel_obj._table_name, obj._table_name))
            d[obj._table_name + "_id"] = obj['id']
        # check if the relationship does exist
        q.cleanup()
        #self._db.lock(rel_obj._table_name, "SHARE")
        q.select("*").from_table(rel_obj._table_name)
        for attr_id in d:
            try:
                q.where("%s=" % attr_id, d[attr_id])
            except FluentSQLQueryError:
                q.and_("%s=" % attr_id, d[attr_id])
        q()
        if q.fetch_one() is not None:
            #self._db.end_transaction()
            return False
        for attr in rel_obj:
            if rel_obj[attr] is not None and type(rel_obj[attr]) is not list:
                d[attr] = rel_obj[attr]
        q.cleanup()
        q.insert(rel_obj._table_name, d)
        q()
        #self._db.end_transaction()
        return q.count() == 1


    def relationship_update(self, attr, rel_obj, behaviour=RRSDB_MISSING, check_first=True):
        """
        Update the relationship. If there's relationship record in db like
        the rel_obj suggests, this method updates all it's attributes.

        @returns True if the record was changed (if anything was updated).
        @returns False if not (in case, that input data weren't of better quality
        or behaviour did not allow update).
        @raises DatabaseError if no such relationship in database
        """
        if not isinstance(rel_obj, _RRSDbEntityRelationship):
            raise TypeError("Param rel_obj has to be type RRSRelationship***")
        if rel_obj._parent['id'] is None:
            raise DatabaseError("All objects of relationship %s have to be "\
                                "stored to database." % rel_obj._table_name)
        d = {rel_obj._parent._table_name + "_id" : rel_obj._parent['id']}
        for obj in rel_obj._entities:
            if obj['id'] is None:
                raise DatabaseError("All objects of relationship %s have to be "\
                "stored to database. Failed on %s.id" % (rel_obj._table_name, obj._table_name))
            d[obj._table_name + "_id"] = obj['id']
        q = FluentSQLQuery()
        #self._db.start_transaction()
        #self._db.lock(rel_obj._table_name, "SHARE")
        if check_first:
            q.select("*").from_table(rel_obj._table_name)
            for attr_id in d:
                try:
                    q.where("%s=" % attr_id, d[attr_id])
                except FluentSQLQueryError:
                    q.and_("%s=" % attr_id, d[attr_id])
            q()
            res = q.fetch_one()
            if res is None:
                #self._db.end_transaction()
                return False
        # load the new relationship object
        db_rel_obj = rel_obj.__class__()
        if behaviour == RRSDB_MISSING:
            _updated = False
            for attr in db_rel_obj:
                if type(rel_obj[attr]) is list:
                    continue
                if db_rel_obj[attr] is None:
                    db_rel_obj[attr] = rel_obj[attr]
                    _updated = True
                else:
                    if "id" in attr: continue # do not erase any ID!
                    setattr(db_obj, attr, None) # avoid overwriting the data
            if not _updated:
                #self._db.end_transaction()
                return False
        elif behaviour == RRSDB_OVERWRITE:
            for attr in db_rel_obj:
                if type(rel_obj[attr]) is list:
                    continue
                if unicode(db_rel_obj[attr]) == unicode(rel_obj[attr]) and attr != 'id':
                    setattr(db_rel_obj, attr, None) # avoid re-writing the same data
                else:
                    if rel_obj[attr] is None:
                        setattr(db_rel_obj, attr, None)
                    else:
                        db_rel_obj[attr] = rel_obj[attr]
        elif behaviour == RRSDB_BESTCHOICE:
            #self._db.end_transaction()
            raise NotImplementedError()
        else:
            #self._db.end_transaction()
            raise ValueError("Parameter behaviour has to be one of "\
            "(RRSDB_MISSING, RRSDB_OVERWRITE, RRSDB_BESTCHOICE)")

        # create real SQL update query
        sql_values = {}
        for attr in db_rel_obj:
            if db_rel_obj[attr] is None: continue
            if type(db_rel_obj[attr]) is list: continue
            sql_values[attr] = unicode(db_rel_obj[attr])
        # skip if no data to update
        if not sql_values:
            #self._db.end_transaction()
            return False

        q.cleanup()
        q.update(db_rel_obj._table_name, sql_values)
        for attr_id in d:
            try:
                q.where("%s=" % attr_id, d[attr_id])
            except FluentSQLQueryError:
                q.and_("%s=" % attr_id, d[attr_id])
        q()
        #self._db.end_transaction()
        return q.count() == 1



    # Special methods - oriented to one entity and taking responsibility for
    # one or more queries wrapped to method. The name of the method is to
    # be specific for the process which it represents.

    def get_meta(self, obj):
        """
        Returns last-change metadata: credibility and time of change.

        FUTURE: return also name of module which changed the entry.
        """
        if obj['id'] is None:
            raise DatabaseError("The object has to contain ID. It has to be"\
                                    " object loaded from database.")
        q = FluentSQLQuery()
        meta_tbl = self._get_meta_table(obj)
        ent_id_pk = obj._table_name + "_id"
        q.select("credibility, changed").from_table(meta_tbl).where("%s=" % ent_id_pk, obj['id'])
        q.order_by("changed", DESCENDING).limit(1)
        q()
        return q.fetch_one()

#-------------------------------------------------------------------------------
# End of class RRSDatabase
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    db = PostgreSQLDatabase(None, NO_LOGS)
    db.connect(host="localhost",
               dbname="reresearch",
               user="reresearch",
               password="lPPb5Wat4rPSMhtc")
    db.set_schema("data")

    q = FluentSQLQuery()
    q.select("*").from_table("publication")
    q.fulltext_search(None, ('title', 'abstract'), 'Temperature & electronics')
    print q.sql()
    q()
    print q.fetch_all()
    exit()
    #q = FluentSQLQuery("SELECT * from data.url")
    #print q.sql()
    #q()
    #print q.fetch_all()

