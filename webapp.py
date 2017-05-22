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
import datetime
import db
import flask
import flask_bootstrap
import flask_dotenv
import flask_httpauth
import forms
import mail
import nav
import sys

auth = flask_httpauth.HTTPBasicAuth()
database = db.db
frontend = flask.Blueprint('nerf-herder frontend', __name__)


@auth.error_handler
def auth_error():
    return render_error(401, "This page is only available to the organizers")

@auth.verify_password
def verify_auth(username, password):
    try: p = db.Person.get(username = username)
    except db.Person.DoesNotExist:
        sys.stderr.write("ERROR: invalid user '%s'\n" % username)
        return False

    if not p.administrator:
        sys.stderr.write("ERROR: %s is not an administrator\n" % username)
        return False

    if password != p.auth():
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



def render_error(code, message, *args):
    error_codes = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
    }

    response = flask.render_template('error.html',
        title = '%d %s' % (code, error_codes[code]),
        message = message,
        details = args
    )

    return (response, code)


@frontend.route('/')
def index():
    return flask.render_template('index.html')


@frontend.route('/attendee/<int:id>')
def attendee(id):
    try:
        p = db.Person.get(id = id)
        if flask.request.args.get('auth') == p.auth():
            return flask.render_template('attendee.html',
                attendee = p, products = db.Product.select())

    except db.Person.DoesNotExist:
        pass

    return render_error(401,
            "Access to an attendee's details requires an authorization code",
            "example: /attendee/42?auth=jp2v55degrkqtlj4o3qk")


@frontend.route('/map/')
def map():
    return flask.render_template('map.html',
        poi = db.POI.select(),
        mapbox_access_token = config.MAPBOX_TOKEN,
    )


@frontend.route('/register/', methods = [ 'GET', 'POST' ])
def register():
    if not config.REGISTRATION_IS_OPEN:
        auth = flask.request.args.get('preregistration')
        if auth != flask.current_app.config['PREREGISTRATION_CODE']:
            return flask.render_template('registration-not-open.html')

    form = forms.AttendeeForm()
    form.add_hosts(db.Person.select())

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
                # Create the person in the database:
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

                if db.Person.select().count() == 1:
                    flask.flash('''You are the first registrant;
                        granting administrative privileges''')
                    p.administrator = True
                    p.save()

                # Buy the "registration" product:
                registration = db.Product.get(name = 'Registration')
                db.Purchase.create(
                    buyer = p,
                    item = registration,
                    quantity = 1,
                    date = datetime.datetime.now()
                )

                flask.flash('Registration successful!')

                mail.send([ p.email ],
                        subject = '%s registration' % config.SITE_TITLE,
                        body = flask.render_template(
                                'registration-email.txt', attendee = p)
                )

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
    bookings = db.Product.select().where(db.Product.cost == 0)
    products = db.Product.select().where(db.Product.cost > 0)
    total_purchases = sum([ p.all_purchases() for p in products ])

    payments = db.Payment.select().order_by(db.Payment.date)

    balances = db.Person.balances()
    balance = sum(balances.values())
    balances = sorted(balances.items(), key = lambda (k,v): v, reverse = True)

    return flask.render_template('admin/index.html',
        config = config,
        attendees = db.Person.select(),
        balance = balance,
        balances = balances,
        bookings = bookings,
        payments = payments,
        products = products,
        todos = db.Todo.select().where(db.Todo.complete == False),
        total_payments = sum([ p.amount() for p in payments ]),
        total_purchases = total_purchases,
        prereg = flask.current_app.config['PREREGISTRATION_CODE'],
    )

@frontend.route('/org/attendees/')
@auth.login_required
def admin_attendees():
    hosts = db.Person.select()

    return flask.render_template('admin/attendees.html',
        config = config,
        attendees = [
            (p, forms.AttendeeUpdate.for_person(p, hosts))
            for p in db.Person.select()
        ],
        new_person = forms.AttendeeForm(obj = None).add_hosts(hosts),
    )

@frontend.route('/org/attendees/attendees.csv')
@auth.login_required
def admin_attendees_csv():
    return flask.Response(
            flask.render_template('admin/attendees.csv',
                attendees = db.Person.select()),
            mimetype = 'text/csv',
    )

@frontend.route('/org/attendees/email')
@auth.login_required
def admin_attendees_email():
    return flask.Response(
            flask.render_template('admin/attendee-emails.txt',
                attendees = db.Person.select()),
            mimetype = 'text/plain',
    )

