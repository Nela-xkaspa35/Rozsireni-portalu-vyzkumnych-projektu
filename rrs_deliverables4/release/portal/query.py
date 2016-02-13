#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------        Autor: Lucie Dvorakova      ----------------------#
#-------------------           Login: xdvora1f          ----------------------# 
#----------------- Automaticky aktualizovaný webový portál -------------------#
#------------------- o evropských výzkumných projektech ----------------------#

import ply
import ply.lex
import ply.yacc
import sys

# The list of tokens to be extracted by the QueryLexer and parsed by
# the QueryParser. 
QUERY_TOKENS = [
    # Initial state tokens
    'SPEC_SEPARATOR',
    'ELEM_SEPARATOR',
    'QUOTATION_MARK',
    # String state tokens
    'UNESCAPED',
    'ESCAPE',
    # Escaped state tokens
    'REVERSE_SOLIDUS',
]

class QueryLexer(object):
    '''
    A class-based wrapper around the ply.lex instance.

    The QueryLexer tokenizes an input string and produces LexToken instances
    corresponding to the QUERY_TOKENS values.
    '''

    def __init__(self, **kwargs):
        '''
        Constructs the QueryLexer based on the tokenization rules herein.

        Successful construction builds the ply.lex instance and sets
        self.lexer.
        '''

        self.lexer = ply.lex.lex(module=self, **kwargs)

    # The QueryLexer uses the QUERY_TOKENS values as a contact between
    # the lexer and the parser.
    tokens = QUERY_TOKENS

    # The QueryLexer has three exclusive states:
    #
    #   default:
    #     The default context.
    #   string:
    #     Within quote-delimited strings.
    #   escaped:
    #     A single-use state that treats the next character literally.
    states = (
        ("string", "exclusive"),
        ("escaped", "exclusive")
    )

    # For wrong lexem, an error msg is written and the lexem then skipped
    def t_ANY_error(self, t): 
        last_cr = self.lexer.lexdata.rfind('\n', 0, t.lexpos)
        if last_cr < 0:
            last_cr = 0
        column = (t.lexpos - last_cr) + 1
        print "Illegal character '%s' at line %d pos %d" % \
            (t.value[0], t.lineno, column)
        t.lexer.skip(1) 

    # Don't skip over any tokens inside the default state
    t_ignore = ""

    # Default state tokens
    t_SPEC_SEPARATOR       = r':'                     
    t_ELEM_SEPARATOR       = r'\s+'                  
    t_UNESCAPED            = r'[\x21,\x23-\x39,\x3B-\x5B,\x5D-\xFF]+'

    # Enters the string state on an opening quotation mark 
    def t_QUOTATION_MARK(self, t):
        r'"'
        t.lexer.push_state("string") 
        return t

    # Enter the escaped state on a '\' character
    def t_ESCAPE(self, t):
        r'\x5C'  # '\'
        t.lexer.push_state("escaped")
        return t

    # Don't skip over any tokens inside the string state
    t_string_ignore = ""

    def t_string_UNESCAPED(self, t):
        r'[\x20-\x21,\x23-\x5B,\x5D-\xFF]+'
        return t

    # Exits the string state on an unescaped closing quotation mark
    def t_string_QUOTATION_MARK(self, t):
        r'"'
        t.lexer.pop_state()
        return t

    # Enter the escaped state on a '\' character
    def t_string_ESCAPE(self, t):
        r'\x5C'  # '\'
        t.lexer.push_state("escaped")
        return t

    # Don't skip over any tokens inside the escaped state
    t_escaped_ignore = ""

    def t_escaped_QUOTATION_MARK(self, t):
        r'"'  # '"'
        t.lexer.pop_state()
        return t

    def t_escaped_REVERSE_SOLIDUS(self, t):
        r'\x5C'  # '\'
        t.lexer.pop_state()
        return t

    def t_escaped_SPEC_SEPARATOR(self, t):
        r':'  # ':'
        t.lexer.pop_state()
        return t

    def tokenize(self, data, *args, **kwargs):
        '''
        Invoke the lexer on an input string an return the list of tokens.
        '''

        self.lexer.input(data)
        tokens = list()
        while True:
            token = self.lexer.token()
            if not token: 
                break
            tokens.append(token)

        return tokens

