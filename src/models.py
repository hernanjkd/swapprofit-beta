import utils
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, desc
from datetime import datetime, timedelta
import enum
import os

db = SQLAlchemy()

# engine = create_engine( os.environ.get('DATABASE_URL') )
# Session = sessionmaker( bind=engine )
# session = Session()

class UserStatus(enum.Enum):
    valid = 'valid'
    invalid = 'invalid'
    suspended = 'suspended'

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.invalid)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = db.relationship('Profiles', back_populates='user', uselist=False)
    results = db.relationship('Results', back_populates='user')


    def __repr__(self):
        return f'<Users {self.email}>'

    def serialize(self):
        return {
            'id': self.id,
            'email': self.email,
            'status': self.status._value_,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }



class SwapAvailabilityStatus(enum.Enum):
    active = 'active' 
    unavailable = 'unavailable'


class Profiles(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100))
    hendon_url = db.Column(db.String(200))
    profile_pic_url = db.Column(db.String(250), default=None)
    
    roi_rating = db.Column(db.Float, default=0)
    swap_rating = db.Column(db.Float, default=0)
    swap_availability_status = db.Column(db.Enum(SwapAvailabilityStatus), default=SwapAvailabilityStatus.active)
    naughty = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('Users', back_populates='profile', uselist=False)
    buy_ins = db.relationship('Buy_ins', back_populates='user')
    transactions = db.relationship('Transactions', back_populates='user')
    devices = db.relationship('Devices', back_populates='user')
    
    buyin_update = db.Column(db.Boolean, default=True)
    swap_update = db.Column(db.Boolean, default=True)
    event_update = db.Column(db.Boolean, default=True)
    chat_update = db.Column(db.Boolean, default=True)
    coin_update = db.Column(db.Boolean, default=True)
    result_update = db.Column(db.Boolean, default=True)
    
    # sending_swaps
    # receiving_swaps

    def __repr__(self):
        return f'<Profiles {self.first_name} {self.last_name}>'

    def get_name(self):
        quoted_nickname = f'"{self.nickname}"' if self.nickname != '' else ''
        return f'{self.first_name} {quoted_nickname} {self.last_name}'


    def get_coins(self):
        total = 0
        for transaction in self.transactions:
            total += transaction.coins
        return total

    def available_percentage(self, tournament_id):
        status_to_consider = ['agreed','pending','counter_incoming']
        total = 0
        for swap in self.sending_swaps:
            if swap.tournament_id == tournament_id:
                if swap.status._value_ in status_to_consider:
                    total += swap.percentage
        return 50 - total if total <= 50 else 0

    def get_swaps_actions(self, tournament_id):
        status_to_consider = ['agreed','pending','counter_incoming']
        actions = 0
        swaps = 0
        for swap in self.sending_swaps:
            if swap.tournament_id == tournament_id:
                if swap.status._value_ in status_to_consider:
                    actions += swap.percentage
                    swaps += 1
        return {
            'actions': actions,
            'swaps': swaps
        }

    def get_agreed_swaps(self, tournament_id=None):
        if tournament_id:
            return list(filter(
                lambda swap: \
                    swap.tournament_id == tournament_id and \
                    swap.status._value_ == 'agreed'
                , self.sending_swaps ))
        return list(filter(
            lambda swap: swap.status._value_ == 'agreed',
            self.sending_swaps ))

    def get_confirmed_swaps(self, tournament_id=None):
        if tournament_id:
            return list(filter(
                lambda swap: \
                    swap.tournament_id == tournament_id and \
                    swap.status._value_ == 'agreed' and \
                    swap.confirmed == True
                , self.sending_swaps ))
        return list(filter(
            lambda swap: swap.status._value_ == 'agreed' and swap.confirmed == True,
            self.sending_swaps ))

    def calculate_roi_rating(self):
        total_swaps = 0
        winning_swaps = 0
        for swap in self.sending_swaps:
            if swap.status._value_ == 'agreed' and swap.result_winnings != None:
                total_swaps += 1
            if swap.result_winnings is True:
                winning_swaps += 1
        if total_swaps == 0:
            return 0
        return winning_swaps / total_swaps * 100

    def calculate_swap_rating(self):
        swaps = Swaps.query \
            .filter_by( sender_id=self.id ) \
            .filter( Swaps.due_at != None ) \
            .filter_by( confirmed = True)
        total_swap_ratings = 0
        for swap in swaps:
            print("SWAP", swap.swap_rating)
            total_swap_ratings += swap.swap_rating
        return total_swap_ratings / swaps.count()

    # swaps that need coin reservation: pending, incoming, counter_incoming
    def get_reserved_coins(self):
        status_to_consider = ['pending','incoming','counter_incoming']
        reserved_coins = 0
        for swap in self.sending_swaps:
            if swap.status._value_ in status_to_consider:
                reserved_coins += swap.cost
        print('reserved_coins',reserved_coins)
        return reserved_coins        

    def serialize(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'nickname': self.nickname,
            'email': self.user.email,
            'profile_pic_url': self.profile_pic_url,
            'hendon_url': self.hendon_url,
            'total_swaps': len( self.get_confirmed_swaps() ),
            'roi_rating': self.roi_rating,
            'swap_rating': self.swap_rating,
            'coins': self.get_coins() - self.get_reserved_coins(),
            'swap_availability_status': self.swap_availability_status._value_,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'naughty': self.naughty,
            'coin_update': self.coin_update,
            'swap_update': self.swap_update,
            'buyin_update': self.buyin_update,
            'chat_update': self.chat_update,
            'event_update': self.event_update,
            'result_update': self.result_update,
            'transactions': [x.serialize() for x in self.transactions],
            'devices': [x.serialize() for x in self.devices]
        }



