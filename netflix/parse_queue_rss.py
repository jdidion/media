#!/usr/bin/env python

import re
import sys
from feedparser import parse

assert len(sys.argv) == 3

exp = re.compile('^(\d+)- (.*)')

with open(sys.argv[2], 'w') as o:
    for i in parse(sys.argv[1]).entries:
        pos, title = exp.match(i['title']).groups()
        o.write(title.encode('utf-8'))
        o.write("\n")
