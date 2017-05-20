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

shirt_choices = [ (i,i) for i in ('', 'S', 'M', 'L', 'XL', '2XL', '3XL') ]

class AttendeeForm(FlaskForm):
    name = TextField()
    username = TextField('FreeBSD username')
    host = SelectField(coerce = int)
    email = TextField('Email address')
    address = TextField(widget = TextArea(), validators = [ Required() ])
    arrival = DateField('Arrival date (or empty if local)',
                        validators = [ Optional() ])
    departure = DateField('Departure date (or empty if local)',
                          validators = [ Optional() ])
    shirt_size = SelectField(choices = shirt_choices)
    dietary_needs = TextField()

    @classmethod
    def with_hosts(cls, hosts):
        form = AttendeeForm()
        form.host.choices = [ (-1, '') ] + [ (p.id, p.name) for p in hosts ]
        return form

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
