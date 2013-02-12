#!/usr/bin/python -OO
# -*- coding: utf-8 -*-
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import time, datetime
import re
import hashlib
import urllib2
import tempfile
import traceback
import threading
import random
import subprocess
import cStringIO as StringIO
import shutil
import itertools
from Queue import Queue
import wikitools
import wikiUpload
try:
	import feedparser
except:
	feedparser = None
try:
	import steam
except:
	steam = None
from wikiUpload import wikiUploader

from botConfig import config
if steam is not None and 'steamAPI' in config:
	steam.set_api_key(config['steamAPI'])
config['runtime'] = {
	'rcid': -1,
	'onlinercid': -1,
	'wiki': None,
	'edits': 0,
	'regexes': {},
	'pages': {},
	'uploader': wikiUploader(config['username'], config['password'], config['api'])
}

def u(s):
	if type(s) is type(u''):
		return s
	if type(s) is type(''):
		try:
			return unicode(s)
		except:
			try:
				return unicode(s.decode('utf8'))
			except:
				try:
					return unicode(s.decode('windows-1252'))
				except:
					return unicode(s, errors='ignore')
	try:
		return unicode(s)
	except:
		try:
			return u(str(s))
		except:
			return s
_printLock = threading.RLock()
def tprint(*args):
	s = u' '.join(map(u, args))
	with _printLock:
		try:
			print(s.encode('utf-8'))
		except:
			pass
class curry:
	def __init__(self, func, *args, **kwargs):
		self.func = func
		self.pending = args[:]
		self.kwargs = kwargs
	def __str__(self):
		if u(self.func) == u(regSub):
			return 'Regex' + u(self.pending)
		return u'<Curry of ' + u(self.func) + u'; args = ' + u(self.pending) + u'; kwargs = ' + u(self.kwargs) + u'>'
	def __repr__(self):
		return self.__str__()
	def __call__(self, *args, **kwargs):
		if kwargs and self.kwargs:
			kw = self.kwargs.copy()
			kw.update(kwargs)
		else:
			kw = kwargs or self.kwargs
		return self.func(*(self.pending + args), **kw)
def getTempFilename(extension=None):
	global config
	if extension is None:
		f = tempfile.mkstemp(prefix=config['tempPrefix'])
	else:
		f = tempfile.mkstemp(suffix=u'.' + u(extension), prefix=config['tempPrefix'])
	os.close(f[0]) # Damn you Python I just want a filename
	return u(f[1])

def wiki():
	global config
	if config['runtime']['wiki'] is None:
		config['runtime']['wiki'] = wikitools.wiki.Wiki(config['api'])
		tprint('Logging in as', config['username'], '...')
		config['runtime']['wiki'].login(config['username'], config['password'])
		try:
			config['runtime']['onlinercid'] = int(u(wikitools.page.Page(wiki(), config['pages']['rcid']).getWikiText()).strip())
			config['runtime']['rcid'] = config['runtime']['onlinercid']
		except:
			error('Couldn\'t read RCID.')
		tprint('Logged in.')
	return config['runtime']['wiki']
def page(p):
	global config
	if type(p) in (type(''), type(u'')):
		p = u(p)
		if p not in config['runtime']['pages']:
			try:
				config['runtime']['pages'][p] = wikitools.page.Page(wiki(), p, followRedir=False)
			except wikitools.page.BadTitle:
				# Try URL-decoding the title
				config['runtime']['pages'][p] = wikitools.page.Page(wiki(), urllib2.unquote(p), followRedir=False)
		return config['runtime']['pages'][p]
	# Else, it is a page object
	title = u(p.title)
	if title not in config['runtime']['pages']:
		config['runtime']['pages'][title] = p
	return config['runtime']['pages'][title]
def getSummary(summary):
	summary = u(summary)
	while len(summary) > 250:
		if summary.find(u' ') == -1:
			summary = summary[:summary.rfind(u' ')] + u'...'
		else:
			summary = summary[:247] + u'...'
	return summary
_editLock = threading.RLock()
def editPage(p, content, summary=u'', minor=True, bot=True, nocreate=True):
	global config
	with _editLock:
		now = time.time()
		if 'editWaitTime' in config and type(config['editWaitTime']) is type(()) and len(config['editWaitTime']) == 2:
			if 'lastEdit' not in config['runtime']:
				config['runtime']['lastEdit'] = now
			waitTime = random.uniform(*config['editWaitTime'])
			if config['runtime']['lastEdit'] + waitTime > now:
				time.sleep(config['runtime']['lastEdit'] + waitTime - now)
	summary = getSummary(summary)
	p = page(p)
	try:
		tprint('Editing', p.title, 'with summary', summary)
	except:
		pass
	try:
		if nocreate:
			if minor:
				result = p.edit(u(content), summary=summary, minor=True, bot=bot, nocreate=nocreate)
			else:
				result = p.edit(u(content), summary=summary, notminor=True, bot=bot, nocreate=nocreate)
		else:
			if minor:
				result = p.edit(u(content), summary=summary, minor=True, bot=bot)
			else:
				result = p.edit(u(content), summary=summary, notminor=True, bot=bot)
	except:
		warning('Couldn\'t edit', p.title)
		return None
	try:
		if result['edit']['result']:
			config['runtime']['edits'] += 1
	except:
		warning('Couldn\'t edit', p.title)
	config['runtime']['lastEdit'] = now
	return result
def deletePage(p, summary=False):
	if summary:
		summary = getSummary(summary)
	return page(p).delete(summary)
def uploadFile(filename, destfile, pagecontent='', license='', overwrite=False, reupload=False):
	global config
	return config['runtime']['uploader'].upload(filename, destfile, pagecontent, license, overwrite=overwrite, reupload=reupload)
def updateRCID():
	if abs(config['runtime']['rcid'] - config['runtime']['onlinercid']) >= config['rcidrate']:
		tprint('Updating last RCID...')
		try:
			editPage(config['pages']['rcid'], config['runtime']['rcid'], summary=u'Updated Recent Changes log position to ' + u(config['runtime']['rcid']))
			config['runtime']['onlinercid'] = config['runtime']['rcid']
		except:
			warning('Couldn\'t update RCID.')
