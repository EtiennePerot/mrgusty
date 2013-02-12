# -*- coding: utf-8 -*-

config = {
	'api': 'http://wiki.teamfortress.com/w/api.php', # Wiki API URL
	'steamAPI': '4D05B3AEB8DBC59F0CB06E15F5C4D52A', # Steam API key (Optional, put gibberish if you don't need that)
	'username': 'MrGusty', # Username
	'password': 'My Little Password', # Password
	'maxrequests': 16, # Max PageRequests to process per run
	'rcidrate': 50, # Edit RCID every n edits
	'freshnessThreshold': 300, # Pages must not have been edited in the last freshnessThreshold for them to be considered by the bot
	'pagePasses': 8, # Maximum number of parsing/filtering passes
	'filterPasses': 64, # Maximum number of times to run a fitler on a filtering pass
	'tempPrefix': 'MrGusty', # Prefix for temporary filenames
	'concurrency': True, # Enable concurrency
	'maxConcurrency': 8, # Max number of requests going on concurrently
	'editWaitTime': (0.1, 0.5), # Before every edit, wait a random number of seconds between the two provided numbers. Set to None or remove the line to ignore.
	'pages': {
		'filters': 'User:MrGusty/Filters', # Filters page
		'blacklist': 'User:MrGusty/Blacklist', # Blacklist
		'pagerequests': 'User:MrGusty/PageRequests', # PageRequests
		'pagerequestsforce': 'User:MrGusty/PageRequestsForce', # PageRequests bypassing blacklist
		'rcid': 'User:MrGusty/RCID', # RCID page
		'editcount': 'User:MrGusty/EditCount' # Edit count page
	}
}
