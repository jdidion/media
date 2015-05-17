#!/usr/bin/env python
# Scrape all images from a webcomic and create a .cbz file for viewing in a
# comic reader.

import argparse
from datetime import date, datetime, timedelta
import itertools
import logging
import math
import os
import shutil
import tempfile
import time
import urllib
import zipfile

def dateiter(start, end, schedule=None):
    cur = start
    if schedule is None:
        steps = (1,)
    elif len(schedule) == 1:
        steps = (7,)
    else:
        steps = [schedule[i] - schedule[i-1] for i in xrange(1, len(schedule))]
        steps.append(7 - schedule[-1] + schedule[0])
    c = itertools.cycle(steps)
    
    while cur <= end:
        yield cur
        cur += timedelta(days=c.next())

def on_or_after(d, schedule):
    day = d.weekday()
    for i in schedule:
        if day <= schedule[i]:
            if day < schedule[i]:
                d += timedelta(days=schedule[i] - day)
            break
    else:
        d += (7 % day) + schedule[0]
    return d

def on_or_before(d, schedule):
    day = d.weekday()
    for i in schedule:
        if day >= schedule[i]:
            if day > schedule[i]:
                d -= timedelta(days=day - schedule[i])
            break
    else:
        d -= day - 7 + schedule[-1]
    return d

def scrape_schedule(url_fmt, start, schedule, outdir, end=date.today(), wait=10):
    # advance to the first scheduled day after the start date
    start = on_or_after(start, schedule)
    end = on_or_before(end, schedule)
    
    # calculate max number of images and the number of digits we should use
    # to number images
    max_imgs = math.ceil((end - start + timedelta(days=1)).days / 7) * len(schedule)
    digits = int(math.ceil(math.log10(max_imgs)))
    
    # create the format for the output file
    ext = url_fmt[(url_fmt.rfind(".")+1):]
    outfile_fmt = "img{{0:0>{0}d}}.{1}".format(digits, ext)
    logging.debug("Downloading all comics between {0} and {1}".format(start, end))
    
    outfiles = []
    for i,d in enumerate(dateiter(start, end, schedule)):
        url = url_fmt.format(d)
        
        outfile = os.path.join(outdir, outfile_fmt.format(i))
        logging.debug("Downloading {0} to {1}".format(url, outfile))
        
        try:
            urllib.urlretrieve(url, outfile)
            outfiles.append(outfile) 
        except:
            logging.debug("No image for {0}".format(d))
        
        if wait:
            time.sleep(wait)
        
    return outfiles

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--start_date", default=str(date.today() - timedelta(days=365)),
        help="First date to grab. Defaults to one year ago.")
    parser.add_argument("-u", "--update_schedule", default=None,
        help="Comma-separated list of days of the week on which the comic is "\
             "updated. Monday = 0, Sunday = 6.")
    parser.add_argument("-w", "--wait", type=int, metavar="SEC", default=10,
        help="Seconds to wait in between requests.")
    parser.add_argument("--log_level", default="INFO")
    parser.add_argument("url")
    parser.add_argument("outfile")
    args = parser.parse_args()
    
    log_level = logging._levelNames[args.log_level]
    logging.basicConfig(level=log_level)
    
    try:
        outdir = tempfile.mkdtemp()
    
        if args.update_schedule:
            start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
            schedule = sorted(map(int, args.update_schedule.split(",")))
            img_files = scrape_schedule(args.url, start, schedule, outdir, wait=args.wait)
        else:
            sys.exit("Nothing to do")

        # create archive from temp dir
        with zipfile.ZipFile(args.outfile, "w") as cbz:
            for i in img_files:
                cbz.write(i, os.path.basename(i))
                
    finally:
        shutil.rmtree(outdir)

if __name__ == "__main__":
    main()