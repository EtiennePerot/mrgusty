# -*- coding: utf-8 -*-
# A hacky script that allows file upload to MediaWiki without the API.
# It was necessary prior to MediaWiki 1.16 as there was no API call to upload a file.

import urllib, urllib2, re, cookielib
import wikitools
from MultipartPostHandler import MultipartPostHandler

class wikiUploader:
	def __init__(self, username, password, url):
		self.referral = None
		self.cookiejar = cookielib.LWPCookieJar()
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar), MultipartPostHandler)
		self.username = username
		self.password = password
		self.url = url.replace(u'api.php', u'')
		self.wiki = wikitools.wiki.Wiki(self.url + 'api.php')
		if True:
			login1 = self.buildGrab('Special:UserLogin')
			match = re.search("""<input[^<>]*name=['"]?wpLoginToken['"]?[^<>]*value=['"]?([^"]+)['"]?""", login1, re.IGNORECASE)
			if not match:
				raise Exception()
			self.token = urllib.unquote(match.group(1))
			login2 = self.buildGrab('Special:UserLogin', action='submitlogin', type='login', data={
				'wpName': self.username,
				'wpPassword': self.password,
				'wpLoginattempt': 'Log in',
				'wpRemember': '1',
				'wpLoginToken': self.token
			})
			if login2.find('id="pt-userpage"') == -1:
				raise Exception()
		else:
			raise Exception('Could not log in with username ' + self.username)
	def buildURL(self, title, **params):
		params['title'] = title
		return self.url + '?' + urllib.urlencode(params)
	def urlGet(self, url, data=None, referral=None):
		print 'Opening', url, 'with data', data
		req = urllib2.Request(url)
		if referral is not None:
			req.add_header('Referral', referral)
		elif self.referral is not None:
			req.add_header('Referral', self.referral)
		self.referral = url
		if data is None:
			return self.opener.open(req).read(-1)
		return self.opener.open(req, data).read(-1)
	def buildGrab(self, title, data=None, referral=None, **params):
		return self.urlGet(self.buildURL(title, **params), data=data, referral=referral)
	def exists(self, destfile):
		try:
			wikitools.page.Page(self.wiki, u'File:' + destfile).getWikiText()
			return True
		except:
			return False
	def upload(self, filename, destfile, pagecontent='', license='', overwrite=False, reupload=False):
		if type(filename) is type(u''):
			filename = filename.encode('utf8')
		if type(destfile) is type(u''):
			destfile = destfile.encode('utf8')
		if type(pagecontent) is type(u''):
			pagecontent = pagecontent.encode('utf8')
		if type(license) is type(u''):
			license = license.encode('utf8')
		destfile = (destfile[0].upper() + destfile[1:]).replace(' ', '_').replace('File:', '')
		if not overwrite and self.exists(destfile):
			print 'Skipping', destfile,'- File already exists.'
			return
		fHandle = open(filename, 'rb')
		if reupload:
			data = {
				'wpUploadFile': fHandle,
				'wpSourceType': 'file',
				'wpDestFile': destfile,
				'wpUploadDescription': pagecontent,
				'wpLicense': license,
				'wpUpload': 'Upload file',
				'wpDestFileWarningAck': '',
				'wpForReUpload': '1',
				'wpIgnoreWarning': 'true'
			}
		else:
			data = {
				'wpUploadFile': fHandle,
				'wpSourceType': 'file',
				'wpDestFile': destfile,
				'wpUploadDescription': pagecontent,
				'wpLicense': license,
				'wpUpload': 'Upload file',
				'wpDestFileWarningAck': '',
				'wpForReUpload': '',
				'wpIgnoreWarning': 'true'
			}
		result = self.buildGrab('Special:Upload', data=data, referral=self.buildURL('Special:Upload'))
		try:
			fHandle.close()
		except:
			pass
		return result