def updateEditCount(force=False):
	global config
	if not config['runtime']['edits']:
		return
	if not force and random.randint(0, 40) != 7:
		return
	try:
		editPage(config['pages']['editcount'], int(wikitools.api.APIRequest(wiki(), {
			'action': 'query',
			'list': 'users',
			'usprop': 'editcount',
			'ususers': config['username']
		}).query(querycontinue=False)['query']['users'][0]['editcount']) + 1, summary=u'Updated edit count.')
		config['runtime']['edits'] = 0
	except:
		warning('Couldn\'t update edit count.')

# Because SOME LIBRARY will not use singletons, this has to be done at the bot level
# rather than the individual filter level to avoid loading the damn thing twice.
steamGameSchemas = {}
def steamGetGameSchema(game):
	global steamGameSchemas
	if steam is None:
		return None
	if game not in steamGameSchemas:
		steamGameSchemas[game] = game.item_schema()
	return steamGameSchemas[game]
steamGameAssets = {}
def steamGetGameAssets(game):
	global steamGameAssets
	if steam is None:
		return None
	if game not in steamGameAssets:
		steamGameAssets[game] = game.assets()
	return steamGameAssets[game]

def compileRegex(regex, flags=re.IGNORECASE):
	global config
	regex = u(regex)
	if regex in config['runtime']['regexes']:
		return config['runtime']['regexes'][regex]
	config['runtime']['regexes'][regex] = re.compile(regex, flags)
	return config['runtime']['regexes'][regex]

def warning(*info):
	s = []
	tprint(info)
	import traceback
	traceback.print_exc()
def error(*info):
	warning(*info)
	sys.exit(1)

def setFilterName(f, name):
	name = u(name)
	f.__unicode__ = lambda: name
	f.__str__ = lambda: name.encode('utf8')
	f.filterName = name
	return f

def setFilterLowPriority(f, priority=True):
	f.lowPriority = priority
	return f
class link:
	def __init__(self, content):
		content = u(content)
		self.joined = False
		self.setBody(content)
		self.setType(u'unknown')
		self.setLabel(None)
		self.setLink(u'')
		self.anchor = None
		self.joined = False
		if len(content) > 2:
			if content[:2] == u'[[' and content[-2:] == u']]':
				split = content[2:-2].split(u'|')
				if len(split) in (1, 2):
					self.setType(u'internal')
					lnk = split[0]
					if lnk.find(u':') == -1:
						lnk = lnk.replace(u'_', u' ')
					anchor = None
					if lnk.find(u'#') != -1:
						lnk, anchor = lnk.split(u'#', 1)
						self.setAnchor(anchor)
					self.setLink(lnk)
					if len(split) == 2:
						self.setLabel(split[1])
					else:
						self.setLabel(split[0])
						self.joined = anchor is None
			elif content[0] == u'[' and content[-1] == u']':
				split = content[1:-1].split(u' ', 1)
				self.setType(u'external')
				self.setLink(split[0])
				if len(split) == 2:
					self.setLabel(split[1])
				else:
					self.setLabel(None)
	def getType(self):
		return u(self.kind)
	def getBody(self):
		return u(self.body)
	def getLink(self, withAnchor=False):
		if withAnchor and self.getAnchor() is not None:
			return u(self.link) + u'#' + self.getAnchor()
		return u(self.link)
	def getAnchor(self):
		return self.anchor
	def getLabel(self):
		if self.label is None:
			return None
		if self.joined:
			return self.getLink()
		return u(self.label)
	def setType(self, kind):
		self.kind = u(kind)
	def setBody(self, body):
		self.body = u(body)
	def setLink(self, link):
		link = u(link)
		if self.getType() == u'internal' and link.find(u'#') != -1:
			link, anchor = link.split(u'#', 1)
			self.setAnchor(anchor)
		self.link = link
		if self.joined:
			self.label = u(link)
	replaceDots = compileRegex(r'(?:\.[a-f\d][a-f\d])+')
	def _replaceDots(self, g):
		s = ''
		g = g.group(0)
		for i in xrange(0, len(g), 3):
			s += chr(int(g[i + 1:i + 3], 16))
		return s.decode('utf8')
	def setAnchor(self, anchor):
		if self.getType() == u'internal':
			u(anchor).replace(u'_', u' ')
			try:
				anchor = link.replaceDots.sub(self._replaceDots, anchor)
			except:
				pass
			self.anchor = anchor
	def setLabel(self, label):
		if label is None:
			self.label = None
		else:
			self.label = u(label)
		if self.joined:
			self.link = u(label)
	def __str__(self):
		return self.__unicode__()
	def __repr__(self):
		return u'<Link-' + self.getType() + u': ' + self.__unicode__() + u'>'
	def __unicode__(self):
		label = self.getLabel()
		tmpLink = self.getLink(withAnchor=True)
		if self.getType() == u'internal':
			tmpLink2 = tmpLink.replace(u'_', u' ')
			if label in (tmpLink2, tmpLink) or (label and tmpLink and (label[0].lower() == tmpLink[0].lower() and tmpLink[1:] == label[1:]) or (label[0].lower() == tmpLink2[0].lower() and tmpLink2[1:] == label[1:])):
				return u'[[' + label + u']]'
			elif tmpLink and label and len(label) > len(tmpLink) and (label.lower().find(tmpLink2.lower()) == 0 or label.lower().find(tmpLink.lower()) == 0):
				index = max(label.lower().find(tmpLink2.lower()), label.lower().find(tmpLink.lower()))
				badchars = (u' ', u'_', u'.')
				nobadchars = True
				for c in badchars:
					if label[:index].find(c) != -1 or label[index+len(tmpLink):].find(c) != -1:
						nobadchars = False
				if nobadchars:
					return label[:index] + u(link(u'[[' + tmpLink + u'|' + label[index:index+len(tmpLink)] + u']]')) + label[index+len(tmpLink):]
			return u'[[' + tmpLink + u'|' + label + u']]'
		if self.getType() == u'external':
			if label is None:
				return u'[' + tmpLink + u']'
			return u'[' + tmpLink + u' ' + label + u']'
		return self.getBody()
