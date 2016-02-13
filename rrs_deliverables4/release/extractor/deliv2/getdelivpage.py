#!/usr/bin/env python
import sys, re
from gethtmlandparse import GetHTMLAndParse
import deliverrno as derrno

class GetDelivPage:

    def __init__(self, url, verbose=False, debug=False, addkeyw=None):
        # keywords used for document page search
        self._sigwords = ["d((eliverables?)|[0-9])",
                          "documents?",
                          "reports?",
                          "public(ation)?s?",
                          "results?",             
                          "presentations?",
                          "library",
                           #"projects?",
                          "outocomes?", "downloads?",
                          "outputs?"]
        
        if addkeyw != None:
            self._sigwords.append(addkeyw)

        """ Associative array containing links with their flags
        { url : [Index/NoIndex/Frame, Visit/Visited, Rank] }
        index = 0, noindex = 1, frame = 2, unvisited = 0, visited = 1 """
        self._link_stack = { url : [0,0,0] }

        self.base_url = url # save base (input) url

        # Open an parsing agent to get needed data from page
        self.agent = GetHTMLAndParse()

        self._current_url = url

        # a constant used to set rank in order of importance of the expression 
        # being tested (self._sigwords)
        self.rank_const = len(self._sigwords)

        # few a constants for dictionary - just for good-looking source code
        self.IND_FR = 0 # index/noindex/frame/special
        self.VISIT = 1 # unvisited/visited
        self.RANK = 2 # value of rank

        # set verbose flag
        self.__verbose__ = verbose

        #set debug flag
        self.__dbg__ = debug
        
        # checking data types
        if not type(self.__verbose__) == bool:
            raise ValueError("Verbose flag has to be boolean.")


    def __verbose(self, msg):
        _err = "cannot decode verbose message."
        if self.__verbose__ == True:
            try:
                print(str(msg))
            except UnicodeError:
                print(_err) 

        
    def __debug(self, msg):
        _err = "cannot decode debug info."
        if self.__dbg__ == True:
            try:
                print("Debug message:    "+str(msg))
            except UnicodeError:
                print(_err) 

