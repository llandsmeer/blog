---
layout: post
title:  "Serving precompressed static sites using NGINX to save disk space"
date:   2019-08-29 21:50:00 +0200
categories: tech
comments: true
---

I had this idea to build my next ~~app~~ website as a completely static site,
including all user specific content. So no C# ASP / Flask or React, just static files
that get regenerated every so often with a cron job.
The main advantage would be an extremely simple server with nearly instant page loads, and a disadvantage would be more disk usage.
It definitely needs some form of authentication, so I still would have to write
a bit of server code.
But for a proof of concept,
I tried to get nginx to serve precompressed files from disk, as most traffic
is gzip compressed anyway. It's quite simple:

# NGINX with *gzip_static* and *gunzip* modules

To serve gzip-precompressed static file,
nginx needs the [*ngx_http_gzip_static_module*](http://nginx.org/en/docs/http/ngx_http_gzip_static_module.html)
For backwards compatibility with clients that
do not support gzip compression, the
[*ngx_http_gunzip_module*](http://nginx.org/en/docs/http/ngx_http_gunzip_module.html) module is also needed.
These modules have to be included at compile time
with *./configure* flags.
Luckily, these come with the
the prebuilt nginx package that comes with
the Ubuntu 18.04 I use. You can check this calling
`nginx -V`:

```
$ nginx -V
nginx version: nginx/1.14.0 (Ubuntu)
built with OpenSSL 1.1.1  11 Sep 2018
TLS SNI support enabled
configure arguments: [...] --with-http_gunzip_module --with-http_gzip_static_module [...]
```

When these do not show up, you have to recompile [nginx](http://nginx.org/en/download.html)
with the modules enabled.


# Minimal Static Website with Nginx

This step is optional, just to get
you on the same page, in a way which allows
for experimenting with the nginx configuration without
interfering with an existing setup.
It eases testing a lot, but if you already have a
nginx instance or static website running, its not needed.

So, lets build a minimal static website using jekyll:

```console
$ jekyll new static-site
[...]
$ (cd static-site; jekyll build)
[...]
$ (cd static-site/_site; find -type f)
./about/index.html
./js/respond.js
./js/html5shiv.js
./index.html
./jekyll/update/2019/08/29/welcome-to-jekyll.html
./css/main.css
./feed.xml

$ (cd static-site/_site; find . -type f -exec du --apparent-size -ah {} +)
7,3K    ./about/index.html
10K     ./js/respond.js
10K     ./js/html5shiv.js
5,1K    ./index.html
6,7K    ./jekyll/update/2019/08/29/welcome-to-jekyll.html
8,7K    ./css/main.css
3,5K    ./feed.xml
```

Now, write a minimal custom nginx config.
This way nginx can run as a regular user.
Make sure to update the root path to point to
the jekyll build target.

```nginx
# file custom-nginx.conf
error_log /tmp/nginx.error.log;
daemon off;
pid /tmp/nginx.pid;
events { }
http {
    access_log /tmp/nginx.access.log;
    include    /etc/nginx/mime.types;
    server {
        listen 8080 default_server;
        listen [::]:8080 default_server;
        root /home/llandsmeer/static-site/_site;
        index index.html;
        server_name _;
        location / {
                try_files $uri $uri/ =404;
        }
    }
}
```

And run it as a regular user. Note that
you need to specify an absolute path to
the config file.
The default jekyll template should show up at
`localhost:8080`.

```console
$ nginx -c $(readlink -f nginx.conf)
```

With this setup, we can continue to
forcing all assets to be pre gzip-compressed.

# Precompression

So lets precompress the static site. At first, I tried
`gzip -r .` (and also `gzip -r /` in an accident, which was not so much fun...).
That did not work, as nginx needs the original filename to be present
as well as the gzipped variant. As the gzipped version is
always used, the file with the original filename
can be empty.

```console
$ cd static-site/_site
$ for file in $(find . -type f)
do
    gzip -v "$file"
    touch -r "$file".gz "$file"
done
./about/index.html:      72.1% -- replaced with ./about/index.html.gz
./js/respond.js:         62.0% -- replaced with ./js/respond.js.gz
./js/html5shiv.js:       70.1% -- replaced with ./js/html5shiv.js.gz
./index.html:    61.7% -- replaced with ./index.html.gz
./jekyll/update/2019/08/29/welcome-to-jekyll.html:       59.8% -- replaced with ./jekyll/update/2019/08/29/welcome-to-jekyll.html.gz
./css/main.css:  77.5% -- replaced with ./css/main.css.gz
./feed.xml:      64.1% -- replaced with ./feed.xml.gz
$ cd ../..
```

Navigating to `localhost:8080` will give you a blank page now.
To allow nginx to serve precompressed files, the *gzip_static* option needs
to be enabled. Setting it to *on* allows nginx to choose between
a precompressed or normal version, but as there is no normal version,
it is set to *always*. Then, for clients which do not support
gzip compressed communication, the option *gunzip* is enabled
which allows nginx to decompress a file before sending it over the wire.

So add these lines to the *server* directive in the nginx config:

```nginx
gzip_static  always;
gzip_proxied expired no-cache no-store private auth;
gunzip       on;
```

Et voil&agrave;, a completely precompressed static website, served
over nginx with backwards compatibility for clients that do not
support compression.

# Size Comparison

In this simple example, there was a nice reduction in size
(altough for a website this size, precompression
is definitely premature optimization).
Note the distinction between disk usage and apparant file
size. Directories and empty files take up space too!

| Method    | Disk Usage | Apparent |
|:--------- | ----------:| --------:|
| Normal    |       100K |      87K |
| Gzipped   |        64K |      53K |

# Next

There is also [Zopfli](https://github.com/google/zopfli),
which performs better gzip compression but is a bit slower.
However for files this small, the effect was not noticable
in filesizes expressed in kilobytes.
To perform precompression using zopfli, use this:

```console
$ cd static-site/_site
$ for file in $(find . -type f)
do
    zopfli "$file"
    rm "$file"
    touch -r "$file".gz "$file"
done
$ cd ../..
```

Another possibility, of course, is to use a filesystem which has compression built in :).
