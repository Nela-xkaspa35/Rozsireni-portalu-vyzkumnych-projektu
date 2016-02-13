#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
This library implements language identification algorithm based on Monte Carlo
sampling method as classifier and model of lanugage uses "Most-common words".

Supported languages:
 - english
 - german
 - czech
 - chinese
 - french
 - finnish
 - italian
 - spannish
 - greek
 - swedish
 - polish
 - russian
 - portuguese

Missing:
 - dutch
 - japanese
 - korean
 - hungarian
 - danish
 - hebrew
 - romanian
 - norwegian
 - lithuanian
"""

__modulename__ = "language"
__author__ = "Stanislav Heller"
__email__ = "xhelle03@stud.fit.vutbr.cz"
__date__ = "$6.3.2011 21:22:42$"


import random
#import re

DELIMITERS = (# apostrophes
              unichr(96), unichr(8216), unichr(39), unichr(8217), unichr(700),
              unichr(699), unichr(1370),
              # hyphens
              unichr(8208), unichr(45), unichr(173), unichr(8209), unichr(8259),
              unichr(8722),
              # spaces
              unichr(32), unichr(160), unichr(5760), unichr(8192), unichr(8193),
              unichr(8194), unichr(8195), unichr(8196), unichr(8197),
              unichr(8198), unichr(8199), unichr(8200), unichr(8201),
              unichr(8202), unichr(8203), unichr(8204), unichr(8205),
              unichr(8239), unichr(8287), unichr(8288), unichr(12288),
              # newline
              unichr(10), unichr(12), unichr(13), unichr(133), unichr(8232),
              unichr(8233),
              # tabulator
              unichr(9),
              # others
              unichr(187),
              # just for chinese and japanese - some separators
              unichr(65292), unichr(12290), unichr(12300)
             )

# iterations of monte carlo method
MONTE_CARLO_ITERATIONS = 5000

# matched most common words in language
MOST_COMMON = 20


class Language(object):
    """
    Wrapper for informations about language.

    Instantiated object contains these attributes:
    - lang: english expression for the language

    - info: dictionary with additional information about language:
         - ISO 639-1 code
         - ISO 639-3 code
         - tuple of native names
         - language family
    """
    def __init__(self, lang=None, info={}):
        self.lang = lang
        self.info = info

    def __str__(self):
        return "<Language(lang=\'%s\') object at %s>" % (self.lang, hex(id(self)).rstrip("L"))

    def __repr__(self):
        return str(self)

#-------------------------------------------------------------------------------
# End of class Language
#-------------------------------------------------------------------------------


class LanguageModel(object):
    """
    Model of the language. The model is probabilistic and it is based on the
    Most-common-words method.
    """
    def __init__(self, language=None):
        self._model = {}
        self._lang = language

    def probability(self, x):
        """
        Returns probability of the term in the language text (corpus).
        """
        x = x.lower()
        if not x in self._model:
            return 0.0
        return self._model[x]

    def set_model(self, m):
        """
        Sets dictionary with model data into model object.
        """
        if type(m) is not dict:
            raise TypeError("Model has to be type dict.")
        self._model = m

    def get_language(self):
        """
        Returns the language of the model - instance of class Language.
        """
        return self._lang

    def train(self, text):
        """
        Train the language model from text.
        """
        if type(text) is not unicode:
            text = unicode(str(text), encoding='utf-8')
        index = -1
        txt_len = len(text)
        chunk = []
        word_count = 0
        letter = text[index]
        while letter in DELIMITERS:
            index += 1
            if index >= txt_len: return
            letter = text[index]
        while 1:
            stop = False
            if letter in DELIMITERS:
                index += 1
                if index >= txt_len:
                    break
                letter = text[index]
                continue
            while letter not in DELIMITERS:
                chunk.append(letter)
                index += 1
                if index >= txt_len:
                    stop = True
                    break
                letter = text[index]
            term = "".join(chunk)
            chunk = []
            if stop: break
            if not term: continue
            term = term.lower()
            #if not re.search("[a-z]{1,}", term): continue
            if term in self._model:
                self._model[term] += 1
            else:
                self._model[term] = 1
            word_count += 1

        helper = {}
        for w in self._model:
            if self._model[w] in helper:
                helper[self._model[w]].append(w)
            else:
                helper[self._model[w]] = [w]
        _sorted_probabilities = sorted(self._model.values(), reverse=True)
        self._model = {}
        for prob in _sorted_probabilities[:MOST_COMMON]:
            for term in helper[prob]:
                self._model[term] = float(prob) / float(word_count)

    def __str__(self):
        return "<LanguageModel(language=\'%s\') object at %s>" % (self._lang.lang, hex(id(self)).rstrip("L"))

    def __repr__(self):
        return str(self)

#-------------------------------------------------------------------------------
# End of class LanguageModel
#-------------------------------------------------------------------------------


class TextSampler(object):
    def __init__(self, text):
        self._text = text.strip()
        self._len = len(self._text)
        for d in DELIMITERS:
            if d in self._text:
                return
        raise ValueError("Text doesn't contain any tokens to parse.")

    def sample(self):
        l = []
        while 1:
            seed = random.randint(0, self._len - 1)
            letter = self._text[seed]
            next = False
            while letter not in DELIMITERS:
                seed += 1
                if seed >= self._len - 1:
                    next = True
                    break
                letter = self._text[seed]
            if next: continue
            letter = ""
            while letter not in DELIMITERS:
                l.append(letter)
                seed += 1
                if seed >= self._len - 1:
                    del l[0]
                    if not l: break
                    return "".join(l)
                letter = self._text[seed]
            if not l: continue
            del l[0]
            if not l: continue
            return "".join(l)

#-------------------------------------------------------------------------------
# End of class TextSampler
#-------------------------------------------------------------------------------

## LIST OF LANGUAGE MODELS

# ENGLISH
lg_eng = Language('english', {'iso 639-1':'en',
                              'iso 639-3':'eng',
                              'native':('English',),
                              'family':'Indo-European'})
lm_eng = LanguageModel(lg_eng)
lm_eng.set_model(
{u'and': 0.03715769818943344, u'be': 0.05860974547075653, u'for': 0.01227423629676795,
u'on': 0.00941070817514759, u'i': 0.012228920395375296, u'of': 0.04276455255268357,
u'this': 0.006386044560350668, u'it': 0.015071007100564901, u'by': 0.007149502757516838,
u'to': 0.014367864119315801, u'not': 0.006434996240287028, u'a': 0.03022491824647811,
u'have': 0.019017140124522512, u'in': 0.02660221744612713, u'at': 0.00738439064054386,
u'the': 0.08553434449726093, u'with': 0.009331744041909383, u'you': 0.009614740325438676,
u'she': 0.007735996691800956, u'he': 0.009417841489704823})

# GERMAN
lg_ger = Language('german', {'iso 639-1':'de',
                             'iso 639-3':'deu',
                             'native':('Deutsch',),
                             'family':'Indo-European'})
lm_ger = LanguageModel(lg_ger)
lm_ger.set_model(
{u'ich': 0.012157040605141198, u'sie': 0.01725549073885822, u'dem': 0.007955250413141282,
u'die': 0.029256137168118528, u'der': 0.028620134186202906, u'das': 0.01132293833377645,
u'als': 0.005979470657846035, u'auf': 0.007517346720674788, u'war': 0.005979470657846035,
u'nicht': 0.011041428817190849, u'und': 0.02616474562487293, u'sich': 0.00893532058199486,
u'den': 0.014148459778024532, u'in': 0.012756551612684611, u'zu': 0.012370779312178415,
u'ein': 0.009357584856873264, u'von': 0.007381805101578018, u'mit': 0.008002168665905548,
u'es': 0.009425355666421649, u'er': 0.017359753522778812})

# CZECH
lg_cze = Language('czech', {'iso 639-1':'cs',
                            'iso 639-3':'ces',
                            'native':('čeština', 'česky'),
                            'family':'Indo-European'})
lm_cze = LanguageModel(lg_cze)
lm_cze.set_model(
{u'a': 0.035047486680565204, u'do': 0.008223303219828585, u'by': 0.00502663886958536,
u'jako': 0.004918539108949116, u'i': 0.005266002625279901, u'na': 0.016546984788819396,
u'k': 0.005196509922013744, u'ale': 0.007150027024940159, u'za': 0.007041927264303915,
u'o': 0.004378040305767894, u'jsem': 0.008810130491853911, u'to': 0.009736699868736005,
u's': 0.008223303219828585, u'byl': 0.005667516021928809, u'v': 0.013581962782796695,
u'si': 0.005505366380974442, u'je': 0.006493707049648675, u'z': 0.006470542815226623,
u'\u017ee': 0.012964249864875299, u'se': 0.033287004864489225})

# FINNISH
lg_fin = Language('finnish', {'iso 639-1':'fi',
                              'iso 639-3':'fin',
                              'native':('suomi', 'suomen kieli'),
                              'family':'Finno-Ugric'})
lm_fin = LanguageModel(lg_fin)
lm_fin.set_model(
{u'on': 0.013823212211713953, u'ei': 0.010784801725568276, u'ole': 0.0029139704662352744,
u'oli': 0.01409283225485316, u'h\xe4nen': 0.006771611083457773, u'olisi': 0.0029191554670648747,
u'min\xe4': 0.00469761075161772, u'joka': 0.00584868093578895, u'nyt': 0.004148000663680106,
u'ett\xe4': 0.0076841712294673965, u'kun': 0.005625725900116144, u'mutta': 0.007948606271777004,
u'kuin': 0.008783391405342626, u'sit\xe4': 0.004044300647088103, u'sen': 0.006818276090924174,
u'h\xe4n': 0.015176497428239588, u'niin': 0.005942010950721752, u'ja': 0.044974697195951555,
u'se': 0.010904056744649079, u'ollut': 0.0029450804712128752})

# CHINESE
lg_chn = Language('chinese', {'iso 639-1':'zh',
                              'iso 639-3':'zho',
                              'native':('中文', 'Zhōngwén', '汉语', '漢語'),
                              'family':'Sino-Tibetan'})
lm_chn = LanguageModel(lg_chn)
lm_chn.set_model(
{u'\u4f60': 0.0003939899833055092, u'\u53ea': 0.0004006677796327212,
u'\u8aaa\u8457': 0.0002938230383973289, u'\u4e86': 0.000667779632721202,
u'\u4e0d': 0.0006010016694490818, u'\u672a\u77e5\u5f8c\u4e8b\u5982\u4f55': 0.00034056761268781303,
u'\u4e14\u770b\u4e0b\u56de\u5206\u89e3': 0.002964941569282137, u'\u300d': 0.007078464106844741,
u'\u4f86': 0.0008948247078464107, u'\u8aaa\u4e86\u4e00\u904d': 0.0004941569282136894,
u'\u300d\u8aaa\u7f77': 0.0009482470784641069, u'\u4e00': 0.0003672787979966611,
u'\u4e0d\u591a\u6642': 0.0002737896494156928, u'\u4ed6': 0.00034056761268781303,
u'\u65bd\u516c': 0.0003071786310517529, u'\u53bb': 0.0006076794657762938,
u'\u4eba': 0.0005342237061769616, u'\u300d\u8aaa\u8457': 0.0009282136894824708,
u'\u4e0b': 0.000333889816360601, u'\u65bd': 0.00031385642737896495})

# FRENCH
lg_fre = Language('french', {'iso 639-1':'fr',
                             'iso 639-3':'fra',
                             'native':('français', 'langue française'),
                             'family':'Indo-European'})
lm_fre = LanguageModel(lg_fre)
lm_fre.set_model(
{u'\xe0': 0.020844376236689544, u'le': 0.02327543382999803, u'que': 0.010323669231857955,
u'd': 0.013903651304195795, u'la': 0.02527356335874473, u's': 0.007073933567743529,
u'de': 0.046056885637611455, u'dans': 0.006857469535462637, u'l': 0.018194079431199127,
u'du': 0.009249674610156603, u'les': 0.01853542655902669, u'en': 0.011933273574459464,
u'il': 0.014866638729855663, u'je': 0.006987902990811379, u'qui': 0.008075773512017917,
u'et': 0.026100566969253784, u'un': 0.013537327557258899, u'des': 0.009954570305020023,
u'se': 0.007159964144675679, u'une': 0.009418960584119866})

# ITALIAN
lg_ita = Language('italian', {'iso 639-1':'it',
                              'iso 639-3':'ita',
                              'native':('Italiano',),
                              'family':'Indo-European'})
lm_ita = LanguageModel(lg_ita)
lm_ita.set_model(
{u'a': 0.021059008265780308, u'gli': 0.006177415369409439, u'non': 0.011597599177407398,
u'le': 0.01013096120583148, u'e': 0.03153271638888225, u'che': 0.026610711239707627,
u'la': 0.0170058266975936, u'i': 0.007297320994444312, u'di': 0.03066389280789434,
u'l': 0.009194385327243598, u'per': 0.008831711263620205, u'da': 0.006791171477079796,
u'una': 0.007241524984656097, u'si': 0.01153383230907801, u'un': 0.013885235578724184,
u'del': 0.005735032720374312, u'il': 0.017472121922252247, u'in': 0.012781271670771659,
u'd': 0.0050933786078098476, u'con': 0.005667280422774337})

# SPANNISH
lg_spa = Language('spannish', {'iso 639-1':'es',
                               'iso 639-3':'spa',
                               'native':('español', 'castellano'),
                               'family':'Indo-European'})
lm_spa = LanguageModel(lg_spa)
lm_spa.set_model(
{u'a': 0.018541983553725282, u'el': 0.026420853939173393, u'en': 0.023550217163083063,
u'la': 0.0352186422529459, u'una': 0.007746661395760411, u'de': 0.054299933764605166,
u'por': 0.009261174277628407, u'al': 0.007531985412505137, u'su': 0.011218129124985928,
u'los': 0.015624222781310622, u'le': 0.006644483481730288, u'un': 0.010595045173586476,
u'que': 0.03195661450738407, u'no': 0.012398847032889931, u'lo': 0.006414099499700239,
u'y': 0.030926431587738334, u'del': 0.009202269282222996, u'las': 0.010413094187778653,
u'se': 0.01443695987391713, u'con': 0.012057198059538551})

# GREEK
lg_gre = Language('greek', {'iso 639-1':'el',
                            'iso 639-3':'ell',
                            'native':('Ελληνικά',),
                            'family':'Indo-European'})
lm_gre = LanguageModel(lg_gre)
lm_gre.set_model(
{u'\u03c0\u03bf\u03c5': 0.017013232514177693, u'\u03bd\u03b1': 0.02296436322901351,
u'\u03b1\u03c0\u03cc': 0.009759854372330743, u'\u03ba\u03b1\u03b9': 0.03755513547574039,
u'\u03c4\u03bf\u03bd': 0.008975705384022965, u'\u03c4\u03b7\u03bd': 0.01253238115241896,
u'\u03b4\u03b5\u03bd': 0.006735279703143597, u'.': 0.029069523209409788,
u'\u03c4\u03b7\u03c2': 0.01950570608415599, u'\u03c4\u03bf': 0.027795281103409647,
u'\u03b3\u03b9\u03b1': 0.006931316950220542, u'\u03bc\u03b5': 0.014324721697122454,
u'\u03c3\u03c4\u03bf': 0.008163551074704194, u'\u03ba\u03b9': 0.014142687110551005,
u'\u03b7': 0.015094868024924735, u'\u03c4\u03b7': 0.010389974095078065,
u'\u03c4\u03bf\u03c5': 0.017293285724287615, u'\u03b1\u03c0': 0.008751662815935028,
u'\u03bf': 0.013666596653364138, u'\u03c4\u03b1': 0.018735559756353708})

# SWEDISH
lg_swe = Language('swedish', {'iso 639-1':'sv',
                              'iso 639-3':'swe',
                              'native':('svenska',),
                              'family':'Indo-European'})
lm_swe = LanguageModel(lg_swe)
lm_swe.set_model(
{u'och': 0.041605657328170585, u'till': 0.008210501198494561, u'en': 0.019089144133884316,
u'han': 0.022044707643249926, u'med': 0.01132875627718305, u'i': 0.019550103580299134,
u'som': 0.015065239319298474, u'men': 0.009349342183754704, u'det': 0.019739910411175825,
u'om': 0.007445850822677035, u'hon': 0.013199709324396142, u'att': 0.021724747556914933,
u'sig': 0.008807036952678446, u'den': 0.010146530873436805, u'p\xe5': 0.012662827145630646,
u'var': 0.009918762676384776, u'jag': 0.016833154372607077, u'\xe4r': 0.008617230121801754,
u'f\xf6r': 0.009181227562121063, u's\xe5': 0.008069501838414733})

# POLISH
lg_pol = Language('polish', {'iso 639-1':'pl',
                             'iso 639-3':'pol',
                             'native':('polski',),
                             'family':'Indo-European'})
lm_pol = LanguageModel(lg_pol)
lm_pol.set_model(
{u'a': 0.008652726853955666, u'do': 0.010146722857516357, u'co': 0.0031436165908256195,
u'i': 0.028448173901134813, u'na': 0.016944404673717498, u'si\u0119': 0.024047110673978946,
u'od': 0.0038781646259096257, u'za': 0.0036104903419383353, u'o': 0.005303685812640451,
u'nie': 0.01581768268769881, u'to': 0.0073579303175364, u'\u017ce': 0.008497102270251427,
u'jak': 0.00464383757773448, u'w': 0.02478788369241112, u'jego': 0.0031934164576109757,
u'go': 0.0033365910746188756, u'z': 0.016377931189034068, u'po': 0.005832809397234863,
u'ju\u017c': 0.0042080887433626115, u'tak': 0.003809689809079761})

# RUSSIAN
lg_rus = Language('russian', {'iso 639-1':'ru',
                              'iso 639-3':'rus',
                              'native':('русский язык',),
                              'family':'Indo-European'})
lm_rus = LanguageModel(lg_rus)
lm_rus.set_model(
{u'\u043d\u0435': 0.012639825546177765, u'\u0441': 0.006542018333804466,
u'\u043a\u0430\u043a': 0.00625933852925736, u'\u043d\u0430': 0.013972458910471268,
u'\u043f\u043e': 0.003917134434438477, u'\u043a': 0.003917134434438477,
u'\u043d\u043e': 0.004967087994184873, u'\u044f': 0.005451681944837056,
u'\u0442\u044b': 0.005855510237047208, u'\u0432': 0.0233412752897468,
u'\u043e\u043d': 0.00363445462989137, u'\u2014': 0.00726890925978274,
u'\u0441\u0442.': 0.0036748374591123855, u'\u0435\u0433\u043e': 0.006380487016920406,
u'\u0447\u0442\u043e': 0.005976658724710253, u'\u0438': 0.043653838387917455,
u'\u043e\u0442': 0.004603642531195736, u'.': 0.005209384969510964,
u'\u0432\u044a': 0.00880345677018132, u'\u043e': 0.005370916286395025})

# PORTUGUESE
lg_por = Language('portuguese', {'iso 639-1':'pt',
                                 'iso 639-3':'por',
                                 'native':('Português',),
                                 'family':'Indo-European'})
lm_por = LanguageModel(lg_por)
lm_por.set_model(
{u'a': 0.03761600704019562, u'do': 0.01041250306497066, u'lhe': 0.0065733124187572845,
u'e': 0.029457307057997643, u'd': 0.006502776107672, u'para': 0.007362647328521189,
u'\xe9': 0.007063707724397838, u'com': 0.008766655806314007, u'de': 0.03637658328826847,
u'por': 0.006287808302459702, u'o': 0.031177049499696022, u'da': 0.01055357568714123,
u'um': 0.011342910596905136, u'as': 0.00633147363789345, u'que': 0.0334543646861638,
u'n\xe3o': 0.012978681239692461, u'uma': 0.00889429294065881, u'em': 0.008400538763061814,
u'os': 0.009361176142604268, u'se': 0.015474323103328977})

# DUTCH
lg_dut = Language('dutch',  {'iso 639-1':'nl',
                             'iso 639-3':'nld',
                             'native':('Nederlands', 'Vlaams'),
                             'family':'Indo-European'})
lm_dut = LanguageModel(lg_dut)
lm_dut.set_model(
{u'het': 0.026561632185504027, u'en': 0.03674977436823105, u'van': 0.018302207720077755,
u'er': 0.00817481255206887, u'haar': 0.009782438905859484, u'die': 0.008830012496528742,
u'de': 0.03977410788669814, u'maar': 0.008487225770619273, u'dat': 0.013429429325187448,
u'met': 0.008697670785892807, u'ik': 0.01062204943071369, u'een': 0.022255102749236325,
u'zijn': 0.008276780755345737, u'den': 0.010927954040544294, u'in': 0.014577113996112192,
u'niet': 0.007808160927520133, u'hij': 0.010264075951124687, u'te': 0.015332112607608998,
u'zij': 0.010248889197445155, u'op': 0.009582841571785615})


#-------------------------------------------------------------------------------
# End of list of language models
#-------------------------------------------------------------------------------

# soma additional maps

map_lang_en2model = {'english':lm_eng, 'german':lm_ger, 'czech':lm_cze, 'finnish':lm_fin,
                     'chinese':lm_chn, 'french':lm_fre, 'italian':lm_ita, 'spannish':lm_spa,
                     'greek':lm_gre, 'swedish':lm_swe, 'polish':lm_pol, 'russian':lm_rus,
                     'protuguese':lm_por, 'dutch':lm_dut}

map_lang_en2lang = {'english':lg_eng, 'german':lg_ger, 'czech':lg_cze, 'finnish':lg_fin,
                    'chinese':lg_chn, 'french':lg_fre, 'italian':lg_ita, 'spannish':lg_spa,
                    'greek':lg_gre, 'swedish':lg_swe, 'polish':lg_pol, 'russian':lg_rus,
                    'protuguese':lg_por, 'dutch':lg_dut}



class LanguageIdentifier(object):
    """
    Main classifier for language indentification. It uses Monte Carlo sampling
    and Most-common-words language models (probabilistic model).
    """
    def __init__(self):
        self.lang_models = map_lang_en2model.values()
        self._last = None

    def _max(self, prob):
        mxval = max(prob.values())
        for k in prob:
            if prob[k] == mxval:
                return k

    def _percentage(self, lang, prob):
        all_ = float(sum(prob.values()))
        try:
            return (float(prob[lang]) / all_) * 100
        except ZeroDivisionError:
            return 0.0

    def identify(self, document):
        """
        Identifies the language of the document.
        @param document: string or unicode of the classified document.
        @returns tuple (language, probability)
        """
        try:
            document = unicode(document, encoding='utf-8')
        except TypeError:
            pass
        try:
            ts = TextSampler(document)
        except ValueError:
            return (None, 0.0)
        probabilities = {}
        for lm in self.lang_models:
            probabilities[lm] = 0.0
        i = 0
        # some optimization
        iterations = MONTE_CARLO_ITERATIONS
        dl = len(document)
        if dl*2 < MONTE_CARLO_ITERATIONS:
            iterations = dl*2
        # now iterate and classify all samples
        while i < iterations:
            i += 1
            feature = ts.sample()
            for lm in self.lang_models:
                probabilities[lm] += lm.probability(feature)
        self._last = probabilities
        lang = self._max(probabilities)
        perc = self._percentage(lang, probabilities)
        if perc == 0.0:
            return (None, perc)
        return (lang.get_language().lang, perc)

    def add_model(self, lang_model):
        """
        Adds model of new language to classifier.
        """
        if type(lang_model) is not LanguageModel:
            raise TypeError("Model has to be type LanguageModel.")
        self.lang_models.append(lang_model)

    def get_all(self):
        """
        Returns list of tuples (language, probability) created by last classification.
        """
        r = []
        d = {}
        for lm in self._last:
            p = self._percentage(lm, self._last)
            l = lm.get_language().lang
            if p not in d:
                d[p] = [l]
            else:
                d[p].append(l)
        for p in sorted(d.keys(), reverse=True):
            for lang in d[p]:
                r.append((lang, p))
        return r

#-------------------------------------------------------------------------------
# End of class LanguageIdentifier
#-------------------------------------------------------------------------------

if __name__ == "__main__":
    """
    l = Language('asdf')
    lm = LanguageModel(l)
    s = open('/media/Data/Skola/FIT/prace/NLP/python-rrslib/develop/gutenberg-corpora/nl/nl.corp', 'r')
    txt = s.read()
    s.close()
    lm.train(txt)
    print lm._model
    exit()
    """

    li = LanguageIdentifier()
    sample = """Many old mainframe operating systems added a carriage control
    character to the start of the next record, this could indicate if the next
    record was a continuation of the line started by the previous record, or a
    new line, or should overprint the previous line"""

    res = li.identify(sample)
    print res
    l = map_lang_en2lang[res[0]]
    print l.info
    print li.get_all()
