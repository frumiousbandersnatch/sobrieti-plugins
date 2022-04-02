#!/usr/bin/env python3
'''
Render a "comic" from attributed lines of text.
'''
# This is adapted from what began as nekosune's WeedBot comic.py

import os
from random import shuffle
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def wrap(st, font, draw, width):
    '''
    Do line wrapping of text in st rendered with font to fit width
    using draw engine.

    Return a tuple of (lines, bounds) where lines hold an array of
    string, each string fitting in width and bounds provides a tuple
    (width,height) bounding the text.
    '''
    st = st.split()
    mw = 0
    mh = 0
    ret = []

    while len(st) > 0:
        s = 1
        while True and s < len(st):
            w, h = draw.textsize(" ".join(st[:s]), font=font)
            if w > width:
                s -= 1
                break
            else:
                s += 1

        if s == 0 and len(st) > 0:  # we've hit a case where the current line is wider than the screen
            s = 1

        w, h = draw.textsize(" ".join(st[:s]), font=font)
        mw = max(mw, w)
        mh += h
        ret.append(" ".join(st[:s]))
        st = st[s:]

    return ret, (mw, mh)


def rendertext(st, font, draw, pos):
    '''
    Render lines of st text in font at pos using draw.
    '''
    ch = pos[1]
    for s in st:
        w, h = draw.textsize(s, font=font)
        draw.text((pos[0], ch), s, font=font, fill=(0xff, 0xff, 0xff, 0xff))
        ch += h


def fitimg(img, width, height):
    '''
    Return rescaled image.
    '''
    scale1 = float(width) / img.size[0]
    scale2 = float(height) / img.size[1]

    l1 = (img.size[0] * scale1, img.size[1] * scale1)
    l2 = (img.size[0] * scale2, img.size[1] * scale2)

    if l1[0] > width or l1[1] > height:
        l = l2
    else:
        l = l1

    return img.resize((int(l[0]), int(l[1])), Image.ANTIALIAS)

def make_panels(events):
    '''
    Return a panels list from an events list.

    It will pair up events.

    events is list of tuple: [(time,nick,text), ...]
    '''
    panels = list()
    while events:
        panel = [events.pop(0)[1:]]
        if events:
            panel.append(events.pop(0)[1:])
        panels.append(panel)
    return panels
        

def random_images(datadir, kind):
    sd = Path(datadir) / kind
    lst = list(sd.glob('*.png'))
    lst += list(sd.glob('*.jpg'))
    shuffle(lst)
    return lst


def make_comic(panels, datadir):
    '''
    Return an image holding of panels of dialog.

    Expect to find appropriate files in subdirectories backgrounds/,
    chars/ and fonts/ of datadir.

    Panels is a list, each element a panel.  A panel is a list of
    2-tuples of (nick, dialog).
    '''
    chars = set()
    for panel in panels:
        for nick, line in panel:
            chars.add(nick)

    datadir = Path(datadir)

    panelheight = 300
    panelwidth = 450

    filenames = random_images(datadir, 'chars')
    charmap = {c:Image.open(str(f.absolute())) for c,f in zip(chars, filenames)}
    # filenames = map(lambda x: os.path.join('chars', x), filenames[:len(chars)])
    # chars = list(chars)
    # chars = zip(chars, filenames)
    # charmap = dict()
    # for ch, f in chars:
    #     charmap[ch] = Image.open(f)

    imgwidth = panelwidth
    imgheight = panelheight * len(panels)

    backgrounds = random_images(datadir, 'backgrounds')
    background_file = backgrounds[0]
    bg = Image.open(background_file)

    im = Image.new("RGBA", (imgwidth, imgheight), (0xff, 0xff, 0xff, 0xff))
    font_file = str((datadir / "fonts/Comic.ttf").absolute())
    font_size = 14
    print(f'FONT: {font_file} {type(font_file)}')
    font = ImageFont.truetype(font_file, font_size)

    for i in range(len(panels)):
        pim = Image.new("RGBA", (panelwidth, panelheight), (0xff, 0xff, 0xff, 0xff))
        pim.paste(bg, (0, 0))
        draw = ImageDraw.Draw(pim)

        st1w = 0; st1h = 0; st2w = 0; st2h = 0
        (st1, (st1w, st1h)) = wrap(panels[i][0][1], font, draw, 2*panelwidth/3.0)
        rendertext(st1, font, draw, (10, 10))
        if len(panels[i]) == 2:
            (st2, (st2w, st2h)) = wrap(panels[i][1][1], font, draw, 2*panelwidth/3.0)
            rendertext(st2, font, draw, (panelwidth-10-st2w, st1h + 10))

        texth = st1h + 10
        if st2h > 0:
            texth += st2h + 10 + 5

        maxch = panelheight - texth
        im1 = fitimg(charmap[panels[i][0][0]], 2*panelwidth/5.0-10, maxch)
        pim.paste(im1, (10, panelheight-im1.size[1]), im1)

        if len(panels[i]) == 2:
            im2 = fitimg(charmap[panels[i][1][0]], 2*panelwidth/5.0-10, maxch)
            im2 = im2.transpose(Image.FLIP_LEFT_RIGHT)
            pim.paste(im2, (panelwidth-im2.size[0]-10, panelheight-im2.size[1]), im2)

        draw.line([(0, 0), (0, panelheight-1), (panelwidth-1, panelheight-1), (panelwidth-1, 0), (0, 0)], (0, 0, 0, 0xff))
        del draw
        im.paste(pim, (0, panelheight * i))

    im = im.convert("RGB")
    return im