################################################################################

    """ Initialize item in dictionary to noindex/unvisited/rank=0 """
    def _link_item_init__(self, link, index=1, visit=0, rank=0):
        # default setting: noindex,unvisited,norank
        if not self._link_stack.has_key(link):
           self._link_stack[link] = [index,visit,rank]
        return


    """ Edits item in dictionary self._link_stack """
    def _link_item_edit(self, link, index=None, visit=None, rank=None):
        if index is not None:
            self._link_stack[link][self.IND_FR] = index
        if visit is not None:
            self._link_stack[link][self.VISIT] = visit
        if rank  is not None:
            # null rank if zero is argument
            if rank == 0:
                self._link_stack[link][self.RANK] = 0
            # add rank
            else:
                self._link_stack[link][self.RANK] += rank
        return

    
    """ Method representing one level of cascade. Do almost any job to search 
    one word in dictionary """
    def _level_job(self, index=None):
        # get list of links from anchors containing one of expression
        # from self_sigwords
        result = 0
        if index is not None: # searching with one 
            link_list = self.agent.get_all_links(
                regul = re.compile(self._sigwords[index], re.I), 
                base  = self._current_url)        
        else:
            link_list = self.agent.get_all_links(base = self._current_url)
            index = self.rank_const
        if link_list:
            #
            #   RANK giving & filter
            #       
            if index is None:
                rank = 0
            elif index == 0:
                rank = self.rank_const * 2
            else:
                rank = self.rank_const - index
            for link in link_list:
                # GTFO javascript
                if not link or "javascript:" in link or "mailto:" in link: 
                    continue
                if "#" in link: # if pointer delete it
                    link = re.sub('#.*$', '', link)
                if len(link) > 200:  
                    continue                
                if self._link_stack.get(link):
                    # RANK if you see those links for first
                    if self._link_stack[link][self.VISIT] == 0:
                        self._link_item_edit(self._current_url, rank=rank)
                    continue
                if not self.agent.compare_domains(self.base_url, link):
                    continue

                split_link = re.sub("https?://.+?/", "", link)
                # check whether it is file or not
                 
                if self.agent.is_wanted_mime(link):
                    #
                    #   Some PDF or DOC found
                    #
                    # RANK
                    self._link_item_edit(self._current_url, rank=10)
                    self.__debug("Added rank 10 to "+self._current_url)
                    # 
                    if re.search("de?l?(iverable)?[0-9]+([\._-][0-9])?", 
                                  split_link, re.I):
                        self.__debug("Type D on "+self._current_url) # debug print
                        # RANK
                        self._link_item_edit(self._current_url, rank=100)
                    continue
                elif not self.agent.is_page(link):
                    continue
                    self.__debug("UNWATED")
                #
                # Add link
                #
                # RANK
                # initialization of link item in dict
                self._link_item_init__(link)
                self._link_item_edit(self._current_url, rank=rank)
                result += 1
                # debug print
                self.__debug("ADD "+link[7:60])
                self.__debug("Rank "+str(rank)+" "+self._current_url)    
        return result


    """ Cascade search. May improve the speed of script """
    def _cascade_search(self):
        result = 0
        # first cascade - look for links cont. deliverables
        result += self._level_job(0)
        if not result == 0:
            return
        # second cascade - look for links cont. documents and publications
        result += self._level_job(1) 
        result += self._level_job(2)
        if not result == 0:
            return
        # last cascade - all the rest
        for i in range(3,self.rank_const):
            result += self._level_job(i)
        # check Intro page (all links) only on index
        if result == 0 and self._link_stack[self._current_url][0] == 0:
            result += self._level_job() 
        """if result == 0:
            # RANK DOWN
            self._link_item_edit(self._current_url, rank=0)
            print "No anchors on the page"""
        return


    """ TRY TO repair link. But for now only append / in base """
    def _repair_links(self, base=None):
        if base is None:
            base = self.base_url
        if re.match(".*[^/]$", base):
            base += "/"
        if self.agent.get_etree() == -1:
            return -1
        links = self.agent.get_all_links(base = base)
        # compare link with base url
        for link in links:
            if not self.agent.compare_domains(self.base_url, link):
                continue
            link = re.sub("https?://.+?/", base, link)
            # if match, save it as special case
            self._link_item_init__(link, index=3)


    """ Checking intro page. It is page without content, only with Enter label """
    def _check_intro(self):
        links = self.agent.get_all_links(base = self._current_url)
        self.__debug("We've found intro links: "+str(links))
        for link in links:
            if not self.agent.compare_domains(self.base_url, link):
                continue
            # save new link as normal page
            self._link_item_init__(link, index=1)
   

    """ Looks for frames on the page """
    def _check_frames(self):
        frames = self.agent.look_for_frame(base = self._current_url)
        if not frames:
            return None
        fcount = len(frames)
        # debug print
        self.__debug("We've found frames ("+str(fcount)+") on "+self._current_url) 
        # save new link as frame page
        for link in frames:
            if self.agent.compare_domains(self._current_url, link):
              self._link_item_init__(link, index=2)
        return fcount

    
    """ Checks for titles and gives rank according the result """
    def _check_titles(self):
        for i in range(self.rank_const):
            hcount = self.agent.count_all_headers(
                re.compile( self._sigwords[i], re.I ))
            if not hcount == 0:
                if i == 0: 
                    #
                    # "deliverable" match, the highest rank
                    #
                    # RANK constant is multiplied by 4
                    self.__debug("deliverable match"+str(self.rank_const *
                    4)+" "+self._current_url)
                    self._link_item_edit(self._current_url, 
                                         rank = self.rank_const * 4)
                else:
                    #
                    # other word match
                    #
                    # do not multiplied rank constant
                    self.__debug("Rank "+str(self.rank_const - i)+" "+self._current_url) 
                    self._link_item_edit(self._current_url, 
                                         rank = self.rank_const - i)


    """ Get information about current link """
    def _check_anchor(self):
        # tt is Text and Title
        tt = self.agent.get_anchor_from_link(self._current_url)
        # return 0 if no anchor match
        if tt == 0: return tt;
        # match for deliverables
        if re.search(self._sigwords[0], tt, re.I):
            self.__debug("Anchor matched "+self._current_url) # debug print
            return 1
        

    """ Returns list of unvisited links. Useful in cycle. """
    def _check_unvisited_links(self):
        unvisitedLinks = []
        for link in self._link_stack:
            if self._link_stack[link][self.VISIT] == 0: # if unvisited
                unvisitedLinks.append(link)
        return unvisitedLinks # list of unvisited page links

    
    """ Aplying all methods to unvisited links - next level of searching. 
    It is main private method. Only this method can decide end of searching """
    def _handle_unvis_links(self):
        unvisLinks = self._check_unvisited_links()
        if not unvisLinks:
            return None # end of searching
        for link in unvisLinks: # cycle in unvisited links
            # visit and parse page
            self._link_item_edit(link, visit = 1)

            (res, err) = self.agent.ghap(link)
            if res == -1:
                self.__debug(str(err)+" "+str(link)) # debug print
                # if link is broken (IND_FR == 3)
                if self._link_stack[link][self.IND_FR] != 3:
                    self._repair_links()
                continue
            # little hack with error message, there is no error but URL!
            if res == 2:
                self.base_url = err # URL of the new base
            self.__debug("Getting url in ghap(): "+str(link)) # debug print
            self.__verbose("Searching... URL: "+str(link)) # verbose print
            self._current_url = link
            if self._link_stack[link][self.IND_FR] == 2:
                dname = self.agent.get_domain_name(link)
                if dname is not None:
                    self.base_url = dname

            ###############
            # frame check #
            self._check_frames()

            ################
            # titles check #
            self._check_titles() # rank giving here

            ################
            # anchor check #
            if self._check_anchor():
                self._link_item_edit(link, rank = 10) # rank giving here too

            self._cascade_search() # search for next links on this page
        # when no unvisited links in list, return
        return 1


    """ Returns link of the highest value of rank in self._link_stack. 
    It is called in the end of process."""
    def _get_highest_ranks_link(self):
        hRank = 0
        hLink = ""
        # check all links and choose link with the highest rank
        for link in self._link_stack:
            if self._link_stack[link][self.RANK] > hRank:
                hLink = link
                hRank = self._link_stack[link][self.RANK]
        return hLink # WINNER


    """ Returns list of all links leading to deliverables. 
    Try to find more sites with deliverables.. i.e. like www.awissenet.com has.
    Maybe test for name of link - anchor: i.e. next, prev, [0-9]+ and so one...
    Page usualy looks like:       next pages: 1 2 3 4 ... """
    def _get_deliv_link_list(self,first_link):
        # agent gets first_link
        final_list = []
        nonvisited = [first_link]
        current = nonvisited.pop()
        while current:
            if not current or "javascript:" in current or "mailto:" in current:
                try:
                    current = nonvisited.pop()
                except: 
                    break
                continue
            if self.agent.ghap(current)[0] == -1: # CACHE ??? maybe 
                try:
                    current = nonvisited.pop()
                except: 
                    break
                continue

            nonvisited.extend(self.agent.get_pager_links(base=current))
            final_list.append(current) # append only one link
            try:
                current = nonvisited.pop()
            except: 
                break
        return final_list # returning all pages with deliverables
    
        
    """ Returns list of links on pages with deliverable-documents.
    If found returns list, if not found, return -1. 
    Only public method in module. """
    def get_deliverable_page(self):
        # the main searching loop 
        # while we have some unvisited links, search
        while self._handle_unvis_links(): 
            # security case
            if len(self._link_stack) > 10:
                break
            self.__debug("Stack content: "+str(self._link_stack))
        if len(self._link_stack) == 1 :
            return derrno.__err__(derrno.ELNOTFOUND)

        final_link = self._get_highest_ranks_link()
        if not final_link or self._link_stack[final_link][2] == 0:
            return derrno.__err__(derrno.ELNOTFOUND)
        self.__debug('#'*79)
        self.__debug("DELIVERABLE PAGE: "+final_link)
        return [final_link]
        
        ####### not in use #############
        result = self._get_deliv_link_list(final_link)
        if len(result) == 0:
            return derrno.__err__(derrno.ELNOTFOUND)
        else:
            return result
    
    

# end of class GetDelivPage.


class Main: # XXX for testing only
    def __init__(self,params):
        self.argv = params

    def print_help(self):
        print("usage: deliverables url")
        print("       [-h] prints this help.")
        sys.exit(0)

    def handle_cmd(self):
        if len(self.argv) > 2:
            print("deliverables: wrong number of parameters.") # sys.stderr.write() ??
            self.print_help()
        if len(self.argv) == 1:
            print("deliverables: missing operand: url")
            self.print_help()
        if self.argv[1] == "-h": # print help
            self.print_help()
        return self.argv[1]

if __name__ == '__main__':
    
    main = Main(sys.argv)
    url = main.handle_cmd()
    if not "http://" in url:
        print("wrong url format.")
        sys.exit(0)

    gdp = GetDelivPage(url, True, True)
    print gdp.get_deliverable_page()
    exit()
    import cProfile
    cProfile.run("print gdr.get_records([deliv], base3)")
