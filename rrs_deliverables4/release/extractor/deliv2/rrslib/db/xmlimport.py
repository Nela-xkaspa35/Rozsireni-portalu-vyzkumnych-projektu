#! /usr/bin/python

"""
This module solves the problem of importing RRS-XML into rrs-database.
It contains some classes, each of them takes care of import XML from one rrs-module.
"""


__modulename__="xmlimport"
__author__="Stanislav Heller"
__email__="xhelle03@stud.fit.vutbr.cz"
__date__ ="$11.2.2011 19:55:00$"


from rrslib.db.dbal import RRSDatabase, FluentSQLQuery, RRSDB_MISSING, \
                           FluentSQLQueryError, DatabaseError, SELE_LOG
from rrslib.xml.xmlconverter import XML2ModelConverter
from rrslib.extractors.normalize import Normalize
from rrslib.db.model import *
from rrslib.db.model import _RRSDatabaseEntity, _RRSDbEntityRelationship
from rrslib.web.mime import MIMEHandler
from rrslib.others.logger import RRSLogManager
from collections import namedtuple
from itertools import combinations
from difflib import SequenceMatcher
from psycopg2 import IntegrityError



class XMLImportError(Exception): pass
"""
Base Exception class for all errors within XMLImporter classes.
"""

#-------------------------------------------------------------------------------
# End of class XMLImportError
#-------------------------------------------------------------------------------

class WaitingQueue(list):
    def wait(self, item):
        if item in self: return
        self.append(item)

    def waiting(self, item):
        return item in self

#-------------------------------------------------------------------------------
# End of class WaitingQueue
#-------------------------------------------------------------------------------


class RRSXMLImporter(object):
    """
    RRSXMLImporter is the main class representing the WHOLE process from
    parsing rrs-xml, database lookup and storing appropriate data into db.
    """

    def __init__(self, params):
        self.lookup_level = LOOKUP_PRECISE
        self.update_rule = RRSDB_MISSING
        self.logfile = 'xmlimport'
        self.logs = SELE_LOG
        self.module = 'unknown_module'
        self.schema = 'data'
        for arg in ('update_rule', 'logfile', 'lookup_level', 'module', 'schema', 'logs'):
            if arg in params and params[arg] is not None:
                self.__dict__[arg] = params[arg]
        # initialize RRS database
        self.db = RRSDatabase(self.logfile, self.schema, self.logs)
        # set logging
        self.manager = RRSLogManager()
        logfilename = "%s.importer.log" % self.logfile
        self.logger = self.manager.new_logger("xml_importer", logfilename)
        self.logger.info("Importer %s initialized." % self.module)

        # create xml->model converter
        self.xmlconv = XML2ModelConverter()

        # and import manager
        self.manager = RRSDbImportManager(params)

        # store of all objects
        self.topology = []

        # queue for objects waiting to solve their constraints
        self.queue = WaitingQueue()


    def _recurse(self, obj):
         # avoid infinite recursion
        if obj in self.topology:
            return False
        # gtfo None
        if obj is None:
            return False
        # add the object to the store
        self.topology.append(obj)
        # object preprocessing
        if not self.manager.prearrange(obj):
            # if obj is damaged, do not insert it into db
            return False

        # if object doesn't have any ID, we try to find it in database in a very
        # intelligent way (lookup)
        if not obj.isset('id'):
            self.manager.lookup(obj)
        # set the constraint flag
        fk_constraint = False

        if obj['id'] is None: # not in db
            # insert object into database
            # here has to be some CONSTRAINT-LOOKUP TABLE TODO
            #if obj._table_name == "citation" and obj['publication'] is not None:
            #    fk_constraint = True
            #    self.queue.wait(obj)
            #else:
            try:
                self.db.insert(obj, self.module)
            except IntegrityError:
                fk_constraint = True
                self.queue.wait(obj)
            except DatabaseError:
                pass # try to keep going

        # do some magic with the names, attributes, bind types, location to woeid etc.
        # This all manages the RRSDbImportManager, so do not care about that
        if obj.isset('id'):
            self.manager.handle(obj)

        # iterate over all attributes of object
        for attrname in obj:
            attr = obj[attrname]
            if attr is None: continue
            # if it is list of relationship objects
            if type(attr) is list:
                # iterate over relations, insert all objects
                for relationship in attr:
                    # recurse for every entity in relationship
                    _waiting = False
                    for ent in relationship.get_entities():
                        # if this object doesnt have solved all contraints
                        # (is waiting), skip processing of the relationship.
                        if self.queue.waiting(ent):
                            _waiting = True
                            break
                        self._recurse(ent)
                    if _waiting: break
                    # insert relation (record in junction table)
                    try:
                        exists = not self.db.relationship(attrname, relationship)
                        if exists:
                            self.db.relationship_update(attrname,
                                                        relationship,
                                                        behaviour=self.update_rule,
                                                        check_first=False)
                    except DatabaseError:
                        pass

            # some bound entity
            elif isinstance(attr, _RRSDatabaseEntity):
                # do not insert type, it's already done (if needed)
                if attrname == "type": continue
                 # if this object doesnt have solved all contraints, skip it
                if self.queue.waiting(attr): continue
                # just insert the object into db and assign to parent object it's ID
                self._recurse(attr)

            # own attributes are already inserted, so continue
            else: continue
        # now we have all the FK's available

        if fk_constraint:
            # insert the row (wasnt inserted before because of constraint)
            try:
                self.db.insert(obj, self.module)
                self.queue.remove(obj)
            except IntegrityError:
                pass
        else:
            # update the row
            try:
                self.db.update(obj['id'], obj, behaviour=self.update_rule)
            except DatabaseError:
                pass

        # try again to handle the manager-stuff
        if obj.isset('id'):
            self.manager.handle(obj)

        # return ID of inserted (od updated) row
        return obj['id']


    def import_xml(self, filepath):
        # convert the xml into object model
        self.topology = []
        # refresh queue (important)
        self.queue = WaitingQueue()
        # convert xml to model
        obj_list = self.xmlconv.convert(filepath)
        for obj in obj_list:
            # compile the object to clean it up and find possible cyclic deps..
            obj.compile()
            # get recursed..
            self._recurse(obj)
        for obj in self.queue:
            self._recurse(obj)
        return obj_list


    def import_model(self, obj):
        # convert the xml into object model
        self.topology = []
        # refresh queue (important)
        self.queue = WaitingQueue()
        if isinstance(obj, (list, tuple)):
            for o in obj:
                o.compile()
                self._recurse(o)
        else:
            obj.compile()
            self._recurse(obj)
        for q in self.queue:
            self._recurse(q)
        return True


