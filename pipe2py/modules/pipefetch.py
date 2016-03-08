# -*- coding: utf-8 -*-
# vim: sw=4:ts=4:expandtab
"""
pipe2py.modules.pipefetch
~~~~~~~~~~~~~~~~~~~~~~~~~
Provides functions for fetching RSS feeds.

Lets you specify one or more RSS news feeds as input to your Pipe. The module
understands feeds in RSS, Atom, and RDF formats. Feeds contain one or more
items. When you add more feed URLs, you get a single feed combining all the
items from the individual feeds.

Examples:
    basic usage::

        >>> from pipe2py.modules.pipefetch import pipe
        >>> pipe(conf={'url': {'value': FILES[0]}}).next()['title']
        u'Donations'

Attributes:
    OPTS (dict): The default pipe options
    DEFAULTS (dict): The default parser options
"""

from __future__ import (
    absolute_import, division, print_function, with_statement,
    unicode_literals)

import speedparser

from functools import partial
from itertools import imap
from urllib2 import urlopen
from twisted.internet.defer import inlineCallbacks, returnValue

from . import processor, FEEDS, FILES
from pipe2py.lib import utils
from pipe2py.twisted import utils as tu
from pipe2py.lib.log import Logger

OPTS = {'listize': True, 'extract': 'url', 'emit': True, 'ftype': 'none'}
logger = Logger(__name__).logger


# http://blog.mekk.waw.pl/archives/
# https://github.com/steder/ng-images/blob/master/natgeo.py
# http://code.activestate.com/recipes/277099/
@inlineCallbacks
def asyncParser(_, urls, skip, **kwargs):
    """ Asynchronously parses the pipe content

    Args:
        _ (None): Ignored
        objconf (obj): The pipe configuration (an Objectify instance)
        skip (bool): Don't parse the content
        kwargs (dict): Keyword argurments

    Kwargs:
        assign (str): Attribute to assign parsed content (default: content)
        feed (dict): The original item

    Returns:
        Tuple(Iter[dict], bool): Tuple of (feed, skip)

    Examples:
        >>> from twisted.internet.task import react
        >>> from pipe2py.lib.utils import Objectify
        >>>
        >>> def run(reactor):
        ...     callback = lambda x: print(x[0].next()['title'])
        ...     objconf = Objectify({'url': FILES[0]})
        ...     kwargs = {'feed': {}}
        ...     d = asyncParser(None, objconf, False, **kwargs)
        ...     return d.addCallbacks(callback, logger.error)
        >>>
        >>> try:
        ...     react(run, _reactor=tu.FakeReactor())
        ... except SystemExit:
        ...     pass
        ...
        Donations
    """
    if skip:
        feed = kwargs['feed']
    else:
        abs_urls = imap(utils.get_abspath, urls)
        contents = yield tu.asyncImap(tu.urlRead, abs_urls)
        parsed = imap(speedparser.parse, contents)
        entries = imap(utils.gen_entries, parsed)
        feed = utils.multiplex(entries)

    result = (feed, skip)
    returnValue(result)


def parser(_, urls, skip, **kwargs):
    """ Parses the pipe content

    Args:
        _ (None): Ignored
        urls (List[str]): The urls to fetch
        skip (bool): Don't parse the content

    Returns:
        List(dict): the tokenized content

    Examples:
        >>> kwargs = {'feed': {}}
        >>> result, skip = parser(None, FILES, False, **kwargs)
        >>> result.next()['title']
        u'Donations'
    """
    if skip:
        feed = kwargs['feed']
    else:
        abs_urls = imap(utils.get_abspath, urls)
        contents = (urlopen(url).read() for url in abs_urls)
        parsed = imap(speedparser.parse, contents)
        entries = imap(utils.gen_entries, parsed)
        feed = utils.multiplex(entries)

    return feed, skip


@processor(async=True, **OPTS)
def asyncPipe(*args, **kwargs):
    """A source that asynchronously fetches and parses one or more feeds to
    return the feed entries.

    Args:
        item (dict): The entry to process
        kwargs (dict): The keyword arguments passed to the wrapper

    Kwargs:
        context (obj): pipe2py.Context object
        conf (dict): The pipe configuration. Must contain the key 'url'. May
            contain the key 'assign'.

            url (str): The web site to fetch
            assign (str): Attribute to assign parsed content (default: content)

        field (str): Item attribute from which to obtain the string to be
            tokenized (default: content)

    Returns:
        dict: twisted.internet.defer.Deferred item with feeds

    Examples:
        >>> from twisted.internet.task import react
        >>>
        >>> def run(reactor):
        ...     callback = lambda x: print(x.next().keys())
        ...     urls = [{'value': FILES[0]}, {'value': FILES[1]}]
        ...     d = asyncPipe(conf={'url': urls})
        ...     return d.addCallbacks(callback, logger.error)
        >>>
        >>> try:
        ...     react(run, _reactor=tu.FakeReactor())
        ... except SystemExit:
        ...     pass
        ...
        ['updated', 'updated_parsed', u'pubDate', 'author', u'y:published', \
'title', 'comments', 'summary', 'content', 'link', u'y:title', u'dc:creator', \
u'author.uri', u'author.name', 'id', u'y:id']
    """
    return asyncParser(*args, **kwargs)


@processor(**OPTS)
def pipe(*args, **kwargs):
    """A source that fetches and parses one or more feeds to return the
    entries.

    Args:
        item (dict): The entry to process
        kwargs (dict): The keyword arguments passed to the wrapper

    Kwargs:
        context (obj): pipe2py.Context object
        conf (dict): The pipe configuration. Must contain the key 'url'. May
            contain the key 'assign'.

            url (str): The web site to fetch
            assign (str): Attribute to assign parsed content (default: content)

        field (str): Item attribute from which to obtain the string to be
            tokenized (default: content)

    Returns:
        dict: an iterator of items

    Examples:
        >>> url = [{'value': FILES[0]}, {'value': FILES[1]}]
        >>> keys = [
        ...     'updated', 'updated_parsed', u'pubDate', 'author',
        ...     u'y:published', 'title', 'comments', 'summary', 'content',
        ...     'link', u'y:title', u'dc:creator', u'author.uri',
        ...     u'author.name', 'id', u'y:id']
        >>> pipe(conf={'url': url}).next().keys() == keys
        True
        >>> result = pipe({'url': FILES[0]}, conf={'url': [{'subkey': 'url'}]})
        >>> result.next().keys() == keys
        True
    """
    return parser(*args, **kwargs)