class template:
	maxInlineParams = 1
	def __init__(self, content):
		content = u(content)
		self.changed = False
		self.content = content
		self.name = None
		self.order = None
		self.links = []
		self.params = []
		self.paramNum = 0
		self.indentation = {}
		self.defaultIndent = 0
		if len(content) > 4 and content[:2] == '{{' and content[-2:] == '}}':
			innerRegex = compileRegex(r'\s*\|\s*')
			itemRegex = compileRegex(r'^(\S[^=]*?)\s*=\s*([\s\S]*?)$')
			content = content[2:-2]
			content, self.links, self.keys = linkExtract(content)
			innerStuff = innerRegex.split(content)
			if innerStuff[0][:9].lower() == 'template:':
				innerStuff[0] = innerStuff[0][9:]
			self.name = u(innerStuff[0][0].upper() + innerStuff[0][1:]).replace(u'_', u' ').strip()
			innerStuff = innerStuff[1:]
			for i in innerStuff:
				i = linkRestore(i.strip(), self.links, self.keys, restore=True)
				itemRes = itemRegex.search(i)
				if itemRes:
					self.params.append((u(itemRes.group(1)).lower(), u(itemRes.group(2))))
				else:
					self.paramNum += 1
					self.params.append((u(self.paramNum), i))
		self.originalContent = self.content
		self.originalParams = self.params[:]
		self.originalName = self.name
		self.forceindent = False
	def indentationMatters(self, doesitmatter=True):
		self.forceindent = doesitmatter
	def getName(self):
		return self.name
	def setName(self, name):
		self.name = u(name).replace(u'_', u' ')
		self.changed = self.changed or self.name != self.originalName
	def getParam(self, key):
		key = u(key).lower()
		for k, v in self.params:
			if k == key:
				return v
		return None
	def delParam(self, *indexes):
		for index in indexes:
			index = u(index)
			isNumber = self.isInt(index)
			for p in range(len(self.params)):
				k, v = self.params[p]
				if k == index:
					self.changed = True
					self.params = self.params[:p] + self.params[p+1:]
					if isNumber:
						if int(index) == self.paramNum:
							self.paramNum -= 1
					break
	def setParam(self, index=None, value=u''):
		if value is None:
			return self.delParam(index)
		if index is None:
			index = u(self.paramNum)
		else:
			index = u(index).lower()
		isNumber = self.isInt(index)
		value = u(value)
		hasChanged = False
		for p in range(len(self.params)):
			k, v = self.params[p]
			if k == index:
				self.changed = self.changed or v != value
				self.params[p] = (k, value)
				hasChanged = True
				break
		if not hasChanged:
			if isNumber:
				while self.numParam < int(index) - 1:
					self.appendParam(u'')
			self.params.append((index, value))
			self.changed = True
	def appendParam(self, value=u''):
		self.paramNum += 1
		self.params.append((u(self.paramNum), value))
	def setPreferedIndentation(self, index, indent=0):
		self.indentation[u(index)] = indent
		self.changed = self.changed or self.forceindent
	def setDefaultIndentation(self, indent=0):
		self.defaultIndent = indent
		self.changed = self.changed or self.forceindent
	def setPreferedOrder(self, order=None):
		order2 = []
		for o in order:
			order2.append(u(o))
		self.order = order2
		oldParams = self.params[:]
		self.changed = self.changed or self.fixOrder() == oldParams
	def renameParam(self, oldkey, newkey):
		oldkey, newkey = u(oldkey).lower(), u(newkey).lower()
		if oldkey == newkey:
			return
		for p in range(len(self.params)):
			k, v = self.params[p]
			if k == oldkey:
				self.params[p] = (newkey, v)
				self.changed = True
				break
	def fixOrder(self):
		if self.order is None:
			return self.params
		newParams = []
		doneParams = []
		for k in self.order:
			k = u(k)
			if self.getParam(k) is not None:
				newParams.append((k, self.getParam(k)))
				doneParams.append(k)
		for k, v in self.params:
			if k not in doneParams:
				doneParams.append(k)
				newParams.append((k, v))
		self.params = newParams
		return self.params
	def defined(self):
		return self.name is not None
	def isInt(self, i):
		try:
			return u(int(i)) == u(i) and int(i) > 0
		except:
			return False
	def __str__(self):
		return self.__unicode__()
	def __repr__(self):
		return u'<Template-' + self.getName() + u': ' + self.__unicode__() + u'>'
	def __unicode__(self):
		if not self.defined():
			return u''
		if not self.changed:
			return self.originalContent
		self.fixOrder()
		params = [self.name]
		indentMode = len(self.params) > template.maxInlineParams or self.forceindent
		maxIndent = 0
		if indentMode:
			for k, v in self.params:
				l = len(k) + self.defaultIndent
				if k in self.indentation:
					l = len(k) + self.indentation[k]
				if not self.isInt(k) and l > maxIndent:
					maxIndent = l
		numParam = 1
		for k, v in self.params:
			indent = self.defaultIndent
			if k in self.indentation and indentMode:
				indent = self.indentation[k]
			try:
				isNumber = u(int(index)) == u(index) and int(index) > 0
			except:
				isNumber = False
			if indentMode:
				key = u' ' * indent + u'| '
				addKey = True
				if self.isInt(k):
					if int(k) == numParam:
						addKey = False
					numParam += 1
				if addKey:
					key += k + (u' ' * max(0, maxIndent - len(k) - indent)) + u' = '
			else:
				key = u''
				addKey = True
				if self.isInt(k):
					if int(k) == numParam:
						addKey = False
					numParam += 1
				if addKey:
					key += k + u' = '
			params.append(key + v)
		if indentMode:
			params = u'\n'.join(params) + u'\n'
		else:
			params = u' | '.join(params)
		return u'{{' + params + u'}}'
extractKey = itertools.count()
def getNewKey(): # Should be made threadsafe if threads are ever used
	return next(extractKey)
