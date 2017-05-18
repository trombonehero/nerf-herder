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


@frontend.route('/register/', methods = [ 'GET', 'POST' ])
def register():
    form = forms.RegistrationForm()
    if form.validate_on_submit():
        return 'thanks for registering'

    if (not config.REGISTRATION_IS_OPEN and
        flask.request.args.get('preregistration')
            != flask.current_app.config['PREREGISTRATION_CODE']):
        return flask.render_template('registration-not-open.html')

    return flask.render_template('register.html')


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
