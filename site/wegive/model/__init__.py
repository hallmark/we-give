# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""The application's model objects"""
import sqlalchemy as sa
from sqlalchemy import orm, schema, types, Column, Sequence, ForeignKey
from sqlalchemy.databases.mysql import MSBigInteger
import datetime

from wegive.model import meta

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""

    sm = orm.sessionmaker(autoflush=True, autocommit=False, expire_on_commit=True, bind=engine)

    meta.engine = engine
    meta.Session = orm.scoped_session(sm)


def now():
    # TODO: is this UTC now?
    return datetime.datetime.now()

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base(metadata=meta.metadata)

#
# Define We Give's model classes
#
# Note: __init__ and __repr__ are not required by SQLAlchemy, but provided for convenience
#

class User(Base):
    """
    A user of We Give, void of details specific to any social network.
    """
    __tablename__ = 'wg_user'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('user_id_seq', optional=True), primary_key=True)
    email = Column(types.Unicode(255), unique=True)
    password = Column(types.String(50))
    first_name = Column(types.Unicode(64))
    last_name = Column(types.Unicode(64))
    address_id = Column(types.Integer, ForeignKey("wg_address.id"))
    created = Column(types.TIMESTAMP(), default=now)  # TODO: is this UTC?????
    
    received_gifts = orm.relation("Donation", primaryjoin="(Donation.recipient_id==User.id) & (Donation.pending==False)",
                                  order_by="desc(Donation.given_date)", backref="recipient")
    sent_gifts = orm.relation("Donation", primaryjoin="(Donation.donor_id==User.id) & (Donation.pending==False)",
                                  order_by="desc(Donation.given_date)", backref="donor")
    address = orm.relation("Address", primaryjoin="User.address_id==Address.id", uselist=False)
    personas = orm.relation("UserPersona", backref="user")
    
    # locale?
    # timezone?
    
    # TODO: this is temporary.  Should be moved to a UserMapping or UserPersona table
    # NOTE: Facebook User IDs:
    # The user ID is a 64-bit int datatype. If you're storing it in a MySQL database, use the BIGINT unsigned datatype
    facebook_uid = Column(MSBigInteger(unsigned=True))
    
    def __init__(self):
        pass
    
    def __repr__(self):
        return "<User('%s')>" % (self.email)

class UserPersona(Base):
    """
    A user's representation on a specific social network.
    
    Needs to handle a super-set of all info to store from the various networks.
    """
    __tablename__ = 'wg_userpersona'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('userpersona_id_seq', optional=True), primary_key=True)
    
    # the base mapping info (userID, networkID, network-userID)
    wg_user_id = Column(types.Integer, ForeignKey("wg_user.id"), nullable=False)
    network_id = Column(types.Integer, ForeignKey("wg_network.id"), nullable=False)
    network_user_id = Column(MSBigInteger(unsigned=True), nullable=False)
    created = Column(types.TIMESTAMP(), default=now)
    # TODO: uniqueness constraint on [network_id, network_user_id]
    # TODO: uniqueness constraint on [wg_user_id, network_id]
    
    # whether the user has added/authorized the We Give app
    is_app_user = Column(types.Boolean, default=False)
    
    # the proxied email address (Facebook)
    proxied_email = Column(types.Unicode(255))
    
    def __init__(self, wg_user_id, network_id, network_user_id):
        self.wg_user_id = wg_user_id
        self.network_id = network_id
        self.network_user_id = network_user_id

    def __repr__(self):
        return "<UserPersona(%d on network<%d>)>" % (self.wg_user_id, network_id)

class SocialNetwork(Base):
    """
    A network with which We Give has integrated, such as Facebook, MySpace, LinkedIn, or Bebo.
    """
    __tablename__ = 'wg_network'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('network_id_seq', optional=True), primary_key=True)
    name = Column(types.Unicode(255), nullable=False)
    url = Column(types.Unicode(255), nullable=False)

    def __init__(self, name, url):
        self.name = name
        self.url = url
    
    def __repr__(self):
        return "<SocialNetwork(%s)>" % (self.name)

