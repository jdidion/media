#!/usr/bin/env python
# Use imdbapi.org to get official title, year and IMDB ID for a list of movies, 
# output in csv. Default is to output to stdout for direct piping to 
# trakt_import.py. To resolve non-unique matches, the script can be run 
# interactively or it can use some simple logic to pick a single match.
# TODO: There's some problem with puncuation...is this an encoding issue or a
# bug with the API?
# TODO: HTML decode responses

from argparse import ArgumentParser
import codecs
import re
from requests import get
import sys
from time import sleep

URL = "http://imdbapi.org/"
PROMPT = "Select the correct movie, or type a new title and/or year to rerun the search: "

def to_row(r):
    return tuple(r.get(k, "?") for k in (u"title", u"year", u"imdb_id"))

def match_title(title, x, exact=True):
    other = x[u"title"].lower()
    if not exact:
        other = other[0:len(title)]
    if title == other:
        return True
    if u"also_known_as" in x:
        for aka in x[u"also_known_as"]:
            other = aka[u"title"]
            if not exact:
                other = other[0:len(title)]
            if title == other:
                return True
    return False

def match_year(year, x):
    return year and u"year" in x and int(x[u"year"]) == int(year)

def query(title, year=None, matching=False, interactive=False):
    sys.stderr.write("\nQuery: {0}, (year: {1})\n".format(title, year or "?"))
    
    year_order = None
    if year in ("oldest","newest"):
        year_order = year
        year = None
    
    request = get(URL, params=dict(
        title=title, year=year or "", yg=1 if year else 0, type="json", limit=10, mt="M", aka="full"))
    try:
        results = request.json()
    except:
        sys.stderr.write("Error: No valid result for query")
        return None
            
    if isinstance(results, dict):
        sys.stderr.write(
            "Error {0}: {1}\n".format(results[u"code"], results[u"error"]))
        return None
    
    if len(results) == 1:
        match = to_row(results[0])
        sys.stderr.write("Single match: {0}\n".format(match))
        return match
    else:
        match_limit = len(results) >= 10
        sys.stderr.write("{0} matches\n".format("10+" if match_limit else len(results)))
        
        if matching:
            exact_results = filter(lambda x: match_title(title, x, True), results)
            if (len(exact_results) == 1 and (
                    not match_limit or 
                    matching == "fuzzy" or 
                    match_year(year, results[0]))):
                match = to_row(exact_results[0])
                sys.stderr.write("Single exact match: {0}\n".format(match))
                return match
            elif len(exact_results) > 1 and matching == "fuzzy" and year_order:
                exact_results = sorted(exact_results,
                    key=lambda x: x.get(u"year", None), reverse=year_order=="newest")
                match = to_row(exact_results[0])
                sys.stderr.write("Selected {0} of multiple exact matches: {1}\n".format(
                    year_order, match))
                return match
                
            if matching == "fuzzy" and year:
                fuzzy_results = filter(
                    lambda x: match_title(title, x, False) and match_year(year, x), 
                    results)
                if len(results) == 1:
                    match = to_row(fuzzy_results[0])
                    sys.stderr.write("Single fuzzy match: {0}\n".format(match))
                    return match
    
    for i,match in enumerate(results, 1):
        sys.stderr.write("{0}) {1}\n".format(i, to_row(match)))
    
    if interactive is True:
        sys.stderr.write(PROMPT)
        choice = sys.stdin.readline().strip().lower()
        
        if choice:
            if len(choice) == 1:
                return to_row(results[int(choice)-1])
            else:
                new_query = tuple(s.strip() for s in choice.split(","))
                if len(new_query) == 1:
                    try:
                        year = int(new_query[0])
                    except:
                        title = new_query[0]
                else:
                    title, year = new_query
                return query(title, year, matching, interactive)
        else:
            return None

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-i", "--interactive", action="store_true", default=False,
        help="If a query has multiple results, ask the user to select the corret one.")
    parser.add_argument("-m", "--matching", choices=("exact","fuzzy"), default=None,
        help="Use matching rules if a query has multiple results.")
    parser.add_argument("-o", "--output_file", default="-")
    parser.add_argument("-u", "--unmatched_file", default=None)
    parser.add_argument("-w", "--wait_time", type=int, default=2,
        help="Seconds to wait between queries (must be >= 1).")
    parser.add_argument("-y", "--default_year", default=None,
        help="If not run interactively, the script will use this as the default "\
            "year to resolve queries with multiple results. Also accepts "\
            "'newest' (to always pick the most recent movie) or 'oldest'.")
    parser.add_argument("movie_file")
    args = parser.parse_args()
    
    out = sys.stdout if args.output_file == "-" else codecs.open(args.output_file, "w", "utf-8")
    unmatched = codecs.open(args.unmatched_file, "w", "utf-8") if args.unmatched_file else None
    with open(args.movie_file, "rU") as movies, out:
        for m in movies:
            q = tuple(s.strip() for s in m.split("\t"))
            title = q[0].lower()
            year = q[1] if len(q) > 1 else args.default_year
            result = query(title, year, args.matching, args.interactive)
            if result:
                out.write("\t".join(unicode(x) for x in result))
                out.write("\n")
            elif unmatched:
                unmatched.write(m)
            # wait
            sleep(max(args.wait_time, 1))
    
    if unmatched:
        unmatched.close()
