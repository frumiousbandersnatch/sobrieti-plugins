import cgi
import re
def wash_quote(line, newline='|'):
    '''
    Return \n-separted string suitable for adding to qdb.

    It tries to find breaks based on "|" characters and "<nick>" markup.
    '''
    out = []
    for word in line.split():
        word = word.strip()

        if word == newline:
            out.append('\n')
            continue

        if re.search(r'<\w+>', word):
            out.append('\n')
        out.append(word)
        continue
    return cgi.escape(' '.join(out))

