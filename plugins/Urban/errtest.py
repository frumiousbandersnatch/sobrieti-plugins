d = {
    u'definition': u'To spew large amounts of a bodily fluid, especially male ejaculate. Could also pertain to female ejaculation.', 
    u'permalink': u'http://raevie.urbanup.com/6744908', 
    'total': 1, 
    u'word': u'raevie', 
    u'author': u'AmbivalentFanatic', 
    u'current_vote': u'', 
    'result_type': u'exact', 
    u'thumbs_up': 1, 
    'number': 1, 
    'pages': 1, 
    'has_related_words': False, 
    u'thumbs_down': 0, 
    u'defid': 6744908, 
    u'example': u'"OMG! Frumious raevied all over his keyboard!"\n\n"Yeah, I raevied in her mouth, but the bitch spit it out."'
    }

for k,v in d.items():
    s = '(%s)' % k
    s = '%' + s
    if isinstance(v,int):
        s += 'd'
    else:
        s += 's'

    print s%d


s = '''
[%(number)d/%(total)d] (+%(thumbs_up)d/-%(thumbs_down)d) "%(word)s" definition: %(definition)s example: %(example)s By %(author)s. %(result_type)s match.'''

print s % d
