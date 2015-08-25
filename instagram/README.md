
# Instagram API Pagination

A Python script to fetch posts, likes or comments from the Instagram API.

The script accepts a set of access tokens and Instagram IDs along with an endpoint. It retrieves data associated with that endpoint for each ID, cycling through the access tokens with every request.

Run `./instapi.py --help` for a full list of options.

## Endpoints

Currently 3 different endpoints are supported:

1.  `tags`: paginate through all posts containing a specific hashtag.
2.  `comments`: fetch the first 150 comments associated with a post.
3.  `likes`: fetch the last 120 likes associated with a post.

Refer to the [Instagram API documentation](https://instagram.com/developer/endpoints/) for more information.


## Pagination


The Instagram API uses timestamps as a pagination cursor.

The tag endpoint encodes the timestamps into Instagram IDs. A helper script (`post_timestamp`) is provided to extract timestamps from or encode timestamps into post IDs.

The comments and likes endpoints *do not support pagination*.

Pagination stops once either of the following conditions are met:

1.  the cursor returned is the same as that of the previous request,
2.  no cursor is returned, or
3.  no data is returned, or
4.  an error is returned.

## Output

The output of the script is a set of files in the destination directory, one for each request. Files can be JSON (the default), or YAML.

Every file contains the following fields:

```yaml
status: HTTP status code returned
endpoint: Request URL without any query parameters
parameters: Query parameters including access token
content: Response
```

## Dependencies

This script requires [Python](https://www.python.org/), [requests](http://docs.python-requests.org/en/latest) and optionally [PyYaml](http://pyyaml.org/wiki/PyYAML).

It has been tested successfully with Python 2.7.6 and 3.4.0, requests 2.2.1 and PyYaml 3.10.

## Examples

The following examples assume some basic knowledge of UNIX command line utilities, as well as [jq](http://stedolan.github.io/jq).

The `TOKEN` environment variable is assumed to refer to a valid access token.

1.  Let's see what people considered `#gossip` between August 20 08:00 UTC and August 21 12:00 UTC:

    ```bash
    ./instapi.py -d gossip -e tags -t "$TOKEN" -q min_tag_id $(./post_timestamp -r $(date --utc +%s -d'2015-08-20 08:00')) -q max_tag_id $(./post_timestamp -r $(date --utc +%s -d'2015-08-21 12:00')) gossip
    ```

    ```bash
    ls gossip
    ```

    ```text
    tags-gossip-0001.json  tags-gossip-0013.json  tags-gossip-0025.json
    ...
    tags-gossip-0012.json  tags-gossip-0024.json  tags-gossip-0036.json
    ```

    ```bash
    jq -r '.content.data[]|.created_time' gossip/tags* | sort -n | sed -n '1p;$p' | xargs -L1 -Ix date -d@x
    ```
    ```text
    Thu Aug 20 09:00:31 BST 2015
    Fri Aug 21 12:57:27 BST 2015
    ```

    ```bash
    jq -r '.content.data[]|.id' gossip/* | tee >(sort -u | wc -l) | wc -l
    ```
    ```text
    1136
    1101
    ```

    It turns out we made 36 requests resulting in 1136 posts, 35 of which are duplicates. This makes sense as we get the same post twice at a pagination boundary.

2.  These posts will contain some embedded comments and likes, but what if we want more?

    ```bash
    function histogram() { sort "$@" | uniq -c; };
    ```
    ```bash
    jq '.content.data[]|.comments.data|length' gossip/* | histogram 
    ```
    ```text
    613 0
    237 1
    116 2
     51 3
     33 4
     17 5
     21 6
      9 7
     39 8
    ```

    ```bash
    jq -r '.content.data[]|.id' gossip/* | sort -u | xargs -L4 -P4 ./instapi.py -d gossip -e comments -t $TOKEN
    ```

    No pagination parameters are necessary here since the comment/like endpoints do not support it.

    ```bash
    ls gossip/comments-*
    ```
    ```text
    gossip/comments-105560237998..._33512...-0001.json
    gossip/comments-105560272117..._21032...-0001.json
    ...
    gossip/comments-105560300095..._21032...-0001.json

    ```

    Now let's compare the data we got to the total number of comments for each post as reported in our initial request:

    ```bash
    jq -r '.content.data[]|"\(.id) \(.comments.count)"' gossip/tags-gossip-00* | while read post count; do echo $((count - $(jq -r '.content.data|length' gossip/comments-${post}-0001.json))); done | histogram
    ```
    ```text
    1132 0
       1 1
       1 -1
       1 142
       1 238
    ```

    So it looks like most posts had between 0 and 150 comments in which case we retrieved all them, 3 posts had more than 150 and 1 post had 1 new comment added in between requests.

