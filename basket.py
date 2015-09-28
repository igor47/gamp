#!/usr/bin/python
# Created by Igor Serebryany (igor47@moomers.org)
# released under FreeBSD license. Do whatever you like 
# with the code, but if you use it I'm not responsible for
# anything you do with it or anything it does to you.

##################### Some user settings #####################
site_prefix = "http://www.memphismembers.com/"
max_downloads = 10		#maximum number of concurrent downloads

base_music_dir = "/media/music"
def downloadPath(artist, album, tracknum, trackname):
	return os.path.join(base_music_dir,artist.lower(),album.lower(),"%s %s" % (tracknum, trackname.lower()))

###################### End User Settings ######################

import os, os.path, sys, re, time
import urllib,urllib2,cookielib,getpass
import Queue, threading
from sgmllib import SGMLParser
from urllib2 import URLError

class basketManager:
	"""Handles downloading of albums using two public methods: downloadTrack and downloadAlbum"""
	def __init__(self):
		jar = cookielib.CookieJar()
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
		self.basketURL = None

		# Stuff for managing the actual downloads
		self.downloadQueue = Queue.Queue()
		self.downloadsList = {}
		self.downloadsLock = threading.Lock()
		self.triedbefore = []		#for retrying timed out connects, once

		album_re = "downloads_iframe_history.shtml\?(&group=\d+&album=\d+)"
		self.albumRe = re.compile(album_re)

	def request(self, url, data = None):
		"""wrapper to the url request, always parses the data for the new baset url"""
		if data:
			data = urllib.urlencode(data)

		request = urllib2.Request(url, data)
		r = self.opener.open(request)
		page = r.read()
		r.close()

		return page

	def downloadAlbum(self, album):
		"""Given an album, downloads all tracks in the album"""
		for track in album['tracks']:
			self.downloadTrack(album, track['num'])

	def downloadTrack(self, album, tracknum):
		"""Given an album and a track number, causes the download of the track to happen"""

		for track in album['tracks']:		#find the right track
			if track['num'] == tracknum:
				break

		path = downloadPath(album["artist"],album["title"],tracknum,track["name"])
		path+=track['ext']

		self.downloadsLock.acquire()
		if path in self.downloadsList:
			print "File %s is already being downloaded; it is %s%% done" % (path, self.downloadsList[path])
			self.downloadsLock.release()
			return
		else:
			self.downloadsList[path] = "Not started"
		self.downloadsLock.release()

		dirname = os.path.dirname(path)
		if not os.path.exists(dirname):
			try:
				os.makedirs(dirname)
			except IOError, err:
				print "Cannot create download directory %s: %s" % (dirname, err)
				return
		try:
			output = open(path, "wb")
		except IOError, err:
			print "Cannot open %s: %s" % (path, err)
			return

		self.downloadQueue.put((track["url"], output, path))
		print "Added track %s %s to the download queue" % (tracknum, track['name'])

		if threading.activeCount() <= max_downloads:
			newThread = threading.Thread(target=self.downloadThread)
			newThread.setDaemon(True)	#we want to be able to exit without waiting for the threads
			newThread.start()

	def downloadThread(self):
		"""The thread function which handles the actual downloading"""
		while True:
			try:
				url, output, path = self.downloadQueue.get(timeout=15)
			except Queue.Empty:
				break

			try:
				sock = self.opener.open(url)
			except URLError:
				print "\nError: could not connect to", url, "\n"
				time.sleep(15)
				self.downloadsLock.acquire()
				if url not in self.triedbefore:
					self.triedbefore.append(url)
					self.downloadQueue.put( (url, output, path) )
				else:
					self.triedbefore.remove(url)
					del self.downloadsList[path]
				self.downloadsLock.release()
				continue

			try:
				size = int(sock.info()['Content-length'])
				got = 0

				while got < size:
					s = sock.read(8192)
					got += len(s)
					output.write(s)
					self.downloadsList[path] = int( float(got)/size * 100 )

			finally:
				sock.close()
				output.flush()
				output.close()
				self.downloadsLock.acquire()
				del self.downloadsList[path]
				self.downloadsLock.release()

	def getTracks(self, album):
		"""Given an album, adds a list of available tracks for the album, sorted in track order"""

		albumSock = self.opener.open(album['url'])		#download the album page
		albumPage = albumSock.read()
		albumSock.close()

		p = albumParser()
		p.feed(albumPage)
		p.close()

		album['tracks'] = p.tracks
		album['tracks'].sort(lambda x, y: cmp( x['num'], y['num'] )) #sort in track order

	def getAlbums(self):
		"""Retrieve a list of albums in the allOfMp3 basket"""
		basketPage = self.request(site_prefix + 'basket.shtml')

		p = linksParser()
		p.feed(basketPage)
		p.close()

		albums = []
		for link,desc in p.links.items():
			m = self.albumRe.match(link)
			if m:
				new = dict()
				new['url'] = site_prefix + "downloads_iframe.shtml?" + m.group(1)
				new['artist'] = desc[1][0].strip()
				new['title'] = "".join(desc[1][1:]).strip()
				new['tracks'] = []
				albums.append(new)

		return albums

	def login(self):
		"""Logs the class into allOfMp3"""
		login_form_url = site_prefix + "do-login.shtml"
		invalid = re.compile(".*?Invalid login or password.*$", re.MULTILINE|re.DOTALL)

		while True:
			username = raw_input("allofmp3 username: ")
			password = getpass.getpass()
			data = {
					'login':username,
					'password':password,
					'url_to_return':site_prefix,
					}

			result = self.request(login_form_url, data)
			if invalid.match(result):
				print "Invalid username/password.  Try again."
			else:
				return

	def showAlbum(self, album):
		"""Displays a listing of the tracks in an album"""
		self.getTracks(album)

		while True:
			existingTracks = [ track['num'] for track in album['tracks'] ]

			print "\n\n\n"
			print "The album %s by %s contains the following songs:" % (album['title'],album['artist'])
			for track in album['tracks']:
				print "	%s %s %s	%s	%s" % \
						( track['num'], track['name'].ljust(40)[0:40], track['time'], track['size'], track['ext'])

			print
			print "(#) Download song   (a) Download all   (r) Refresh   (b) Back to album listing"

			c = raw_input("Select your action: ")
			c.lower().strip()

			if c == 'b':
				return
			if c == 'r':
				self.getTracks(album)
				continue
			elif c == 'a':
				self.downloadAlbum(album)
				print "Album added to download queue"
				return

			try:
				trackNum = "%02d" % (int(c))
				if not trackNum in existingTracks: 
					raise ValueError

				self.downloadTrack(album,trackNum)

			except ValueError:
				print "Invalid selection.  Please try again."

	def showStatus(self):
		self.downloadsLock.acquire()
		print "\n\n"
		for song,progress in self.downloadsList.items():
			if len(song) > 60:
				song = "..." + song[len(song)-57:len(song)]
			print "%s	%s%%" % (song.ljust(60), progress)

		print "Threads: %d	Downloads: %d	Queue: %d\n" % \
				( threading.activeCount(), len(self.downloadsList), self.downloadQueue.qsize() )
		self.downloadsLock.release()

