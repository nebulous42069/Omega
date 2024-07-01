# -*- coding: utf-8 -*-

# Author/Copyright: fr33p0rt
# License: GPLv3 https://www.gnu.org/copyleft/gpl.html

import requests
import sys

url = sys.argv[1]
dest_file = sys.argv[2]

r = requests.get(URL)
with open(dest_file, "wb") as code:
    code.write(r.content)
print "Download Complete!"