def linkExtract(content):
	content = u(content)
	links1 = compileRegex(r'\[\[([^\[\]]+)\]\]')
	links2 = compileRegex(r'\[([^\[\]]+)\](?!\])')
	linklist = {}
	keys = []
	res = links1.search(content)
	while res:
		key = getNewKey()
		linklist[key] = link(res.group())
		content = content[:res.start()] + u'~!~!~!~OMGLINK-' + u(key) + u'~!~!~!~' + content[res.end():]
		keys.append(key)
		res = links1.search(content)
	res = links2.search(content)
	while res:
		key = getNewKey()
		linklist[key] = link(res.group())
		content = content[:res.start()] + u'~!~!~!~OMGLINK-' + u(key) + u'~!~!~!~' + content[res.end():]
		keys.append(key)
		res = links2.search(content)
	return content, linklist, keys
def templateExtract(content):
	content = u(content)
	templatesR = compileRegex(r'\{\{([^\{\}]+)\}\}')
	templatelist = {}
	keys = []
	res = templatesR.search(content)
	while res:
		key = getNewKey()
		templatelist[key] = template(res.group())
		content = content[:res.start()] + u'~!~!~!~OMGTEMPLATE-' + u(key) + u'~!~!~!~' + content[res.end():]
		keys.append(key)
		res = templatesR.search(content)
	return content, templatelist, keys
def blankAround(content, search, repl=u''):
	content = u(content)
	search = u(search)
	repl = u(repl)
	blank = compileRegex(u'(\\s*)' + u(re.escape(search)) + u'(\\s*)')
	res = blank.search(content)
	if not res:
		return content.replace(search, repl)
	if u(res.group(0)) == content:
		return repl
	if len(res.group(1)) < len(res.group(2)):
		return content[:res.end(1)] + content[res.end(2):]
	else:
		return content[:res.start()] + content[res.start(2):]
def linkRestore(content, links=[], keys=[], restore=False):
	for k in reversed(keys):
		l = links[k]
		if l is None:
			content = blankAround(content, u'~!~!~!~OMGLINK-' + u(k) + u'~!~!~!~', u'')
		else:
			if restore:
				l = l.getBody()
			content = content.replace(u'~!~!~!~OMGLINK-' + u(k) + u'~!~!~!~', u(l))
	return content
def templateRestore(content, templates={}, keys=[]):
	for k in reversed(keys):
		t = templates[k]
		if t is None:
			content = blankAround(content, u'~!~!~!~OMGTEMPLATE-' + u(k) + u'~!~!~!~', u'')
		else:
			content = content.replace(u'~!~!~!~OMGTEMPLATE-' + u(k) + u'~!~!~!~', u(t))
	return content
def safeContent(content):
	safelist = []
	tags = compileRegex(r'<(?:ref|gallery|pre|code)[^<>]*>[\S\s]*?</(?:ref|gallery|pre|code)>', re.IGNORECASE | re.MULTILINE)
	comments = compileRegex(r'<!--[\S\s]*?-->')
	res = tags.search(content)
	if not res:
		res = comments.search(content)
	while res:
		key = getNewKey()
		safelist.append(('~!~!~!~OMGTAG-' + u(key) + u'~!~!~!~', u(res.group())))
		content = content[:res.start()] + u'~!~!~!~OMGTAG-' + u(key) + u'~!~!~!~' + content[res.end():]
		res = tags.search(content)
		if not res:
			res = comments.search(content)
	return content, safelist
def safeContentRestore(content, safelist=[]):
	for s in reversed(safelist):
		content = content.replace(s[0], s[1])
	return content
def regReplaceCallBack(sub, match):
	groupcount = 1
	for g in match.groups():
		if g is not None:
			sub = sub.replace(u'$' + u(groupcount), g)
		else:
			sub = sub.replace(u'$' + u(groupcount), u'')
		groupcount += 1
	return sub
def regSub(regexes, content, **kwargs):
	content = u(content)
	for regex in regexes.keys():
		if type(regex) in (type(()), type([])):
			compiled = compileRegex(u(regex[0]), regex[1])
		else:
			compiled = compileRegex(u(regex), re.IGNORECASE | re.DOTALL | re.MULTILINE)
		callback = curry(regReplaceCallBack, u(regexes[regex]))
		oldcontent = u''
		while content != oldcontent:
			oldcontent = content
			content = compiled.sub(callback, content)
	return u(content)
def dumbReplacement(strings, content, **kwargs):
	content = u(content)
	for s in strings.keys():
		content = content.replace(u(s), u(strings[s]))
	return content
def filterEnabled(f, **kwargs):
	if type(f) is not type(()):
		return True
	if len(f) < 2:
		return True
	if type(f[1]) is not type({}):
		return True
	article = None
	if 'article' in kwargs.keys():
		article = kwargs['article']
		if article is None:
			return True
		if type(article) not in (type(u''), type('')):
			article = article.title
	if article is None:
		return True
	if 'languageBlacklist' in f[1].keys():
		for i in f[1]['languageBlacklist']:
			if compileRegex(u'/' + u(i) + u'$').search(u(article)):
				return False
		return True
	if 'languageWhitelist' in f[1].keys():
		for i in f[1]['languageWhitelist']:
			if compileRegex(u'/' + u(i) + u'$').search(u(article)):
				return True
		return False
	if 'language' in f[1].keys():
		return compileRegex(u'/' + u(f[1]['language']) + u'$').search(u(article))
	return True
scheduledTasks = []
def scheduleTask(task, oneinevery):
	global scheduledTasks
	result = random.randint(0, oneinevery-1)
	tprint('Task:', task, '; result:', result)
	if not result:
		scheduledTasks.append(task)
def runScheduledTasks():
	global scheduledTasks
	if not len(scheduledTasks):
		tprint('No tasks scheduled.')
		return
	tprint('Running scheduled tasks...')
	for t in scheduledTasks:
		tprint('Running task:', t)
		try:
			t()
			tprint('End of task:', t)
		except:
			tprint('Error while executing task:', t)
