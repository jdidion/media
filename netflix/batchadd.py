# Sample code to use the Netflix python client

from Netflix import *
import getopt
import time
import httplib
import re

APP_NAME   = 'NetflixBackupRestore'
API_KEY    = 'TODO: pass on command line'
API_SECRET = 'TODO: pass on command line'
CALLBACK   = ''

USER = {
    'request': {
        'key': 'TODO: pass on command line',
        'secret': 'TODO: pass on command line'
    },
    'access': {
        'key': 'TODO: pass on command line',
        'secret': 'TODO: pass on command line'
    }
}

def getAuth(netflix, verbose):
    netflix.user = NetflixUser(USER,netflix)
    
    if USER['request']['key'] and not USER['access']['key']:
      tok = netflix.user.getAccessToken( USER['request'] )
      print "now put this key / secret in USER.access so you don't have to re-authorize again:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
      USER['access']['key'] = tok.key
      USER['access']['secret'] = tok.secret
      sys.exit(1)

    elif not USER['access']['key']:
      (tok, url) = netflix.user.getRequestToken()
      print "Authorize user access here: %s" % url
      print "and then put this key / secret in USER.request:\n 'key': '%s',\n 'secret': '%s'\n" % (tok.key, tok.secret)
      print "and run again."
      sys.exit(1)
    return netflix.user

def getUserInfo(netflix,user):
    print "*** Who is this person? ***"
    userData = user.getData()
    print "%s %s" % (userData['first_name'], userData['last_name'])
    
    ######################################
    # User subinfo is accessed similarly
    # to disc subinfo.  Find the field
    # describing the thing you want, then
    # retrieve that url and get that info
    ######################################
    print "*** What are their feeds? ***"
    feeds = user.getInfo('feeds')
    print simplejson.dumps(feeds,indent=4)

    print "*** Do they have anything at home? ***"
    feeds = user.getInfo('at home')
    print simplejson.dumps(feeds,indent=4)

    print "*** Show me their recommendations ***"
    recommendations = user.getInfo('recommendations')
    print simplejson.dumps(recommendations,indent=4)

    ######################################
    # Rental History
    ######################################
    # Simple rental history
    history = netflix.user.getRentalHistory()
    print simplejson.dumps(history,indent=4)

    # A little more complicated, let's use mintime to get recent shipments
    history = netflix.user.getRentalHistory('shipped',updatedMin=1219775019,maxResults=4)
    print simplejson.dumps(history,indent=4)

def userQueue(netflix,user):
    ######################################
    # Here's a queue.  Let's play with it
    ######################################
    queue = NetflixUserQueue(netflix.user)
    print "*** Add a movie to the queue ***"
    print simplejson.dumps(queue.getContents(), indent=4)
    print queue.addTitle( urls=["http://api.netflix.com/catalog/titles/movies/60002013"] )
    print "*** Move it to the top! ***"
    print queue.addTitle( urls=["http://api.netflix.com/catalog/titles/movies/60002013"], position=1 )
    print "*** Take it out ***"
    print queue.removeTitle( id="60002013")
    
    discAvailable = queue.getAvailable('disc')
    print  "discAvailable" + simplejson.dumps(discAvailable)
    instantAvailable =  queue.getAvailable('instant')
    print "instantAvailable" + simplejson.dumps(instantAvailable)
    discSaved =  queue.getSaved('disc')
    print "discSaved" + simplejson.dumps(discSaved)
    instantSaved = queue.getSaved('instant')
    print "instantSaved" + simplejson.dumps(instantSaved)
    
# One required argument: file name. One of three options is required:
# -b backup queue to a file
# -r restore queue from a file
# -t batch add titles from a file with one title per line (default)
#
# Optional arguments:
# -v verbose
# -n number of titles to include in search results
# 
if __name__ == '__main__':  
    try:
        opts, args = getopt.getopt(sys.argv[1:], "abn:rtv:")
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        sys.exit(2)
    
    always_commit = False
    mode = "-t"
    num_titles = 25
    verbose = 0
    for o, a in opts:
        if o == "-a":
            always_commit = True
        if o == "-n":
            num_titles = int(a)
        elif o == "-v":
            verbose = int(a)
        else:
            mode = o
            
    if len(args) == 0:
        print "File name required"
        sys.exit(2)
        
    netflixClient = NetflixClient(APP_NAME, API_KEY, API_SECRET, CALLBACK, verbose > 1)
    user = getAuth(netflixClient, verbose > 1)

    if mode == "-b":
        # TODO
        print "Backup not yet implemented"
        sys.exit(2)
    else:
        discs = []
        commit_all = True
        
        for line in open(args[0], 'r').readlines():
            line = line.strip()
            if verbose:
                print "\n" + line
            
            commit_disc = False
            
            try:
                title_discs = netflixClient.catalog.searchTitles(line, 0, num_titles)
            except httplib.BadStatusLine, e:
                print "Unexpected error: ", e
                print e.args
                raise
            
            if len(title_discs) == 0:
                print "No discs for title " + line
            elif len(title_discs) == 1:
                disc = title_discs[0]
                if verbose:
                    print "Exact match: " + disc['title']['regular']
                discs.append(disc)
                commit_disc = True
            else:
                if verbose:
                    print "Multiple discs for title"
                
                candidates = []
                for disc in title_discs:
                    title = disc['title']['regular'].strip()
                    if title.lower() == line.lower():
                        if verbose:
                            print "Exact match: " + title
                        candidates.append(disc)
                
                if len(candidates) == 0:
                    print "No exact matches for [" + line + "]; all results:"
                    for disc in title_discs:
                        print disc['title']['regular']
                elif len(candidates) == 1:
                    discs.append(candidates[0])
                    commit_disc = True
                else:
                    # TODO: show matches and let user pick
                    print "Multiple exact matches for[" + line + "]"
            
            if not commit_disc and not always_commit:
                commit_all = False 
                
            time.sleep(1)
            
        if mode == "-r":
            # TODO: wipe queue
            print "Restore not yet implemented"
            
        if not commit_all:
            print "No exact match for one or more discs; not adding titles to queue"
            sys.exit(2)
        elif verbose:
            print "Adding " + str(len(discs)) + " to queue"
            
        queue = NetflixUserQueue(netflixClient.user)    
        time.sleep(1)
        
        msg_re = re.compile("<message>(.+?)</message>", re.S | re.I | re.M)
        status_re = re.compile("<status_code>(.+?)</status_code>", re.S | re.I | re.M)

        for disc in discs:
            result = queue.addTitle(urls = [disc['id']])
            time.sleep(1)
            
            if verbose > 1:
                print "Result: " + result
            
            msg_match = msg_re.search(result)
            status_match = status_re.search(result)
            
            if not msg_match or not status_match:
                print "Invalid result for disc " + disc['title']['regular'] + ": " + result
            else:
                msg = msg_match.group(1)
                rc = status_match.group(1)
            
                if "success" == msg.lower().strip() and int(rc) == 201:
                    if verbose > 1:
                        print "Success!"
                else:
                    print "Failure for disc " + disc['title']['regular'] + ": " + msg + " " + rc