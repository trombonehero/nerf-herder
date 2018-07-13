# nerf-herder

nerf-herder is a Web-based tool for managing developer summits.
It is a system of shining parts: Flask, Bootstrap, Material Design,
WTForms with CSRF protection... all the latest toys.


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
  * Apache + [mod_wsgi](https://modwsgi.readthedocs.io/en/develop/)
  * Nginx + [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)


## Deploying `nerf-herder`

### Configuration

Configuration of nerf-herder itself is done via either environment variables
or a `.env` file.
A sample `.env` file has been included at [samples/dot-env](samples/dot-env).
Copy this file into the directory you want to run nerf-herder from
(i.e., your source directory on the production server)
and customize it as appropriate.
**This file contains a secret key: don't forget `chmod 400 .env`!**


### Postgres

When running the Cambridge DevSummit, we use Postgres as our production
database.
We initialize the database as follows, assuming a username `me` for yourself,
`www` for the Nginx user and a registration cost of £65.00
(or $65.00, or €65.00, or...):

```sh
[me@bsdcam]$ sudo su - pgsql
$ psql postgres
psql (9.2.20, server 9.2.19)
Type "help" for help.

postgres=# create database bsdcam_2017;
CREATE DATABASE
postgres=# create role me with login;
CREATE ROLE
postgres=# create role www with login;
CREATE ROLE
postgres=# grant all privileges on database foo to me;
GRANT
postgres=# grant connect on database foo to www;
GRANT
postgres=# \q
$ exit
[me@bsdcam]$ cd /usr/local/www/nerf-herder
[me@bsdcam]$ ./nerfherd init
[me@bsdcam]$ psql bsdcam_2017
bsdcam_2017=> grant select, update, insert on all tables in schema public to www;
GRANT
bsdcam_2017=> grant usage, select on all sequences in schema public to www;
GRANT
bsdcam_2017=> update product set cost=6500 where name='Registration'
UPDATE 1
bsdcam_2017=> \q
[me@bsdcam]$
```


### Nginx and uWSGI

First, we need to arrange for uWSGI to run nerf-herder.
Copy [samples/uwsgi.ini](samples/uwsgi.ini) to somewhere handy
(`/usr/local/etc/ngix`, `/var/www`, etc.) and customize it.
For example, to run the Cambridge DevSummit we use:

```ini
[uwsgi]
chdir = /usr/local/www/nerf-herder
wsgi-file = /usr/local/www/nerf-herder/wsgi.py
uid = www
gid = wheel
socket = 127.0.0.1:3031
stats = 127.0.0.1:9191
```

On FreeBSD, we add the following to `/etc/rc.conf`:

```sh
uwsgi_enable="YES"
uwsgi_flags="--ini /usr/local/www/nerf-herder.ini"
```

Then we start uWSGI with `service uwsgi start`.
Progress will be logged to the default location,
`/var/log/uwsgi.log` (but this can be customized with the `logto` directive
in your uWSGI INI file).

Once that's done, Nginx configuration is very simple.
Inside the relevant `server` section:

```
location / {
  uwsgi_pass 127.0.0.1:3031;
  include uwsgi_params;
}
```

Then we start Nginx with `service nginx start`.


## User admin

The first user to register will be treated as an administrator.
To make sure that first user is you, run the server without any
`REGISTRATION_IS_OPEN` keys in your `.env` file:

```
./nerfherd run --port=5000
```

You can see the preregistration code on console, then goto

```
http://localhost:5000/register?preregistration=<code>
```

The organiser's interface is at `/org/`


## About the name

Yes, it's a Star Wars reference.
According to [Wookiepedia](http://starwars.wikia.com):

> Nerfs were a species of furry, non-sentient animals [...].
> Despite their usefulness, nerfs were often regarded as disgusting because of their strong body odor.

Software developers are useful people but sometimes a bit unwieldy to
herd without proper tools.
Also, at least in the FreeBSD context, they can sometimes be a bit furry.
Any further comparisions between developers and nerfs are disclaimed.