class linksParser(SGMLParser):
	"""Parses an HTML document to find links and the text between the link tags"""
	def __init__(self):
		SGMLParser.__init__(self)
		self.links={}
		self.linkIndex = None
		self.descIndex = 0

	def start_a(self,attributes):
		for attr, val in attributes:
			if attr == "href":
				if val not in self.links: 
					self.links[val] = []
				self.linkIndex = val
				self.descIndex = len(self.links[val])
				self.links[val].append([])

	def handle_data(self,data):
		if self.linkIndex:
			self.links[self.linkIndex][self.descIndex].append(data)

	def end_a(self):
		self.linkIndex = None

class albumParser(SGMLParser):
	"""Parses an allOfMp3 album page to find song download links and other information"""
	def __init__(self):
		SGMLParser.__init__(self)
		self.save = False
		self.tracks = [ ]
		self.tdType = None
		self.usedTypes = ("num","time","size","name","price")

	def start_tbody(self, attributes):
		self.save = True

	def end_tbody(self):
		self.save=False

	def start_tr(self, attributes):
		self.track={ }

	def end_tr(self):
		if self.save:
			filename = self.track['url'].split('/')[-1]
			self.track['ext'] = os.path.splitext(filename)[1]
			self.track['num'] = filename[0:2]
			self.tracks.append(self.track)

	def start_td(self, attributes):
		for attr, val in attributes:
			if attr == "class":
				self.tdType = val

	def end_td(self):
		self.tdType = None

	def start_a(self, attributes):
		if self.tdType == "artist":
			for attr, val in attributes:
				if attr == "href":
					self.track['url'] = val
					self.tdType = "name"

	def end_a(self):
		self.tdType = None

	def handle_data(self,data):
		if self.tdType in self.usedTypes:
			self.track[self.tdType] = data

def main():
	#create a new allOfMp3 connection
	basket = basketManager()
	basket.login()

	albums = basket.getAlbums()

	while True:			#main program loop
		print "You have the following albums in your basket:"
		for i in xrange(len(albums)):
			print "\t%d %s - %s" % (i, albums[i]['artist'], albums[i]['title'])

		print
		print "(#) Download album   (a) Download all   (s) Status   (r) Refresh   (q) Exit"
		c = raw_input("Select your action: ")
		c = c.lower().strip()

		if c == 'q':
			return 0
		elif c == 'a':
			print "Feature coming soon"
			continue
		elif c == 'r':
			albums = basket.getAlbums()
			continue
		elif c == 's':
			basket.showStatus()
			continue
		try:
			n = int(c)
			if n >= len(albums) or n < 0:
				raise ValueError

			basket.showAlbum(albums[n])

		except ValueError:
			print "Invalid selection.  Try again - \n\n"
			continue

	return 0

if __name__ == "__main__":
	sys.exit(main())
