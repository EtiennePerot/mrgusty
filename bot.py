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
import re
import urllib2
import random
import subprocess
import wikitools

from botConfig import config
config['runtime'] = {
	'rcid': -1,
	'onlinercid': -1,
	'wiki': None,
	'edits': 0,
	'patrolled': [],
	'regexes': {}
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
class curry:
	def __init__(self, func, *args, **kwargs):
		self.func = func
		self.pending = args[:]
		self.kwargs = kwargs
	def __str__(self):
		return u'<DamnCurry of ' + u(self.func) + u'; args = ' + u(self.pending) + u'; kwargs = ' + u(self.kwargs) + u'>'
	def __repr__(self):
		return self.__str__()
	def __call__(self, *args, **kwargs):
		if kwargs and self.kwargs:
			kw = self.kwargs.copy()
			kw.update(kwargs)
		else:
			kw = kwargs or self.kwargs
		return self.func(*(self.pending + args), **kw)

def wiki():
	global config
	if config['runtime']['wiki'] is None:
		config['runtime']['wiki'] = wikitools.wiki.Wiki(config['api'])
		print 'Logging in as', config['username'], '...'
		config['runtime']['wiki'].login(config['username'], config['password'])
		try:
			config['runtime']['onlinercid'] = int(u(wikitools.page.Page(wiki(), config['pages']['rcid']).getWikiText()).strip())
			config['runtime']['rcid'] = config['runtime']['onlinercid']
		except:
			error('Couldn\'t read RCID.')
		print 'Logged in.'
	return config['runtime']['wiki']
def page(p):
	if type(p) in (type(''), type(u'')):
		p = wikitools.page.Page(wiki(), u(p))
	return p
def editPage(p, content, summary=u'', minor=True, bot=True, nocreate=True):
	global config
	summary = u(summary)
	while len(summary) > 250:
		if summary.find(u' ') == -1:
			summary = summary[:summary.rfind(u' ')] + u'...'
		else:
			summary = summary[:247] + u'...'
	result = page(p).edit(u(content), summary=summary, minor=minor, bot=bot, nocreate=nocreate)
	try:
		if result['edit']['result']:
			config['runtime']['edits'] += 1
	except:
		warning('Couldn\'t edit', p)
	return result
def updateRCID():
	if abs(config['runtime']['rcid'] - config['runtime']['onlinercid']) >= config['rcidrate']:
		print 'Updating last RCID...'
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

def compileRegex(regex, flags=re.IGNORECASE):
	global config
	regex = u(regex)
	if regex in config['runtime']['regexes']:
		return config['runtime']['regexes'][regex]
	config['runtime']['regexes'][regex] = re.compile(regex, flags)
	return config['runtime']['regexes'][regex]

def warning(*info):
	s = []
	print info
	import traceback
	traceback.print_exc()
def error(*info):
	warning(*info)
	sys.exit(1)

class link:
	def __init__(self, content):
		content = u(content)
		self.joined = False
		self.setBody(content)
		self.setType(u'unknown')
		self.setLabel(None)
		self.setLink(u'')
		self.joined = False
		if len(content) > 2:
			if content[:2] == u'[[' and content[-2:] == u']]':
				split = content[2:-2].split(u'|')
				if len(split) in (1, 2):
					self.setType(u'internal')
					lnk = split[0]
					if lnk.find(u':') == -1:
						lnk = lnk.replace(u'_', u' ')
					self.setLink(lnk)
					if len(split) == 2:
						self.setLabel(split[1])
					else:
						self.setLabel(split[0])
						self.joined = True
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
	def getLink(self):
		return u(self.link)
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
		self.link = u(link)
		if self.joined:
			self.label = u(link)
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
		tmpLink = self.getLink()
		if self.getType() == u'internal':
			tmpLink2 = tmpLink.replace(u'_', u' ')
			if label in (tmpLink2, tmpLink):
				return u'[[' + label + u']]'
			elif label and tmpLink and (label[0].lower() == tmpLink[0].lower() and tmpLink[1:] == label[1:]) or (label[0].lower() == tmpLink2[0].lower() and tmpLink2[1:] == label[1:]):
				return u'[[' + label + u']]'
			elif tmpLink and label and len(label) > len(tmpLink) and (label.lower().find(tmpLink2.lower()) != -1 or label.lower().find(tmpLink.lower()) != -1):
				index = max(label.lower().find(tmpLink2.lower()), label.lower().find(tmpLink.lower()))
				badchars = (u' ', u'_')
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
def linkExtract(content):
	links1 = compileRegex(r'\[\[([^\[\]]+)\]\]')
	links2 = compileRegex(r'\[([^\[\]]+)\](?!\])')
	linkcount = 0
	linklist = []
	res = links1.search(content)
	while res:
		linklist.append(link(res.group()))
		content = content[:res.start()] + u'~!~!~!~OMGLINK-' + u(linkcount) + u'~!~!~!~' + content[res.end():]
		linkcount += 1
		res = links1.search(content)
	res = links2.search(content)
	while res:
		linklist.append(link(res.group()))
		content = content[:res.start()] + u'~!~!~!~OMGLINK-' + u(linkcount) + u'~!~!~!~' + content[res.end():]
		linkcount += 1
		res = links2.search(content)
	return content, linklist
def linkRestore(content, linklist=[]):
	linkcount = len(linklist)
	i = 0
	linklist.reverse()
	for l in linklist:
		i += 1
		content = content.replace(u'~!~!~!~OMGLINK-' + u(linkcount - i) + u'~!~!~!~', u(l))
	return content
def safeContent(content):
	content, linklist = linkExtract(content)
	safelist = []
	templates = compileRegex(r'\{\{(?:(?!\{\{|\}\})[\s\S])+\}\}')
	templatecount = 0
	res = templates.search(content)
	while res:
		safelist.append(('~!~!~!~OMGTEMPLATE-' + u(templatecount) + u'~!~!~!~', u(res.group())))
		content = content[:res.start()] + u'~!~!~!~OMGTEMPLATE-' + u(templatecount) + u'~!~!~!~' + content[res.end():]
		templatecount += 1
		res = templates.search(content)
	tags = compileRegex(r'<(?:ref|gallery|pre|code)[^<>]*>[\S\s]*?</(?:ref|gallery|pre|code)>|^  [^\r\n]*', re.IGNORECASE | re.MULTILINE)
	tagcount = 0
	res = tags.search(content)
	while res:
		safelist.append(('~!~!~!~OMGTAG-' + u(tagcount) + u'~!~!~!~', u(res.group())))
		content = content[:res.start()] + u'~!~!~!~OMGTAG-' + u(tagcount) + u'~!~!~!~' + content[res.end():]
		tagcount += 1
		res = tags.search(content)
	return content, linklist, safelist
def safeContentRestore(content, linklist=[], safelist=[]):
	safelist.reverse()
	for s in safelist:
		content = content.replace(s[0], s[1])
	content = linkRestore(content, linklist)
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
def sFilter(filters, content, **kwargs):
	content = u(content)
	lenfilters = len(filters)
	if not lenfilters:
		return content
	oldcontent = content
	filtercount = 0
	for f in filters:
		filtercount += 1
		#print 'Filter', f, '(', filtercount, '/', lenfilters, ')'
		loopTimes = 0
		while not loopTimes or oldcontent != content:
			loopTimes += 1
			if loopTimes >= 1024:
				print 'Warning: More than 1024 loops with filter', f
				break
			oldcontent = content
			content = u(f(content, **kwargs))
	return content
def linkFilter(filters, linklist, **kwargs):
	for f in filters:
		for i in range(len(linklist)):
			linklist[i] = f(linklist[i], **kwargs)
	return linklist
def linkTextFilter(filters, linklist, linksafe=False):
	for i in range(len(linklist)):
		l = linklist[i]
		if l.getType() == u'internal' and l.getLink().find(u':') == -1 and pageFilter(l.getLink()):
			if linksafe:
				l.setLink(sFilter(filters, l.getLink()))
			if l.getLabel().find(u':') == -1:
				l.setLabel(sFilter(filters, l.getLabel()))
		linklist[i] = l
	return linklist

def regexes(rs):
	return curry(regSub, rs)
def regex(reg, replace):
	return regexes({reg: replace})
def dumbReplaces(rs):
	return curry(dumbReplacement, rs)
def dumbReplace(subject, replacement):
	return curry({subject: replacement})
def wordRegex(word):
	word = u(re.sub(r' +', r'[-_ ]', u(word)))
	return u(r"(?<![\u00E8-\u00F8\xe8-\xf8\w])(?<!'')(?<!" + r'"' + r")(?:\b|^)" + word + r"(?:\b(?![\u00E8-\u00F8\xe8-\xf8\w])(?!''|" + r'"' + r")|$)")
def wordFilter(correct, *badwords, **kwargs):
	correct = u(correct)
	rs = {}
	badwords2 = []
	for i in badwords:
		badwords2.append(u(i))
	if not len(badwords2):
		badwords2.append(correct)
	for w in badwords2:
		rs[wordRegex(w)] = correct
	return regexes(rs)
def enforceCapitalization(*words, **kwargs):
	for w in words:
		addSafeFilter(wordFilter(u(w), **kwargs))

pageFilters = []
categoryFilters = []
def pageFilter(page):
	global pageFilters
	if type(page) in (type(()), type([])):
		pages = []
		for p in page:
			if pageFilter(p):
				pages.append(p)
		return pages
	if type(page) not in (type(u''), type('')):
		page = page.title
	page = u(page)
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
		pageFilters.append(compileRegex(u(f), re.IGNORECASE))
def addBlacklistPage(*pages):
	for p in pages:
		addPageFilter(re.escape(u(p)))
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

filters = []
safeFilters = []
linkFilters = []
def addFilter(*fs):
	global filters
	for f in fs:
		filters.append(f)
def addSafeFilter(*fs):
	global safeFilters
	for f in fs:
		safeFilters.append(f)
def addLinkFilter(*fs):
	global linkFilters
	for f in fs:
		linkFilters.append(f)
def fixContent(content, article=None):
	global filters, safeFilters, linkFilters
	content = u(content)
	oldcontent = u''
	loopTimes = 0
	while not loopTimes or content != oldcontent:
		loopTimes += 1
		if loopTimes > 2:
			print 'Pass', loopTimes, 'on', article
		if loopTimes >= 1024:
			print 'Warning: More than 1024 fix passes on article', article
			break
		oldcontent = content
		# Apply unsafe filters
		content = sFilter(filters, content, article=article)
		# Apply safe filters
		if len(safeFilters):
			content, linklist, safelist = safeContent(content)
			linklist = linkTextFilter(safeFilters, linklist)
			content = sFilter(safeFilters, content, article=article)
			content = safeContentRestore(content, linklist, safelist)
		if len(linkFilters):
			content, linklist = linkExtract(content)
			linklist = linkFilter(linkFilters, linklist)
			content = linkRestore(content, linklist)
	return content
def fixPage(article, **kwargs):
	article = page(article)
	force = False
	if 'force' in kwargs and kwargs['force']:
		force = True
	try:
		catFilter = categoryFilter(article)
	except wikitools.page.NoPage:
		print 'No such page:', article
		return False
	except:
		catFilter = True
	if not force and (not pageFilter(article) or not catFilter):
		print 'Skipping:', article
		return
	originalContent = u(article.getWikiText())
	content = fixContent(originalContent, article=article)
	if content != originalContent:
		print article, 'needs to be updated.'
		summary = u'Applied filters to [[:' + u(article.title) + u']]'
		if 'reason' in kwargs:
			summary += u' (' + u(kwargs['reason']) + u')'
		editPage(article, content, summary=summary)
		return True
	print article, 'is up-to-date.'
	return False
def patrol(change):
	global config
	if int(change['rcid']) <= config['runtime']['rcid'] or not pageFilter(change['title']) or change['title'] in config['runtime']['patrolled']:
		print 'Skipping', change['rcid'], change['title']
		if int(change['rcid']) > config['runtime']['rcid']:
			config['runtime']['rcid'] = int(change['rcid'])
		return
	print 'Patrolling', change['title']
	config['runtime']['rcid'] = int(change['rcid'])
	result = fixPage(change['title'], reason=u'Review RC#' + u(change['rcid']))
	config['runtime']['patrolled'].append(change['title'])
	updateRCID()
def loadPage(p):
	p = page(p)
	try:
		code = u(p.getWikiText())
	except:
		error('Couldn\'t grab page', p)
	coderegex = compileRegex(r'^(?:  [^\r\n]*(?:[\r\n]+|$))+', re.MULTILINE)
	trimcode = compileRegex(r'^  ', re.MULTILINE)
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
	for change in recentChanges:
		try:
			patrol(change)
		except KeyboardInterrupt:
			error('Interrupted:', change)
		except:
			warning('Failed to patrol change:', change)
	print 'Done patrolling.'
def parsePageRequest(l, links=[]):
	l = u(l)
	content = []
	selfContent = u'* [[:' + l + u']]'
	if l.find(u':'):
		if l[:l.find(u':')].lower() == 'category':
			subpages = wikitools.category.Category(wiki(), l[l.find(u':')+1:]).getAllMembers(titleonly=True)
			if len(subpages):
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
	print 'Executing page requests. Force =', force
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
	requests = regSub({r'^[ \t]*(\*[^\r\n]+)[\r\n]+(?=^[ \t]*\*)':'$1\r\n'}, requests)
	if len(tofix) and originalRequests != requests:
		if tooMany:
			editPage(requestPage, requests, summary=u'Processed: [[:' + u']], [[:'.join(tofix) + u']]')
		else:
			editPage(requestPage, requests, summary=u'Finished all requests. Processed: [[:' + u']], [[:'.join(tofix) + u']]')
def run():
	global config
	print 'Bot started.'
	loadPage(config['pages']['filters'])
	loadBlacklist()
	patrolChanges()
	updateRCID()
	doPageRequests(force=True)
	doPageRequests(force=False)
	updateEditCount()
	try:
		subprocess.Popen(['killall', 'cpulimit']).communicate()
	except:
		pass
	print 'All done.'
run()