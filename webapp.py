# Copyright 2017 Jonathan Anderson
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import config
import db
import flask
import flask_bootstrap
import flask_dotenv
import flask_httpauth
import forms
import nav
import sys

auth = flask_httpauth.HTTPBasicAuth()
database = db.db
frontend = flask.Blueprint('nerf-herder frontend', __name__)


@auth.error_handler
def auth_error():
    return 'Authentication error'

@auth.verify_password
def verify_auth(username, password):
    try: p = db.Person.get(username = username)
    except db.Person.DoesNotExist:
        sys.stderr.write("ERROR: invalid user '%s'\n" % username)
        return False

    if not p.administrator:
        sys.stderr.write("ERROR: %s is not an administrator\n" % username)
        return False

    if password != x.auth():
        sys.stderr.write("ERROR: %s used incorrect password\n" % username)
        return False

    return True


@frontend.before_request
def _db_connect():
    database.connect()

@frontend.teardown_request
def _db_close(exc):
    if not database.is_closed():
        database.close()


@frontend.route('/')
def index():
    return flask.render_template('index.html')


@frontend.route('/attendee/<int:id>')
def attendee(id):
    try: p = db.Person.get(id = id)
    except db.Person.DoesNotExist:
        return 'no such person'

    if flask.request.args.get('auth') != p.auth():
        return 'noooope.'

    return 'Person %d' % id


@frontend.route('/register/', methods = [ 'GET', 'POST' ])
def register():
    if not config.REGISTRATION_IS_OPEN:
        auth = flask.request.args.get('preregistration')
        if auth != flask.current_app.config['PREREGISTRATION_CODE']:
            return flask.render_template('registration-not-open.html')

    form = forms.RegistrationForm()
    form.host.choices = [ (-1, '') ] + [
            (p.id, p.name) for p in db.Person.select()
    ]

    if flask.request.method == 'POST':
        if form.validate_on_submit():
            email = form.email.data
            if email is None or email == '':
                assert form.username.data is not None
                email = '%s@FreeBSD.org' % form.username.data

            host = form.host.data
            if host == -1:
                host = None

            try:
                p = db.Person.create(
                    name = form.name.data,
                    username = form.username.data,
                    host = host,
                    email = email,
                    address = form.address.data,
                    arrival = form.arrival.data,
                    departure = form.departure.data,
                    shirt_size = form.shirt_size.data,
                    dietary_needs = form.dietary_needs.data,
                )

                flask.flash('Registration successful!')
                return flask.redirect('/attendee/%d?auth=%s' % (
                        p.id, p.auth()
                ))

            except db.peewee.IntegrityError, e:
                flask.flash(u"Error: %s (have you already registered?)" % e,
                            'error')

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flask.flash(u"Problem with '%s': %s" % (
                        getattr(form, field).label.text, error),
                        'error')

    return flask.render_template('register.html', form = form)


@frontend.route('/org/')
@auth.login_required
def admin():
    return 'admin'


nav.nav.register_element('frontend_top',
    nav.Navbar(
        nav.View(config.SITE_TITLE, '.index'),
        nav.View('Register', '.register'),
        nav.Subgroup(
            'External',
            nav.Link('Floor plans', 'https://www.cl.cam.ac.uk/maps'),
            nav.Link('Wiki', 'https://wiki.freebsd.org/DevSummit/201708'),
        ),
    )
)


def create_app(dev_mode = True):
    # See http://flask.pocoo.org/docs/patterns/appfactories
    app = flask.Flask(__name__)
    nav.nav.init_app(app)
    flask_dotenv.DotEnv().init_app(app, verbose_mode = dev_mode)

    flask_bootstrap.Bootstrap(app)
    app.register_blueprint(frontend)

    app.config['BOOTSTRAP_SERVE_LOCAL'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = dev_mode

    if not config.REGISTRATION_IS_OPEN:
        import crypto
        app.config['PREREGISTRATION_CODE'] = crypto.hmac('preregistration')

    return app
