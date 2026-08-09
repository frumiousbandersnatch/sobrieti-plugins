#!/usr/bin/env python3
'''
Save file content to a local directory under a name derived from the
SHA1 hash of its content and form a URL for fetching it back.
'''

import hashlib
from pathlib import Path
from urllib.parse import urljoin


def save(data, outdir, baseurl, suffix=""):
    '''
    Write bytes 'data' to a file named by its SHA1 hash (plus optional
    'suffix', eg ".jpg") in directory 'outdir'.

    Return the URL formed by joining 'baseurl' with the file name.
    '''
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fname = hashlib.sha1(data).hexdigest() + suffix
    (outdir / fname).write_bytes(data)

    if not baseurl.endswith('/'):
        baseurl += '/'
    return urljoin(baseurl, fname)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', help="File to save")
    parser.add_argument('-o', '--outdir', required=True,
                         help="Directory to save the file into")
    parser.add_argument('-u', '--baseurl', required=True,
                         help="Base URL used to construct the returned URL")
    parser.add_argument('-s', '--suffix', default='',
                         help="Suffix to append to the hashed file name (eg '.jpg')")
    args = parser.parse_args()

    data = Path(args.file).read_bytes()
    print(save(data, args.outdir, args.baseurl, args.suffix))


if __name__ == '__main__':
    main()