def sFilter(filters, content, returnActive=False, **kwargs):
	content = u(content)
	lenfilters = len(filters)
	if not lenfilters:
		if returnActive:
			return content, []
		return content
	filtercount = 0
	activeFilters = []
	for f in filters:
		if not filterEnabled(f, **kwargs):
			continue
		if type(f) is type(()):
			f, params = f
			if 'lowPriority' in params and params['lowPriority']:
				setFilterLowPriority(f)
		filtercount += 1
		loopTimes = 0
		beforeFilter = u''
		while not loopTimes or beforeFilter != content:
			loopTimes += 1
			if loopTimes >= config['filterPasses']:
				tprint('Warning: More than', config['filterPasses'], 'loops with filter', u(f))
				break
			beforeFilter = content
			content = u(f(content, **kwargs))
			if content != beforeFilter and f not in activeFilters:
				activeFilters.append(f)
	if returnActive:
		return content, activeFilters
	return content
def linkFilter(filters, links, linkkeys, returnActive=False, **kwargs):
	activeFilters = []
	for f in filters:
		if not filterEnabled(f, **kwargs):
			continue
		if type(f) is type(()):
			f, params = f
			if 'lowPriority' in params and params['lowPriority']:
				setFilterLowPriority(f)
		for i in linkkeys:
			if links[i] is not None and isinstance(links[i], link):
				oldLink = u(links[i])
				links[i] = f(links[i], **kwargs)
				if oldLink != u(links[i]) and f not in activeFilters:
					activeFilters.append(f)
	if returnActive:
		return links, linkkeys, activeFilters
	return links, linkkeys
def templateFilter(filters, templatelist, templatekeys, returnActive=False, **kwargs):
	activeFilters = []
	for f in filters:
		if not filterEnabled(f, **kwargs):
			continue
		if type(f) is type(()):
			f, params = f
			if 'lowPriority' in params and params['lowPriority']:
				setFilterLowPriority(f)
		for i in templatekeys:
			if templatelist[i] is not None and isinstance(templatelist[i], template):
				oldTemplate = u(templatelist[i])
				templatelist[i] = f(templatelist[i], **kwargs)
				if oldTemplate != u(templatelist[i]) and f not in activeFilters:
					activeFilters.append(f)
	if returnActive:
		return templatelist, templatekeys, activeFilters
	return templatelist, templatekeys
def linkTextFilter(subfilters, l, linksafe=False, **kwargs):
	if l.getType() == u'internal' and l.getLink().find(u':') == -1 and pageFilter(l.getLink()):
		if linksafe:
			l.setLink(sFilter(subfilters, l.getLink(), **kwargs))
		if l.getLabel().find(u':') == -1:
			l.setLabel(sFilter(subfilters, l.getLabel(), **kwargs))
	return l
def linkDomainSub(fromDomain, toDomain, link, **kwargs):
	domainR = compileRegex(r'^(https?://(?:[-\w]+\.)*)' + u(re.escape(fromDomain)) + r'(\S+)$')
	toDomain = u(toDomain)
	if link.getType() == 'external':
		linkInfo = domainR.search(link.getLink())
		if linkInfo:
			link.setLink(u(linkInfo.group(1)) + toDomain + u(linkInfo.group(2)))
	return link
def linkDomainFilter(fromDomain, toDomain):
	return curry(linkDomainSub, fromDomain, toDomain)
def regexes(rs):
	return curry(regSub, rs)
def regex(reg, replace):
	return regexes({reg: replace})
def dumbReplaces(rs):
	return setFilterName(curry(dumbReplacement, rs), u'DumbReplacements(' + u(rs) + u')')
def dumbReplace(subject, replacement):
	return setFilterName(dumbReplaces({subject: replacement}), u'DumbReplacement(' + u(subject) + u' \u2192 ' + u(replacement) + u')')
def wordRegex(word, **kwargs):
	flags = None
	if type(word) in (type(()), type([])):
		flags = word[1]
		word = word[0]
	word = u(re.sub(r'[-_ ]+', r'[-_ ]', u(word)))
	word = u(r"(?<![\u00E8-\u00F8\xe8-\xf8\w])(?<!'')(?<!" + r'"' + ")(?:\\b|(?<=[ \\[\\]\\(\\):;.,\"'*\\xab\\xbb])|^)" + word + r"(?:\b(?![\u00E8-\u00F8\xe8-\xf8\w])(?!''|" + r'"' + ")|(?=[ \\[\\]\(\\):;.,\"'*\\xab\\xbb])|$)")
	if flags is None:
		return word
	return (word, flags)
def wordFilter(correct, *badwords, **kwargs):
	correct = u(correct)
	rs = {}
	badwords2 = []
	for i in badwords:
		if type(i) in (type(()), type([])):
			badwords2.extend(map(u, i))
		else:
			badwords2.append(u(i))
	if not len(badwords2):
		badwords2.append(correct)
	for w in badwords2:
		if 'keepcapitalization' in kwargs and kwargs['keepcapitalization']:
			if type(w) not in (type(()), type([])):
				w = (w, 0)
			else:
				w = (w[0], 0)
			rs[wordRegex(w, **kwargs)] = correct
			rs[wordRegex((w[0][0].swapcase() + w[0][1:], w[1]), **kwargs)] = correct[0].swapcase() + correct[1:]
		else:
			rs[wordRegex(w, **kwargs)] = correct
	return setFilterName(regexes(rs), u'WordFilter(' + u'/'.join(badwords2) + u' \u2192 ' + correct + u')')
def enforceCapitalization(*words, **kwargs):
	for w in words:
		addSafeFilter(setFilterName(wordFilter(u(w)), u'EnforceCapitalization(' + u(w) + u')'), **kwargs)
pageFilters = []
pageWhitelist = []
categoryFilters = []
def pageFilter(page):
	global pageFilters, pageWhitelist
	if type(page) in (type(()), type([])):
		pages = []
		for p in page:
			if pageFilter(p):
				pages.append(p)
		return pages
	if type(page) not in (type(u''), type('')):
		page = page.title
	page = u(page)
	if page in pageWhitelist:
		return True
	for f in pageFilters:
		if f.search(page):
			return False
	return True
def categoryFilter(page):
	global categoryFilters
	pageCategories = page.getCategories()
	for c in pageCategories:
		if u(c).replace(u'_', ' ') in categoryFilters:
			return False
	return True
def addPageFilter(*filters):
	global pageFilters
	for f in filters:
		pageFilters.append(compileRegex(f))
def addBlacklistPage(*pages):
	for p in pages:
		addPageFilter(re.escape(u(p)))