@frontend.route('/org/attendees/update', methods = [ 'POST' ])
@auth.login_required
def admin_attendee_update():
    form = forms.AttendeeUpdate()
    form.add_hosts(db.Person.select())

    if form.validate_on_submit():
        p = db.Person.get(id = form.id.data)
        p.name = form.name.data
        p.username = form.username.data
        p.host = form.host.data if form.host.data >= 0 else None
        p.email = form.email.data
        p.administrator = form.administrator.data
        p.address = form.address.data
        p.arrival = form.arrival.data
        p.departure = form.departure.data
        p.shirt_size = form.shirt_size.data
        p.dietary_needs = form.dietary_needs.data
        p.save()

    else:
        for field, errors in new_poi.errors.items():
            for error in errors:
                flask.flash(u"Problem with '%s': %s" % (
                    getattr(new_poi, field).label.text, error),
                    'error')

    return flask.redirect(flask.url_for('nerf-herder frontend.admin_attendees'))

@frontend.route('/org/poi/', methods = [ 'GET', 'POST' ])
@auth.login_required
def admin_poi():
    new_poi = forms.POIForm()

    if flask.request.method == 'POST':
        if not new_poi.validate_on_submit():
            for field, errors in new_poi.errors.items():
                for error in errors:
                    flask.flash(u"Problem with '%s': %s" % (
                        getattr(new_poi, field).label.text, error),
                        'error')

        else:
            try:
                p = db.POI.create(
                    title = new_poi.title.data,
                    description = new_poi.description.data,
                    latitude = new_poi.latitude.data,
                    longitude = new_poi.longitude.data,
                    icon = new_poi.icon.data,
                )

                if new_poi.height:
                    p.height = new_poi.height.data

                if new_poi.width:
                    p.width = new_poi.width.data

            except db.peewee.IntegrityError, e:
                flask.flash(u"Error: %s" % e, 'error')

            new_poi = forms.POIForm(None)

    return flask.render_template('admin/poi.html',
        forms = [
            forms.POIUpdateForm(None, obj = p)
            for p in db.POI.select()
        ],
        poi = db.POI.select(),
        mapbox_access_token = config.MAPBOX_TOKEN,
        new_poi = new_poi,
    )

@frontend.route('/org/poi/update', methods = [ 'POST' ])
@auth.login_required
def admin_poi_update():
    form = forms.POIUpdateForm()

    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flask.flash(u"Problem updating '%s': %s" % (
                    getattr(form, field).label.text, error),
                    'error')

    else:
        try:
            p = db.POI.get(id = form.id.data)
            p.title = form.title.data
            p.description = form.description.data
            p.latitude = form.latitude.data
            p.longitude = form.longitude.data
            p.icon = form.icon.data

            if form.height:
                p.height = form.height.data

            if form.width:
                p.width = form.width.data

            p.save()

        except Exception, e:
            flask.flash(u"Error: %s" % e, 'error')

    return flask.redirect(flask.url_for('nerf-herder frontend.admin_poi'))


@frontend.route('/org/products/', methods = [ 'GET', 'POST' ])
@auth.login_required
def admin_products():
    new = forms.ProductForm()

    if flask.request.method == 'POST':
        if new.validate_on_submit():
            p = db.Product.create(
                name = new.name.data,
                description = new.description.data,
                cost = new.cost.data,
            )

            if new.note:
                p.note = new.note.data
                p.save()

        else:
            for field, errors in new.errors.items():
                for error in errors:
                    flask.flash(u"Problem with '%s': %s" % (
                        getattr(new, field).label.text, error),
                        'error')

    new = forms.ProductForm(None)

    return flask.render_template('admin/products.html',
        products = [
            forms.ProductUpdateForm(None, obj = p) for p in db.Product.select()
        ],
        new = new,
    )

@frontend.route('/org/products/update', methods = [ 'POST' ])
@auth.login_required
def admin_product_update():
    form = forms.ProductUpdateForm()

    if form.validate_on_submit():
        p = db.Product.get(id = form.id.data)
        p.name = form.name.data
        p.description = form.description.data
        p.cost = form.cost.data
        p.note = form.note.data
        p.save()

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flask.flash(u"Problem with '%s': %s" % (
                    getattr(form, field).label.text, error),
                    'error')

    return flask.redirect(flask.url_for('nerf-herder frontend.admin_products'))


