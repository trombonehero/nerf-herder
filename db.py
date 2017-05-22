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
import crypto
import os
import peewee
from peewee import *


(scheme, url) = config.DATABASE_URL.split('://')
db = {
    'mysql': MySQLDatabase,
    'postgres': PostgresqlDatabase,
    'sqlite': SqliteDatabase,
}[scheme](url)

class BaseModel(Model):
    class Meta:
        database = db

class Money(object):
    name = os.environ.get('CURRENCY')
    symbol = os.environ.get('CURRENCY_SYMBOL')

    def __init__(self, micro = 0):
        assert type(micro) == int
        self.micro = micro

    def value(self):
        return self.micro / 100.0

    def __add__(self, other):
        if other == 0: return self
        return Money(self.micro + other.micro)

    def __radd__(self, other):
        if other == 0: return self
        return Money(self.micro + other.micro)

    def __sub__(self, other):
        if other == 0: return self
        return Money(self.micro - other.micro)

    def __mul__(self, factor): return Money(self.micro * factor)
    def __div__(self, factor): return Money(self.micro / factor)

    def __eq__(self, other):
        if other == 0: return self.micro == 0
        return other.micro == self.micro

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if other == 0: return self.micro < 0
        return (self.micro < other.micro)

    def __gt__(self, other):
        if other == 0: return self.micro > 0
        return (self.micro > other.micro)

    def __str__(self):
        return '{:}{:0,.2f}'.format(self.symbol, self.micro / 100.0)

    def __repr__(self):
        return 'Money { currency: {:}, value: {:} }'.format(
                self.name, self.micro)



class POI(BaseModel):
    """
    A point of interest in the vicinity of the DevSummit,
    e.g., working rooms, restaurants and transit.
    """

    latitude = FloatField()
    longitude = FloatField()
    title = TextField(unique = True)
    description = TextField(null = True)
    icon = TextField()
    width = IntegerField(default = 32)
    height = IntegerField(default = 32)

    class Meta:
        order_by = [ 'title' ]

    @classmethod
    def bounds(cls):
        """
        A bounding box containing all POI that match given criteria.

        Returns: ( min_lon, min_lat, max_lon, max_lat )
        """

        minimum = (180, 90)
        maximum = (-180, -90)

        for p in POI.select():
            lon = p.longitude
            lat = p.latitude

            minimum = (min(lon, minimum[0]), min(lat, minimum[1]))
            maximum = (max(lon, maximum[0]), max(lat, maximum[1]))

        minimum = tuple([ i - (2.0/3600) for i in minimum ])
        maximum = tuple([ i + (2.0/3600) for i in maximum ])

        return minimum + maximum

    def __str__(self):
        return "'%s' @ (%f,%f): '%s'" % (
            self.title,
            self.latitude, self.longitude,
            self.description
        )


# Placeholder for a Person (to break the "host" circular dependency)
DeferredPerson = DeferredRelation()

class Person(BaseModel):
    """
    An attendee and/or organizer of the DevSummit.
    """

    name = TextField()
    username = TextField(null = True)
    email = TextField(null = True, unique = True)
    address = TextField()
    administrator = BooleanField(default = False)
    arrival = DateField(null = True)
    departure = DateField(null = True)
    host = ForeignKeyField(DeferredPerson, null = True, related_name = 'guests')
    shirt_size = TextField()
    dietary_needs = TextField(null = True)

    class Meta:
        order_by = [ 'name' ]

    @classmethod
    def balances(cls):
        """ How much each attendee has paid and still owes us. """
        attendees = cls.select()

        balances = {}
        for a in attendees:
            paid = sum([ p.amount() for p in a.payments ])
            owing = sum([ p.total() for p in a.purchases ]) - paid

            balances[a] = owing

        return balances


    def auth(self):
        return crypto.hmac(str(self.id))

    def paid(self):
        return sum([ p.amount() for p in self.payments ])

    def total_purchases(self):
        return sum([ p.total() for p in self.purchases ])

    def __str__(self):
        return self.name

    def __repr__(self):
        attrs = [
            '%s: "%s"' % (name, self.__getattribute__(name))
            for name in [
                'id', 'name', 'username', 'email', 'arrival',
                'departure', 'host', 'shirt_size', 'dietary_needs',
            ]
        ]

        auth = "['" + self.auth() + "']"

        return 'Person { ' + ', '.join(attrs) + ' ' + auth + ' }'

DeferredPerson.set_model(Person)



class Product(BaseModel):
    """
    Something that can be purchased (or registered for) by a Person.
    """

    name = TextField(index = True, unique = True)
    description = TextField()
    cost = IntegerField()
    note = TextField(null = True)

    class Meta:
        order_by = [ 'description' ]

    def price(self):
        return Money(self.cost)

    def quantity(self):
        return sum([ p.quantity for p in self.purchases ])

    def all_purchases(self):
        return self.price() * self.quantity()

    def __str__(self):
        return '%s (%s)' % (self.description, self.price())


class Purchase(BaseModel):
    """
    A record of a Person purchasing a Product.
    """

    buyer = ForeignKeyField(Person, related_name = 'purchases')
    item = ForeignKeyField(Product, related_name = 'purchases')
    quantity = IntegerField()
    date = DateField()

    class Meta:
        order_by = [ 'date' ]

    def total(self):
        return Money(self.item.cost * self.quantity)


class Payment(BaseModel):
    """
    A record of someone paying a bill.
    """

    payer = ForeignKeyField(Person, related_name = 'payments')
    date = DateField()
    value = IntegerField()
    note = TextField(null = True)

    class Meta:
        order_by = [ 'date' ]

    def amount(self): return Money(self.cost)
    def __str__(self): return str(self.amount())


class Todo(BaseModel):
    """
    Something that one of the organizers is supposed to do.
    """

    class Meta:
        order_by = [ 'deadline' ]

    description = TextField()
    deadline = DateTimeField(null = True)
    assignee = ForeignKeyField(Person, null = True, related_name = 'todos')
    complete = BooleanField(default = False)


ALL_TABLES = (
        POI,
        Person,
        Product,
        Purchase,
        Payment,
        Todo,
)

def init(drop_first = True):
    if drop_first:
        db.drop_tables(ALL_TABLES, safe = True)

    db.create_tables(ALL_TABLES)

    Product.create(
        name = 'Registration',
        description = 'Normal registration',
        cost = 0,     # admins should fix this up before opening registration
    )
