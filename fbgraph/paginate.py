#!/usr/bin/env python

"""
Retrieve likes or comments for a specific Facebook post through the Graph API.
"""

try:
    import ujson as json
except:
    import json

import requests
import collections
import sys, os, argparse

ENDPOINTS = ('comments', 'likes')
GRAPH_URL ='https://graph.facebook.com/v2.2'
PARAMETERS = dict(summary=1, filter='stream')


def main(args):
    opts = parse_cli(args[1:], ENDPOINTS, GRAPH_URL)

    if not os.path.isdir(opts.output):
        os.makedirs(opts.output)

    posts = one_of(opts.posts, opts.posts_file)
    tokens = one_of(opts.tokens, opts.tokens_file)

    parameters = dict(PARAMETERS)
    if opts.query_parameters:
        parameters.update(opts.query_parameters)
    parameters['limit'] = opts.limit

    ramp_up = geometric_ramp_up(opts.limit_factor, opts.limit_max)
    progress = write_flush if opts.verbose else lambda x: x

    for post in posts:
        url = "%s/%s/%s" % (opts.url.rstrip('/'), post, opts.endpoint)
        names = filenames(opts.output, '%s_%s' % (opts.endpoint, post))
        count = 0
        for i, entry in enumerate(paginate(url, parameters, tokens, ramp_up), 1):
            filename = names(i)
            write_json(filename, entry, opts.overwrite)
            count += len(entry['content'].get('data', []))
            progress("\r%s %d" % (post, count))
        progress('\n')

    return 0


def paginate(endpoint, parameters, tokens, ramp_up = lambda x: x):
    """Paginate through a graph endpoint using cursors."""
    params = dict(parameters)
    queue = collections.deque(tokens)
    while True:
        params['access_token'] = queue.popleft()
        response = requests.get(endpoint, params=params)
        content = parse_response(response)
        yield dict(content=content, status=response.status_code, endpoint=endpoint, parameters=params)

        after = content.get('paging', {}).get('cursors', {}).get('after', None)
        data = content.get('data', [])
        if after and data:
            queue.append(params['access_token'])
            params['after'] = after
            if 'limit' in params:
                params['limit'] = ramp_up(params['limit'])
        else:
            break

def one_of(*lists):
    return tuple(e.strip() for l in lists if l is not None for e in l)

def write_flush(s):
    sys.stderr.write(s)
    sys.stderr.flush()

def filenames(dst, prefix):
    return lambda i: os.path.join(dst, "%s.%04d" % (prefix, i))

def write_json(filename, data, overwrite=False):
    assert overwrite or not os.path.exists(filename) # XXX: race condition
    with open(filename, 'wb') as fd:
        fd.write(json.dumps(data))

def geometric_ramp_up(multiplier, ceiling):
    return lambda x: min(ceiling, x * multiplier)

def parse_response(r):
    try:
        return r.json()
    except:
        return dict(error=r.text)

def parse_cli(args, endpoints, graph_url):
    parser = argparse.ArgumentParser(description = 'retrieve facebook comments/likes for a set of posts')
    add = parser.add_argument
    posts = parser.add_mutually_exclusive_group(required=True).add_argument
    posts('-p', '--posts', metavar='POST_ID', nargs='+',
        help='add post id to request pool')
    posts('--posts-file', type=argparse.FileType('rb'),
        help='read one post per line from file')
    tokens = parser.add_mutually_exclusive_group(required=True).add_argument
    tokens('-t', '--tokens', nargs='+', metavar='ACCESS_TOKEN',
        help='add access token to request pool')
    tokens('--tokens-file', type=argparse.FileType('rb'),
        help='read one token per line from file')
    add('-l', '--limit', type=int, default=25,
        help='set the starting request limit [%(default)s]')
    add('--limit-max', type=int, default=3000,
        help='set the maximum request limit [%(default)s]')
    add('--limit-factor', type=int, default=2,
        help='set limit multiplication factor [%(default)s]')
    add('-u', '--url', default=graph_url,
        help='set facebook graph url [%(default)s]')
    add('-q', '--query-parameters', nargs=2, action='append',
        help='specify additional query parameters')
    add('-o', '--output', default='.',
        help='set output directory [%(default)s]')
    add('-e', '--endpoint', choices=endpoints, required=True,
        help='choose endpoint')
    add('-v', '--verbose', action='store_true',
        help='print progress information on standard error')
    add('--overwrite', action='store_true',
        help='overwrite output files')
    return parser.parse_args(args)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

