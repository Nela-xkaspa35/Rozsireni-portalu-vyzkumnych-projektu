#! /usr/bin/python

"""
This module is being used for parsing CSS (cascade style sheet) and offers
interface for creating font style and visibility of text on the page.

Some CSS syntax description and terminology:
Cascade style sheet consists of a list of rules. This rule is made by selectors
and the list of definitions. Definition consists of property, colon and a value.
Definitions are splitted by semicolon.

Example of a rule (thank you, wiki):
[#.]?selector [, selector2, ...][:pseudo-class] {
  property: value; /* << declaration (one row and semicolon) */
 [property2: value2;
  ...]
}

"""

__modulename__ = "csstools"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$1.4.2011 17:46:40$"


import re # regular expressions
import math # doing some math..
import string
from urlparse import urlparse

# load rrs libraries
from crawler import Crawler, FileDownloader


try:
    import psyco
    psyco.full()
except ImportError:
    pass
except:
    sys.stderr.write("An error occured while starting psyco.full()")


# TODO's:
# font-size: smaller, larger, % (percentage)
# getting and keeping table semantics
# inline css styles
# CSS font styles:
#   letter-spacing
#   line-height
#   text-align
#   text-indent
#   text-transform
#   white-space
#   word-spacing



class CSSError(Exception):
    pass

class CSSElementStyleError(CSSError):
    pass

class CSSColorError(Exception):
    pass

class CSSStyleError(AttributeError):
    pass

# ------------------------------------------------------------------------------
# end of Exception declarations
# ------------------------------------------------------------------------------