class Charity(Base):
    """
    A charity, such as ACWP or Seva.
    """
    __tablename__ = 'wg_charity'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('charity_id_seq', optional=True), primary_key=True)
    name = Column(types.Unicode(255), nullable=False)
    short_code = Column(types.String(10), nullable=False)
    address_id = Column(types.Integer, ForeignKey("wg_address.id"))
    url = Column(types.Unicode(255))
    recipient_token_id = Column(types.String(128))
    created = Column(types.TIMESTAMP(), default=now)
    
    address = orm.relation("Address", primaryjoin="Charity.address_id==Address.id", uselist=False)
    programs = orm.relation("Program", order_by="Program.name", backref="charity")
    donations = orm.relation("Donation", order_by="desc(Donation.given_date)", backref="charity")
    
    def __init__(self, name, short_code):
        self.name = name
        self.short_code = short_code
    
    def __repr__(self):
        return "<Charity(%s)>" % (self.name)

class Program(Base):
    """
    A charity program, such as the education program with ACWP, or the vaccination program.
    """
    __tablename__ = 'wg_program'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('program_id_seq', optional=True), primary_key=True)
    name = Column(types.Unicode(255), nullable=False)
    description = Column(types.UnicodeText)
    charity_id = Column(types.Integer, ForeignKey("wg_charity.id"))
    url = Column(types.Unicode(255))
    created = Column(types.TIMESTAMP(), default=now)
    
    def __init__(self, name, charity_id):
        self.name = name
        self.charity_id = charity_id
    
    def __repr__(self):
        return "<Program(%s, charity<%d>)>" % (self.name, self.charity_id)

class Address(Base):
    """
    Represents address details, roughly based on the xAL, or eXtensible Address Language.
       http://www.oasis-open.org/committees/ciq/ciq.html#6
       http://docs.oasis-open.org/ciq/v3.0/prd02/specs/ciq-specs-v3-prd2.html#_Toc170648866
    """
    __tablename__ = 'wg_address'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('address_id_seq', optional=True), primary_key=True)
    # street address
    thoroughfare = Column(types.Unicode(255))
    address_line_2 = Column(types.Unicode(255))
    address_line_3 = Column(types.Unicode(255))
    # e.g., company, university, big building, hospital
    premises = Column(types.Unicode(255))
    # city, town
    locality = Column(types.Unicode(255))
    # zip code
    postal_code = Column(types.Unicode(64))
    rural_delivery = Column(types.Unicode(255))
    # PO Box
    postal_delivery_point = Column(types.Unicode(64))
    # state, province, prefecture (region for vCards)
    administrative_area = Column(types.Unicode(255))
    # county
    sub_administrative_area = Column(types.Unicode(255))
    # ISO 3166-1: two letter country codes
    country_name_code = Column(types.String(2))
    
    def __init__(self, street_address, city, state, zip_code, country):
        self.thoroughfare = street_address
        self.locality = city
        self.administrative_area = state
        self.postal_code = zip_code
        self.country_name_code = country
    
    def __repr__(self):
        return "<Address('%s', '%s, %s  %s', '%s')>" % (self.thoroughfare, self.locality,
                                                        self.administrative_area, self.postal_code,
                                                        self.country_name_code)

class Gift(Base):
    """
    A gift that appears in the gift shop.
    """
    __tablename__ = 'wg_gift'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('gift_id_seq', optional=True), primary_key=True)
    artist_id = Column(types.Integer, ForeignKey("wg_user.id"), nullable=False)
    image_id = Column(types.Integer, ForeignKey("wg_image.id"))
    name = Column(types.Unicode(64), nullable=False)
    description = Column(types.UnicodeText)
    base_cost = Column(types.Float, default=1.0)
    charity_id = Column(types.Integer, ForeignKey("wg_charity.id"))
    program_id = Column(types.Integer, ForeignKey("wg_program.id"))
    item_limit = Column(types.Integer)
    for_sale = Column(types.Boolean, default=False, nullable=False)
    created = Column(types.TIMESTAMP(), default=now)
    # TODO is_program_fixed Boolean if this can only be given for a specific charity/program
    # TODO is_cost_fixed Boolean if this can only be given at a certain price point
    
    donations = orm.relation("Donation", order_by="desc(Donation.given_date)", backref="gift")
    
    def __init__(self, artist_id, name, for_sale=False):
        self.artist_id = artist_id
        self.name = name
        self.for_sale = for_sale
    
    def __repr__(self):
        return "<Gift(artist<%d>,'%s')>" % (self.artist_id, self.name)

