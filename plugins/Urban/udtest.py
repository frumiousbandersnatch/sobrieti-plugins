#!/usr/bin/env python

import urllib, urllib2, json

ud_api_base_url = \
    'http://api.urbandictionary.com/v0/define?'

def udquery(term, page=1):
    url = ud_api_base_url + urllib.urlencode(locals())
    res = urllib2.urlopen(url)
    page = res.read()
    return json.loads(page)
    
# rely on post processing to clean up spacing
default_result_pattern = '''
    [%(number)d/%(total)d] (+%(thumbs_up)d/-%(thumbs_down)d)
    "%(word)s"
    definition: %(definition)s 
    example: %(example)s
    By %(author)s
'''
def format_result(res, number, pat = default_result_pattern):
    defi = dict(res['list'][number-1])
    defi['number'] = number
    defi['total'] = res['total']
    defi['pages'] = res['pages']
    defi['result_type'] = res['result_type']
    defi['has_related_words'] = res['has_related_words']

    return pat % defi


if '__main__' == __name__:
    import sys 
    d = udquery(' '.join(sys.argv[1:]))
    print format_result(d,1)


example = """

'raevie' returns:

{
  "has_related_words": false,
  "list": [
    {
      "definition": "To spew large amounts of a bodily fluid, especially male ejaculate. Could also pertain to female ejaculation.",
      "permalink": "http://raevie.urbanup.com/6744908",
      "word": "raevie",
      "author": "AmbivalentFanatic",
      "current_vote": "",
      "thumbs_up": 1,
      "thumbs_down": 0,
      "defid": 6744908,
      "example": "\"OMG! Frumious raevied all over his keyboard!\"\n\n\"Yeah, I raevied in her mouth, but the bitch spit it out.\""
    }
  ],
  "result_type": "exact", # or "fulltext" or "no_results"
  "sounds": [],
  "total": 1,
  "pages": 1
}


"""
