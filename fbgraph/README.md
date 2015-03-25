
# Facebook Graph Pagination

A Python script to fetch posts, likes, or comments from the Facebook Graph API.

The script accepts a set of access tokens and object IDs along with an endpoint (or edge). It retrieves all data associated with that endpoint for each object, cycling through the access tokens with every request.

## Endpoints

Currently 4 different endpoints are supported:

1.  `feed`: paginate through all posts published by a user or people on a user's profile, or posts in a page's wall.
2.  `posts`: a derivative of `feed` which only includes posts published by the object.
3.  `comments`: the set of comments associated with an object, e.g. a post.
4.  `likes`: the set of likes associated with an object, e.g. a post.

Refer to the [Graph API documentation](https://developers.facebook.com/docs/graph-api/reference) for more information.

## Pagination

The Graph API uses two main forms of pagination:

1.  date-based pagination with the `since` and `until` query parameters (any date supported by PHP's strptime).
2.  cursor-based pagination with the `after` query parameter (an opaque base64-encoded value).

Pagination stops once either of the following conditions are met:

1.  the cursor returned is the same as that of the previous request, or
2.  no cursor is returned, or
3.  no data is returned, or
4.  an error is returned.

The `posts` and `feed` endpoints both use date-based pagination. By default they fetch data up to 7 and 2 days prior to invocation respectively, which can be changed by providing a value for the `since` query parameter. To resume from a specific page you can provide a value for the `until` query parameter.

The `comments` and `likes` endpoints both use cursor-based pagination. To resume from a specific page you can provide a value for the `after` query parameter.

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


1.  Let's see what Lady Gaga has been up to in the last 10 days by fetching all of her page's posts:

    ```bash
    ./paginate.py -d gaga -t "$TOKEN" -q since $(date -d-10days +%s) -q fields from,story,message -e feed ladygaga
    ```

    ```bash
    ls gaga/
    ```

    ```text
     feed-ladygaga-0001.json  feed-ladygaga-0003.json
     feed-ladygaga-0002.json  feed-ladygaga-0004.json
    ```

    ```bash
    jq -r '.content.data[]|.id' gaga/feed-ladygaga-000* | tee >(sort -u | wc -l) | wc -l
    ```

    ```text
     175
     172
    ```

    How interesting, it looks like we fetched 175 posts, 3 of which are duplicates.

    The number of duplicates sounds right, since date-based pagination will always include the last post on each subsequent request, and we have 4 different requests.

2.  Now let's see what people think of those posts by fetching all of their comments in 4 parallel processes:


    ```bash
    jq -r '.content.data[]|.id' gaga/feed-ladygaga-000* | sort -u | xargs -L 4 -P 4 ./paginate.py -d gaga -t "$TOKEN" -q fields 'from.fields(name),message' -e comments 
    ```

    Be careful when running commands like the above: access tokens have rate limits associated with them and you could easily exceed them. It makes more sense to specify more than one access token, through the `-t|--tokens` or `--tokens-file` options. Requests will then alternate between them. This approach is not without caveats of its own however, since user IDs returned by the graph are app-scoped, and comment/like cursors may not be valid across tokens.

    Let's examine the output:

    ```bash
    ls gaga/
    ```

    ```text
      comments-103........_100.......-0001.json
      comments-103........_101.......-0001.json
      comments-103........_101.......-0002.json
      ...
      comments-368........_919.......-0001.json
      feed-ladygaga-0001.json
      feed-ladygaga-0002.json
      feed-ladygaga-0003.json
      feed-ladygaga-0004.json
    ```

    Wow, such data, we should probably analyse it:

    ```bash
    function histogram() { sort "$@" | uniq -c; };
    ```

    ```bash
    jq -r '.content.summary.total_count' gaga/comments-*-0001.json | histogram | sort -rnk 1 -k 2
    ```

    ```text
       160 0
         4 1
         1 3263
         1 3146
         1 1495
         1 1395
         1 1285
         1 1142
         1 947
         1 5
    ```

    Looks like posts are either really popular or not at all. But what about the authors of those comments?


    ```bash
    jq -r '.content.data[]|.from.name' gaga/comments-* | tee >(wc -l) | histogram | awk '{ print $1 }' | histogram | sort -nk 2
    ```

    ```text
      10935
        7145 1
         759 2
         231 3
          88 4
          61 5
          33 6
          26 7
          10 8
           4 9
           4 10
           5 11
           3 12
           5 13
           1 15
           2 16
           1 20
           1 21
           1 25
           1 43
           1 74
    ```

    We might have spotted some spammers there, those 5 people with 20 or more comments (or some seriously engaged fans).

