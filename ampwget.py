#!/usr/bin/python

import sys, os
import re, mmap

class InputError(Exception):
	"""Improper filename given or file not appropriate"""

def download(links):
	for link in links:
		print "downloading " + link

def getLinks(file):
	ahref = re.compile(r"""<a.+?href\s*?=\s*?['"]?(.+?)['"\s].+?>""", 
				re.MULTILINE|re.DOTALL)

	return ahref.findall(file)

def main():
	try:
		try:
			linksFile = sys.argv[1]
			extention = sys.argv[2]
		except IndexError:
			raise InputError, "Usage Error"

		try:
			filedesc = os.open(linksFile,os.O_RDONLY)
		except NameError:
			raise InputError, linksFile + " could not be opened"

		file = mmap.mmap(filedesc, os.fstat(filedesc).st_size,
					mmap.MAP_SHARED, mmap.PROT_READ)
		
		try:
			htmlfile = re.compile(".*?<html>.*?</html>",
								re.MULTILINE|re.DOTALL)
			if not htmlfile.match(file):
				raise InputError, linksFile +" doesn't appear to be an HTML file"

			ext = re.compile( "^.+?" + extention + "$")
			links = [link for link in getLinks(file) if ext.match(link)]

			if not links:
				raise InputError, linksFile + " contains no links at all!"
			download(links)
		finally:
			file.close()
			os.close(filedesc)
				
	except InputError, e:
		print e
		print "Proper usage: " + sys.argv[0] + " <filename> <extention>"
		print "<filename> should be the file containing all the links"
		print "you want to download.\n"
		print "<extention> should be the file extention!  Duh!"
		return 1
	return 0
	
if __name__ == "__main__":
	sys.exit(main())