def addWhitelistPage(*pages):
	global pageWhitelist
	for p in pages:
		if type(p) in (type([]), type(())):
			addWhitelistPage(*p)
		elif u(p) not in pageWhitelist:
			pageWhitelist.append(u(p))
def addBlacklistCategory(*categories):
	global categoryFilters
	for c in categories:
		categoryFilters.append(u(c).replace(u'_', ' '))
def loadBlacklist():
	global config
	for l in page(config['pages']['blacklist']).getLinks():
		l = u(l)
		if l.find(u':') != -1:
			if l[:l.find(u':')].lower() == 'category':
				addBlacklistCategory(l)
				continue
		addBlacklistPage(l)

filters = {
	'regular': [],
	'safe': [],
	'link': [],
	'template': [],
	'file': []
}
def addFilterType(filterType, *fs, **kwargs):
	global filters
	for f in fs:
		f = (f, kwargs)
		if f not in filters[filterType]:
			filters[filterType].append(f)
def delFilterType(filterType, *fs, **kwargs):
	global filters
	for f in fs:
		f = (f, kwargs)
		if f in filters[filterType]:
			filters[filterType].remove(f)
def addFilter(*fs, **kwargs):
	addFilterType('regular', *fs, **kwargs)
def delFilter(*fs, **kwargs):
	delFilterType('regular', *fs, **kwargs)
def addSafeFilter(*fs, **kwargs):
	addFilterType('safe', *fs, **kwargs)
def delSafeFilter(*fs, **kwargs):
	delFilterType('safe', *fs, **kwargs)
def addLinkFilter(*fs, **kwargs):
	addFilterType('link', *fs, **kwargs)
def delLinkFilter(*fs, **kwargs):
	delFilterType('link', *fs, **kwargs)
def addTemplateFilter(*fs, **kwargs):
	addFilterType('template', *fs, **kwargs)
def delTemplateFilter(*fs, **kwargs):
	delFilterType('template', *fs, **kwargs)
def addFileFilter(*fs, **kwargs):
	addFilterType('file', *fs, **kwargs)
def delFileFilter(*fs, **kwargs):
	delFilterType('file', *fs, **kwargs)
def filterRepr(filters):
	s = []
	reprRegex = compileRegex(r'^<function (\S+)')
	for f in filters:
		if type(f) in (type([]), type(())) and not len(f[1]):
			f = f[0] # Omit parameters if there are none
		try:
			name = f.filterName
			s.append(name)
		except:
			res = reprRegex.search(u(f))
			if res:
				filterR = u(res.group(1))
				if filterR not in s:
					s.append(filterR)
			elif u(f) not in s:
				s.append(u(f))
	if not len(s):
		return u'Built-in filters' # Link simplification, template formatting, etc
	return u', '.join(s)
def fixContent(content, article=None, returnActive=False, **kwargs):
	global filters
	content = u(content)
	oldcontent = u''
	loopTimes = 0
	redirect = False
	activeFilters = []
	if len(content) > 9:
		redirect = content[:9] == u'#REDIRECT'
	filterKawrgs = {
		'returnActive': True,
		'redirect': redirect
	}
	if article is not None:
		article = page(article)
		filterKawrgs['article'] = article
	while not loopTimes or content != oldcontent:
		loopTimes += 1
		if loopTimes > 2:
			tprint('Pass', loopTimes, 'on', article)
		if loopTimes >= config['pagePasses']:
			tprint('Warning: More than', config['pagePasses'], 'fix passes on article', u(article.title))
			break
		oldcontent = content
		# Apply unsafe filters
		content, activeF = sFilter(filters['regular'], content, **filterKawrgs)
		activeFilters.extend(activeF)
		# Apply safe filters
		content, safelist = safeContent(content)
		content, templatelist, templatekeys = templateExtract(content)
		content, linklist, linkkeys = linkExtract(content)
		content, activeF = sFilter(filters['safe'], content, **filterKawrgs)
		activeFilters.extend(activeF)
		extraLinks = setFilterName(curry(linkTextFilter, filters['safe']), u'(Content filters applied to links)')
		addLinkFilter(extraLinks)
		if not redirect:
			linklist, linkkeys, activeF = linkFilter(filters['link'], linklist, linkkeys, **filterKawrgs)
			activeFilters.extend(activeF)
		content = linkRestore(content, linklist, linkkeys)
		templatelist, templatekeys, activeF = templateFilter(filters['template'], templatelist, templatekeys, **filterKawrgs)
		activeFilters.extend(activeF)
		content = templateRestore(content, templatelist, templatekeys)
		content = safeContentRestore(content, safelist)
		delLinkFilter(extraLinks)
	if article is not None and u(article.title)[:5] == 'File:':
		# Apply file filters
		content, activeF = sFilter(filters['file'], content, **filterKawrgs)
		activeFilters.extend(activeF)
	if returnActive:
		return content, activeFilters
	return content
class BatchScheduler:
	class BatchSchedulerThread(threading.Thread):
		def __init__(self, scheduler):
			threading.Thread.__init__(self)
			self.scheduler = scheduler
			self.killed = False
			self.task = None
			self.busy = threading.Condition()
			self.daemon = True
			self.start()
		def work(self, task):
			with self.busy:
				if not self.killed:
					self.task = task
					self.busy.notify()
		def run(self):
			while not self.killed:
				with self.busy:
					while not self.killed and self.task is None:
						self.busy.wait()
				if not self.killed:
					function, args, kwargs = self.task
					try:
						function(*args, **kwargs)
					except Exception, e:
						tprint('Exception', e, 'occured in worker thread.')
					self.task = None
					self.scheduler.freePool.put(self)
		def stop(self):
			with self.busy:
				self.killed = True
				self.busy.notify()
	def __init__(self, concurrency=16):
		global config
		self.concurrency = concurrency
		if 'concurrency' in config and not config['concurrency']:
			self.concurrency = 1
		elif 'maxConcurrency' in config:
			self.concurrency = min(config['maxConcurrency'], self.concurrency)
		self.tasks = Queue()
		self.freePool = Queue(self.concurrency)
		for x in xrange(self.concurrency):
			self.freePool.put(BatchScheduler.BatchSchedulerThread(self))
		self.deallocated = False
	def schedule(self, target, *args, **kwargs):
		if not self.deallocated:
			self.tasks.put((target, args, kwargs))
	def execute(self, cleanup=True):
		if self.deallocated:
			return
		try:
			while not self.tasks.empty():
				task = self.tasks.get()
				worker = self.freePool.get()
				worker.work(task)
			while not self.freePool.full():
				time.sleep(.2)
		except KeyboardInterrupt:
			self.deallocate()
		if cleanup:
			while not self.tasks.empty():
				self.tasks.get() # Empty the queue
			self.deallocate()
	def deallocate(self):
		if not self.deallocated:
			toJoin = []
			while not self.freePool.empty():
				toJoin.append(self.freePool.get())
				toJoin[-1].stop()
			try:
				for worker in toJoin:
					worker.join()
			except KeyboardInterrupt:
				pass # Give up waiting
			self.deallocated = True
