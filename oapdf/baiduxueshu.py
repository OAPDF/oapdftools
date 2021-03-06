#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Last Update: 2016.1.25 12:20PM

'''Module for DOI and journal record operation
Also include the journal pdf function'''

import os,sys,re
import time,random,gc
import requests
requests.packages.urllib3.disable_warnings()
from bs4 import BeautifulSoup

try:
	from .doi import DOI
	from .crrecord import CRrecord
	from .basic import *
	from .getpdf import *
	from .pdfdoicheck import PDFdoiCheck
	from .bdcheckcgi import BDCheck
except (ImportError,ValueError) as e:
	from doi import DOI
	from crrecord import CRrecord
	from basic import *
	from getpdf import *
	from pdfdoicheck import PDFdoiCheck
	from bdcheckcgi import BDCheck

timeout_setting=30
timeout_setting_download=120

def pdfexistpath(fname):
	if (os.path.exists(fname) or 
		os.path.exists('Good/'+fname) or os.path.exists('Done/'+fname)\
		or os.path.exists('High/'+fname) or os.path.exists('Unsure/'+fname)\
		or os.path.exists('Fail/'+fname) or os.path.exists('Untitle/'+fname) ):
		return True
	else:
		return False

############################# Part5: Search Engine ##################################

class SearchEngine(object):

	def __init__(self):
		self.url=""
		self.word=""
		self.request=None
		
	def search(self,keyword,params={},headers={}):
		r=requests.get(self.url,params=params,headers=headers,timeout=timeout_setting)
		if (r.status_code is 200):
			return r.text
		return ""

	def getitems(self):
		pass

class ResultItem(object):
	def __init__(self):
		self.text=""
		self.title=""
		self.link=""
		self.abstract=""

####################### BaiduXuShu Related ###############################