class Image(Base):
    """
    A gift image.
    
    Published gift images are located at images.wegivetofriends.org.
    
    Unpublished gift images and original assets are located at assets.wegivetofriends.org.
    """
    __tablename__ = 'wg_image'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('image_id_seq', optional=True), primary_key=True)
    # e.g. PSD file, Illustrator, etc
    #origin_file = Column(types.String(255))
    #thumbnail = Column(types.String(255))
    #origin_file_type = Column(types.String(32))
    
    def __init__(self):
        pass
    
    def __repr__(self):
        return "<Image(%d)>" % (self.id)

class Donation(Base):
    """
    A donation to a charity, which is also a gift sent from one user to another.
    """
    __tablename__ = 'wg_donation'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('donation_id_seq', optional=True), primary_key=True)
    donor_id = Column(types.Integer, ForeignKey("wg_user.id"), nullable=False)
    recipient_id = Column(types.Integer, ForeignKey("wg_user.id"), nullable=False)
    amount = Column(types.Float, nullable=False)
    gift_id = Column(types.Integer, ForeignKey("wg_gift.id"), nullable=False)
    charity_id = Column(types.Integer, ForeignKey("wg_charity.id"), nullable=False)
    message = Column(types.UnicodeText)
    pending = Column(types.Boolean, default=True)
    #transaction_id = Column(types.Integer, ForeignKey("wg_transaction.id"))
    given_date = Column(types.DateTime, default=now)
    # designation = Column(types.Integer, ForeignKey("program.id"))  # i.e. earmark
    # tracking_code = Column(types.String(64))
    
    transaction = orm.relation("Transaction", uselist=False, backref='donation')
    
    def __init__(self, donor_id, recipient_id, amount, gift_id, charity_id):
        self.donor_id = donor_id
        self.recipient_id = recipient_id
        self.amount = amount
        self.gift_id = gift_id
        self.charity_id = charity_id
        self.pending = True
    
    def __repr__(self):
        return "<Donation(donor<%d>, recipient<%d>, $%.2f)>" % (self.donor_id, self.recipient_id, self.amount)

class Transaction(Base):
    """
    An Amazon Flexible Payments System (FPS) transaction.
    """
    __tablename__ = 'wg_transaction'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(types.Integer, Sequence('transaction_id_seq', optional=True), primary_key=True)
    fps_action = Column(types.String(64), nullable=False)
    donation_id = Column(types.Integer, ForeignKey("wg_donation.id"), nullable=False)
    caller_reference = Column(types.String(128), nullable=False)
    fps_transaction_id = Column(types.String(40))
    fps_transaction_status = Column(types.String(16))
    amount = Column(types.Float)
    recipient_token_id = Column(types.String(128))              # token representing charity
    sender_token_id = Column(types.String(128))                 # token representing donor
    payment_method = Column(types.String(3))                    # CC, ACH, or ABT
    fps_fees = Column(types.Float)                              # amount of fees collected by Amazon FPS for performing the transaction
    created = Column(types.TIMESTAMP(), default=now)
    authorized_date = Column(types.TIMESTAMP())
    last_attempt_date = Column(types.TIMESTAMP())  # last time Pay operation was attempted
    success_date = Column(types.TIMESTAMP())
    # additional details from Amazon FPS
    
    def __init__(self, fps_action, donation_id, caller_reference):
        self.fps_action = fps_action
        self.donation_id = donation_id
        self.caller_reference = caller_reference
    
    def __repr__(self):
        return "<Transaction(donation<%d>, callerRef<%s>)>" % (self.donation_id, self.caller_reference)


## Classes for reflected tables may be defined here, but the table and
## mapping itself must be done in the init_model function
#reflected_table = None
#
#class Reflected(object):
#    pass
