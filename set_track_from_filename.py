#!/usr/bin/env python

import eyed3

import os
import os.path
import sys

def set_track(filename):
   just_name = os.path.basename(filename)
   track_str = just_name.split()[0]
   track_num = int(track_str)

   audiofile = eyed3.load(filename)
   audiofile.tag.track_num = track_num
   audiofile.tag.save()

def set_all(directory):
   filenames = os.listdir(directory)
   for filename in filenames:
      set_track(os.path.join(directory, filename))


if __name__ == '__main__':
   directory = sys.argv[1]
   set_all(directory)