class BaiduXueshu(object):
	host="http://xueshu.baidu.com"
	path="/s"
	url="http://xueshu.baidu.com/s"
	word="wd"
	citeurl="http://xueshu.baidu.com/u/citation"
	def __init__(self):
		self.request=None
		self.soup=None
		self.items=[]
		#new add to check and remove not good result
		self.pdfcheck=PDFdoiCheck()
	def reset(self):
		self.request=None
		del self.items[:]
		del self.soup; self.soup=None
		del self.request; self.request=None
		self.pdfcheck.reset('')
		
	def search(self,keyword,params={},headers={},proxy=None):
		self.reset()
		if (not keyword):return

		params[self.word]=keyword
		params['sc_hit']='1'#for find all, not exactly
		if proxy:
			if not isinstance(proxy,dict):
				proxy=None
		try:
			if (proxy):
				r=requests.get(self.url,params=params,headers=headers,proxies=proxy,timeout=timeout_setting)
			else:
				r=requests.get(self.url,params=params,headers=headers,timeout=timeout_setting)
			if r.status_code is 200:
				if ('<img src="http://verify.baidu.com/cgi-bin/genimg' in r.text):
					time.sleep(600)
					self.search(keyword,params=params,headers=headers)
				try:
					self.soup=BeautifulSoup(r.text, "html.parser")
					self.items=self.soup.findChildren('div',attrs={'class':'result sc_default_result xpath-log'})
				except Exception as e:
					print e,'when parsing searching result'
					return 
				#print "Find",len(self.items)," Results."
				#for item in items:
		except Exception as e:
			print "Error when searching word.."
			time.sleep(20)
			self.search(keyword=keyword,params=params,headers=headers,proxy=proxy)

	def _parsepdflink(self,link):
		'''Some pdf link in baidu format'''
		if (link):
			link=requests.utils.unquote(link)
		if (len(link)>4):
			if link[:2]=="/s":
				rer=re.search(r'(?<=url=)http.*?(?=\&ie;=utf-8)',link)
				if rer:
					link=rer.group()
					return link
			elif(link[:4] == 'http'):
				return link
			return ''
		return ""

	def getpdflink(self,num=0):
		pdfs=[ i.text for i in self.items[num].findChildren('p',attrs={'class':"saveurl"})] \
			+[ i['href'] for i in self.items[num].findChildren('a',attrs={'class':"sc_download c-icon-download-hover"})]
		pdfs=list(set([ adjustpdflink(self._parsepdflink(pdf)) for pdf in pdfs]))
		if '' in pdfs: pdfs.remove('')
		if (pdfs): print "Get",len(pdfs)," links for record ",num,":",#,str(pdfs)
		return pdfs

	def getcite(self,num=0,citetype="txt"):
		cite=self.items[num].findChild('a',attrs={'class':'sc_q c-icon-shape-hover'})
		try:
			params={'t':citetype,'url':cite['data-link'],'sign':cite['data-sign']}
			r=requests.get(self.citeurl,params=params,timeout=timeout_setting)
			if r.status_code is 200:
				return r.text
		except:
			print "Can't get citation"
		return ""

	def getdoi(self,num=0):
		'''Get DOI from Baidu Cite'''
		soup=BeautifulSoup(self.getcite(num,citetype='txt'),"html.parser")
		if (soup.doi): 
			doi=soup.doi.text
		elif(soup.primarytitle):
			cr=CRrecord()
			cr.getfromtitle(soup.primarytitle.info.text,ignorecheminfo=True)
			doi=cr.doi
		else:
			doi=DOI("")
		return DOI(doi[doi.find('10.'):])

	def getallpdf(self,doifilter=None,onlinecheck=True,savestate=None,usebdcheck=True):
		'''Get All pdf from link
		doifilter should be a function, return True when DOI ok'''
		usedoifilter=callable(doifilter)
		getallfilelist=[]
		if isinstance(savestate,(list,tuple,set)):
			savestate=set(savestate)
		elif (isinstance(savestate,int)):
			savestate=set([savestate])
		else:
			savestate=set([0,1,2,3])
		bdcheck=BDCheck()
		for i in range(len(self.items)):
			try:
				getfilelist=[]
				# Get PDF links
				links=self.getpdflink(i)
				if (links):
					doi=DOI(self.getdoi(i))
					if not doi:
						print "blank doi..",doi
						continue
					if ( usedoifilter and not doifilter(doi)):
						print doi,'Not fit filter..'
						continue
						
					# Check by bdcheck api
					if (usebdcheck):
						bdout=bdcheck.get(doi)
						if sum(bdout)>0:
							print doi, 'has search/oapdf/free',bdout
							continue
					oapdffree=bdcheck.setbycheck(doi)
					if (oapdffree[0] and oapdffree[1]):
						print doi,'exist in oapdf/free library..'
						continue						
					elif oapdffree[0]:
						print doi,'exist in oapdf library..'
						continue				
					elif oapdffree[1]:
						print doi,'exist in free library..'
						continue
					doifname=doi.quote()+".pdf"
					if (pdfexistpath(doifname)):
						print doi,'Files exist in current folder..'
						continue

					# Start to find pdf at each link
					print "### Find for result with DOI: "+doi
					foundDonePDF=False
					for link in links:
						print 'Link:',str(link),
						if (onlinecheck):
							print "Try Getting..",
							# Get a StringIO obj
							getpdfobj=getwebpdf(link,fname=doifname,params=getwebpdfparams(link),stringio=True)
							if (not getpdfobj):
								continue
							try:
								dpfresult=self.pdfcheck.checkonlinepdf(fobj=getpdfobj,doi=doi)
								sys.stdout.flush()
								if (dpfresult!=0):
									if ( savestate and (dpfresult in savestate)):
										#Important to set fname to None
										rmresult=self.pdfcheck.removegarbage(fname=None,notdelete=True)
										if (rmresult <= 1):
											getfilelist.append( (getpdfobj,self.pdfcheck.realdoi,dpfresult))
									else:
										print "Not OK PDF for doi",doi												
								else:
									foundDonePDF=True
									if (self.pdfcheck.savefobj2file(doi=self.pdfcheck.realdoi,state=0,fobj=getpdfobj)):
										print "!!!!!!! Get PDF file to Done!: "+self.pdfcheck.realdoi
										del getfilelist[:]	
										nowdoi=DOI(self.pdfcheck.realdoi)
										getallfilelist.append('Done/'+nowdoi.quote()+'.pdf')

										break
									else:
										print "What? should never happen for pdfdoicheck.savefobj2file Done.."
							except Exception as e:
								print e,'Error at baidu getallpdf(web) when doing pdfcheck',doi,link

						# Now should not use this method
						elif (getwebpdf(link,fname=doifname,params=getwebpdfparams(link))):
							print "Please don't use download pdf to disk, use check online!"
							print "Try Getting..",
							try:
								dpfresult=self.pdfcheck.renamecheck(doifname)
								sys.stdout.flush()
								if (dpfresult!=0): 
									if ( savestate and (dpfresult in savestate)):
										#Important to set fname to None		
										rmresult=self.pdfcheck.removegarbage(fname=None)
										if (rmresult <= 1):
											if (os.path.exists(self.pdfcheck._fname)):
												getfilelist.append((self.pdfcheck._fname, dpfresult))
											else:
												print "What? should never happen for pdfdoicheck.moveresult Not Done.."
										else:
											print "Has been removed.."
									else:
										if (os.path.exists(self.pdfcheck._fname)) : 
											os.remove(self.pdfcheck._fname)
								else:
									foundDonePDF=True
									if (os.path.exists(self.pdfcheck._fname)):
										print "!!!!!!! Get PDF file to Done!: "+doifname
										getfilelist.append(self.pdfcheck._fname)
										#time.sleep(random.randint(1,5))								
										break
									else:
										print "What? should never happen for pdfdoicheck.moveresult Done.."
							except Exception as e:
								if os.path.exists(doifname):
									if (not os.path.exists('tmpfail/'+doifname)):
										os.renames(doifname,'tmpfail/'+doifname)
									else:
										os.remove(doifname)
								print e,'Error at baidu getallpdf when doing pdfcheck'
						else:
							print "can't get at this link"

					bdcheck.set(doi)
					# Online Check but not Done
					if onlinecheck and not foundDonePDF and len(getfilelist)>0:
						minnum=-1
						minresult=999999
						for i in range(len(getfilelist)):
							if getfilelist[i][2]<minresult:
								minnum=i
						nowdoi=DOI(getfilelist[minnum][1])
						if (self.pdfcheck.savefobj2file(doi=nowdoi,state=getfilelist[minnum][2],fobj=getfilelist[minnum][0])):
							print "!!!!!!! Get PDF file to: "+self.pdfcheck.judgedirs.get(getfilelist[minnum][2],'.'),self.pdfcheck.realdoi
							getallfilelist.append(self.pdfcheck.judgedirs.get(getfilelist[minnum][2],'.')+os.sep+nowdoi.quote()+".pdf")
							del getfilelist[:]
			except Exception as e:
				print e, "##### Error when get pdf.."
		return getallfilelist

	def findwordPDF(self,keyword,doifilter=None):
		print "#########################################################################"
		print "## Now finding for: "+ keyword+"............"
		sys.stdout.flush()
		self.search(keyword=keyword)
		self.getallpdf(doifilter)		

	def findcrossreftitledoi(self,doi,printyn=True):
		'''Find doi by crossref first'''
		cr=CRrecord()
		if( cr.getfromdoi(doi,fullparse=False) and cr.doi):
			keyword=cr.title+" "+cr.doi
			print "#########################################################################"
			print "## Now finding for doi with title: "+ keyword.encode('utf-8')+"............"
			sys.stdout.flush()
			self.search(keyword=keyword)
			self.getallpdf()
		else:
			print "Error DOI!: "+doi
		cr.reset()

	def finddoiPDFfromFile(self,fname):
		'''Put doi in file and use it to find pdf'''
		fin=open(fname)
		countN=0
		for line in fin:
			ldoi=line.lower().strip()
			doi=DOI(ldoi)
			if (os.path.exists(doi.quote()+".pdf")):
				continue
			self.findcrossreftitledoi(ldoi)
			#time.sleep(random.randint(1,10))
			countN+=1
			if countN>=10:
				gc.collect()
				countN=0
		fin.close()			

	def findPDFbyISSN(self,issn,maxresult=None, step=100, offset=0, 
		usedoi=True,doifilter=None,onlinecheck=True,savestate=None,proxy=None,usebdcheck=True):
		'''Find PDF by ISSN based on search result from crossref'''
		# may be improve to not only issn..
		if (not issn):return
		if (len(issn)==9 and issn[4]=='-'):
			needurl="http://api.crossref.org/journals/"+issn+"/works"
		elif('10.' in issn):
			needurl="http://api.crossref.org/prefixes/"+issn+"/works"
		else:
			print "Error ISSN/prefix"
			sys.exit(1)
		cr=CRrecord()
		total=cr.gettotalresultfromlink(needurl)
		if (not maxresult or maxresult <=0 or maxresult>total): 
			maxresult=total
		params={"rows":str(step)}
		maxround=(maxresult-offset)/step+1
		offsetcount=offset
		bdcheck=BDCheck()

		for i in range(maxround):
			params["offset"]=str(step*i+offset)
			r=requests.get(needurl,params,timeout=timeout_setting_download)
			if (r.status_code is 200):
				# Get all check/in oapdf 
				if usebdcheck: 
					bdcheckall=bdcheck.filterdois(r.json(),oapdf=1,crjson=True)

				for j in r.json().get('message',{}).get('items',[]):
					keyword=j.get('title',[''])
					doi=DOI(j.get("DOI",""))
					if not doi:
						offsetcount+=1
						time.sleep(2)
						continue

					# Check whether in bdcheck
					if (usebdcheck and doi in bdcheckall):
						print doi, 'has search/oapdf/free by bdcheck'
						offsetcount+=1
						time.sleep(1)
						continue
						
					# If not in bdcheck, check oapdf/free and set it
					# TODO: remove it after combine oapdf information to library
					oapdffree=bdcheck.setbycheck(doi)
					if (oapdffree[0] or oapdffree[1]):
						print doi,'exist in oapdf/free library..'
						offsetcount+=1
						time.sleep(1)
						continue						

					if (keyword): 
						keyword=keyword[0]
					else:
						time.sleep(2)
						offsetcount+=1
						continue
					if usedoi:keyword+=" "+doi
					print "#####################################",offsetcount,"####################################"
					print "## Now finding for doi with title:"+doi+" "+ keyword.encode('utf-8')+"............"
					sys.stdout.flush()
					self.search(keyword.encode('utf-8'),proxy=proxy)
					bdresult=self.getallpdf(doifilter,onlinecheck=onlinecheck,savestate=savestate,usebdcheck=usebdcheck)
					bdcheck.set(doi)
					offsetcount+=1
			gc.collect()
		print "End of process for",issn