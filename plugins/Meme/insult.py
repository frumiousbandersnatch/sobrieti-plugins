#!/usr/bin/env python 
'''
Test insultgenerator.org
'''

from urllib2 import urlopen
import lxml
res = urlopen('http://www.insultgenerator.org')
tree = lxml.html(res)

page = res.read().strip()