@frontend.route('/org/purchases/')
@auth.login_required
def admin_purchases():
    return flask.render_template('admin/index.html',
        config = config,
        attendees = db.Person.select(),
    )

@frontend.route('/org/payments/', methods = [ 'GET', 'POST' ])
@auth.login_required
def admin_payments():
    people = list(db.Person.select())
    new = forms.PaymentForm().add_people(people)

    if flask.request.method == 'POST':
        if new.validate_on_submit():
            p = db.Payment.create(
                payer = new.payer.data,
                date = new.date.data,
                value = 100 * new.value.data
            )
            if new.note:
                p.note = new.note.data
                p.save()

        else:
            for field, errors in new.errors.items():
                for error in errors:
                    flask.flash(u"Problem with '%s': %s" % (
                        getattr(new, field).label.text, error),
                        'error')

    new = forms.PaymentForm(None).add_people(people)

    return flask.render_template('admin/payments.html',
        payments = [
            forms.PaymentUpdateForm(None, obj = p).add_people(people)
            for p in db.Payment.select()
        ],
        new = new,
    )

@frontend.route('/org/payments/update', methods = [ 'POST' ])
@auth.login_required
def admin_payments_update():
    form = forms.PaymentUpdateForm()
    form.add_people(db.Person.select())

    if form.validate_on_submit():
        p = db.Payment.get(id = form.id.data)
        p.date = form.date.data
        p.payer = form.payer.data
        p.value = form.value.data
        p.save()

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flask.flash(u"Problem with '%s': %s" % (
                    getattr(form, field).label.text, error),
                    'error')

    return flask.redirect(flask.url_for('nerf-herder frontend.admin_payments'))


@frontend.route('/org/todo/', methods = [ 'GET', 'POST' ])
@auth.login_required
def admin_todo():
    people = list(db.Person.select())
    new = forms.TodoForm().add_people(people)

    if flask.request.method == 'POST':
        if new.validate_on_submit():
            t = db.Todo.create(description = new.description.data)
            if new.deadline: t.deadline = new.deadline.data
            if new.assignee != -1: t.assignee = new.assignee.data
            if new.complete: t.complete = new.complete.data
            t.save()

        else:
            for field, errors in new.errors.items():
                for error in errors:
                    flask.flash(u"Problem with '%s': %s" % (
                        getattr(new, field).label.text, error),
                        'error')

    new = forms.TodoForm(None).add_people(people)

    return flask.render_template('admin/todos.html',
        todos = [
            forms.TodoUpdateForm(None, obj = t).add_people(people)
            for t in db.Todo.select()
        ],
        new = new,
    )
@frontend.route('/org/todo/update', methods = [ 'POST' ])
@auth.login_required
def admin_todo_update():
    form = forms.TodoUpdateForm()
    form.add_people(db.Person.select())

    if form.validate_on_submit():
        t = db.Todo.get(id = form.id.data)
        t.description = form.description.data
        t.deadline = form.deadline.data
        if form.assignee.data != -1:
            t.assignee = form.assignee.data
        t.complete = form.complete.data
        t.save()

    else:
        for field, errors in form.errors.items():
            for error in errors:
                flask.flash(u"Problem with '%s': %s" % (
                    getattr(form, field).label.text, error),
                    'error')

    return flask.redirect(flask.url_for('nerf-herder frontend.admin_todo'))


nav.nav.register_element('admin',
    nav.Navbar(
        nav.View(config.SITE_TITLE, '.index'),
        nav.Subgroup(
            'Admin',
            nav.View('Summary', '.admin'),
            nav.Separator(),
            nav.View('Attendees', '.admin_attendees'),
            nav.View('POI', '.admin_poi'),
            nav.View('Products', '.admin_products'),
            nav.View('Purchases', '.admin_purchases'),
            nav.View('Payments', '.admin_payments'),
            nav.View('Todos', '.admin_todo'),
        ),
        nav.View('Map', '.map'),
        nav.Subgroup(
            'External',
            nav.Link('Floor plans', 'https://www.cl.cam.ac.uk/maps'),
            nav.Link('Wiki', 'https://wiki.freebsd.org/DevSummit/201708'),
        ),
    )
)

nav.nav.register_element('frontend_top',
    nav.Navbar(
        nav.View(config.SITE_TITLE, '.index'),
        nav.View('Map', '.map'),
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

    import crypto
    app.config['PREREGISTRATION_CODE'] = crypto.hmac('preregistration')

    return app
