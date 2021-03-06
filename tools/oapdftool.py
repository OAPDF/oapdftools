#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Last Update: 2016.1.25 12:20PM

'''Module for DOI and journal record operation
Also include the journal pdf function'''

import os,sys,glob
from optparse import OptionParser

from oapdf.doi import DOI
from oapdf.crrecord import CRrecord
from oapdf.baiduxueshu import BaiduXueshu
from oapdf.bingacademic import BingAcademic
from oapdf.pdfdoicheck import PDFdoiCheck
from oapdf.endnotexml import EndnoteXML
from oapdf.basic import __doifilerename

############ Global setting #############

### browser header
browserhdr={'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'}
browserhdrs=[{'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'}]

timeout_setting=30
timeout_setting_download=120


def acsstyledoi(doi):
	doi=DOI(doi)
	if (doi.prefix == '10.1021'):
		return True
	else:
		return False

class PublisherFilter(object):
	def __init__(self,name):
		'''name can be str/list/set'''
		self.publisher=name
	def filter(self,doi):
		'''Use to filter the publisher'''
		doi=DOI(doi)
		return doi.publisherstyle(self.publisher)

if __name__ == "__main__":
	helpdes='''OAPDF tool for OADPF project'''

	parser = OptionParser(description=helpdes) 
	parser.add_option("-i", "--input", action="store", 
					dest="input", default="",
					help="Read input data from input file")
	parser.add_option("-w", "--word", action="store", 
					dest="word", default="",
					help="To search for a academic word by engine")
	parser.add_option("--maxpage", action="store", 
					dest="maxpage", default="1",
					help="To search for a academic word by engine")
	parser.add_option("--issn", action="store", 
					dest="issn", default="",
					help="To search for a journal issn by engine")
	parser.add_option("--prefix", action="store", 
					dest="prefix", default="",
					help="To search for a journal prefix by engine")
	parser.add_option("--offset", action="store", 
					dest="offset", default="0",
					help="Show result after offset number")
	parser.add_option("--maxresult", action="store", 
					dest="maxresult", default="0",
					help="Max result by searching")
	parser.add_option("--nodoi", action="store_false", 
					dest="doi", default=True,
					help="Turn off doi method")
	parser.add_option("--nobdcheck", action="store_false", 
					dest="bdcheck", default=True,
					help="Don't use bdcheck.")
	parser.add_option("--onlyacs", action="store_true", 
					dest="onlyacs", default=False,
					help="Only get pdf with ACS doi style")
	parser.add_option("--onlysd", action="store_true", 
					dest="onlysd", default=False,
					help="Only get pdf with Elesvier doi style")
	parser.add_option("--onlywiley", action="store_true", 
					dest="onlywiley", default=False,
					help="Only get pdf with Wiley doi style")
	parser.add_option("--onlysp", action="store_true", 
					dest="onlyspringer", default=False,
					help="Only get pdf with Springer doi style")
	parser.add_option("--onlyrsc", action="store_true", 
					dest="onlyrsc", default=False,
					help="Only get pdf with RSC doi style")
	parser.add_option("--onlyaip", action="store_true", 
					dest="onlyaip", default=False,
					help="Only get pdf with AIP doi style")
	parser.add_option("--onlynt", action="store_true", 
					dest="onlynature", default=False,
					help="Only get pdf with Nature doi style")
	parser.add_option("--onlysc", action="store_true", 
					dest="onlyscience", default=False,
					help="Only get pdf with Science doi style")
	parser.add_option("--onlyall", action="store_true", 
					dest="onlyall", default=False,
					help="Only get pdf with given all publisher doi style")
	parser.add_option("-c", "--checkpdf", action="store_true", 
					dest="checkpdf", default=False,
					help="To check and rename pdf file in currenct directory")
	parser.add_option("--morecheck", action="store_true", 
					dest="morecheck", default=False,
					help="To more check and remove Patent/SI pdf file in currenct directory")
	parser.add_option("--title2doi", action="store_true", 
					dest="title2doi", default=False,
					help="Use big title to find doi")
	parser.add_option("--retaindone", action="store_true", 
					dest="retaindone", default=False,
					help="To Only retain pdf for Done")
	parser.add_option("--endnote", action="store", 
					dest="endnote", default="",
					help="Process Endnote XML")
	parser.add_option("--cleannote", action="store_true", 
					dest="cleannote", default=False,
					help="Clean Note to Times Cited in Endnote XML")
	parser.add_option("--bing", action="store_true", 
					dest="bing", default=False,
					help="No Search by bing, default use Bing. ")
	parser.add_option("--baidu", action="store_true", 
					dest="baidu", default=False,
					help="Search by baidu. ")	
	(options, args) = parser.parse_args()

	# Todo..
	onlyretaindone=options.retaindone

	if (options.checkpdf and options.morecheck):
		##### Check and remove garbish
		dpf=PDFdoiCheck()
		for f in glob.iglob("*.pdf"):
			f=__doifilerename(f)
			dpf.reset(f)
			dpfresult=dpf.renamecheck(f)
			if (dpfresult!=0): 
				#Important to set fname to None
				rmresult=dpf.removegarbage(fname=None)
			sys.stdout.flush()
		sys.exit(0)

	elif (options.checkpdf and not options.morecheck):
		##### Check and rename doi file
		dpf=PDFdoiCheck()
		for f in glob.iglob("*.pdf"):
			f=__doifilerename(f)
			dpf.renamecheck(f)
			sys.stdout.flush()
		sys.exit(0)

	elif (options.morecheck):
		##### Check and remove garbish file
		dpf=PDFdoiCheck()
		for f in glob.iglob("*.pdf"):
			f=__doifilerename(f)
			dpf.reset(f)
			dpf.removegarbage(f)
			sys.stdout.flush()
		sys.exit(0)

	elif (options.title2doi):
		dpf=PDFdoiCheck()
		for f in glob.iglob("*.pdf"):
			f=__doifilerename(f)
			dpf.tryrenamefromtitle(f)
			sys.stdout.flush()
		sys.exit(0)

	maxpage=int(options.maxpage)
	if (maxpage<1):maxpage=1
	offset=int(options.offset)
	maxresult=int(options.maxresult)
	usebdcheck=options.bdcheck

	if (options.endnote):
		exml=EndnoteXML(options.endnote)
		tmp=os.path.splitext(options.endnote)
		sys.exit(exml.process(tmp[0]+'_new'+tmp[1], cleannote=options.cleannote,\
		 prefix=options.prefix, issn=options.issn,start=offset))

	pfilter=None
	publishers=[]

	if options.onlyall:
		publishers.append('all')
	else:
		if options.onlyacs:
			publishers.append('acs')
		if options.onlywiley:
			publishers.append('wiley')
		if options.onlysd:
			publishers.append('sd')
		if options.onlyspringer:
			publishers.append('springer')
		if options.onlyrsc:
			publishers.append('rsc')
		if options.onlyaip:
			publishers.append('aip')
		if options.onlynature:
			publishers.append('nature')
		if options.onlyscience:
			publishers.append('science')
	
	if publishers: pfilter=PublisherFilter(publishers).filter	

	if (not options.baidu and options.bing):
		try:
			bingacad=BingAcademic()
			if (options.word):
				#### Find a keyword by Bing and download pdf
				bingacad.grepBingAcadPDF(options.word,maxpage=maxpage)

			if options.input and options.doi:
				#### Find doi saved in file by Bing and download pdf 
				bingacad.finddoiPDFfromFile(options.input)

			#0006-3495 for biophysics
			if options.issn:
				bingacad.findPDFbyISSN(options.issn,maxresult=maxresult,offset=offset)

		finally:
			bingacad.bfile.close()

	elif (options.baidu):
		bdxs=BaiduXueshu()
		if (options.word):
			bdxs.findwordPDF(options.word)
		if (options.input and options.doi):
			bdxs.finddoiPDFfromFile(options.input)
		if (options.issn):
			bdxs.findPDFbyISSN(options.issn,maxresult=maxresult,offset=offset,usedoi=options.doi,
				doifilter=pfilter,usebdcheck=usebdcheck)

# rsc=292
# acs=316
# wiley=311
# springer=297
# sciencedirect=78
# ASBMB=28 (jbc)
# nature: 339
# science: 221
# Oxford: 286

# JMC=0022-2623
# JACS=["0002-7863","1520-5126"]
# SCIENCE="0036-8075","1095-9203
# Nature="0028-0836","1476-4687"