#-------------------------------------------------------------------------------
# End of class PublicationTextData
#-------------------------------------------------------------------------------

IMRuleSet = namedtuple('IMRuleSet', 'entities reqcount', verbose=False)
"""
Ruleset for ImportManager. Lightweight version of object using tuple.
"""
# between the items of IMRuleSet is LOGICAL AND relationship, so all of the
# items has to be present together.

#-------------------------------------------------------------------------------
# End of tuple IMRuleSet
#-------------------------------------------------------------------------------


class _IMLookupLevel(list): pass
"""
Dummy list just for recognition of type of the container in lookup rule list.
"""
#-------------------------------------------------------------------------------
# End of tuple _IMLookupLevel
#-------------------------------------------------------------------------------

class IMLookupError(LookupError): pass
"""
An exception raised when some problem with ImportManager.lookup() occurs.
"""
#-------------------------------------------------------------------------------
# End of tuple IMLookupError
#-------------------------------------------------------------------------------

# some constants for lookup level :)
LOOKUP_FAST = 0
LOOKUP_PRECISE = 1
LOOKUP_EXTREME = 2


class _LookupRules(object):
    # There's nothing complicated here. Just a programmable list (dict) of lookup
    # rules for ImportManager. There are two "public" methods, but this is a very
    # private class, so nobody should feel obligated to intantiate it..
    def __init__(self):
        self._rules = \
        {
            # rules for publication lookup
            RRSPublication:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1),
                    # try to get the same normalized name
                    IMRuleSet(('title_normalized',), 1),
                    IMRuleSet(('isbn',), 1),
                    IMRuleSet(('doi',), 1),
                    IMRuleSet(('publisher','acronym'), 2),
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('event', 'organization_author', 'series', 'person',
                               'parent', 'file'), 2)
                ])
            ),

            # rules for publication_series lookup
            RRSPublication_series:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for person lookup
            RRSPerson:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same full_name
                    IMRuleSet(('full_name',), 1),
                    IMRuleSet(('full_name_ascii',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('last_name', 'publication'), 2),
                    IMRuleSet(('last_name', 'project_responsible'), 2),
                    IMRuleSet(('last_name', 'project_works'), 2),
                    IMRuleSet(('person_name', 'publication', 'project_works',
                               'project_responsible', 'network', 'contact'), 2)
                ])
            ),

            # rules for person_name lookup
            RRSPerson_name:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same full_name
                    IMRuleSet(('full_name',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('person', 'reference'), 1)
                ])
            ),

            # rules for event lookup
            RRSEvent:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title or acronym
                    IMRuleSet(('title',), 1),
                    IMRuleSet(('title_normalized',), 1),
                    IMRuleSet(('acronym',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('event_name', 'series', 'person', 'parent'
                               'location', 'organization'), 2)
                ])
            ),

            # rules for publication_series lookup
            RRSEvent_series:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for event_name lookup
            RRSEvent_name:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title or acronym
                    IMRuleSet(('title',), 1),
                    IMRuleSet(('acronym',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for organization lookup
            RRSOrganization:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title or acronym
                    IMRuleSet(('title',), 1),
                    IMRuleSet(('title_normalized',), 1),
                    IMRuleSet(('acronym',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('organization_name', 'person', 'project_organizes',
                               'project_participated', 'contact', 'url'), 2)
                ])
            ),

            # rules for organization_name lookup
            RRSOrganization_name:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title or acronym
                    IMRuleSet(('title',), 1),
                    IMRuleSet(('acronym',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for project lookup
            RRSProject:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title or acronym
                    IMRuleSet(('title',), 1),
                    IMRuleSet(('title_normalized',), 1),
                    IMRuleSet(('acronym',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('organization_organizes', 'organization_participates',
                               'person_works', 'person_responsible', 'url'), 2)
                ])
            ),

            # rules for contact lookup
            RRSContact:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same email or telephone
                    IMRuleSet(('email',), 1),
                    IMRuleSet(('telephone',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('person', 'organization'), 2)
                ])
            ),

            # rules for contact lookup
            RRSReference:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same content
                    IMRuleSet(('content',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for file lookup
            RRSFile:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same name
                    IMRuleSet(('filename',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for URL lookup
            RRSUrl:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same link
                    IMRuleSet(('link',), 1)
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('file',), 1)
                ])
            ),

            # rules for tag lookup
            RRSTag:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for topic lookup
            RRSTopic:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for text lookup
            RRSText:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same content
                    IMRuleSet(('content',), 1)
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for citation lookup
            RRSCitation:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same content
                    IMRuleSet(('content',), 1),
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('publication', 'reference'), 2)
                ])
            ),

            # rules for location lookup
            RRSLocation:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same name or country, city and address
                    IMRuleSet(('name',), 1),
                    IMRuleSet(('country','city','address'), 3),
                    IMRuleSet(('country','city'), 2),
                    IMRuleSet(('city',), 1),
                    IMRuleSet(('country',), 1),
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for keyword lookup
            RRSKeyword:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same title
                    IMRuleSet(('title',), 1),
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for network lookup
            RRSNetwork:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same name
                    IMRuleSet(('name',), 1),
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            ),

            # rules for rank lookup
            RRSRank:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same name
                    IMRuleSet(('name',), 1),
                ]),
                # LEVEL 1
                (_IMLookupLevel)([
                    IMRuleSet(('url',), 1)
                ])
            ),

            # rules for award lookup
            RRSAward:
            (
                # LEVEL 0
                (_IMLookupLevel)([
                    # the same name
                    IMRuleSet(('name',), 1),
                ]),
                # LEVEL 1
                _IMLookupLevel() # no rules
            )
        }


    def get_rules(self, classinfo, level):
        return self._rules[classinfo][level]


    def new_rule(self, classinfo, level, ruleset):
        if type(ruleset) is not IMRuleSet:
            raise IMLookupError('param ruleset has to be type IMRuleSet.')
        if not issubclass(classinfo, _RRSDatabaseEntity):
            raise TypeError("Parameter classinfo has to be entity-class - "\
                            "subclass of _RRSDatabaseEntity")
        if classinfo not in self._rules:
            self._rules[classinfo] = (_IMLookupLevel(), _IMLookupLevel())
        self._rules[classinfo][level].append(ruleset)

