from sqlalchemy import func
from models import db, Users, Profiles, Tournaments, Swaps, Flights, Buy_ins, \
    Transactions, Devices, Chats, Messages, Casinos, Results
from datetime import datetime, timedelta
from utils import sha256
import actions
import pytz


def run():
    Results.query.delete()
    Chats.query.delete()
    Devices.query.delete()
    Transactions.query.delete()
    Buy_ins.query.delete()
    Swaps.query.delete()
    Flights.query.delete()
    Tournaments.query.delete()
    Casinos.query.delete()
    Messages.query.delete()

    Profiles.query.delete()
    # Users.query.delete()

    # db.session.execute("ALTER SEQUENCE casinos_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE results_id_seq RESTART")
    # db.session.execute("ALTER SEQUENCE casinos RESTART")
    # db.session.execute("ALTER SEQUENCE users_id_seq RESTART")

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
        email='lou@gsmail.com',
        password=sha256('loustadsler'),
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
        email='techpriest.gabriel@gmail.com',
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

    # d1 = datetime.utcnow()
    # d2 = datetime.utcnow() - timedelta(hours=16, minutes=59)

    # exampleCasino = Casinos(
    #     id='USFL001',
    #     name='Seminole Hard Rock Hotel & Casino',
    #     address='1 Seminole Way',
    #     city='Davie',
    #     state='FL',
    #     zip_code='33314',
    #     latitude=26.0510,
    #     longitude=-80.2097,
    #     time_zone='Etc/GMT-4'
    # )
    # db.session.add(exampleCasino)
    # exampleStart = Tournaments(
    #     name='Example Start Event', 
    #     casino = exampleCasino,
    #     start_at=d1
    # )
    # db.session.add(exampleStart)

    # exampleEnd = Tournaments(
    #     name='Example End Event',
    #     casino = exampleCasino,
    #     start_at=d2
    # )
    # db.session.add(exampleEnd)

    # flight1_start = Flights(
    #     start_at=exampleStart.start_at,
    #     tournament=exampleStart,
    #     day=1
    # )
    # db.session.add(flight1_start)

    # flight1_end = Flights(
    #     start_at=exampleEnd.start_at,
    #     tournament=exampleEnd,
    #     day=1
    # )
    # db.session.add(flight1_end)


    db.session.flush()


    db.session.commit()


    return