class CSSColor(object):
    """
    This class is a color-handler for cascade styles. Methods can parse color in
    hexadecimal, rgb and textual format. Also the output can be in hex, rgb and text.
    """

    # dictionary mapping textual representation of colors to hex.
    text2hex = { 'gold': '#FFD700', 'firebrick': '#B22222', 'yellow': '#FFFF00',
                 'darkolivegreen': '#556B2F', 'darkseagreen': '#8FBC8F',
                 'mediumvioletred': '#C71585', 'mediumorchid': '#BA55D3',
                 'chartreuse': '#7FFF00', 'mediumslateblue': '#7B68EE',
                 'black': '#000000', 'springgreen': '#00FF7F',
                 'crimson': '#DC143C', 'lightsalmon': '#FFA07A',
                 'brown': '#A52A2A', 'turquoise': '#40E0D0',
                 'olivedrab': '#6B8E23', 'cyan': '#00FFFF',
                 'silver': '#C0C0C0', 'skyblue': '#87CEEB',
                 'gray': '#808080', 'darkturquoise': '#00CED1',
                 'goldenrod': '#DAA520', 'darkgreen': '#006400',
                 'darkviolet': '#9400D3', 'darkgray': '#A9A9A9',
                 'lightpink': '#FFB6C1', 'teal': '#008080',
                 'darkmagenta': '#8B008B', 'lightgoldenrodyellow': '#FAFAD2',
                 'lavender': '#E6E6FA', 'yellowgreen': '#9ACD32',
                 'thistle': '#D8BFD8', 'violet': '#EE82EE', 'navy': '#000080',
                 'orchid': '#DA70D6', 'blue': '#0000FF', 'ghostwhite': '#F8F8FF',
                 'honeydew': '#F0FFF0', 'cornflowerblue': '#6495ED',
                 'darkblue': '#00008B', 'darkkhaki': '#BDB76B',
                 'indianred ': '#CD5C5C', 'mediumpurple': '#9370D8',
                 'cornsilk': '#FFF8DC', 'red': '#FF0000', 'bisque': '#FFE4C4',
                 'slategray': '#708090', 'lime': '#00FF00', 'khaki': '#F0E68C',
                 'wheat': '#F5DEB3', 'deepskyblue': '#00BFFF',
                 'darkred': '#8B0000', 'steelblue': '#4682B4',
                 'aliceblue': '#F0F8FF', 'gainsboro': '#DCDCDC',
                 'mediumturquoise': '#48D1CC', 'floralwhite': '#FFFAF0',
                 'coral': '#FF7F50', 'purple': '#800080', 'lightgrey': '#D3D3D3',
                 'darksalmon': '#E9967A', 'beige': '#F5F5DC',
                 'azure': '#F0FFFF', 'lightsteelblue': '#B0C4DE',
                 'oldlace': '#FDF5E6', 'greenyellow': '#ADFF2F',
                 'royalblue': '#4169E1', 'lightseagreen': '#20B2AA',
                 'mistyrose': '#FFE4E1', 'sienna': '#A0522D',
                 'lightcoral': '#F08080', 'orangered': '#FF4500',
                 'navajowhite': '#FFDEAD', 'darkcyan': '#008B8B',
                 'palegreen': '#98FB98', 'burlywood': '#DEB887',
                 'seashell': '#FFF5EE', 'mediumspringgreen': '#00FA9A',
                 'fuchsia': '#FF00FF', 'papayawhip': '#FFEFD5',
                 'blanchedalmond': '#FFEBCD', 'lightblue': '#ADD8E6',
                 'aquamarine': '#7FFFD4', 'white': '#FFFFFF',
                 'darkslategray': '#2F4F4F', 'ivory': '#FFFFF0',
                 'dodgerblue': '#1E90FF', 'lemonchiffon': '#FFFACD',
                 'chocolate': '#D2691E', 'orange': '#FFA500',
                 'forestgreen': '#228B22', 'slateblue': '#6A5ACD',
                 'olive': '#808000', 'indigo': '#4B0082',
                 'mintcream': '#F5FFFA', 'antiquewhite': '#FAEBD7',
                 'darkorange': '#FF8C00', 'cadetblue': '#5F9EA0',
                 'moccasin': '#FFE4B5', 'limegreen': '#32CD32',
                 'saddlebrown': '#8B4513', 'darkslateblue': '#483D8B',
                 'lightskyblue': '#87CEFA', 'deeppink': '#FF1493',
                 'plum': '#DDA0DD', 'aqua': '#00FFFF', 'lightcyan': '#E0FFFF',
                 'darkgoldenrod': '#B8860B', 'maroon': '#800000',
                 'sandybrown': '#F4A460', 'magenta': '#FF00FF',
                 'tan': '#D2B48C', 'rosybrown': '#BC8F8F', 'pink': '#FFC0CB',
                 'palevioletred': '#D87093', 'mediumseagreen': '#3CB371',
                 'dimgray': '#696969', 'powderblue': '#B0E0E6',
                 'seagreen': '#2E8B57', 'snow': '#FFFAFA', 'peru': '#CD853F',
                 'mediumblue': '#0000CD', 'midnightblue': '#191970',
                 'paleturquoise': '#AFEEEE', 'palegoldenrod': '#EEE8AA',
                 'whitesmoke': '#F5F5F5', 'darkorchid': '#9932CC',
                 'salmon': '#FA8072', 'lightslategray': '#778899',
                 'lawngreen': '#7CFC00', 'lightgreen': '#90EE90',
                 'tomato': '#FF6347', 'hotpink': '#FF69B4',
                 'lightyellow': '#FFFFE0', 'lavenderblush': '#FFF0F5',
                 'linen': '#FAF0E6', 'mediumaquamarine': '#66CDAA',
                 'green': '#008000', 'blueviolet': '#8A2BE2',
                 'peachpuff': '#FFDAB9'}

    d = {'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15}

    def __init__(self, rgb=(0.0, 0.0, 0.0)):
        self.r = rgb[0]
        self.g = rgb[1]
        self.b = rgb[2]


    def _fromhex(self, h):
        """
        Because in python 2.5.5 float.fromhex wasnt implemented, here is some
        stupid solution. FIXME!
        """
        base = int(0)
        try:
            for i in range(1, len(h)+1):
                hexa = h[-i]
                if hexa in string.letters:
                    hexa = CSSColor.d[hexa.lower()]
                base += int(hexa) * math.pow(16, int(i)-1)
            return base
        except Exception, e:
            raise CSSColorError(e)


    def set_hex(self, color):
        """
        Stores color in hex into the object. Hex can be in 24bit format or in 12 bit:
        #10a8ff or even  #ff0.
        """
        try:
            fromhex = float.fromhex
        except:
            fromhex = self._fromhex
        # FIXME is this 12bit handling OK?
        if len(color) == 4:
            r, g, b = fromhex(color[1]), fromhex(color[2]), fromhex(color[3])
            self.r = (r * float(16)) + r
            self.g = (g * float(16)) + g
            self.b = (b * float(16)) + b
        else:
            self.r = fromhex(color[1:3])
            self.g = fromhex(color[3:5])
            self.b = fromhex(color[5:7])


    def set_rgb(self, rgb):
        """
        rgb has to be a tuple (r, g, b)
        """
        self.r = float(rgb[0])
        self.g = float(rgb[1])
        self.b = float(rgb[2])


    def to_hex(self):
        """
        Returns hexadecimal representation of color stored in the object.
        """
        return "#" + hex(int(self.r))[2:] + hex(int(self.g))[2:] + hex(int(self.b))[2:]


    def to_rgb(self):
        """
        Sets color to the object in rgb format.
        """
        return (self.r, self.g, self.b)


    def set_text(self, text):
        """
        Sets color to the object in textual format. If no appropriate item found,
        throws CSSColorError.
        """
        try:
            h = CSSColor.text2hex[text.lower()]
        except:
            raise CSSColorError('No such CSS color: '+text)
        self.set_hex(h)


    def to_text(self):
        """
        Returns textual representation of color. If not found (could be some
        weird color, which has not any textual repr), returns None.
        """
        h = self.to_hex()
        for k in CSSColor.text2hex:
            if CSSColor.text2hex[k] == h: return k
        return None


    def __str__(self):
        return "<"+__modulename__+".CSSColor(rgb="+str((self.r, self.g, self.b))+") instance>"

# ------------------------------------------------------------------------------
# end of class CSSColor
# ------------------------------------------------------------------------------


class CSSRule(object):
    """
    This class represents one rule of CSS rule-list. Rule contains list of
    selectors and list of declarations.
    """
    def __init__(self):
        self.declarations = []
        self.selectors = []

    def add_selector(self, s):
        if type(s) is not CSSSelector:
            raise CSSError("Selector has to be type CSSSelector.")
        self.selectors.append(s)

    def add_declaration(self, d):
        if type(d) is not CSSDeclaration:
            raise CSSError("Declaration has to be type CSSDeclaration.")
        self.declarations.append(d)

    def get_declarations(self):
        return self.declarations

    def get_selectors(self):
        return self.selectors


# ------------------------------------------------------------------------------
# end of class CSSRule
# ------------------------------------------------------------------------------


class CSSDeclaration(object):
    """
    This class represents one declaration in css rule.
    Defines slots not to make __dict__ to safe some space in memory.
    """
    __slots__ = ["property", "value"]

    def __init__(self, property, value):
        self.property = property
        self.value = value

# ------------------------------------------------------------------------------
# end of class CSSDeclaration
# ------------------------------------------------------------------------------


class CSSSelector(object):
    """
    This class represents one selector in css rule.
    Defines slots not to make __dict__ to safe some space in memory.
    """
    # identificators and also a css priority
    TAG = 0
    CLASS = 1
    ID = 2
    __slots__ = ["type", "name"]

    def __init__(self, type_, name):
        if type_ not in (CSSSelector.TAG, CSSSelector.CLASS, CSSSelector.ID):
            raise CSSError("Selector type has to be one of constants: TAG, CLASS, ID.")
        self.type = type_
        self.name = name

# ------------------------------------------------------------------------------
# end of class CSSSelector
# ------------------------------------------------------------------------------


class CascadeStyleSheet(object):
    """
    This class represents the whole cascade style sheet with all declarations.
    """
    def __init__(self, list_of_rules):
        self._mapper = {}
        self._rules = list_of_rules
        for rule in self._rules:
            for s in rule.get_selectors():
                self._mapper[s] = rule.get_declarations()


    def get_css_by_selector(self, selector):
        return self._mapper[selector]


    def get_rules(self):
        return self._rules

# ------------------------------------------------------------------------------
# end of class CascadeStyleSheet
# ------------------------------------------------------------------------------


class CSSTokenizer(object):
    """
    Main scanner for CSSParser. Output ofg
    """
    def __init__(self):
        self.source = None
        self._rules = []
        self._ptr = 0
        self.cleaner = _MyCSSCleaner()


    def parse_source(self, src):
        self.source = src
        self._ptr = 0
        self._rules = []
        self._parse()


    def _clean_comments(self):
        self.source = re.sub("/\*([^\*]|\*[^/])*\*/", "", self.source)


    def _parse_declarations(self, rule):
        d = []
        field = (rule.split("{")[1]).split("}")[0]
        if ";" in field:
            attrs = re.findall("[a-z\-]+\:[^;]+;", field, re.I)
        else:
            attrs = [field]
        for a in attrs:
            # not attribute in style definition
            if ":" not in a: continue
            # parse the attribute
            sp = a.split(":")
            _val = (self.cleaner.clean(sp[1])).replace(";", "")
            valsp = _val.split()
            _val = re.sub("\![ ]*important", "", valsp[0])
            d.append(CSSDeclaration(self.cleaner.clean(sp[0]), _val))
        return d


    def _parse_selectors(self, rule):
        # - contextual selectors (like .myclass span a) NOT SUPPORTED
        # - pseudo-classes and pseudo-elements (a:hover) NOT SUPPORTED
        # - #style>body directive NOT SUPPORTED
        res = []
        selector_field = self.cleaner.clean(rule.split("{")[0])
        names = selector_field.split(",")
        for n in names:
            n = n.rstrip(' ').lstrip(' ')

            # TODO parse contextual selectors, If parsed, delete this row
            if ' ' in n: continue

            if n[0] not in ("#", "."):
                type_ = CSSSelector.TAG
                name_ = n.lower()
                # TODO parse selectors like a.class.class or span#id
                #spl = n.split(".")
                #_name = spl[0].lower()
                #if len(spl) > 1:
                #    _name += "." + "".join(spl[1:])
                #    type_ = CSSSelector.CLASS
            elif n[0] == "#":
                type_ = CSSSelector.ID
                name_ = n[1:]
            elif n[0] == ".":
                type_ = CSSSelector.CLASS
                name_ = n[1:]
            res.append(CSSSelector(type_, name_))
        return res


    def _parse(self):
        self._clean_comments()
        _raw_rules = re.findall("[\.#]?[a-z0-9][ a-z0-9\.-_]*[\n\t\r ]*{[^}]+}", self.source, re.I)
        for _rule in _raw_rules:
            r = CSSRule()
            r.declarations = self._parse_declarations(_rule)
            r.selectors = self._parse_selectors(_rule)
            self._rules.append(r)


    def get_next_rule(self):
        self._ptr += 1
        try:
            self._rules[self.ptr - 1]
        except IndexError:
            return None

    def get_rules(self):
        return self._rules

    def get_sheet(self):
        return CascadeStyleSheet(self._rules)

#-------------------------------------------------------------------------------
# End of class CSSTokenizer
#-------------------------------------------------------------------------------


class _MyCSSCleaner(object):

    def clean(self, text):
        """
        Cleans text
        """
        if text == None: return None
        plaintext = re.sub('['+string.whitespace+'\xc2\xa0]+', ' ', text)    # smaze tabulatory a odradkovani
        clear_plaintext = re.sub('[ ]+', ' ', plaintext) # smaze dlouhe mezery
        return clear_plaintext.rstrip(' ').lstrip(' ')

    def contains_text(self, tag):
        """
        Testing if tag contains some useful text (non-whitechar)
        """
        try:
            if isinstance(tag, basestring):
                txt = tag
            else:
                txt = tag.text
            if re.search("[\w]+", txt, re.I): return True
        except:
            return False

#-------------------------------------------------------------------------------
# End of class _MyCSSCleaner
#-------------------------------------------------------------------------------


class CSSParser(object):
    """
    This class is a CSS parser of css **font** declarations.

    CSSParser instantiates his own Crawler, because of downloading extern
    cascade style sheet files.

    Supported are:
        DECLARATIONS:
        External css declarations <link> and @import
        Internal css declarations in <style type='text/css'>

        PARSING PRIORITY (where 1=lowest and 3 = highest priority):
        1. TAG
        2. CLASS
        3. ID

        PARSED SELECTORS:
        tag                 a {}
        class               .myClass {}
        id                  .myNewId {}
        tag.class           a.myClass{}
        grouped selectors:  a, b, .myClass {}


    Not supported:
        Specificity (parsing is only on basis of priority which is shown above)
        Contextual selectors (like .myclass span a)
        Pseudo-classes and pseudo-elements (a:hover)
        Directive #style>body (whats the name of this??)
        Inline css declarations - THIS IS IN TODO!
    """

    def __init__(self):
        self._crawler = Crawler()
        self._crawler.set_handler(FileDownloader)
        self.cleaner = _MyCSSCleaner()
        self._last_url = None
        self._url = None
        self._rules = []
        self.cssfiles = []
        # init tokenizer (scanner)
        self.tokenizer = CSSTokenizer()
        # css style parser converts css rules to css styles
        self.cssstyleparser = _CSSStyleParser()
        # element -> font style mapper maps lxml elements to CSSStyle instances
        self._elem2style_map = Element2CSSStyleMapper()


    def _identical_domain(self, url1, url2):
         if url1 == None or url2 == None:
             return False
         p1 = urlparse(url1)
         p2 = urlparse(url2)
         return p1.netloc == p2.netloc


    def _get_onpage_styles(self):
        stylefields = self.elemtree.findall(".//style")
        _css = ''
        for style in stylefields:
            if style.get('type') != None and style.get('type') == 'text/css':
                _css += style.text
        self.tokenizer.parse_source(_css)
        self._rules.extend( self.tokenizer.get_rules() )


    def _get_css_files(self):
        # Method returns True if some css are to download, False otherwise.
        self.last_cssfiles = self.cssfiles
        if self.ident_last_domain:
            # If we had last URL's domain identical like this url, we have probably
            # the same css files. So check it!
            if self.cssfiles and set(self.cssfiles) == set(self.last_cssfiles):
                return False
        else:
            # delete css file list
            self.cssfiles = []
        # handle css 2.0 imports of extern files
        styles = self.elemtree.findall(".//style")
        for style in styles:
            if style.get('type') != None and style.get('type') == 'text/css':
                if style.text is not None and re.search("@import", style.text, re.I):
                    urlre = re.search('^(http|https|ftp)\://[a-z0-9\-\.]+\.[a-z]{2,3}(:[a-z0-9]*)?/?' + \
                                      '([a-z0-9\-\._\?\,\'/\\\+&amp;%\$#\=~])*$', style.text, re.I)
                    urlre != None and self.cssfiles.append(urlre.group(0))
        # handle usual <link> declarations of extern css files
        links = self.elemtree.findall(".//link")
        for link in links:
            if link.get('type') != None and link.get('type') == 'text/css' \
               and link.get('href') != None:
                link.make_links_absolute(self._url)
                self.cssfiles.append(link.get('href'))
        return len(self.cssfiles) != 0


    def parse(self, elemtree, url):
        """
        Main method for parsing.
        @param elemtree - lxml.etree._ElementTree of the page which is to be parsed
        @param url - URL identifier of the page
        @return CSSStyleContainer object with parsed css declarations.
        """
        # css parsing order
        # 1. Browser default
        # 2. External style sheet
        # 3. Internal style sheet
        # 4. Inline style FIXME not supported yet!

        self.elemtree = elemtree
        self._url = url

        # make all links absolute
        root = self.elemtree.getroot()
        root.make_links_absolute(self._url)

        # If we had last URL's domain identical like this url, we are probably
        # on the same site but different web page. There is very high probability
        # that we will have identical css files, so there's no need to download
        # and parse them again.
        if not self._identical_domain(self._url, self._last_url):
            self._styles = []
            self.ident_last_domain = False
        else:
            self.ident_last_domain = True
        # get css files if needed
        if self._get_css_files():
            # download css sheets
            files = self._crawler.start(self.cssfiles)
            for f in self.cssfiles:
                try:
                    # and parse them
                    self.tokenizer.parse_source(files[f])
                    self._rules.extend( self.tokenizer.get_rules() )
                except TypeError:
                    pass
        self._last_url = self._url
        # parse on-page definitions
        self._get_onpage_styles()
        # create cascade style sheet
        self._sheet = CascadeStyleSheet(self._rules)
        # stylesheet is instance of CSSSelector2CSSStyleMapper
        self._selector2style_map = self.cssstyleparser.get_style_mapper(self._sheet)
        # parse font styles

        for elem in root.iterdescendants():
            style = CSSStyle()
            style.parse_element(elem, self._selector2style_map, self._elem2style_map)
            elem.style = style


    def get_sheet(self):
        return self._sheet

# ------------------------------------------------------------------------------
# end of class CSSParser
# ------------------------------------------------------------------------------


# The next part of this module is targeted to CSS inheritance. Main class is
# CSSStyle, which contains (after parsing) the final style of the element.
# CSSStyle determines also final visibility of the text or font on the page.
#
# Next classes are Element2CSSStyleMapper and CSSStyleParser. Output of the
# CSSStyleParser is CSSSelector2CSSStyleMapper instance, which maps selector to
# CSSStyle.
#
# Element2CSSStyleMapper maps instances of lxml.etree._Element to CSSStyle objecs
# and after parsing you can get final style of element.


class CSSStyle(object):
    """
    This class keeps information about style of the font (and text of course)
    which has this CSSStyle object assigned.
    Stored informations (css):
        - font-size
        - font-style
        - font-color (instance of CSSColor)
        - font-variant
        - font-decoration
        - font-family (not handled yet)
        - importance (not a css style, but here are stored other informations i.e.:
                  importance of h[1-6] tags etc.)
    """

    # Styles
    S_NORMAL = 1.0
    ITALIC = 2.0
    # Here's some exception: EM is not font-style, but logical tag. Visually it
    # seems to be ITALIC, so for our purposes we consider it to be italic font
    # with the same visibility (2.0), but with higher logical importance (+0.5)
    EM = 2.5

    # Variant
    V_NORMAL = 1.0
    SMALL_CAPS = 1.5

    # Decoration
    D_NORMAL = 1.0
    # semantic importance of striked text is minimized
    # because the value of text content is false.
    STRIKE = 0.01
    UNDERLINE = 2.0

    # Weights
    W_NORMAL = 500
    BOLDER = 600
    LIGHTER = 300
    BOLD = 800
    # Again exception: Strong isn't defined as font-weight
    # (it is logical tag), but displays as bold and has higher importance than
    # bold for our purposes
    STRONG = 900

    # Size
    XX_SMALL = 8 # shouldnt be 6?
    X_SMALL = 10 # shouldnt be 8?
    SMALL = 13   # shouldnt be 11?
    MEDIUM = 16  # shouldnt be 14?
    LARGE = 22
    X_LARGE = 28
    XX_LARGE = 36
    # NOT IMPLEMENTED YET
    SMALLER = 0.7
    LARGER = 1.3

    __slots__ = ('font_weight', 'font_style', 'font_size', 'font_color', 'font_variant',
                 'font_decoration', 'font_family', 'importance')

    def __init__(self, weight=None, size=None, style=None, color=None,
                       variant=None, decor=None, family=None): # future use

        if weight != None and (weight < 100 or weight > 900):
            raise CSSStyleError("Value of font weight out of range.")
        if style != None and (style < CSSStyle.S_NORMAL or style > CSSStyle.EM):
            raise CSSStyleError("Bad font style.")
        self.font_weight = weight
        self.font_style = style
        self.font_size = size
        self.font_color = color
        self.font_variant = variant
        self.font_decoration = decor
        self.font_family = family # FUTURE
        self.importance = 1.0


    def set_font_weight(self, weight):
        self.font_weight = weight


    def set_font_style(self, style):
        self.font_style = style


    def set_font_size(self, size):
        self.font_size = size


    def set_font_color(self, color):
        self.font_color = color


    def set_font_variant(self, variant):
        self.font_variant = variant


    def set_font_decoration(self, decor):
        self.font_decoration = decor


    def set_importance(self, importance):
        self.importance = importance


    def get_params(self):
        return (self.font_weight, self.font_style, self.font_size, self.font_color,
                self.font_variant, self.font_decoration, self.font_family, self.importance)


    def reset(self):
        """
        Resets all attributes of FontStyle to None.
        """
        self.font_weight = None
        self.font_style = None
        self.font_size = None
        self.font_color = None
        self.font_variant = None
        self.font_decoration = None
        self.font_family = None # FUTURE
        self.importance = 1.0


    def unchanged(self):
        """
        Returns true, if object stays in unchanged state (like after init without
        any params in construcotr or after reset(). Otherwise return false.
        """
        return not any([self.font_weight, self.font_size, self.font_style, \
                        self.font_variant, self.font_color, self.font_decoration])


    def get_visibility(self):
        """
        Returns number representing visual importance of font.
        Big and fat red font returns higher value than small usual black font.
        1.0 = normal font
        > 1.0 visible font. Important. > 4.0 is probably header or very important message.
        < 1.0 small font, not important

        This value is very informal and sometimes doesn't reflect real visiblity
        of the element on the page, but in most of tested cases it does.
        """
        (w, si, st, c, v, d) = self._getparam()
        r = math.pow((float(w)/float(CSSStyle.W_NORMAL)), 1.8) * float(v) * \
               math.pow((float(si)/float(CSSStyle.MEDIUM)), 3) * float(d) * \
               float(st) * float(self._get_color_visibility()) * float(self.importance)
        return r


    def inherite(self, ancestor):
        """
        Object, which calls method inherite(ancestor), inherites all attributes
        (which are not None) from ancestor.
        """
        if not isinstance(ancestor, CSSStyle):
            raise AttributeError("ancestor has to be instance of FonstStyle class.")
        (w, st, si, c, v, d, f, i) = ancestor.get_params()
        if self.font_weight == None: self.font_weight = w
        if self.font_size == None: self.font_size = si
        if self.font_style == None: self.font_style = st
        if self.font_color == None: self.font_color = c
        if self.font_variant == None: self.font_variant = v
        if self.font_decoration == None: self.font_decoration = d
        self.importance *= i
        # FIXME this isnt correct !!!!!! Check out, why importance is sometimes inf.
        if self.importance > 2.0: self.importance = 2.0


    def copy(self, style):
        """
        Makes from calling object copy of style. (Overwrites all attribues and
        also them, which are None.
        """
        # violating encapsulation.
        self.font_weight = style.font_weight
        self.font_size = style.font_size
        self.font_style = style.font_style
        self.font_color = style.font_color
        self.font_variant = style.font_variant
        self.font_decoration = style.font_decoration
        self.importance = style.importance


    def parse_element(self, elem, stylesheet=None, element_styles=None):
        """
        This method parses lxml.Element and his params to get complex information
        about display-style of fonts inside. Gets class, id and tag informations,
        searches for saved CSSStyles and inherits all properties from parents
        of given Element.
        """
        def _parse_elem_semantics(elem):
            types = (CSSStyle.SMALL, CSSStyle.MEDIUM, CSSStyle.LARGE,
                     CSSStyle.X_LARGE, CSSStyle.XX_LARGE)
            _fs = CSSStyle()
            # handle strong and bold (strong is logical tag, but affects)
            if elem.tag == 'strong':
                _fs.set_font_weight( CSSStyle.STRONG )
            elif elem.tag == 'b':
                _fs.set_font_weight( CSSStyle.BOLD )
            # italic
            elif elem.tag == 'em': _fs.set_font_style( CSSStyle.EM )
            elif elem.tag == 'i': _fs.set_font_style( CSSStyle.ITALIC )
            # height of font
            elif elem.tag == 'big': _fs.set_font_size( CSSStyle.LARGE )
            elif elem.tag == 'small': _fs.set_font_size( CSSStyle.SMALL )
            # strike
            elif elem.tag in ('strike', 's'):
                _fs.set_font_decoration( CSSStyle.STRIKE )
            # underline
            elif elem.tag == 'u': _fs.set_font_decoration( CSSStyle.UNDERLINE )

            # handle <font> tag
            elif elem.tag == 'font':
                if elem.get('size') != None:
                    s = int(elem.get('size'))
                    if s < 6: _fs.set_font_size(types[s-1])
                if elem.get('color') != None:
                    c = CSSColor()
                    try:
                        c.set_text(elem.get('color'))
                        _fs.set_font_color(c)
                    except CSSColorError:
                        pass
                # TODO parse style attribute!!
            # handle header
            elif re.search("h[1-6]", elem.tag, re.I):
                level = int(re.search("[1-6]", elem.tag).group(0))
                if level == 1: _fs.set_font_size( CSSStyle.XX_LARGE )
                elif level == 2: _fs.set_font_size( CSSStyle.X_LARGE )
                elif level == 3: _fs.set_font_size( CSSStyle.LARGE )
                elif level == 4: _fs.set_font_size( CSSStyle.MEDIUM + 3 )
                else: _fs.set_font_size( CSSStyle.MEDIUM )
                _fs.set_importance(2.0)
                _fs.set_font_weight(CSSStyle.STRONG)
            # table header is also important
            elif elem.tag == 'th':
                _fs.set_font_weight(CSSStyle.BOLD)

            return _fs

        ##########
        # method
        ##########

        # FIXME delete this when cleaning code in wrap() method will be implemented
        if str(elem.tag) == '<built-in function Comment>': return

        # call singleton to get global storage of element css-styles
        #element_styles = Element2CSSStyleMapper()

        # helper storage of parent styles
        parent_styles = {}
        parent_order = []

        # get all parents of this element
        p = elem
        while p != None:
            # if element p was already parsed,  dont go up the tree (simpy we dont
            # have to)
            _parentstyle = element_styles.get_elem_style(p)
            if _parentstyle != None:
                parent_styles[str(p)] = _parentstyle
                parent_order.append(str(p))
                break

            # new styles we will process
            _class_css, _id_css, result_css = None, None, CSSStyle()
            _this_style = CSSStyle()

            # get tag style from css
            _tag = p.tag
            _tag_css = stylesheet.get_style(_tag, CSSSelector.TAG)

            # get style of class selector
            if p.get('class') != None:
                _class = p.get('class')
                _class_css = stylesheet.get_style(_class, CSSSelector.CLASS)
                if _class_css == None:
                    # get style of tag.class selector
                    _class_css = stylesheet.get_style(_tag+"."+_class, CSSSelector.CLASS)

            # get style of id selector
            if p.get('id') != None:
                _id = p.get('id')
                _id_css = stylesheet.get_style(_id, CSSSelector.ID)

            # get tag style from tag semantic
            _this_style = _parse_elem_semantics(p)

            # put all styles together in the right order
            _order = (_this_style, _tag_css, _class_css, _id_css)
            for c in _order:
                try:
                    c.inherite(result_css)
                    result_css = c
                except AttributeError: pass
            # store textual representation of this tag
            parent_styles[str(p)] = result_css
            parent_order.append(str(p))

            # go to next parent
            p = p.getparent()

        # Create parent inherited styles and finally this tag's style.
        # We walk over parents from second highest element in tree and all params
        # are inherited. If we're on tag and if we have finally inherited all
        # attributes, we store {element:CSSStyle} to element_styles (which is
        # singleton instance of Element2CSSStyleMapper)
        _len = len(parent_order)
        for i in range(2, _len + 1):
            # now we ask: is this tag's style already stored?
            _parent_final_style = element_styles.get_elem_style(parent_order[-i+1])
            if _parent_final_style != None: # if yes
                parent_styles[parent_order[-i]].inherite(_parent_final_style)
                # add this element to global storage (final inheritance for sure)
                element_styles.add_elem_style(parent_order[-i], parent_styles[parent_order[-i]])
            else:
                # if not stored, inherite from parent
                parent_styles[parent_order[-i]].inherite(parent_styles[parent_order[-i+1]])
                # add parent to global storage
                element_styles.add_elem_style(parent_order[-i+1], parent_styles[parent_order[-i+1]])

        # store inherited properties to THIS CSSStyle object
        # parent_order[0] == this tag's name with address (textual representation)
        # parent_styles[parent_order[0]] == last inherited style (and of course
        # this style)
        self.copy(parent_styles[parent_order[0]])


    def _get_color_visibility(self):
        """
        Returns relative visibility of font on page. This value is empiric and
        cannot be evaluated. In the 3D space of RGB font there are many objects
        with different subjective visibilities, so it is impossible to construct
        exact vector space and calculate this visibility.
        """
        if self.font_color == None:
            return 1.0

        # hack: because we dont check backgroud and contrast, if we have white
        # color, we consider it to be on dark background, so visibility is 1.0
        if self.font_color.to_hex() == "#ffffff":
            return 1.0

        # convert to RGB
        (r,g,b) = self.font_color.to_rgb()
        r = int(r)
        g = int(g)
        b = int(b)

        # get visiblity. Is this ugly if-else net necessary?
        if r >= 0 and r < 32:
            if g >= 0 and g < 32:
                if b >= 0 and b < 32:
                    return 1.0
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
            elif g >= 32 and g < 64:
                if b >= 0 and b < 32:
                    return 1.2
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
            else:
                if b >= 0 and b < 32:
                    return 1.3
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
        # not much red
        elif r >= 32 and r < 64:
            if g >= 0 and g < 32:
                if b >= 0 and b < 32:
                    return 1.1
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
            elif g >= 32 and g < 64:
                if b >= 0 and b < 32:
                    return 1.2
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
            else:
                if b >= 0 and b < 32:
                    return 1.3
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
        # a lot of red color
        else:
            if g >= 0 and g < 32:
                if b >= 0 and b < 32:
                    return 2.0
                elif b >= 32 and b < 64:
                    return 1.9
                else:
                    return 1.7
            elif g >= 32 and g < 64:
                if b >= 0 and b < 32:
                    return 2.0
                elif b >= 32 and b < 64:
                    return 1.7
                else:
                    return 1.6
            else:
                if b >= 0 and b < 32:
                    return 1.3
                elif b >= 32 and b < 64:
                    return 1.3
                else:
                    return 1.5
        # mistake ? return 1
        return 1.0


    def _getparam(self):
        """
        Collect all params of font and return tuple containing them.
        """
        w = CSSStyle.W_NORMAL
        if self.font_weight != None: w = self.font_weight
        si = CSSStyle.MEDIUM
        if self.font_size != None: si = self.font_size
        st = CSSStyle.S_NORMAL
        if self.font_style != None: st = self.font_style
        c = CSSColor()
        if self.font_color != None: c = self.font_color
        v = CSSStyle.V_NORMAL
        if self.font_variant != None: v = self.font_variant
        d =  CSSStyle.D_NORMAL
        if self.font_decoration != None: d = self.font_decoration
        return (w, si, st, c, v, d)


    def __str__(self):
        """
        Returns informal textual representation of object.
        """
        (w, si, st, c, v, d) = self._getparam()
        if st == CSSStyle.S_NORMAL:
            st = 'S_NORMAL'
        elif st == CSSStyle.ITALIC:
            st = 'ITALIC'
        elif st == CSSStyle.EM:
            st = 'EMPHASIS'
        if v == CSSStyle.SMALL_CAPS:
            v = 'SMALL_CAPS'
        else:
            v = 'V_NORMAL'
        return "<"+__modulename__+".FontStyle(weight="+str(w)+", size="+str(si)+\
               ", style="+str(st)+", color="+str(c)+", variant="+str(v)+", decor="+\
               str(d)+", family=None)>"

# ------------------------------------------------------------------------------
# end of class CSSStyle
# ------------------------------------------------------------------------------


class CSSSelector2CSSStyleMapper(object):
    """
    This class keeps stored cascade styles in order of tag-style, class-style and
    ID-style. Tag.class or Tag#id selectors are stored in TAG-dictionary and recognizing
    if there was class/tag or tag.class selector is not a job of this class.

    Instance of this class maps CSS selector (name and type or CSSSelector instance)
    to CSSStyle instance.
    """
    _txt2pointer = {'tag':CSSSelector.TAG,
                    'class':CSSSelector.CLASS,
                    'id':CSSSelector.ID}

    def __init__(self):
        self._styles = [{}, {}, {}]


    def add_style(self, name, _type, style):
        """
        Adds FontStyle mapped to css selector name.
        """
        self._styles[_type][name] = style


    def get_style(self, name, _type):
        """
        Returns appropriate style for css selector name $name and of type _type.
        """
        if _type in CSSSelector2CSSStyleMapper._txt2pointer:
            _type = CSSSelector2CSSStyleMapper._txt2pointer[_type]
        if not name in self._styles[_type]: return None
        return self._styles[_type][name]


    def get_style_by_selector(self, selector):
        """
        Returns appropriate style for selector
        """
        if not selector.name in self._styles[selector.type_]: return None
        return self._styles[selector.type_][selector.name]

# ------------------------------------------------------------------------------
# end of class CSSSelector2CSSStyleMapper
# ------------------------------------------------------------------------------


class Element2CSSStyleMapper(object):
    """
    This class maps elements of ElementTree to CSSStyles ({elem: CSSStyle}). This
    is very comfortable when parsing css, because when the whole element tree with
    CSS is parsed, every element has his own style kept in here and no more looping
    over tree is needed to get style.
    """
    def __init__(self):
        self._style_tree = {}

    def add_elem_style(self, elem, style):
        """
        Insert new style and map it on element. Element has to be instance of
        lxml.Element. If trying to add style to element, which is already mapped,
        raises HSWCSSElementStyleError.
        """
        # we hash string representation of object. lxml.Element containts unique repr
        # (0x address in memory) so this should be safe.
        if str(elem) in self._style_tree:
            raise CSSElementStyleError("Element already mapped to style " + \
                                           str(self._style_tree[str(elem)]))
        self._style_tree[str(elem)] = style


    def get_elem_style(self, elem):
        """
        Returns appropriate FontStyle for element $elem. If element not found
        (not stored yet), returns None.
        """
        if str(elem) not in self._style_tree:
            return None
        return self._style_tree[str(elem)]

#    __single = None # Singleton instance
#    _style_tree = None
#
#    def __new__(classtype, *args, **kwargs):
#        # Check to see if a __single exists already for this class
#        # Compare class types instead of just looking for None so
#        # that subclasses will create their own __single objects
#        if classtype != type(classtype.__single):
#            classtype.__single = object.__new__(classtype, *args)
#        return classtype.__single
#
#
#    def __init__(self):
#        if Element2CSSStyleMapper._style_tree == None:
#            Element2CSSStyleMapper._style_tree = {}
#
#
#    def add_elem_style(self, elem, style):
#        """
#        Insert new style and map it on element. Element has to be instance of
#        lxml.Element. If trying to add style to element, which is already mapped,
#        raises HSWCSSElementStyleError.
#        """
#        # we hash string representation of object. lxml.Element containts unique repr
#        # (0x address in memory) so this should be safe.
#        if str(elem) in Element2CSSStyleMapper._style_tree:
#            raise CSSElementStyleError("Element already mapped to style " + \
#                                           str(Element2CSSStyleMapper._style_tree[str(elem)]))
#        Element2CSSStyleMapper._style_tree[str(elem)] = style
#
#
#    def get_elem_style(self, elem):
#        """
#        Returns appropriate FontStyle for element $elem. If element not found
#        (not stored yet), returns None.
#        """
#        if str(elem) not in Element2CSSStyleMapper._style_tree:
#            return None
#        return Element2CSSStyleMapper._style_tree[str(elem)]



# ------------------------------------------------------------------------------
# end of class Element2CSSStyleMapper
# ------------------------------------------------------------------------------


class _CSSStyleParser(object):
    def __init__(self):
        self._styles = None


    def _parse_css_color(self, color):
        """
        Parses css color declaration and return appropriate FontStyle object.
        """
        # create new CSSColor object with default colr (#000000)
        c = CSSColor()
        # handle hexa
        if color[0] == "#":
             c.set_hex(color)
        # handle text
        else:
            try:
                c.set_text(color)
            except CSSColorError:
                return c
        # can be color written in rgb format??
        return c


    def _make_mapper(self, declarations):
        m = {}
        for d in declarations:
            m[d.property] = d.value
        return m


    def _parse_css(self, rule_list):
        """
        Parses string $f with css declarations and stores them to self._styles.
        """
        self._styles = CSSSelector2CSSStyleMapper()
        for cssrule in rule_list:
            style = CSSStyle()
            attr = self._make_mapper( cssrule.get_declarations() )
            # Handle font-size params
            # Params 'smaller' and 'larger' NOT IMPLEMENTED yet
            # Percentage "%" handling solution is very poor. Has to be
            # implemented in the way to inherit attributes from ancestors,
            # not to have percent*0.16 !!!
            if 'font-size' in attr:
                _val = attr['font-size']
                if _val == 'xx-small': style.set_font_size(CSSStyle.XX_SMALL)
                elif _val == 'x-small': style.set_font_size(CSSStyle.X_SMALL)
                elif _val == 'small': style.set_font_size(CSSStyle.SMALL)
                elif _val == 'medium': style.set_font_size(CSSStyle.MEDIUM)
                elif _val == 'large': style.set_font_size(CSSStyle.LARGE)
                elif _val == 'x-large': style.set_font_size(CSSStyle.X_LARGE)
                elif _val == 'xx-large': style.set_font_size(CSSStyle.XX_LARGE)

                try:
                    # size in pixels
                    if "px" in _val: style.set_font_size(int(_val.replace("px", "")))
                    # size in "em", size of big M
                    elif "em" in _val: style.set_font_size(float(_val.replace("em", ""))*float(16))
                    # size in "ex", it means size of small x in that font
                    elif "ex" in _val: style.set_font_size(float(_val.replace("ex", ""))*float(8))
                    # size in percent
                    elif "%" in _val: style.set_font_size(float(_val.replace("%", ""))*float(0.16))
                except:
                    style.set_font_size(CSSStyle.MEDIUM)

            # Handle font-style.
            if 'font-style' in attr:
                if attr['font-style'] == 'italic':
                    style.set_font_style(CSSStyle.ITALIC)

            # Handle font-weight
            # params bolder and lighter are considered to be 1.3 and 0.7 * normal weight.
            if 'font-weight' in attr:
                _val = attr['font-weight']
                if _val == 'normal': style.set_font_weight(CSSStyle.W_NORMAL)
                elif _val == 'bold': style.set_font_weight(CSSStyle.BOLD)
                elif _val == 'bolder': style.set_font_weight(CSSStyle.BOLDER)
                elif _val == 'lighter': style.set_font_weight(CSSStyle.LIGHTER)
                elif _val.isdigit(): style.set_font_weight(int(_val))
                else: style.set_font_weight(CSSStyle.W_NORMAL)

            # Color is handled by CSSColor() object and this is ment to be
            # a color repr. in CSSStyle.
            if 'color' in attr:
                style.set_font_color(self._parse_css_color(attr['color']))

            # Handle font-variant.
            if 'font-variant' in attr:
                if attr['font-variant'] == 'small-caps':
                    style.set_font_variant(CSSStyle.SMALL_CAPS)

            # if empty css entry found ie. #myNewStyle { }, dont save it
            if not attr: continue

            # if no attribute which could affect font behaviour found, do not save it
            #if style.unchanged(): continue

            # save style to storage
            for _selector in cssrule.get_selectors():

                # when implementing support for events, delete this
                _stop = False
                for _pseudo in ('hover', 'link', 'visited', 'active'):
                    if re.search(":"+_pseudo, _selector.name, re.I):
                        _stop = True
                        break
                    if _stop: continue
                # add style to CSSSelector2CSSStyleMapper
                self._styles.add_style(_selector.name, _selector.type, style)


    def get_style_mapper(self, stylesheet):
        """
        Returns instance of CSSSelector2CSSStyleMapper full of mapped CSSSelectors
        to CSSStyles.
        """
        self._parse_css(stylesheet.get_rules())
        return self._styles

# ------------------------------------------------------------------------------
# end of class CSSStyleParser
# ------------------------------------------------------------------------------