class QueryParser(object):
    '''
    A class-based wrapper around the ply.yacc instance.

    '''

    def __init__(self, lexer=None, **kwargs):
        '''
        Constructs the QueryParser based on the grammar contained herein.

        Successful construction builds the ply.yacc instance and sets
        self.parser.
        '''

        self.has_errors = False

        if lexer is not None:
            if isinstance(lexer, QueryLexer):
                self.lexer = lexer.lexer
            else:
                # Assume that the lexer is a ply.lex instance or similar
                self.lexer = lexer
        else:
            self.lexer = QueryLexer().lexer

        self.parser = ply.yacc.yacc(module=self, **kwargs)

    # The QueryParser uses the QUERY_TOKENS values as a contact between
    # the lexer and the parser.
    tokens = QUERY_TOKENS

    # Precedence rules for the arithmetic operators
    precedence = (
        ('left','SPEC_SEPARATOR'),
        ('left','ELEM_SEPARATOR'),
        ('left','QUOTATION_MARK'),
        ('left','UNESCAPED', 'ESCAPE')
    )

    # Define the parser
    def p_query(self, p):
        '''
        query : qelem
              | query ELEM_SEPARATOR qelem
        '''

        if len(p) == 2:
            p[0] = [ p[1] ]
        else:
            p[0] = p[1] + [ p[3] ]

    def p_qelem(self, p):
        '''
        qelem : string spec_opt
        '''

        p[0] = (p[1], p[2])

    def p_spec_opt(self, p):
        '''
        spec_opt :
                 | SPEC_SEPARATOR string
        '''

        if len(p) == 1:
            p[0] = None
        else:
            p[0] = p[2]

    def p_string(self, p):
        '''
        string : chars
               | QUOTATION_MARK chars QUOTATION_MARK
        '''

        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = p[2]

    def p_chars(self, p):
        '''
        chars : char
              | chars char
        '''

        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = p[1] + p[2]

    def p_char(self, p):
        '''
        char : UNESCAPED
             | ESCAPE QUOTATION_MARK
             | ESCAPE REVERSE_SOLIDUS
             | ESCAPE SPEC_SEPARATOR
        '''

        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = p[2]

    def p_error(self, p): 
        self.has_errors = True
        print "Syntax error at '%s'" % p

        ## Try to recover
        #while True:
        #    # Get next token
        #    tok = self.lexer.token()
        #    if not tok or tok.type == 'ELEM_SEPARATOR':
        #        break
        #self.parser.errok()

        #return tok

    # Invoke the parser
    def parse(self, data, lexer=None, *args, **kwargs):
        '''
        Parse the input query data."
        '''

        self.has_errors = False
        if lexer is None:
            lexer = self.lexer
        return self.parser.parse(data, lexer=lexer, *args, **kwargs)

    def status(self):
        return not self.has_errors

# Maintain a reusable parser instance
query_parser = None

class Query():
    def __init__(self, s):
        '''
        Builds a query from the given string.
        '''

        global query_parser
        valid_specs = ["country", "programme", "subprogramme", "coordinator",
            "participant", "year"]

        self.keywords = []
        self.specifications = dict({})
        self.has_errors = False

        # Parse the input string
        if query_parser is None:
            query_parser = QueryParser()

        # Go through parsed elements
        s = s.strip()
        if s == "":
            self.keywords.append("")
            return
        
        query_elems = query_parser.parse(s)
        #if query_elems == None:
        #    return

        self.has_errors = not query_parser.status()
        for (key, val) in query_elems:
            #print val
            #print key
            if val == None and key != "":
                self.keywords.append(key)
            elif val != None and val != "" and key in valid_specs:
                #vals = val.split('&')
                #print vals
                #for v in vals:
                self.specifications[key] = val
                #print specifications[key]
            elif key == "":
                self.keywords.append("")              
            else:
                self.has_errors = True

    def getSpecification(self, key):
        '''
        Gets a specification with the given key.
        '''
       
        return self.specifications.get(key)

    def getKeywords(self):
        '''
        Gets all keywords of the query.
        '''

        return list(self.keywords)

    def getStatus(self):
        '''
        Reports status of the parsing        
        '''

        return not self.has_errors


def parse(s):
    '''
    Parse a string-like object and return the corresponding python structure.
    '''

    return Query(s)

def parse_file(f):
    '''
    Parse a file-like object and return the corresponding python structure.
    '''

    return parse(f.read())

def main(argv):
    if len(argv) > 1:
        for filename in argv[1:]:
            q = parse_file(open(filename))
    else:
        q = parse_file(sys.stdin)
    
    print q.getKeywords()
    print q.getSpecification("prog")
    print q.specifications
    print q.has_errors

if __name__ == '__main__':
    main(sys.argv)

