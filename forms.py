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

from flask_wtf import FlaskForm
from wtforms.fields import *
from wtforms.widgets import HiddenInput, TextArea
from wtforms.validators import Email, Optional, Required

class AttendeeForm(FlaskForm):
    name = TextField(validators = [ Required() ])
    username = TextField('FreeBSD username')
    host = SelectField(coerce = int)
    email = TextField('Email address')
    administrator = BooleanField()
    address = TextField(widget = TextArea(), validators = [ Required() ])
    arrival = DateField('Arrival date (or empty if local)',
                        validators = [ Optional() ])
    departure = DateField('Departure date (or empty if local)',
                          validators = [ Optional() ])
    dietary_needs = TextField()

    def add_hosts(self, hosts):
        self.host.choices = [ (-1, '') ] + [ (p.id, p.name) for p in hosts ]
        return self

    def validate(self):
        if not FlaskForm.validate(self):
            return False

        if self.username.data == '' and self.host.data == -1:
            self.host.errors.append(
                    "Guests without a FreeBSD username require a host")
            return False

        if self.username.data != '' and self.host.data != -1:
            self.host.errors.append(
                    "People with @FreeBSD.org usernames do not require a host")
            return False

        return True


class RegistrationForm(AttendeeForm):
    shirt_style = SelectField(coerce = int, validators = [ Required() ])

    def add_shirt_styles(self, styles):
        self.shirt_style.choices = [ (s.id, s.description) for s in styles ]
        return self


class AttendeeUpdate(AttendeeForm):
    """
    AttendeeUpdate differs from AttendeeForm only in having an existing
    Person.id to contend with.
    """

    id = IntegerField(widget = HiddenInput())

    @classmethod
    def for_person(cls, person, hosts):
        form = AttendeeUpdate(None, obj = person)
        form.host.choices = [ (-1, '') ] + [ (p.id, p.name) for p in hosts ]
        form.host.data = person.host_id if person.host_id else -1
        return form


class POIForm(FlaskForm):
    title = TextField()
    latitude = FloatField()
    longitude = FloatField()
    description = TextField()
    icon = TextField()
    width = IntegerField(validators = [ Optional() ])
    height = IntegerField(validators = [ Optional() ])

class POIUpdateForm(POIForm):
    id = IntegerField(widget = HiddenInput())


class ProductForm(FlaskForm):
    name = TextField()
    description = TextField()
    cost = IntegerField()
    note = TextField()

class ProductUpdateForm(ProductForm):
    id = IntegerField(widget = HiddenInput())


class PurchaseForm(FlaskForm):
    buyer = SelectField(coerce = int)
    item = SelectField(coerce = int)
    quantity = IntegerField(validators = [ Required() ])
    complimentary = BooleanField(default = False)

    def set_buyers(self, buyers):
        self.buyer.choices = [ (b.id, b.name) for b in buyers ]
        return self

    def set_products(self, products):
        self.item.choices = [ (p.id, p.description) for p in products ]
        return self

class PurchaseUpdateForm(PurchaseForm):
    id = IntegerField(widget = HiddenInput(), validators = [ Required() ])

    @classmethod
    def create(cls, people, products, data):
        if isinstance(data, dict):
            form = PurchaseUpdateForm(data)

        else:
            form = PurchaseUpdateForm(None, obj = data)
            form.buyer.data = data.buyer.id
            form.item.data = data.item.id

        form.set_buyers(people)
        form.set_products(products)

        return form


class PaymentForm(FlaskForm):
    payer = SelectField(coerce = int)
    date = DateField(validators = [ Required() ])
    value = IntegerField(validators = [ Required() ])
    note = TextField()

    def add_people(self, people):
        self.payer.choices = [ (p.id, p.name) for p in people ]
        return self

    def set_payer(self, p):
        self.payer.data = p.id if p else -1
        return self

class PaymentUpdateForm(PaymentForm):
    id = IntegerField(widget = HiddenInput())


class TodoForm(FlaskForm):
    description = TextField(validators = [ Required() ])
    deadline = DateField(validators = [ Optional() ])
    assignee = SelectField(coerce = int)
    complete = BooleanField(validators = [ Optional() ])

    def add_people(self, people):
        self.assignee.choices = [ (-1, '') ] + [
                (p.id, p.name) for p in people ]
        return self

    def set_assignee(self, a):
        self.assignee.data = a.id if a else -1
        return self

class TodoUpdateForm(TodoForm):
    id = IntegerField(widget = HiddenInput())
