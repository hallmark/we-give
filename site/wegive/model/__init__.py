"""The application's model objects"""
import sqlalchemy as sa
from sqlalchemy import orm, schema, Column, Sequence, ForeignKey
from sqlalchemy import Integer, Float, String, Unicode, UnicodeText, DateTime, TIMESTAMP, Boolean
from sqlalchemy.databases.mysql import MSBigInteger
import datetime

from wegive.model import meta

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    ## Reflected tables must be defined and mapped here
    #global reflected_table
    #reflected_table = sa.Table("Reflected", meta.metadata, autoload=True,
    #                           autoload_with=engine)
    #orm.mapper(Reflected, reflected_table)

    sm = orm.sessionmaker(autoflush=True, autocommit=False, bind=engine)

    meta.engine = engine
    meta.Session = orm.scoped_session(sm)


def now():
    return datetime.datetime.now()

## Non-reflected tables may be defined and mapped at module level
#foo_table = sa.Table("Foo", meta.metadata,
#    sa.Column("id", sa.types.Integer, primary_key=True),
#    sa.Column("bar", sa.types.String(255), nullable=False),
#    )
#
#class Foo(object):
#    pass
#
#orm.mapper(Foo, foo_table)

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
    __tablename__ = 'user'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('user_id_seq', optional=True), primary_key=True)
    email = Column(Unicode(255), nullable=False, unique=True)
    password = Column(String(50), nullable=False)
    first_name = Column(Unicode(64))
    last_name = Column(Unicode(64))
    address_id = Column(Integer, ForeignKey("address.id"))
    created = Column(TIMESTAMP(), default=now)
    
    # locale?
    # timezone?
    
    # TODO: this is temporary.  Should be moved to a UserMapping or UserPersona table
    # NOTE: Facebook User IDs:
    # The user ID is a 64-bit int datatype. If you're storing it in a MySQL database, use the BIGINT unsigned datatype
    facebook_uid = Column(MSBigInteger(unsigned=True))
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
    
    def __repr__(self):
        return "<User('%s')>" % (self.email)

class UserPersona(Base):
    """
    A user's representation on a specific social network.
    
    Needs to handle a super-set of all info to store from the various networks.
    """
    __tablename__ = 'userpersona'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('userpersona_id_seq', optional=True), primary_key=True)
    
    # the base mapping info (userID, networkID, network-userID)
    wg_user_id = Column(Integer, ForeignKey("user.id"))
    network_id = Column(Integer, ForeignKey("network.id"))
    network_user_id = Column(MSBigInteger(unsigned=True))
    created = Column(TIMESTAMP(), default=now)
    # TODO: uniqueness constraint on [network_id, network_user_id]
    # TODO: uniqueness constraint on [wg_user_id, network_id]
    
    # whether the user has added/authorized the We Give app
    added_wg = Column(Boolean, default=False)
    
    # the proxied email address (Facebook)
    proxied_email = Column(Unicode(255))
    
    def __repr__(self):
        return "<UserPersona(%d on network<%d>)>" % (self.wg_user_id, network_id)

class SocialNetwork(Base):
    __tablename__ = 'network'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('network_id_seq', optional=True), primary_key=True)
    name = Column(Unicode(255), nullable=False)
    url = Column(Unicode(255))
    
    def __repr__(self):
        return "<SocialNetwork(%s)>" % (self.name)

class Charity(Base):
    __tablename__ = 'charity'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('charity_id_seq', optional=True), primary_key=True)
    name = Column(Unicode(255), nullable=False)
    address_id = Column(Integer, ForeignKey("address.id"))
    url = Column(Unicode(255))
    short_code = Column(String(10), nullable=False)
    created = Column(TIMESTAMP(), default=now)
    
    def __init__(self, name, short_code):
        self.name = name
        self.short_code = short_code
    
    def __repr__(self):
        return "<Charity(%s)>" % (self.name)

