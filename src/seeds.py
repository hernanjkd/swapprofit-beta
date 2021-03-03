from sqlalchemy import func
from models import db, Users, Profiles, Tournaments, Swaps, Flights, Buy_ins, \
    Transactions, Devices, Chats, Messages, Casinos, Results
from datetime import datetime, timedelta
from utils import sha256
import actions
import pytz


def run():
    Transactions.query.delete()

    
    Results.query.delete()
    Chats.query.delete()
    Devices.query.delete()
    Buy_ins.query.delete()
    Swaps.query.delete()
    Flights.query.delete()
    Tournaments.query.delete()
    Casinos.query.delete()
    Messages.query.delete()
    Profiles.query.delete()
    Users.query.delete()


    # db.session.execute("ALTER SEQUENCE casinos_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE results_id_seq RESTART")
    # db.session.execute("ALTER SEQUENCE casinos RESTART")
    db.session.execute("ALTER SEQUENCE users_id_seq RESTART")

    db.session.execute("ALTER SEQUENCE buy_ins_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE flights_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE tournaments_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE swaps_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE transactions_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE devices_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE chats_id_seq RESTART")
    db.session.execute("ALTER SEQUENCE messages_id_seq RESTART")


    # db.session.commit()


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


    d0 = datetime.utcnow() - timedelta(hours=17, minutes=1)
    d1 = datetime.utcnow() + timedelta(minutes=5)
    d2 = datetime.utcnow() - timedelta(hours=16, minutes=59)
    d3 = datetime.utcnow() + timedelta(days=300)
    d4 = datetime.utcnow() + timedelta(days=301)

    oneCasino= Casinos(
        id='USFL001',
        name='Seminole Hard Rock Hotel & Casino',
        address='1 Seminole Way',
        city='Davie',
        state='FL',
        zip_code='33314',
        latitude=26.0510,
        longitude=-80.2097,
        time_zone='America/New_York',
    )
    db.session.add(oneCasino)
    

    # Demo Past Tournament
    past = Tournaments(
        casino=oneCasino,
        name='Past Demo Event #1',
        start_at= d0,
        buy_in_amount=100, 
        results_link='lol',
    )
    db.session.add(past)
    flight1_past = Flights(
        start_at=past.start_at,
        tournament=past,
    )
    db.session.add(flight1_past)
 


    # Apple Demo Tournament and Flights
    demo1 = Tournaments(
        casino=oneCasino,
        name="Apple Demo Event '22",
        start_at= d3,
        buy_in_amount=100
    )
    db.session.add(demo1)
    flight1_demo1 = Flights(
        start_at=demo1.start_at,
        tournament=demo1,
        day='1A'
    )
    db.session.add(flight1_demo1)
    flight2_demo1 = Flights(
        start_at=demo1.start_at + timedelta(hours=6),
        tournament=demo1,
        day='1B'
    )
    db.session.add(flight2_demo1)


    # Android Demo Tournament and Flights
    demo2 = Tournaments(
        casino=oneCasino,
        name="Android Demo Event '22",
        start_at= d4,
        buy_in_amount=100
    )
    db.session.add(demo2)
    flight1_demo2 = Flights(
        start_at=demo2.start_at,
        tournament=demo2,
        day='1A'
    )
    db.session.add(flight1_demo2)
    flight2_demo2 = Flights(
        start_at=demo2.start_at + timedelta(hours=6),
        tournament=demo2,
        day="1B"
    )
    db.session.add(flight2_demo2)



    ########################
    #  USERS AND PROFILES
    ########################

    # MY ADMIN ACCOUNT
    gabe = Users(
        id=1,
        email='techpriest.gabriel@gmail.com',
        password=sha256('casper5'),
        status='valid'
    )
    db.session.add(gabe)
    gabe = Profiles(
        id=1,
        first_name='Gabriel', 
        last_name='Herndon',
        nickname='',
        hendon_url=None,
        profile_pic_url='https://d1we5yax8fyln6.cloudfront.net/sites/stage32.com/files/imagecache/head_shot_500/headshots/3a160ee8689722fd93f3999b10d2b8d9_1428609546_l.jpg',
        user=gabe,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(gabe)
    db.session.add( Transactions(
        coins=5,
        user=gabe
    ))
    
    
    # TEST ACCOUNT 1
    alice = Users(
        id=2,
        email='gherndon5@hotmail.com',
        password=sha256('Casper5!'),
        status='valid'
    )
    db.session.add(alice)
    alice = Profiles(
        id=2,
        first_name='Allison', 
        last_name='Avery',
        nickname='Alice',
        user=alice,
        profile_pic_url='https://media.heartlandtv.com/images/Alice1.PNG',
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(alice)
    db.session.add( Transactions(
        coins=5,
        user=alice
    ))

    # TEST ACCOUNT 1 - BUY INS

    a_buyinPast = Buy_ins(
        status='active',
        # tournament_id = past.id,
        chips = 1000,
        table = 5,
        seat = 10,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = alice,
        flight = flight1_past,
        place='3rd',
        winnings=5000
    )
    db.session.add(a_buyinPast)
    
    a_buyin1 = Buy_ins(
        status='active',
        # tournament_id = demo1.id,
        chips = 15000,
        table = 7,
        seat = 4,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = alice,
        flight = flight1_demo1
    )
    db.session.add(a_buyin1)

    a_buyin2 = Buy_ins(
        status='active',
        # tournament_id = demo2.id,
        chips = 15000,
        table = 7,
        seat = 4,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = alice,
        flight = flight1_demo2
    )
    db.session.add(a_buyin2)


    # TEST ACCOUNT 2
    bob = Users(
        id=3,
        email='cuckookazoo5@gmail.com',
        password=sha256('Casper5!'),
        status='valid'
    )
    db.session.add(bob)
    bob = Profiles(
        id=3,
        first_name='Bobert', 
        last_name='Benderson',
        nickname='Bob',
        profile_pic_url='https://www.bobross.com/content/bob_ross_img.png',
        user=bob,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(bob)
    db.session.add( Transactions(
        coins=5,
        user=bob
    ))

    # TEST ACCOUNT 2 - BUY INS
    b_buyinPast = Buy_ins(
        status='active',
        # tournament_id = past.id,
        chips = 10000,
        table = 15,
        seat = 6,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = bob,
        flight = flight1_past,
        place='4th',
        winnings=3000
    )
    db.session.add(b_buyinPast)

    b_buyin1 = Buy_ins(
        status='active',

        # tournament_id = demo1.id,
        chips = 12000,
        table = 9,
        seat = 3,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = bob,
        flight = flight2_demo1
    )
    db.session.add(b_buyin1)

    b_buyin2 = Buy_ins(
        status='active',
        # tournament_id = demo2.id,
        chips = 12000,
        table = 9,
        seat = 3,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = bob,
        flight = flight2_demo2
    )
    db.session.add(b_buyin2)


    # APPLE TEST ACCOUNT
    apple = Users(
        id=4,
        email='swapprofit.test.apple@gmail.com',
        password=sha256('AppleTest07?'),
        status='valid'
    )
    db.session.add(apple)
    apple = Profiles(
        id=4,
        first_name='Apple',
        last_name='Demo Account',
        nickname='',
        hendon_url=None,
        profile_pic_url='https://www.macworld.co.uk/cmsdata/features/3793151/apple_logo_thumb800.jpg',
        user=apple,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(apple)
    db.session.add( Transactions(
        coins=5,
        user=apple
    ))

    # APPLE TEST ACCOUNT - BUYINS
    app_buyinPast = Buy_ins(
        status='active',
        # tournament_id = past.id,
        chips = 3000,
        table = 2,
        seat = 1,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = apple,
        flight = flight1_past,
        place='6th',
        winnings=500
    )
    db.session.add(app_buyinPast)

    app_buyin1 = Buy_ins(
        status='active',
        # tournament_id = demo1.id,
        chips = 10000,
        table = 17,
        seat = 2,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = apple,
        flight = flight1_demo1
    )
    db.session.add(app_buyin1)

 ########## APPLE PAST TOURNAMENT ###########


    s1 = Swaps(
        tournament=past,
        sender_user=apple,
        recipient_user=alice,
        percentage=10,
        status='agreed',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=alice,
        recipient_user=apple,
        percentage=10,
        status='agreed',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])
  

    s1 = Swaps(
        tournament=past,
        sender_user=apple,
        recipient_user=alice,
        percentage=5,
        status='canceled',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=alice,
        recipient_user=apple,
        percentage=7,
        status='canceled',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])



    s1 = Swaps(
        tournament=past,
        sender_user=apple,
        recipient_user=bob,
        percentage=6,
        status='rejected',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=bob,
        recipient_user=apple,
        percentage=21,
        status='rejected',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])





    ########## APPLE CURRENT TOURNAMENT ###########

    s1 = Swaps(
        tournament=demo1,
        sender_user=apple,
        recipient_user=alice,
        percentage=5,
        status='pending',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo1,
        sender_user=alice,
        recipient_user=apple,
        percentage=7,
        status='incoming',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])

    s1 = Swaps(
        tournament=demo1,
        sender_user=apple,
        recipient_user=alice,
        percentage=5,
        status='agreed',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo1,
        sender_user=alice,
        recipient_user=apple,
        percentage=7,
        status='agreed',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])
  

    s1 = Swaps(
        tournament=demo1,
        sender_user=apple,
        recipient_user=alice,
        percentage=15,
        status='canceled',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo1,
        sender_user=alice,
        recipient_user=apple,
        percentage=17,
        status='canceled',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])



    s1 = Swaps(
        tournament=demo1,
        sender_user=apple,
        recipient_user=bob,
        percentage=6,
        status='rejected',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo1,
        sender_user=bob,
        recipient_user=apple,
        percentage=21,
        status='rejected',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])

  


    # ANDORID TEST ACCOUNT
    android = Users(
        id=5,
        email='swapprofit.test.and@gmail.com',
        password=sha256('AndroidTest08?'),
        status='valid'
    )
    db.session.add(android)
    android = Profiles(
        id=5,
        first_name='Android', 
        last_name='Demo Account',
        nickname='',
        hendon_url=None,
        profile_pic_url='https://1000logos.net/wp-content/uploads/2016/10/Android-Logo.png',
        user=android,
        roi_rating=0.0,
        swap_rating=0.0
    )
    db.session.add(android)
    db.session.add( Transactions(
        coins=5,
        user=android
    ))
    
    # ANDORID TEST ACCOUNT - BUYINS
    and_buyinPast = Buy_ins(
        status='active',
        # tournament_id = past.id,
        chips = 2000,
        table = 14,
        seat = 2,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = android,
        flight = flight1_past,
        place='7th',
        winnings=400
    )
    db.session.add(and_buyinPast)

    and_buyin1 = Buy_ins(
        status='active',
        # tournament_id = demo2.id,
        chips = 10000,
        table = 17,
        seat = 2,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow(),
        user = android,
        flight = flight1_demo2
    )
    db.session.add(and_buyin1)



    ########## ANDROID PAST TOURNAMENT ###########


    s1 = Swaps(
        tournament=past,
        sender_user=android,
        recipient_user=alice,
        percentage=10,
        status='agreed',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=alice,
        recipient_user=android,
        percentage=10,
        status='agreed',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])
  

    s1 = Swaps(
        tournament=past,
        sender_user=android,
        recipient_user=alice,
        percentage=5,
        status='canceled',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=alice,
        recipient_user=android,
        percentage=7,
        status='canceled',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])



    s1 = Swaps(
        tournament=past,
        sender_user=android,
        recipient_user=bob,
        percentage=6,
        status='rejected',
        # due_at=(past.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=past,
        sender_user=bob,
        recipient_user=android,
        percentage=21,
        status='rejected',
        # due_at=(past.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])





    ########## ANDROID CURRENT TOURNAMENT ###########

    s1 = Swaps(
        tournament=demo2,
        sender_user=android,
        recipient_user=alice,
        percentage=5,
        status='pending',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo2,
        sender_user=alice,
        recipient_user=android,
        percentage=7,
        status='incoming',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])

    s1 = Swaps(
        tournament=demo2,
        sender_user=android,
        recipient_user=alice,
        percentage=5,
        status='agreed',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo2,
        sender_user=alice,
        recipient_user=android,
        percentage=7,
        status='agreed',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])
  

    s1 = Swaps(
        tournament=demo2,
        sender_user=android,
        recipient_user=alice,
        percentage=15,
        status='canceled',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo2,
        sender_user=alice,
        recipient_user=android,
        percentage=17,
        status='canceled',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])



    s1 = Swaps(
        tournament=demo2,
        sender_user=android,
        recipient_user=bob,
        percentage=6,
        status='rejected',
        # due_at=(demo2.start_at + timedelta(days=4))
    )
    s2 = Swaps(
        tournament=demo2,
        sender_user=bob,
        recipient_user=android,
        percentage=21,
        status='rejected',
        # due_at=(demo2.start_at + timedelta(days=4)),
        counter_swap=s1
    )
    s1.counter_swap = s2
    db.session.add_all([s1, s2])


    db.session.execute("ALTER SEQUENCE tournaments_id_seq RESTART WITH 100")
    db.session.execute("ALTER SEQUENCE flights_id_seq RESTART WITH 100")
# Give room for Swap Profit to add mock tournaments
    db.session.execute("ALTER SEQUENCE users_id_seq RESTART WITH 6")
    db.session.commit()


    return