class PageReviewSpooler:
	def __init__(self):
		self.pages = Queue()
		self.editQueue = Queue()
		self.pageLock = threading.RLock()
		self.seenPages = {}
	def addPage(self, page, **kwargs):
		pageTite = page
		if hasattr(page, 'title'):
			pageTite = page.title
		with self.pageLock:
			if pageTite not in self.seenPages:
				self.seenPages[pageTite] = True
				self.pages.put((page, kwargs))
	def addEdit(self, page, content, summary):
		self.editQueue.put((page, content, summary))
	def processPage(self, article, kwargs):
		article = page(article)
		force = False
		priorityEdits = False
		if 'force' in kwargs and kwargs['force']:
			force = True
		try:
			catFilter = categoryFilter(article)
		except wikitools.page.NoPage:
			tprint('No such page:', article)
			return False
		except:
			catFilter = True
		if not force and (not pageFilter(article) or not catFilter):
			tprint('Skipping:', article)
			return
		originalContent = u(article.getWikiText())
		content, activeFilters = fixContent(originalContent, returnActive=True, article=article)
		if content != originalContent:
			# Check if all edits are low priority
			for f in activeFilters:
				if not hasattr(f, 'lowPriority') or not f.lowPriority:
					priorityEdits = True
					break
			if priorityEdits:
				tprint(article, 'needs to be updated.')
				summary = u'Auto: ' + filterRepr(activeFilters)
				if 'reason' in kwargs:
					summary += u' (' + u(kwargs['reason']) + u')'
				if 'fake' in kwargs:
					tprint('-------- New content is: --------')
					tprint(content)
					tprint('---------------------------------')
				else:
					self.addEdit(article, content, summary)
			else:
				tprint(article, 'only requires low priority edits. Skipping.')
		else:
			tprint(article, 'is up-to-date.')
	def run(self):
		self.readScheduler = BatchScheduler()
		self.writeScheduler = BatchScheduler()
		while not self.pages.empty():
			while not self.pages.empty():
				page, kwargs = self.pages.get()
				self.readScheduler.schedule(self.processPage, page, kwargs)
			self.readScheduler.execute(cleanup=False) # May add more pages to self.pages, hence the double while loop
		self.readScheduler.deallocate()
		while not self.editQueue.empty():
			page, content, summary = self.editQueue.get()
			self.writeScheduler.schedule(editPage, page, content, summary=summary)
		self.writeScheduler.execute()
_pageReviewSpooler = PageReviewSpooler()
def fixPage(article, **kwargs):
	_pageReviewSpooler.addPage(article, **kwargs)
def executeEdits():
	_pageReviewSpooler.run()
def patrol(change):
	global config
	secondsElapsed = (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(time.mktime(time.strptime(change['timestamp'], r'%Y-%m-%dT%H:%M:%SZ'))))
	totalTime = secondsElapsed.seconds + secondsElapsed.days * 86400
	if int(change['rcid']) <= config['runtime']['rcid'] or not pageFilter(change['title']) or totalTime <= config['freshnessThreshold']:
		reason = '(Too fresh)'
		if int(change['rcid']) <= config['runtime']['rcid']:
			reason = '(Latest RCID: ' + str(config['runtime']['rcid']) + ')'
		elif not pageFilter(change['title']):
			reason = '(Page filtered)'
		tprint('Skipping', change['rcid'], change['title'], reason)
		if int(change['rcid']) > config['runtime']['rcid']:
			config['runtime']['rcid'] = int(change['rcid'])
		return
	tprint('Patrolling', change['title'])
	config['runtime']['rcid'] = int(change['rcid'])
	fixPage(change['title'], reason=u'Review RC#' + u(change['rcid']))
def loadPage(p):
	p = page(p)
	try:
		code = u(p.getWikiText())
	except:
		error('Couldn\'t grab page', p)
	coderegex = compileRegex(r'^(?: [^\r\n]*(?:[\r\n]+|$))+', re.MULTILINE)
	trimcode = compileRegex(r'^ |</?nowiki>', re.MULTILINE)
	for m in coderegex.finditer(code):
		try:
			exec(trimcode.sub(u'', u(m.group())))
		except:
			error('Error while parsing code: ', m.group())
def patrolChanges():
	try:
		recentChanges = wikitools.api.APIRequest(wiki(), {
			'action':'query',
			'list':'recentchanges',
			'rctoken':'patrol',
			'rclimit':'500'
		}).query(querycontinue=False)[u'query'][u'recentchanges']
		recentChanges.reverse()
	except:
		error('Error while trying to grab recent changes.')
	uniquePages = []
	uniqueChanges = {}
	for change in recentChanges:
		if change['title'] not in uniquePages:
			uniquePages.append(change['title'])
		if change['title'] not in uniqueChanges or uniqueChanges[change['title']]['rcid'] < change['rcid']:
			uniqueChanges[change['title']] = change
			# Move page to end of queue
			uniquePages.remove(change['title'])
			uniquePages.append(change['title'])
	for title in uniquePages:
		change = uniqueChanges[title]
		try:
			patrol(change)
		except KeyboardInterrupt:
			error('Interrupted:', change)
		except:
			warning('Failed to patrol change:', change)
	executeEdits()
	updateRCID()
	tprint('Done patrolling.')
