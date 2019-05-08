from database_setup import Item, User, Category
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
import random
import string

db_engine = create_engine('sqlite:///ItemCatalog.db')
db_session_binding = sessionmaker(bind=db_engine)
db_session = db_session_binding()

admin = User(name = 'Admin', email = 'admin@itemcatalog.com')
tester = User(name = 'Tester', email = 'tester@itemcatalog.com')
db_session.add(admin)
db_session.add(tester)
db_session.commit()

db_session.add(Category(name = 'Soccer', user = admin))
db_session.add(Category(name = 'Basketball', user = tester))
db_session.add(Category(name = 'Baseball', user = admin))
db_session.add(Category(name = 'Frisbee', user = tester))
db_session.add(Category(name = 'Snowboarding', user = admin))
db_session.add(Category(name = 'Rock Climbing', user = tester))
db_session.add(Category(name = 'Foosball', user = admin))
db_session.add(Category(name = 'Skating', user = tester))
db_session.add(Category(name = 'Hockey', user = admin))
db_session.commit()

db_session.add(Item(user=admin, description='-', name = 'Stick', category = db_session.query(Category).filter_by(name='Hockey').first()))
db_session.add(Item(user=tester, description='-', name = 'Goggles', category = db_session.query(Category).filter_by(name='Snowboarding').first()))
db_session.add(Item(user=admin, description='-', name = 'Snowboard', category = db_session.query(Category).filter_by(name='Snowboarding').first()))
db_session.add(Item(user=tester, description='-', name = 'Two shinguards', category = db_session.query(Category).filter_by(name='Soccer').first()))
db_session.add(Item(user=admin, description='-', name = 'Shinguards', category = db_session.query(Category).filter_by(name='Soccer').first()))
db_session.add(Item(user=tester, description='-', name = 'Frisbee', category = db_session.query(Category).filter_by(name='Frisbee').first()))
db_session.add(Item(user=admin, description='-', name = 'Bat', category = db_session.query(Category).filter_by(name='Baseball').first()))
db_session.add(Item(user=tester, description='-', name = 'Jersey', category = db_session.query(Category).filter_by(name='Soccer').first()))
db_session.add(Item(user=admin, description='-', name = 'Soccer Cleats', category = db_session.query(Category).filter_by(name='Soccer').first()))
db_session.commit()




'''
print('Add users')
user1 = User(
    name = 'Nicol',
    email = 'nicol.gaspar.narciso@gmail.com')
db_session.add(user1)
user2 = User(
    name = 'TestTest',
    email = 'test.test@gmail.com')
db_session.add(user2)
db_session.commit()

print('Add Categories')
for count in range(1, 25):
    category1 = Category(
        name = 'Category_1_{}'.format(count),
        user = user1)
    category2 = Category(
        name = 'Category_2_{}'.format(count),
        user = user2)
    db_session.add(category1)
    db_session.add(category2)
db_session.commit()

print('Add Items')
categories = db_session.query(Category).all()
for count in range(1, 200):
    item = Item(
        name = 'Item_{}'.format(count),
        description = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(240)),
        user = random.choice([user1, user2]),
        category = random.choice(categories))
    db_session.add(item)
db_session.commit()
'''

print('Finish')