class SwapStatus(enum.Enum):
    agreed = 'agreed'
    pending = 'pending'
    incoming = 'incoming'
    rejected = 'rejected'
    canceled = 'canceled'
    counter_incoming = 'counter_incoming'

class Swaps(db.Model):
    __tablename__ = 'swaps'
    id = db.Column(db.Integer, primary_key=True)
    counter_swap_id = db.Column(db.Integer, db.ForeignKey('swaps.id'))
    sender_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'))
    percentage = db.Column(db.Integer, nullable=False)
    due_at = db.Column(db.DateTime, default=None)
    
    paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.DateTime, default=None)
    confirmed = db.Column(db.Boolean, default=False)
    confirmed_at = db.Column(db.DateTime, default=None)
    disputed = db.Column(db.Boolean, default=False)
    disputed_at = db.Column(db.DateTime, default=None)
    
    swap_rating = db.Column(db.Integer)
    result_winnings = db.Column(db.Boolean, default=None)
    cost = db.Column(db.Integer, default=1)
    status = db.Column(db.Enum(SwapStatus), default=SwapStatus.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tournament = db.relationship('Tournaments', back_populates='swaps')
    sender_user = db.relationship('Profiles', foreign_keys=[sender_id], backref='sending_swaps')
    recipient_user = db.relationship('Profiles', foreign_keys=[recipient_id], backref='receiving_swaps')
    counter_swap = db.relationship('Swaps', remote_side=[id], post_update=True, uselist=False,
                                            backref='counter_swap2')

    def __repr__(self):
        return (f'<Swaps sender_email:{self.sender_user.user.email} ' 
            + f'recipient_email:{self.recipient_user.user.email} '
            + f'tournament:{self.tournament.name}>')

    @staticmethod
    def counter_status(status):
        switch = {
            'incoming': 'pending',
            'counter_incoming': 'pending',
            'pending': 'counter_incoming' }
        return switch.get(status, status)

    def serialize(self):
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'percentage': self.percentage,
            'due_at': self.due_at,
            'status': self.status._value_,
            'sender_user': self.sender_user.serialize(),
            'recipient_user': self.recipient_user.serialize(),
            'paid': self.paid,
            'paid_at': self.paid_at,
            'confirmed': self.confirmed,
            'confirmed_at': self.confirmed_at,
            'disputed': self.disputed,
            'disputed': self.disputed_at,
            'cost': self.cost,
            'counter_swap_id': self.counter_swap_id,
            'counter_percentage': self.counter_swap.percentage,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class Casinos(db.Model):
    __tablename__ = 'casinos'
    id = db.Column(db.String(10), primary_key=True, nullable=False)
    name = db.Column(db.String(500), nullable=False)
    address = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(20))
    zip_code = db.Column(db.String(14))
    longitude = db.Column(db.Float)
    latitude = db.Column(db.Float)
    time_zone = db.Column(db.String(50))
    website = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    facebook = db.Column(db.String(50))
    twitter = db.Column(db.String(50))
    instagram = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournaments = db.relationship('Tournaments', back_populates='casino')

    def __repr__(self):
        return f'<Casino {self.name} {self.city}, {self.state}>'

    def getTimeZoneName(self):
        time_zone_name = ''
        print('Time Zone', self.time_zone)

        if(self.time_zone){

        }elif(self.time_zone){

        }elif(self.time_zone){

        }elif(self.time_zone){

        }

        print('time_zone_name', time_zone_name)
        return time_zone_name 


    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'time_zone': self.time_zone,
            'website': self.website,
            'phone': self.phone,
            'facebook': self.facebook,
            'twitter': self.twitter,
            'instagram': self.instagram,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            # 'time_zone_name': self.getTimeZoneName()
        }

    def serialize_simple(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'longitude': self.longitude,
            'latitude': self.latitude,
            'time_zone': self.time_zone,
            # 'time_zone_name': self.getTimeZoneName()
        }