def parsePageRequest(l, links=[]):
	l = u(l)
	content = []
	selfContent = u'* [[:' + l + u']]'
	if l.find(u':'):
		if l[:l.find(u':')].lower() == 'category':
			subpages = wikitools.category.Category(wiki(), l[l.find(u':')+1:]).getAllMembers(titleonly=True)
			for s in subpages:
				if s not in links:
					links.append(s)
					newLink, links = parsePageRequest(s, links=links)
					content.append(newLink)
	if len(content):
		selfContent += u'\r\n' + u'\r\n'.join(content)
	return selfContent, links
def doPageRequests(force=False):
	global config
	tprint('Executing page requests. Force =', force)
	if force:
		requestPageTitle = config['pages']['pagerequestsforce']
	else:
		requestPageTitle = config['pages']['pagerequests']
	requestPage = page(requestPageTitle)
	reqre = compileRegex(r'^\*[\t ]*\[\[:?([^][]+)\]\]', re.MULTILINE)
	originalRequests = u(requestPage.getWikiText())
	requests = originalRequests
	matches = []
	links = []
	for m in reqre.finditer(requests):
		matches.append(m)
		l = u(m.group(1))
		if l not in links:
			links.append(l)
	matches.reverse()
	for m in matches:
		pagelink, links = parsePageRequest(u(m.group(1)), links=links)
		requests = requests[:m.start()] + pagelink + requests[m.end():]
	requests = regSub({r'^[ \t]*(\*[^\r\n]+)[\r\n]+(?=^[ \t]*\*)':'$1\r\n'}, requests)
	reqre2 = compileRegex(r'^\*[\t ]*\[\[:?([^][]+)\]\]\s*', re.MULTILINE)
	matches2 = []
	requestsDone = 0
	tooMany = False
	for m in reqre2.finditer(requests):
		requestsDone += 1
		if requestsDone > config['maxrequests']:
			tooMany = True
			break
		matches2.append(m)
	matches2.reverse()
	tofix = []
	for m in matches2:
		tofix.append(u(m.group(1)))
		requests = requests[:m.start()] + requests[m.end():]
	tofix.reverse()
	for p in tofix:
		fixPage(p, reason=u'Requested on [[:' + u(requestPageTitle) + u']]', force=force)
	executeEdits()
	requests = regSub({r'^[ \t]*(\*[^\r\n]+)[\r\n]+(?=^[ \t]*\*)':'$1\r\n'}, requests)
	if len(tofix) and originalRequests != requests:
		if tooMany:
			editPage(requestPage, requests, summary=u'Processed: [[:' + u']], [[:'.join(tofix) + u']]')
		else:
			editPage(requestPage, requests, summary=u'Finished all requests. Processed: [[:' + u']], [[:'.join(tofix) + u']]')
def parseLocaleFile(content, language='english', languages={}):
	content = u(content)
	language = u(language)
	if content.find('Tokens') != -1:
		content = content[content.find('Tokens')+6:]
	regexSplit = compileRegex('\n(?=\s*")', re.IGNORECASE | re.MULTILINE)
	content = regexSplit.split(content)
	regexLang = compileRegex(r'^"\[([-\w]+)\]([^"\s]+)"\s+"([^"]*)"', re.IGNORECASE | re.MULTILINE)
	regexNoLang = compileRegex(r'^"([^[][^"\s]+)"\s+"([^"]*)"', re.IGNORECASE | re.MULTILINE)
	for l in content:
		l = u(l.strip())
		curlang = None
		key, value = None, None
		langRes = regexLang.search(l)
		if langRes:
			curlang = u(langRes.group(1))
			key, value = langRes.group(2), langRes.group(3)
		else:
			langRes = regexNoLang.search(l)
			if langRes:
				curlang = language
				key, value = langRes.group(1), langRes.group(2)
		if curlang is not None:
			if u(key) not in languages:
				languages[u(key)] = {}
			languages[u(key)][curlang] = u(value)
		else:
			pass
	return languages
def languagesFilter(languages, commonto=None, prefix=None, suffix=None, exceptions=[]):
	filtered = {}
	for k in languages:
		if k in exceptions:
			continue
		if commonto is not None:
			doit = True
			for i in commonto:
				if i not in languages[k]:
					doit = False
					break
			if not doit:
				continue
		if prefix is not None:
			doit = False
			for i in prefix:
				if k.lower()[:len(i)] == i.lower():
					doit = True
					break
			if not doit:
				continue
		if suffix is not None:
			doit = False
			for i in suffix:
				if k.lower()[-len(i):] == i.lower():
					doit = True
					break
			if not doit:
				continue
		filtered[u(k)] = languages[k]
	return filtered
def readLocaleFile(f):
	return u(f.decode('utf16'))
def associateLocaleWordFilters(languages, fromLang, toLang, targetPageLang=None):
	for a in languages:
		f = wordFilter(languages[a][toLang], languages[a][fromLang])
		if targetPageLang is None:
			addSafeFilter(f)
		else:
			addSafeFilter(f, language=targetPageLang)
def getRandBits():
	return random.getrandbits(128)
def getFileHash(filename):
	h = hashlib.md5()
	f = open(filename, 'rb')
	for i in f.readlines():
		h.update(i)
	f.close()
	return u(h.hexdigest())
def deleteFile(*fs):
	for f in fs:
		try:
			os.remove(f)
		except:
			pass
def programExists(programName):
	try:
		result = subprocess.call(['which', programName])
		return result == 0
	except:
		return False
def run():
	global config
	tprint('Bot started.')
	loadPage(config['pages']['filters'])
	for p in sys.argv[1:]:
		tprint('Forced update to', p, '...')
		fixPage(p, force=True)
	executeEdits()
	loadBlacklist()
	patrolChanges()
	updateRCID()
	doPageRequests(force=True)
	doPageRequests(force=False)
	runScheduledTasks()
	executeEdits() # In case scheduled tasks create some edits
	updateEditCount()
	try:
		import rcNotify
		rcNotify.main(once=True)
	except:
		pass
	tprint('All done.')
if __name__ == '__main__':
	run()