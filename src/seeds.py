from sqlalchemy import func
from models import db, Users, Profiles, Tournaments, Swaps, Flights, Buy_ins, \
    Transactions, Devices, Chats, Messages
from datetime import datetime, timedelta
from utils import sha256
import actions
import pytz


def run():
         
    Messages.query.delete()
    Chats.query.delete()
    Devices.query.delete()
    Transactions.query.delete()
    Buy_ins.query.delete()
    Swaps.query.delete()
    Flights.query.delete()
    Tournaments.query.delete()
    Profiles.query.delete()
    Users.query.delete()

    db.session.execute("ALTER SEQUENCE users_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE buy_ins_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE flights_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE tournaments_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE swaps_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE transactions_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE devices_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE chats_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE messages_id_seq RESTART")

    db.session.commit()


    # LOAD FILES
    # actions.load_tournament_file()

    # latest_trmnt_id = db.session.query( func.max( Tournaments.id)).scalar()
    # db.session.execute(
    #     "ALTER SEQUENCE tournaments_id_seq RESTART WITH " + 
    #     str(latest_trmnt_id + 1) )

    # latest_flight_id = db.session.query( func.max( Flights.id)).scalar()
    # db.session.execute(
    #     "ALTER SEQUENCE flights_id_seq RESTART WITH " +
    #     str(latest_flight_id + 1) )
    
 
    ########################
    #  USERS AND PROFILES
    ########################

    johnDoe = Users(
        email='lou@gmail.com',
        password=sha256('loustadler'),
        status='valid'
    )
    db.session.add(johnDoe)
    johnDoe = Profiles(
        first_name='John', 
        last_name='Doe',
        nickname='',
        hendon_url='',
        # naughty =False,
        profile_pic_url='https://www.hartvillethriftshoppe.org/sites/default/files/styles/basic_page/public/male_silhouette_0_0.jpg?itok=PN7U5Zf3',
        pokersociety_id=1,
        user=johnDoe,
        roi_rating=0.0,
        swap_rating=0.0,
    )
    db.session.add(johnDoe)
    db.session.add( Transactions(
        coins=10,
        user=johnDoe
    ))

    cary = Users(
        email='gherndon5@hotmail.com',
        password=sha256('casper5'),
        status='valid'
    )
    db.session.add(cary)
    cary = Profiles(
        first_name='Cary', 
        last_name='Katz',
        nickname='',
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=26721',
        profile_pic_url='https://pokerdb.thehendonmob.com/pictures/carykatzpic.png',
        pokersociety_id=2,
        user=cary,
        # naughty =False,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(cary)
    db.session.add( Transactions(
        coins=5,
        user=cary
    ))

    gabe = Users(
        email='gherndon5@gmail.com',
        password=sha256('casper5'),
        status='valid'
    )
    db.session.add(gabe)
    gabe = Profiles(
        first_name='Gabriel', 
        last_name='Herndon',
        nickname='',
        hendon_url='',
        profile_pic_url='https://d1we5yax8fyln6.cloudfront.net/sites/stage32.com/files/imagecache/head_shot_500/headshots/3a160ee8689722fd93f3999b10d2b8d9_1428609546_l.jpg',
        pokersociety_id=3,
        user=gabe,
        # naughty =False,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(gabe)
    db.session.add( Transactions(
        coins=5,
        user=gabe
    ))

    lou = Users(
        email='lou@pokersociety.com',
        password=sha256('swaptest'),
        status='valid'
    )
    db.session.add(lou)
    lou = Profiles(
        first_name='Luiz', 
        last_name='Stadler',
        nickname='Lou',
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=207424',
        profile_pic_url='https://pokerdb.thehendonmob.com/pictures/Lou_Stadler_Winner.JPG',
        pokersociety_id=4,
        user=lou,
        # naughty =False,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(lou)
    db.session.add( Transactions(
        coins=5,
        user=lou
    ))

    perry = Users(
        email='perry1830@msn.com',
        password=sha256('Kobe$$'),
        status='valid'
    )
    db.session.add(perry)
    perry = Profiles(
        first_name='Perry', 
        last_name='Shiao',
        nickname='',
        # naughty =False,
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=371190',
        profile_pic_url='https://i.imgur.com/qIq2VPH.jpg',
        pokersociety_id=5,
        user=perry,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(perry)
    db.session.add( Transactions(
        coins=5,
        user=perry
    ))
    
    neal = Users(
        email='neal_corcoran@yahoo.com',
        password=sha256('Brooklyn1'),
        status='valid'
    )
    db.session.add(neal)
    neal = Profiles(
        first_name='Neal', 
        last_name='Corcoran',
        nickname='',
        # naughty =False,
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=506855',
        profile_pic_url='https://i.imgur.com/PYNkNgc.jpg',
        pokersociety_id=6,
        user=neal,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(neal)
    db.session.add( Transactions(
        coins=5,
        user=neal
    ))

    brian = Users(
        email='brooklynbman@yahoo.com',
        password=sha256('Brooklyn1'),
        status='valid'
    )
    db.session.add(brian)
    brian = Profiles(
        first_name='Brian', 
        last_name='Gelrod',
        nickname='',
        # naughty =False,
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=239802',
        profile_pic_url='https://i.imgur.com/1bMetyL.jpg',
        pokersociety_id=7,
        user=brian,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(brian)
    db.session.add( Transactions(
        coins=5,
        user=brian
    ))


    bobby = Users(
        email='leff1117@aol.com',
        password=sha256('eatme'),
        status='valid'
    )
    db.session.add(bobby)
    bobby = Profiles(
        first_name='Bobby', 
        last_name='Leff',
        nickname='',
        # naughty ='nice',
        hendon_url='https://pokerdb.thehendonmob.com/player.php?a=r&n=187837',
        profile_pic_url='https://i.imgur.com/ZMo8UJ8.jpg',
        pokersociety_id=8,
        user=bobby,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(bobby)
    db.session.add( Transactions(
        coins=5,
        user=bobby
    ))
    db.session.flush()

    ########################
    #     TOURNAMENTS
    ########################
    d1 = datetime.utcnow()
    d2 = datetime.utcnow() - timedelta(days=4,hours=18, minutes=0)


    aboutToStart = Tournaments(
        casino='Seminole Hard Rock Hotel & Casino',
        name='About To Start Event',
        address='1 Seminole Way',
        city='Davie',
        state='FL',
        zip_code='33314',
        latitude=26.0510,
        longitude=-80.2097,
        start_at= d1,
        time_zone='Etc/GMT-4'
    )
    db.session.add(aboutToStart)
    aboutToEnd = Tournaments(
        casino='Seminole Hard Rock Hotel & Casino',
        name='About To End Event',
        address='1 Seminole Way',
        city='Davie',
        state='FL',
        zip_code='33314',
        latitude=26.0510,
        longitude=-80.2097,
        start_at= d2,
        time_zone='EST',
    )
    db.session.add(aboutToEnd)

    ########################
    #       FLIGHTS
    ########################

    flight1_start = Flights(
        start_at=aboutToStart.start_at,
        tournament=aboutToStart,
        day=1
    )
    db.session.add(flight1_start)

    flight1_end = Flights(
        start_at=aboutToEnd.start_at,
        tournament=aboutToEnd,
        day=1
    )
    db.session.add(flight1_end)

    db.session.flush()


    ########################
    #        SWAPS
    ########################

    s1 = Swaps(
        tournament=aboutToEnd,
        sender_user=gabe,
        recipient_user=cary,
        percentage=10,
        status='agreed',
    )
    s2 = Swaps(
        tournament=aboutToEnd,
        sender_user=cary,
        recipient_user=gabe,
        percentage=10,
        status='agreed',
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])
    
    s1 = Swaps(
        tournament=aboutToEnd,
        sender_user=gabe,
        recipient_user=cary,
        percentage=2,
        status='agreed',
    )
    s2 = Swaps(
        tournament=aboutToEnd,
        sender_user=cary,
        recipient_user=gabe,
        percentage=3,
        status='agreed',
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])

    s1 = Swaps(
        tournament=aboutToEnd,
        sender_user=gabe,
        recipient_user=cary,
        percentage=2,
        status='canceled',
    )
    s2 = Swaps(
        tournament=aboutToEnd,
        sender_user=cary,
        recipient_user=gabe,
        percentage=3,
        status='canceled',
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])

    ########################
    #       BUY INS
    ########################

    db.session.add(Buy_ins(
        chips=770,
        table='1',
        seat=2,
        user=gabe,
        flight=flight1_start,
        status='active'
    ))
    db.session.add(Buy_ins(
        chips=1600,
        table='14',
        seat=8,
        user=cary,
        flight=flight1_start,
        status='active'
    ))

    db.session.add(Buy_ins(
        chips=770,
        table='1',
        seat=2,
        user=gabe,
        flight=flight1_end,
        status='active'
    ))
    db.session.add(Buy_ins(
        chips=1600,
        table='14',
        seat=8,
        user=cary,
        flight=flight1_end,
        status='active'
    ))

    db.session.flush()

    db.session.commit()


    return