class TournamentStatus(enum.Enum):
    open = 'open'
    closed = 'closed'
    waiting_results = 'waiting_results'

class Tournaments(db.Model):
    __tablename__ = 'tournaments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    start_at = db.Column(db.DateTime)
    results_link = db.Column(db.String(256), default=None)
    structure_link = db.Column(db.String(500))
    blinds = db.Column(db.String(20))
    buy_in_amount = db.Column(db.String(20))
    starting_stack = db.Column(db.String(20))


    status = db.Column(db.Enum(TournamentStatus), default=TournamentStatus.open)
    casino_id = db.Column(db.String, db.ForeignKey('casinos.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    casino = db.relationship('Casinos', back_populates='tournaments')
    flights = db.relationship('Flights', back_populates='tournament')
    swaps = db.relationship('Swaps', back_populates='tournament')
    results = db.relationship('Results', back_populates='tournament')


    def __repr__(self):
        return f'<Tournament {self.id} {self.name}>'

    @staticmethod
    def get_live_upcoming(user_id=False):
        close_time = utils.designated_trmnt_close_time()
        trmnts = Tournaments.query \
                    .filter( Tournaments.flights.any(
                        Flights.start_at > close_time ))
        if user_id:
            trmnts =  trmnts.filter( Tournaments.flights.any( 
                    Flights.buy_ins.any( user_id = user_id ))) \
                .order_by( Tournaments.start_at.asc() )

        return trmnts if trmnts.count() > 0 else None

    @staticmethod
    def get_history(user_id=False):
        close_time = utils.designated_trmnt_close_time()
                        # db.not_( Flights.start_at > close_time ))) \
        # print('close time', close_time)

        trmnts = Tournaments.query \
                    .filter( Tournaments.flights.any(Flights.start_at < close_time )) \
                    .order_by( Tournaments.start_at.desc() )
        # for trmnt in trmnts:
        #     print("YOU WERE IN HERE", trmnt)
        if user_id:
            trmnts = trmnts.filter( Tournaments.flights.any( 
                            Flights.buy_ins.any( user_id = user_id )))
                        
        return trmnts if trmnts.count() > 0 else None
    
    def get_all_users_latest_buyins(self):
        all_buyins = Buy_ins.query.filter( 
                        Buy_ins.flight.has( 
                            Flights.tournament_id == self.id ))
        user_ids = []
        buyins = []
        for buyin in all_buyins:
            user_id = buyin.user_id
            # Users may have multiple buy_ins in one tournament
            if user_id not in user_ids:
                user_ids.append( user_id )
                ueser = db.session.query(Buy_ins) \
                    .filter( Buy_ins.flight.has( tournament_id=self.id )) \
                    .filter( Buy_ins.user_id==user_id ) \
                    .order_by( Buy_ins.id.desc() ).first().serialize()
                buyins.append( ueser )
        return buyins
        
    def get_local_start_time(self):
        self.start_at

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'start_at': self.start_at,
            'casino': self.casino.serialize(),
            'buy_in_amount': self.buy_in_amount,
            'blinds': self.blinds,
            'starting_stack': self.starting_stack,
            'results_link': self.results_link,
            'structure_link': self.structure_link,
            'tournament_status': self.status._value_,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'flights': [x.serialize() for x in self.flights],
            'swaps': [x.serialize() for x in self.swaps],
            'buy_ins': self.get_all_users_latest_buyins()
        }

    def serialize_simple(self):
        return {
            'id': self.id,
            'name': self.name,
            'casino': self.casino.simple_serialize(),
            'start_at': self.start_at,
            'results_link': self.results_link,
            'tournament_status': self.status._value_,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'flights': [x.serialize() for x in self.flights],
            'swaps': [x.serialize() for x in self.swaps],
        }



class Flights(db.Model):
    __tablename__ = 'flights'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'))
    start_at = db.Column(db.DateTime)
    day = db.Column(db.String(5), default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournament = db.relationship('Tournaments', back_populates='flights')
    buy_ins = db.relationship('Buy_ins', back_populates='flight')

    def __repr__(self):
        return f'<Flights tournament_id:{self.tournament_id} day:{self.day}>'

    @staticmethod
    def get(history, user_id=False):
        close_time = utils.designated_trmnt_close_time()
        condition = Flights.start_at < close_time if history == True \
                else Flights.start_at > close_time
        flights = Flights.query.filter( condition )
        if user_id:
            flights = flights.filter( Flights.buy_ins.any( user_id=user_id ) )
        return flights if flights.count() > 0 else None

    def serialize(self):
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'tournament': self.tournament.name,
            'start_at': self.start_at,
            'day': self.day,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }



class BuyinStatus(enum.Enum):
    active = 'active'
    busted = 'busted'
    cashed = 'cashed'
    bagged = 'bagged'
    pending = 'pending'

class Buy_ins(db.Model):
    __tablename__ = 'buy_ins'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'))
    receipt_img_url = db.Column(db.String(250))
    chips = db.Column(db.Integer)
    table = db.Column(db.String(20))
    seat = db.Column(db.Integer)
    place = db.Column(db.String(6), default=None)
    winnings = db.Column(db.String(30), default=None)
    player_name = db.Column(db.String(50))
    status = db.Column(db.Enum(BuyinStatus), default=BuyinStatus.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('Profiles', back_populates='buy_ins')
    flight = db.relationship('Flights', back_populates='buy_ins')

    def __repr__(self):
        return f'<Buy_ins id:{self.id} user:{self.user_id} flight:{self.flight_id}>'

    @staticmethod
    def get_latest(user_id, tournament_id):
        # print('user_id', user_id)
        # print('tournament_id', tournament_id)
        latest_buyin = db.session.query(Buy_ins) \
            .filter( Buy_ins.flight.has( tournament_id=tournament_id )) \
            .filter( Buy_ins.user_id==user_id ) \
            .order_by( Buy_ins.id.desc() ).first()
        return latest_buyin
        # print('plz', Buy_ins.query.filter( Buy_ins.user_id==user_id ))
        # return ( __self__.query.get( user_id )
        #     .filter( Buy_ins.flight.has( tournament_id=tournament_id ))
        #     .filter( Buy_ins.user_id==user_id )
        #     .order_by( Buy_ins.id.desc() ).first() )

    def serialize(self):
        u = self.user
        return {
            'id': self.id,
            'user_id': self.user_id,
            'flight_id': self.flight_id,
            'tournament_id': self.flight.tournament_id,
            'place': self.place,
            'chips': self.chips,
            'table': self.table,
            'seat': self.seat,
            'winnings': self.winnings,
            'receipt_img_url': self.receipt_img_url,
            'player_name': self.player_name,
            'status': self.status._value_,
            'user_name': f'{u.first_name} {u.last_name}',
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class Results(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    full_name = db.Column(db.String(40))
    place = db.Column(db.String(6))
    winnings = db.Column(db.String(30), default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tournament = db.relationship('Tournaments', back_populates='results')
    user = db.relationship('Users', back_populates='results')

    def __repr__(self):
        return f'<Results id:{self.id}>'

    def serialize(self):
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'place': self.place,
            'winnings': self.winnings,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }



class Transactions(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    coins = db.Column(db.Integer, nullable=False)
    dollars = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('Profiles', back_populates='transactions')

    def __repr__(self):
        return f'<Transactions user:{self.user.email} coins:{self.coins} dollars:{self.dollars}>'

    def serialize(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'coins': self.coins,
            'dollars': self.dollars,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }



class Devices(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    token = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('Profiles', back_populates='devices')

    def __repr__(self):
        return f'<Devices id:{self.id} user_email:{self.user.email}>'

    def serialize(self):
        return {
            'id': self.id,
            'token': self.token,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }



class ChatStatus(enum.Enum):
    opened = 'opened'
    closed = 'closed'

class Chats(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    user2_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    status = db.Column(db.Enum(ChatStatus), default=ChatStatus.opened)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('Messages', back_populates='chat')
    user1 = db.relationship('Profiles', foreign_keys=[user1_id], backref='chats1')
    user2 = db.relationship('Profiles', foreign_keys=[user2_id], backref='chats2')

    def __init__(self, user1_id, user2_id):
        if user1_id == user2_id:
            raise utils.APIException('user1 and user2 must be different users', 400)

        user2 = Users.query.get( user2_id )
        if user2 is None:
            raise utils.APIException('User2 not found', 404)
        self.user1_id = user1_id
        self.user2_id = user2_id

    def __repr__(self):
        return f'<Chats user1={self.user1_id} user2={self.user2_id}>'

    @staticmethod
    def get(user1_id, user2_id):
        chatjson = lambda flip=False: {
            'user1_id': user1_id if flip else user2_id,
            'user2_id': user2_id if flip else user1_id }
        return Chats.query.filter_by( **chatjson() ).first() or \
               Chats.query.filter_by( **chatjson(flip=True) ).first()

    @staticmethod
    def getMine(user1_id):
        chatjson = lambda flip=False: {
            'user1_id': user1_id }
        return Chats.query.filter_by( **chatjson() )

    def serialize(self):
        the_last_message = [x.serialize() for x in self.messages]
        w = the_last_message[-1]['updated_at']
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'status': self.status._value_,
            'created_at': self.created_at,
            'updated_at': w,
            'messages': [x.serialize() for x in self.messages]
        }
    def serialize2(self):

        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'status': self.status._value_,
            'created_at': self.created_at,
            'updated_at':  self.updated_at,
            'messages': [x.serialize() for x in self.messages]

        }
    def serialize3(self):
        the_last_message = [x.serialize() for x in self.messages]
        w = the_last_message[-1]['updated_at']
        return {
            'id': self.id,
            'user1_id': self.user1_id,
            'user2_id': self.user2_id,
            'status': self.status._value_,
            'created_at': self.created_at,
            'updated_at': w,
            'last_message': the_last_message[-1]
        }

class Messages(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id'))
    user_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chat = db.relationship('Chats', back_populates='messages')

    def __init__(self, chat_id, user_id, message):
        chat = Chats.query.get( chat_id )
        if chat is None:
            raise utils.APIException('Chat not found', 404)
        if chat.status._value_ == 'closed':
            raise utils.APIException('This chat is closed', 400)
        if user_id not in [ chat.user1_id, chat.user2_id ]:
            raise utils.APIException('User not in chat', 400)
        if message == '':
            raise utils.APIException("Message can't be empty", 400)
        self.chat_id = chat_id
        self.user_id = user_id
        self.message = message

    def __repr__(self):
        return f'<Messages id={self.id} chat={self.chat_id} user={self.user_id}>'

    def serialize(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'user_id': self.user_id,
            'message': self.message,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }