#!/usr/bin/python

import os
import os.path
import sys

def set_track(filename):
   just_name = os.path.basename(filename)
   track_str = just_name.split()[0]
   track_num = int(track_str)

   os.system("mp3info -n %d '%s'" % (track_num, filename))

def set_all(directory):
   filenames = os.listdir(directory)
   for filename in filenames:
      set_track(os.path.join(directory, filename))


if __name__ == '__main__':
   directory = sys.argv[1]
   set_all(directory)