class Program(Base):
    __tablename__ = 'program'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('program_id_seq', optional=True), primary_key=True)
    name = Column(Unicode(255), nullable=False)
    description = Column(UnicodeText)
    charity_id = Column(Integer, ForeignKey("charity.id"))
    url = Column(Unicode(255))
    created = Column(TIMESTAMP(), default=now)
    
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
    __tablename__ = 'address'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('address_id_seq', optional=True), primary_key=True)
    # street address
    thoroughfare = Column(Unicode(255))
    address_line_2 = Column(Unicode(255))
    address_line_3 = Column(Unicode(255))
    # e.g., company, university, big building, hospital
    premises = Column(Unicode(255))
    # city, town
    locality = Column(Unicode(255))
    # zip code
    postal_code = Column(Unicode(64))
    rural_delivery = Column(Unicode(255))
    # PO Box
    postal_delivery_point = Column(Unicode(64))
    # state, province, prefecture (region for vCards)
    administrative_area = Column(Unicode(255))
    # county
    sub_administrative_area = Column(Unicode(255))
    # ISO 3166-1: two letter country codes
    country_name_code = Column(String(2))
    
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
    __tablename__ = 'gift'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('gift_id_seq', optional=True), primary_key=True)
    artist_id = Column(Integer, ForeignKey("user.id"))
    image_id = Column(Integer, ForeignKey("image.id"))
    name = Column(Unicode(64), nullable=False)
    description = Column(UnicodeText)
    base_cost = Column(Float, default=1.0)
    charity_id = Column(Integer, ForeignKey("charity.id"))
    program_id = Column(Integer, ForeignKey("program.id"))
    item_limit = Column(Integer)
    for_sale = Column(Boolean, default=False)
    created = Column(TIMESTAMP(), default=now)
    # TODO is_program_fixed Boolean if this can only be given for a specific charity/program
    # TODO is_cost_fixed Boolean if this can only be given at a certain price point
    
    def __init__(self, artist_id, name, for_sale=False):
        self.artist_id = artist_id
        self.name = name
        self.for_sale = for_sale
    
    def __repr__(self):
        return "<Gift(artist<%d>,'%s')>" % (self.artist_id, self.name)

class Image(Base):
    __tablename__ = 'image'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('image_id_seq', optional=True), primary_key=True)
    # e.g. PSD file, Illustrator, etc
    #origin_file = Column(String(255))
    #thumbnail = Column(String(255))
    #origin_file_type = Column(String(32))
    
    def __init__(self):
        pass
    
    def __repr__(self):
        return "<Image(%d)>" % (self.id)

class Donation(Base):
    """
    A donation to a charity, which is also a gift sent from one user to another.
    """
    __tablename__ = 'donation'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('donation_id_seq', optional=True), primary_key=True)
    donor_id = Column(Integer, ForeignKey("user.id"))
    recipient_id = Column(Integer, ForeignKey("user.id"))
    amount = Column(Float)
    gift_id = Column(Integer, ForeignKey("gift.id"), nullable=False)
    charity_id = Column(Integer, ForeignKey("charity.id"), nullable=False)
    message = Column(UnicodeText)
    transaction_id = Column(Integer, ForeignKey("transaction.id"))
    given_date = Column(DateTime, default=now)
    # earmark = Column(Integer, ForeignKey("program.id"))  # TODO: call these designations instead?
    # tracking_code = Column(String(64))
    
    def __init__(self, donor_id, recipient_id, amount, gift_id, charity_id):
        self.donor_id = donor_id
        self.recipient_id = recipient_id
        self.amount = amount
        self.gift_id = gift_id
        self.charity_id = charity_id
    
    def __repr__(self):
        return "<Donation(donor<%d>, recipient<%d>, $%.2f)>" % (self.donor_id, self.recipient_id, self.amount)

class Transaction(Base):
    __tablename__ = 'transaction'
    __table_args__ = {'mysql_engine':'InnoDB'}
    
    id = Column(Integer, Sequence('transaction_id_seq', optional=True), primary_key=True)
    date = Column(TIMESTAMP(), default=now)
    amount = Column(Float)
    # additional details from Amazon FPS
    
    def __init__(self):
        pass
    
    def __repr__(self):
        return "<Transaction()>"


## Classes for reflected tables may be defined here, but the table and
## mapping itself must be done in the init_model function
#reflected_table = None
#
#class Reflected(object):
#    pass
