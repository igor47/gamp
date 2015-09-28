#!/usr/bin/python

import threading, Queue

class dThread(threading.Thread)
	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.queue = queue

	def run(self):
		while True:
			object = self.queue.get()


