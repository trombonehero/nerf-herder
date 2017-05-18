# nerf-herder

nerf-herder is a Web-based tool for managing developer summits.

## Requirements

* Python
  * either v2 or v3 should be fine with nerf-herder itself
  * the full set of package dependencies works with v2, v3 may come in time?
* a database
  * Postgres is recommended for production use
  * SQLite is suitable for local prototyping
* Python packages:
  * docopt
  * flask
  * flask-bootstrap
  * flask-nav
  * flask-wtf
  * flask-DotEnv
  * peewee
  * psycopg2 (for use with Postgres)
  * python-dotenv
  * sqlite3 (for use with SQLite)
* WSGI hosting software
  * [Apache + mod_wsgi](https://modwsgi.readthedocs.io/en/develop/)
  * [Nginx + uWSGI](https://www.digitalocean.com/community/tutorials/how-to-deploy-python-wsgi-applications-using-uwsgi-web-server-with-nginx)

## About the name

Yes, it's a Star Wars reference.
According to [Wookiepedia](http://starwars.wikia.com):

> Nerfs were a species of furry, non-sentient animals [...].
> Despite their usefulness, nerfs were often regarded as disgusting because of their strong body odor.

Software developers are useful people but sometimes a bit unwieldy to
herd without proper tools.
Also, at least in the FreeBSD context, they can sometimes be a bit furry.
Any further comparisions between developers and nerfs are disclaimed.
