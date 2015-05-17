#!/usr/bin/env python
from argparse import ArgumentParser
import codecs
import csv
import hashlib
import json
from requests import post

URL = "http://api.trakt.tv/movie/watchlist/{0}"

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-k", "--api_key")
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("-m", "--movie_file", default="-",
        help="Tab-delimited file with three columns: title, year, IMDB ID.")
    parser.add_argument("-s", "--skipped_file", default=None)
    args = parser.parse_args()
    
    def make_movie(row):
        title, year, imdb_id = row.strip().split("\t")
        return dict(type="movie", title=title, year=year, imdb_id=imdb_id)

    movies = sys.stdin if args.movie_file == "-" else codecs.open(args.movie_file, "rU", "utf_8")
    with movies:
        data = dict(
            username=args.username,
            password=hashlib.sha1(args.password).hexdigest(),
            movies=[make_movie(row) for row in movies])

    print "Making request to add {0} movies".format(len(data["movies"]))
    request = post(URL.format(args.api_key), data=json.dumps(data))

    print "Response: " + str(request.status_code)
    response = request.json()
    
    if request.status_code == 200:
        print "Added: {0}".format(response.get(u'inserted', 0))
        print "Already in your list: {0}".format(response.get(u'already_exist', 0))
        print "Skipped: {0}".format(response.get(u'skipped', 0))
    else:
        print "Error: {0}".format(response.text)
    
    if args.skipped_file and response.get(u'skipped', 0) > 0:
        with codecs.open(args.skipped_file, "w", "utf_8") as out:
            for movie in response[u'skipped_movies']:
                row = (movie[k] for k in (u'title', u'year', u'imdb_id'))
                out.write("\t".join(unicode(x) for x in row))
                out.write("\n")
    