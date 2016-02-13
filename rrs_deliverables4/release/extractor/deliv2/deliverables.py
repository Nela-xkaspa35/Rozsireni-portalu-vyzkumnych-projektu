#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  Script name: Deliverables
  Task: Find out page with deliverables, get links leading to deliverable
        documents and index all available data.

  Input: project site URL
  Output: XML containing data stored in objects (rrslib.db.model) about deliverables


  This script is part of ReResearch system.

  Implemented by (authors): Pavel Novotny
                            Stanislav Heller
                            Lukas Macko

  Brno University of Technology (BUT)
  Faculty of Information Technology (FIT)
"""


from optparse import OptionParser
from rrslib.web.httptools import is_url_valid
from rrslib.db.model import RRSProject,RRSUrl,RRSRelationshipPublicationProject
from rrslib.db.model import RRSRelationshipProjectUrl
from rrslib.xml.xmlconverter import Model2XMLConverter
from gethtmlandparse import GetHTMLAndParse
from getdelivpage import GetDelivPage
from getdelivrecords import GetDelivRecords
import StringIO
import os
import re

""" Command line parser """
class OptHandler:

    def __init__(self):
        
        usage = "usage: %prog [options] arg"
        self.parser = OptionParser(usage)
        
        self.parser.add_option("-u", "--url", action="store", \
          type="string", dest="url", help="URL input")

        self.parser.add_option("-r", "--regexp", action="store", \
          type="string", dest="regexp", \
          help="add a regular expression keyword to operate with in searching. Use expression with quotes. \
Example: --regexp=\"public(ation)?s?\"")

        self.parser.add_option("-q", "--quiet", action="store_true", \
          dest="quiet", default=False, help="don't print result. Often used in combination with -v/-d")
        
        self.parser.add_option("-l", "--lookup-page", action="store_true", \
          dest="lookup_page", default=False, help="only find the page with deliverables. Useful for deliverables3 (system)")

        self.parser.add_option("-v", "--verbose", action="store_true", \
          dest="verbose", default=False, help="print status messages to stdout")
          
        self.parser.add_option("-p", "--page", action="store_true", \
          dest="page", default=False, help="use this option when deliverable page url entered \
(in option --url=deliverable_page) to search for files and descriptions only.")

        self.parser.add_option("-f", "--file", dest="readfile", \
          help="read URLs from FILE", metavar="FILE")
                          
        self.parser.add_option("-s", "--store", action="store_true", \
          dest="storefile", default=False, help="store XML to file. Format of filename: input.url.adress.xml")

        self.parser.add_option("-d","--debug",action="store_true",\
          default=False,help="print debug messages")
        (self.options, self.args) = self.parser.parse_args()

        # Verify input options and data
        #########################################################
        # check input
        if not self.options.url and not self.options.readfile:
            self.parser.error("no input specified.")
        elif self.options.url and self.options.readfile:
            self.parser.error("options -f and -u are mutually exclusive.")
        elif self.options.quiet and self.options.storefile:
            self.parser.error("options -q and -s are mutually exclusive.")
        elif self.options.page and self.options.lookup_page:
            self.parser.error("options -p and -l are mutually exclusive.")
            
        
        # check url
        if self.options.url:
            if not is_url_valid(self.options.url):
                self.parser.error("wrong URL format.")
        else:
            if not os.path.isfile(self.options.readfile):
                self.parser.error("input file doesn't exist.")
                
        # check added keyword (RE)
        if self.options.regexp != None:
            try:
                re.search(self.options.regexp, "deliverables")
            except:
                self.parser.error("Bad keyword format. Has to be python-like RE with quotes.")

        # check internet connection
        if not os.popen("ping www.google.com -c 2"):
            self.parser.error("Internet connection failed.")
        #########################################################
        
    # returns options as a dictionary
    def getOptions(self):
        return self.options

    def printerror(self, msg):
        self.parser.error(msg)


# End of class OptHandler

""" Main class implementing all helper classes and handling the whole process """
class Deliverables:
    		   # static options
    	            opt = {
                    'debug': False,
                    'verbose': False,
		    'regexp': None,
		    'quiet': False,
		    'page': False,
		    'file': None,
		    'storefile': False,
            'lookup_page': False,
            }
	    
		    def __init__(self, options=opt, url=None):
			# get options
			self.opt = options
			if url != None:
			    self.opt_url = url
			else:
			    self.opt_url = self.opt.url
			
			# initialize main html handler and parser
			self.htmlhandler = GetHTMLAndParse()

			# searching deliverable page
			self.pagesearch = GetDelivPage(self.opt_url,
						       debug=self.opt['debug'],
						       verbose=self.opt['verbose'],
						       addkeyw=self.opt['regexp'])
						       
			# extracting informations from page
			self.recordhandler = GetDelivRecords(debug=self.opt['debug'])
		       
		    def __debug(self,msg):
			if self.opt['debug']:
			   print("Debug message:    " +str(msg));
			
		   
		    """ Main method handling all objects """
		    def main(self):
			

			# Searching deliverable page
			if self.opt['page']:
			    self.links = [self.opt_url]
			else:
			    self.links = self.pagesearch.get_deliverable_page() 

			    ##################################
			    if self.links[0] == -1:
				    return self.links

			    if self.opt['lookup_page']:
				    return (1,self.links)

			    if self.opt['verbose']:
				print "*"*80
				print "Deliverable page: ", " ".join(self.links)
				print "*"*80

			pr = RRSProject()

			#Project - Url relationship
			if not self.opt['page']:
			   pr_url = RRSUrl(link=self.opt_url)
			   pr_url_rel = RRSRelationshipProjectUrl()
			   pr_url_rel.set_entity(pr_url)
			   pr['url'] = pr_url_rel

		       
			self.recordhandler.process_pages(self.links)

			records = self.recordhandler.get_deliverables()

			if type(records) == list:
			    #create relationship Project Publication
			    for r in records:
				rel = RRSRelationshipPublicationProject()
				#print unicode(r['title'])
				rel.set_entity(r)
				pr['publication'] = rel
			    #create XML from RRSProject
			    output    = StringIO.StringIO()
			    converter = Model2XMLConverter(stream=output)
			    converter.convert(pr)
			    out       = output.getvalue()
			    output.close()
			    #Either return RRSProject object or XML in string or store result into a file           
			    if self.opt['storefile']:

				r = self._storeToFile(self.opt_url,out)
				#test if store ok
				if r[0]!=1:
				    print r[1]
			       
			    else:
				print out.encode('UTF-8')
			    return pr

			else:
			    return records


		    
		    def _storeToFile(self,url,res):   
		       """ From url generates filename, creates file and save res into it"""
		       name = url.replace(':', '.').replace("/", "").replace("?", "").replace("#", "")
		       file_name = name+".xml"
		       filepath = os.path.join(os.getcwd(), file_name)

		       try:
			  fw = open(filepath, "w")
		       except:
			  return (-1, 'Cannot make output file.')

		       try:
			  fw.write(res.encode('UTF-8'))
		       except:
			  return (-2, 'Cannot write data to output file.')

		       fw.flush()
		       fw.close()

		       return (1, 'OK')

		# End of class Deliverables

if __name__ == '__main__':
		   optPars = OptHandler()
		   options = optPars.getOptions() 
		   deliv   = Deliverables(options)
    
		   print options

		   if options.readfile:
		   #process link from a file
		      print("Processing links from file")
		      f    = open(deliv.opt.readfile)
		      link = True
		      while link:
			 try:
			   link = f.readline().strip()
			   if not is_url_valid(link):
			      print("Not valid link: " + link)
			      continue

			   print("Start processing: " + link)
			   deliv = Deliverables(options,link)
			   res = deliv.main()
			   #print("Deliv page:       "+"".join(deliv.links))
			   if type(res)!=RRSProject:
			       #doslo k chybe
			       print res[1]
			 except Exception as e:
				   print "Error" + str(e)
		      f.close()
		   else:
		      res = deliv.main()
	      
		      if type(res)!=RRSProject:
			print res[1]
		   exit()

