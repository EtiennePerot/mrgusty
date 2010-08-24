#!/usr/bin/python -OO
# -*- coding: utf-8 -*-

config = {
	'directory': r'/home/wind/Desktop/Soldier voices',
	'description': 'Voice file from Team Fortress 2 Spanish version.',
	'license': 'AudioTF2',
	'fileprefix': '',
	'filesuffix': '',
	'username': 'WindBOT',
	'password': 'Poot password heer',
	'wikiURL': 'http://wiki.teamfortress.com/w/'
}

import os
import wikiUpload
import urllib2

uploader = wikiUpload.wikiUploader(config['username'], config['password'], config['wikiURL'])
failed = []
classes = ['announcer', 'scout', 'soldier', 'pyro', 'demoman', 'heavy', 'engineer', 'medic', 'sniper', 'spy']
catclasses = {
	'announcer': 'Administrator',
	'scout': 'Scout',
	'soldier': 'Soldier',
	'pyro': 'Pyro',
	'demoman': 'Demoman',
	'heavy': 'Heavy',
	'engineer': 'Engineer',
	'medic': 'Medic',
	'sniper': 'Sniper',
	'spy': 'Spy'
}
files = os.listdir(config['directory'])
files.sort()
try:
	for f in files:
		i = f.rfind('.')
		if i == -1:
			continue
		print 'Uploading', config['directory'] + os.sep + f, 'as', config['fileprefix'] + f[:i] + config['filesuffix'] + f[i:], '...'
		category = ''
		smallest = 99999999
		for c in classes:
			if f.find(c) != -1 and f.find(c) < smallest:
				smallest = f.find(c)
				category = '\n[[Category:'+catclasses[c]+' audio responses/es]]'
		if True:
			uploader.upload(config['directory'] + os.sep + f, config['fileprefix'] + f[:i] + config['filesuffix'] + f[i:], config['description'] + category, config['license'], overwrite=False)
		else:
			print 'Failed', f
			failed.append(f)
except KeyboardInterrupt:
	print 'Stopped.'
print 'Failed:', failed