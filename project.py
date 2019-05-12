from database_setup import Item, User, Category
from flask import Flask, render_template, request, redirect, jsonify, url_for
from flask import flash, make_response
from flask import session as login_session
from flask import make_response
import httplib2
import json
import random
import requests
import string
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError


app = Flask(__name__)

# Connect to data base
db_engine = create_engine('sqlite:///ItemCatalog.db')
db_session_binding = sessionmaker(bind=db_engine)
db_session = db_session_binding()


# Load the client_id for google sign-in
CLIENT_SECRET_FILE_NAME = 'client_secret_apps.googleusercontent.com.json'
with open(CLIENT_SECRET_FILE_NAME, 'r') as secret_file:
    CLIENT_ID = json.loads(secret_file.read())['web']['client_id']


@app.route('/login')
def show_login():
    """Create anti-forgery state token and route to login page."""
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    print('ClientID =|{}|'.format(CLIENT_ID))
    print('State = '+state)
    return render_template("login.html", STATE=state, CLIENT_ID=CLIENT_ID)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """Connect to google sign-in, verify the access_token, get the user of the session and return the response."""
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(CLIENT_SECRET_FILE_NAME, scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    google_id = credentials.id_token['sub']
    if result['user_id'] != google_id:
        response = make_response(json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID does not match app's."), 401)
        print("Token's client ID does not match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_google_id = login_session.get('google_id')
    if stored_access_token is not None and google_id == stored_google_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['google_id'] = google_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    print(login_session['email'])
    # see if user exists, if it doesn't make a new one
    user_id = get_user_id(login_session['email'])
    print(user_id)
    if not user_id:
        user_id = create_new_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print("you are now logged in as %s" % login_session['username'])
    print("you are now logged in with user-id %s" % login_session['user_id'])
    print("done!")
    return output


def gdisconnect():
    """Disconnect the logged-in user and return the response from google."""
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            json.dumps('Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/logout')
def show_logout():
    """Log out the active user and redirect to the main page."""
    if 'username' in login_session:
        gdisconnect()
        del login_session['google_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        flash("You have been successfully logged out!")
        return redirect(url_for('show_home'))
    else:
        flash("You were not logged in!")
        return redirect(url_for('show_home'))


def create_new_user(login_session):
    """Add new user to the db and return it´s id."""
    db_session.add(User(
        name=login_session['username'],
        email=login_session['email'])
    )
    db_session.commit()
    return get_user_id(login_session['email'])


def get_user_id(email):
    """Look up user in db and return it´s id"""
    userinfo = get_user_info(email=email)
    if userinfo:
        return userinfo.id
    else:
        return None


def get_user_info(email):
    """Look up user in db and return it"""
    user = db_session.query(User).filter_by(email=email).first()
    return user


@app.route('/')
def show_home():
    """Route to the the main page."""
    all_items = db_session.query(Item).all()
    all_categories = db_session.query(Category).all()
    return render_template('home.html', categories=all_categories, items=all_items)


@app.route('/catalog/<string:category_name>/items')
def show_category_items(category_name):
    """Route to a overview of all items of a category."""
    category = (db_session.query(Category).filter_by(name=category_name).first())
    if(category is None):
        flash("Unknow category")
        return redirect(url_for('show_home'))
    else:

        return render_template(
            'category_items.html',
            categories=db_session.query(Category).all(),
            category=db_session.query(Category).filter_by(id=category.id).first(),
            items=db_session.query(Item).filter_by(category_id=category.id).all(),
            items_count=db_session.query(Item).filter_by(category_id=category.id).count())


@app.route('/catalog/<string:category_name>/<string:item_name>')
def show_item(category_name, item_name):
    """Route to a single item."""
    if(db_session.query(Item).filter_by(name=item_name).first() is None):
        flash("Unknow item")
        return redirect(url_for('show_home'))
    else:
        return render_template(
            'item.html',
            item=db_session.query(Item).filter_by(name=item_name).first(),
            owner=db_session.query(User).filter_by(name=item_name).first())


@app.route('/catalog/<string:item_name>/edit', methods=['GET', 'POST'])
def show_edit_item(item_name):
    """Route to a edit single item."""
    if 'username' not in login_session:
        return redirect(url_for('show_login'))
    item = db_session.query(Item).filter_by(name=item_name).first()
    if(item is None):
        flash("Unknow item")
        return redirect(url_for('show_home'))
    if item.user.id != login_session['user_id']:
        return "<script>function f() {alert('You are not authorized to edit this item.');}</script><body onload='f()''>"
    if request.method == 'POST':
        if request.form['name']:
            item.name = request.form['name']
        if request.form['description']:
            item.description = request.form['description']
        if request.form['category']:
            item.category = db_session.query(Category).filter_by(name=request.form['category']).first()
        db_session.add(item)
        db_session.commit()
        flash('Item successfully edited!')
        return redirect(url_for('show_item', category_name=item.category.name, item_name=item.name))
    else:
        return render_template('edititem.html', item=item, categories=db_session.query(Category).all())


@app.route('/catalog/<string:item_name>/delete', methods=['GET', 'POST'])
def show_delete_item(item_name):
    """Route to a delete single item."""
    if 'username' not in login_session:
        return redirect(url_for('show_login'))
    item = db_session.query(Item).filter_by(name=item_name).first()
    if(item is None):
        flash("Unknow item")
        return redirect(url_for('show_home'))
    if item.user.id != login_session['user_id']:
        return "<script>function f() {alert('You are not authorized to delete this item.');}</script><body onload='f()''>"
    if request.method == 'POST':
        db_session.delete(item)
        db_session.commit()
        flash('Item successfully deleted!')
        return redirect(url_for(
            'show_home',
            item_name=item.name))
    else:
        return render_template('deleteitem.html', item=item)


@app.route('/catalog/create', methods=['GET', 'POST'])
def show_create_new_item():
    """Route to a create new item."""
    if 'username' not in login_session:
        return redirect(url_for('show_login'))
    if request.method == 'POST':
        if request.form['name'] and request.form['description'] and request.form['category']:
            db_session.add(Item(
                name=request.form['name'],
                description=request.form['description'],
                user=db_session.query(User).filter_by(id=login_session['user_id']).first(),
                category=db_session.query(Category).filter_by(name=request.form['category']).first()))
            db_session.commit()
            flash('Item successfully created!')
        return redirect(url_for('show_home'))
    else:
        return render_template(
            'createnewitem.html',
            categories=db_session.query(Category).all())


@app.route('/api/v1/catalog.json')
def return_catalog_as_json():
    '''JSON endpoint for reding all catalog items.'''
    output_categories = []
    all_categories = db_session.query(Category).all()
    for category in all_categories:
        items_in_db = db_session.query(Item).filter_by(category=category).all()
        output_items = []
        for item in items_in_db:
            output_items.append({
                'category_id': item.category_id,
                'description': item.description,
                'id': item.id,
                'name': item.name})
        output_categories.append({
            'id': category.id,
            'name': category.name,
            'Item': output_items})
    return jsonify(Category=output_categories)


if __name__ == '__main__':
    app.secret_key = b'ub\xcd\x83\xa5f\xf9}\xfe\xa9\xd6\xe0\x04|\xc3\xd2'  # generated with os.urandom(16)
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