#-------------------------------------------------------------------------------
# End of class _LookupRules
#-------------------------------------------------------------------------------

WQEntry = namedtuple('WQEntry', 'method args', verbose=False)
"""
Entry for IMWaitingQueue. This is the only way how to add some process to wait
for - method and it's arguments.
"""
#-------------------------------------------------------------------------------
# End of namedtuple WQEntry
#-------------------------------------------------------------------------------

class IMWaitingQueue(WaitingQueue):
    """
    Special waiting queue containing tuples of (method, arguments) for
    re-application.
    """
    def wait(self, item):
        """
        This is gonna be legen..... wait for it..... dary!
        """
        if type(item) is not WQEntry:
            raise TypeError("Waiting item has to be type WQEntry.")
        if item in self:
            return
        self.append(item)


    def solve(self):
        """
        Try to solve all solvable items (objects).
        """
        if not self: return
        _trash = []
        for item in self:
            try:
                item.method(*item.args)
            except:
                pass
            else:
                _trash.append(item)
        for i in _trash:
            self.remove(i)

#-------------------------------------------------------------------------------
# End of class IMWaitingQueue
#-------------------------------------------------------------------------------


class RRSDbImportManager(object):
    def __init__(self, params=None):
        """
        Initialize RRSDatabase, lookup rules, handle_rules, queue and object
        topology map.
        """
        # param initialization
        self.lookup_level = LOOKUP_PRECISE
        self.update_rule = RRSDB_MISSING
        self.logfile = 'xmlimport'
        self.logs = SELE_LOG
        self.module = 'unknown_module'
        self.schema = 'data'
        for arg in ('update_rule', 'logfile', 'lookup_level', 'module', 'schema', 'logs'):
            if arg in params and params[arg] is not None:
                self.__dict__[arg] = params[arg]

        # working space
        self._queue = IMWaitingQueue()
        self._mime = MIMEHandler()
        self._rrsdb = RRSDatabase(self.logfile, self.schema, self.logs)
        self._db = self._rrsdb._db
        self._table_to_class_map = self._rrsdb._table_to_class_map
        self._lookup_rules = _LookupRules()

        # set logging
        self.manager = RRSLogManager()
        logfilename = "%s.importer.log" % self.logfile
        self.logger = self.manager.new_logger("xml_import_manager", logfilename)
        self.logger.info("RRSImportManager initialized.")



    def _bind_location_to_woeid(self, location):
        """
        Binds location to woeid number.
        @returns True if woeid found, False otherwise
        """
        if type(location) is not RRSLocation:
            raise TypeError("location has to be type RRSLocation")
        if not 'woeid' in location:
            q = FluentSQLQuery()
            for attr in ("address", "city", "country", "name"):
                if location[attr] is None: continue
                q.cleanup()
                q.select("woeid").from_table("geoplanet").where("name=", location[attr])
                q()
                res = q.fetch_one()
                if res is None: continue
                location['woeid'] = res[0]
                return True
            return False
        return True


    def _bind_entity_to_series(self, item):
        # TODO implementation missing
        return


    def _bind_publ_section_to_text(self, publ_section):
        if type(publ_section) is not RRSPublication_section:
            raise TypeError("Publication section has to be type RRSPublication_section.")
        publ = publ_section['publication']
        if not 'text' in publ:
            return
        publ_section['text'] = publ['text']


    def _bind_entity_to_name(self, namedentity, source_module):
        """
        This method creates connection between entity and it's name, which is stored
        in other database table. These tables are:
         - person vs person_name
         - organization vs organization_name
         - event vs event_name
        @returns ID of the row in the name-table.
        """
        ACRONYM = 'acronym' # to be easily changed to abbreviation or whatever needed..
        TITLE = 'title' # will be name? or what?
        if not isinstance(namedentity, _RRSDatabaseEntity):
            raise TypeError("Named object has to be instance of subclass of _RRSDatabaseEntity")
        if not 'id' in namedentity:
            raise DatabaseError("Named object has to contain ID!")
        q = FluentSQLQuery()
        if namedentity._table_name == "person":
            # act like person and handle person_name
            # this is slightly different because there is N:N relationship

            # create new person name object
            pname = RRSPerson_name()
            for attr in ('first_name', 'middle_name', 'last_name', 'full_name'):
                if attr in namedentity:
                    pname[attr] = namedentity[attr]
            # create relationship object
            rel_obj = RRSRelationshipPersonPerson_name()
            rel_obj.set_entity(pname)
            namedentity['person_name'] = rel_obj
            # look for this name in database
            if self.lookup(pname):
                # it is in db yet, just check if rel exists
                q.select("person_id").from_table(("j__person__person_name"))
                q.where("person_id=", namedentity['id']).and_("person_name_id=", pname['id'])
                q()
                if not q.count():
                    # if the relationship doesn't exist, create new one
                    self._rrsdb.relationship("person_name", rel_obj)
                elif q.count() > 1:
                    self.logger.warning("There are more than one relationship "\
                                        "entries in table 'j__person__person_name"\
                                        " between person.id=%s and person_name.id=%s" \
                                        % (namedentity['id'], pname['id']))
            else:
                # insert new person_name and create the relationship
                self._rrsdb.insert(pname, self.module)
                self._rrsdb.relationship("person_name", rel_obj)

            # get the reference out of which is this name extracted and assign
            # the person name to the reference (j__person_name__reference)
            try:
                refe = namedentity['publication'][0].get_entities()[0]['reference_reference'][0].get_entities()[0]
            except (KeyError, TypeError, IndexError):
                pass
            else:
                pname_ref_rel = RRSRelationshipPerson_nameReference()
                pname_ref_rel.set_entity(refe)
                pname['reference'] = pname_ref_rel
                try:
                    self._rrsdb.relationship('reference', pname_ref_rel)
                except DatabaseError:
                    self._queue.wait(WQEntry(self._rrsdb.relationship, ('reference', pname_ref_rel)))


        elif namedentity._table_name in ("event", "organization"):
            if TITLE not in namedentity:
                # this violates constraint... raise exception?? Or return false?
                return False
            name_tbl = "%s_name" % namedentity._table_name
            # if there in the database is no title like this, insert it
            q.select(("id", "%s_id" % namedentity._table_name, ACRONYM, TITLE)).from_table(name_tbl)
            q.where("%s=" % TITLE, namedentity[TITLE])
            if ACRONYM in namedentity:
                q.or_("%s=" % ACRONYM, namedentity[ACRONYM])
            q()
            if q.count():
                # check the parent id if it matches
                for row in q.fetch_all():
                    if namedentity['id'] == row[1]:
                        # if it matched on acronym, check the titles if they are the same
                        if row[TITLE] != namedentity[TITLE]:
                            # if not, check the rest and maybe add new row into table
                            continue
                        # add the missing acronym if needed
                        if row[ACRONYM] is None and namedentity[ACRONYM] is not None:
                            # update the row
                            q.cleanup()
                            q.update(name_tbl, {ACRONYM: namedentity[ACRONYM]})
                            q.where("id=", row['id'])
                            q()
                        return row['id']
                # if nothing matched, insert new name
            name_obj = self._table_to_class_map[name_tbl]()
            for attr in (TITLE, ACRONYM):
                if attr in namedentity:
                    name_obj[attr] = namedentity[attr]
            if name_obj.empty():
                return False
            name_obj[namedentity._table_name] = namedentity
            self._rrsdb.insert(name_obj, source_module)
            return name_obj['id']
        else:
            raise RRSDatabaseEntityError("%s is not a named entity." % type(namedentity))
        self._db.refresh()


    def _bind_type(self, obj):
        """
        If object has a type (publication_type, organization_type, event_type etc.)
        this method assigns type from the database enum to this object. If the type
        doesn't exist, method returns False. If everything went OK, returns True.
        If object doesn't have a type, raises DatabaseError.

        The object itself has to be inserted into database before binding type!
        (it fact, it has to contain attribute ID). If not, method raises Exception.
        """
        if obj['id'] is None:
            raise DatabaseError("Object has to contain attribute ID. Insert it into db first.")
        if 'type' in obj:
            type_name = obj['type']['type']
            q = FluentSQLQuery()
            q.select("id").from_table(obj['type']._table_name).where("type=", type_name)
            q()
            res = q.fetch_one()
            if res is None:
                return False
            type_id = res['id']
            q.cleanup()
            q.update(obj._table_name, {"type_id": type_id}).where("id=", obj['id'])
            q()
            return q.count() == 1
        else:
            raise RRSDatabaseEntityError("Entity doesn't have a type to bind to.")

    #---------------------------------------------------------------------------
    # PUBLIC METHODS
    #---------------------------------------------------------------------------

    def prearrange(self, obj):
        """
        Passive preprocessing of object data. It means adding attributes like
        title_normalized, looking for mime-types of file etc etc.
        This method doesnt touch the database, it works only on the object
        attributes.
        @return True if object was successfully preprocessed
        @return False if object doesnt fulfill table contraints or if object damaged
        """
        # add normalized title
        if 'title_normalized' in [x for x in obj]:
            norm_method = getattr(Normalize, obj._table_name)
            # I'm still not sure if it is implemented yet
            assert callable(norm_method)
            if obj['title'] is None:
                return False
            obj['title_normalized'] = norm_method(obj['title'])
            if obj['title_normalized'] is None:
                return False
        # add missing mime type if needed
        if obj._table_name == "file":
            #if "type" not in obj:  TODO really??
            fn = obj['filename']
            r = self._mime.start([fn])
            obj['type'] = r[fn]
        elif obj._table_name == "person":
            if obj['full_name'] is None:
                obj['full_name'] = " ".join([obj[x] for x in ('first_name', \
                            'middle_name', 'last_name') if obj[x] is not None])
            if obj['full_name_ascii'] is None:
                obj['full_name_ascii'] = Normalize.to_ascii(obj['full_name'])
        elif obj._table_name == "location":
            if 'city' in obj:
                city = Normalize.location(obj['city'], True)
                if city is None: obj.city = None
                else: obj['city'] = city
            if 'country' in obj:
                country = Normalize.location(obj['country'], True)
                if country is None: obj.country = None
                else: obj['country'] = country
            if 'address' in obj:
                addr = Normalize.location(obj['address'])
                if addr is None: obj.address = None
                else: obj['address'] = addr
        elif obj._table_name == "publication_section":
            self._bind_publ_section_to_text(obj)
        return True


    def handle(self, obj):
        """
        Main process - this method takes care of all possible relationships
        of object and creates or updates them.
        """
        # solve all previous problems if possible (solves constraint-like problems)
        self._queue.solve()
        # handle entity type
        if 'type' in obj and issubclass(obj.__types__['type'], _RRSDatabaseEntity):
            if not self._bind_type(obj):
                if self.logger is not None:
                    self.logger.warning("No such %s_type: '%s'" % (obj._table_name, obj['type']['type']))
        # bind location to woeid
        if isinstance(obj, RRSLocation):
            self._bind_location_to_woeid(obj)
        # named entity?
        if obj._table_name in ("person", "organization", "event"):
            self._bind_entity_to_name(obj, self.module)
        # does it have any series?
        if obj._table_name in ("event", "publication"):
            self._bind_entity_to_series(obj)
        self._db.refresh()


    def lookup(self, obj, level=None):
        """
        More sophisticated RRSDatabase.contains(). This method doesnt call
        RRSDatabase.contains() explicitly, it checks other entities and tries
        to find relationship between them. This method uses list of lookup rules.
        @returns True if found (the object now carries the ID)
                 False if not found
        """
        if level is None:
            level = self.lookup_level
        if level < 0:
            return
        if not isinstance(obj, _RRSDatabaseEntity):
            raise TypeError('lookup() method can be called only on database '\
                                'entity objects.')
        if obj._table_name.endswith("_meta"):
            raise RRSDatabaseEntityError('lookup() method cannot be called on meta-tables.')

        q = FluentSQLQuery()
        # LEVEL 0 rules
        try:
            lvl_zero_rules = self._lookup_rules.get_rules(type(obj), 0)
        except KeyError:
            if self.logger is not None:
                self.logger.error("Level 0 rules for '%s' not found." % obj._table_name)
            return False
        for rule in lvl_zero_rules:
            attr_present = [item for item in rule.entities if item in obj]
            # if there are no such attrubutes or not the requested count of them,
            # continue to the next rule
            if rule.reqcount > len(attr_present):
                continue
            self._db.refresh()
            for cnt in reversed(range(rule.reqcount, len(attr_present)+1)):
                for attr_comb in combinations(attr_present, cnt):
                    # now select them
                    q.cleanup()
                    q.select("id").from_table(obj._table_name)
                    for attr in attr_comb:
                        try:
                            q.where("%s=" % attr, obj[attr])
                        except FluentSQLQueryError:
                            q.and_("%s=" % attr, obj[attr])
                    q()
                    res = q.fetch_all()
                    if q.count() > 1: # there shouln't be more results than one
                        self.logger.warning("There are more than one identical "\
                        "%ss. List of ID's: %s" % (obj._table_name, str([x[0] for x in res])))
                    if not res or res is None:
                        continue
                    obj['id'] = res[0][0]
                    return True

        # LEVEL 1 rules
        try:
            lvl_one_rules = self._lookup_rules.get_rules(type(obj), 1)
        except KeyError:
            if self.logger is not None:
                self.logger.error("Level 1 rules for '%s' not found." % obj._table_name)
            return False
        # returns type of entity mapped in ent_id_map
        def getetype(ent_id_map, ent):
            for k in ent_id_map.keys():
                e, et = k
                if ent == e:
                    return et
        # these are objects which really are present in the entity
        for rule in lvl_one_rules:
            ent_present = [item for item in rule.entities if item in obj]
            # if there are no such entities or not the requested count of them,
            # continue to the next rule
            if rule.reqcount > len(ent_present):
                continue

            # get all those identifiers
            ent_id_map = {}
            for ent_name in ent_present:
                target = obj[ent_name]
                if type(target) is list and target:
                    # list of relationship objects
                    key = (ent_name, type(target[0]))
                    ent_id_map[key] = []
                    for rel_obj in target:
                        assert len(rel_obj.get_entities()) > 0
                        e = rel_obj.get_entities()[0]
                        if self.lookup(e, level-1):
                            if not key in ent_id_map:
                                ent_id_map[key] = []
                            ent_id_map[key].append(e)
                    if not ent_id_map[key]:
                        del ent_id_map[key]
                elif isinstance(target, _RRSDatabaseEntity):
                    # this is FK - @target is RRS*** object
                    if self.lookup(target, level-1):
                        ent_id_map[(ent_name, type(target))] = [target]
                else:
                    ent_id_map[(ent_name, type(target))] = [target]


            # if we did not found as much as the rules requests, continue
            if rule.reqcount > len(ent_id_map):
                continue
            # try to catch some data from the minimum count of requested entities
            # to match, probably 2
            # if this select spits out too many results (>100), the reqcount level 2
            # is omitted and the process starts again from 3.
            # There has to be a flag, which indicates, that the level 2
            # requested entities returned too many results
            next_reqcount_lvl = False
            ent_keys = [x[0] for x in ent_id_map.keys()]
            for cnt in range(rule.reqcount, len(ent_id_map)+1):
                next_reqcount_lvl = False
                for entity_comb in combinations(ent_keys, cnt):
                    if next_reqcount_lvl: break
                    self._db.refresh() # re-create cursors to drop the loaded data
                    # construct the query
                    q.cleanup()
                    tg_tbl = obj._table_name
                    from_lst = [tg_tbl]
                    q.select("%s.id" % tg_tbl)
                    # recognition of the same table in the query
                    tablecounter = 1
                    for ent in entity_comb:
                        etype = getetype(ent_id_map, ent)
                        # now we have key to the object -> ent_id_map[(ent, etype)]

                        # @ent is instance of RRS****** - 1:N relationship
                        # the object contains id of this entity
                        if issubclass(etype, _RRSDatabaseEntity):
                            o = ent_id_map[(ent, etype)][0]
                            try:
                                q.where("%s.%s_id=" % (tg_tbl, ent), o['id'])
                            except FluentSQLQueryError:
                                q.and_("%s.%s_id=" % (tg_tbl, ent), o['id'])

                        # @ent is fake junction table - it means, that it's
                        # the second side of 1:N relationship - N:1.
                        elif issubclass(etype, _RRSDbEntityRelationship) and etype._fake_table:
                            # TODO
                            return False

                        # @ent is true junction table - this M:N relationship.
                        elif issubclass(etype, _RRSDbEntityRelationship) and not etype._fake_table:
                            j_tbl_uniq_as = None
                            # storage of all acronyms iof junction tables
                            j_tbl_uniq_as_list = []
                            o = None

                            # join together all the found entities - for example:
                            # given publication, two persons (authors), both found
                            # in db so create query which selects ID of publication
                            # which has both - the first AND the second person.
                            for o in ent_id_map[(ent, etype)]:
                                j_tbl_uniq_as = "%s%s" % (etype._table_name, tablecounter)
                                j_tbl_uniq_as_list.append(j_tbl_uniq_as)
                                e_tbl_uniq_as = "%s%s" % (o._table_name, tablecounter)
                                # add table to the list of tables we are joining together
                                from_lst.append("%s AS %s" % (etype._table_name, j_tbl_uniq_as))
                                from_lst.append("%s AS %s" % (o._table_name, e_tbl_uniq_as))
                                try:
                                    q.where("%s.id=" % e_tbl_uniq_as, o['id'])
                                except FluentSQLQueryError:
                                    q.and_("%s.id=" % e_tbl_uniq_as, o['id'])
                                q.and_("%s.%s_id=" % (j_tbl_uniq_as, o._table_name), "%s.id" % e_tbl_uniq_as, True)
                                tablecounter += 1

                            # add the condition that all the junction table ID's of
                            # the entity we are looking for has to be the same - we
                            # are looking not for union, but intersection of them
                            for i in range(0, len(j_tbl_uniq_as_list)):
                                try:
                                    j1 = j_tbl_uniq_as_list[i]
                                    j2 = j_tbl_uniq_as_list[i+1]
                                    q.and_("%s.%s_id=" % (j1, tg_tbl), "%s.%s_id" % (j2, tg_tbl), True)
                                except IndexError:
                                    break
                            # bind junction table.entity_id to id of entity we are looking for
                            q.and_("%s.%s_id=" % (j_tbl_uniq_as, tg_tbl), "%s.id" % tg_tbl, True)

                        # @ent is attribute (int, basestring ect.)
                        else:
                            attr = ent_id_map[(ent, etype)][0]
                            try:
                                q.where("%s.%s=" % (tg_tbl, ent), attr)
                            except FluentSQLQueryError:
                                q.and_("%s.%s=" % (tg_tbl, ent), attr)

                    q.from_table(from_lst)
                    q()
                    search_sql_query = q._sql
                    # now if the total count of probably identical files is higher
                    # than 100, we need to specify it more, so we jump to next
                    # request count level (probably 1->2 or 2->3).
                    if q.count() > 100:
                        next_reqcount_lvl = True
                        continue
                    res = q.fetch_all()
                    if not res:
                        continue
                    elif len(res) == 1:
                        obj['id'] = res[0][0]
                        self.logger.info("Found exactly one result for lookup: %s, params: %s, found ID: %s, SQL: %s" % \
                                        (obj._table_name, str(entity_comb), obj['id'], search_sql_query))
                        return True
                    else:
                        # do some magic stuff here
                        # intelligenty compare the attribute of all returned results
                        # and choose the most similar
                        q.cleanup()
                        id_list = [x[0] for x in res]
                        attrunion = set(["id"])
                        lvl_zero_rules = self._lookup_rules.get_rules(type(obj), 0)
                        # make a list of attributes needed to acomplish the rules
                        # (these are all which are present in rules)
                        for rule in lvl_zero_rules:
                            attrunion = attrunion.union(set(rule.entities))
                        # construct query which loads all needed attributes of all returned ID's
                        q.select(list(attrunion)).from_table(obj._table_name)
                        for _id in id_list:
                            try:
                                q.where("id=", _id)
                            except FluentSQLQueryError:
                                q.or_("id=", _id)
                        q() # perform the query
                        loaded_data = q.fetch_all()

                        similarity = {}
                        # every rule tell us what attributes have to be similar
                        # (or identical)
                        for rule in lvl_zero_rules:
                            attrs = [item for item in rule.entities if item in obj]
                            if rule.reqcount > len(attrs):
                                continue

                            # count every row's similarity (the result is sum of
                            # similarities of their attributes)
                            sim_lst = {}
                            for d in loaded_data:
                                row_similarity = 0.0
                                for attr in attrs:
                                    if attr not in d or d[attr] is None or attr not in obj:
                                        continue
                                    if (d['id'], attr) not in similarity:
                                        s = SequenceMatcher(None, d[attr], obj[attr])
                                        similarity[(d['id'], attr)] = s.ratio()
                                    row_similarity += similarity[(d['id'], attr)]
                                sim_lst[row_similarity] = d['id']
                            # get the most similar row to the object
                            obj['id'] = sim_lst[max(sim_lst.keys())]
                            self.logger.info("Found more than one result for lookup: %s, params: %s, "\
                                             "Choosen ID: %s, SQL: %s" % (obj._table_name, str(entity_comb), obj['id'], search_sql_query))
                            return True


    def add_lookup_rule(self, classinfo, level, ruleset):
        """
        Add new rule (append it to current hard-implemented rules).
        @param rule has to be type IMRule.
        """
        # recognize rule type and add it to the right container
        self._lookup_rules.new_rule(classinfo, level, ruleset)


#-------------------------------------------------------------------------------
# End of class RRSDbImportManager
#-------------------------------------------------------------------------------



if __name__ == "__main__":
    importer_kwargs = {
        'update_rule':  RRSDB_MISSING,  # update only NULL columns
        'lookup_level': LOOKUP_PRECISE, # lookup level 1 (own attrs and fk's)
        'logfile':      'xmlimport.log',
        'module':       'publication_file_data',
        'schema':       'data'
    }
    importer = RRSXMLImporter(importer_kwargs)
    importer.import_xml("/media/Data/Skola/FIT/prace/NLP/xml09/test-700/small/008000e5f34116118197e9b0897303e236eab6d6.xml")
