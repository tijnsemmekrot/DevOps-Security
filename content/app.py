from flask import Flask, request, redirect, make_response, escape
import sqlite3
import urllib
import quoter_templates as templates

# Run using `poetry install && poetry run flask run --reload`
app = Flask(__name__)
app.static_folder = '.'

# Open the database. Have queries return dicts instead of tuples.
# The use of `check_same_thread` can cause unexpected results in rare cases. We'll
# get rid of this when we learn about SQLAlchemy.
db = sqlite3.connect("db.sqlite3", check_same_thread=False)
db.row_factory = sqlite3.Row

# Log all requests for analytics purposes
log_file = open('access.log', 'a', buffering=1)
@app.before_request
def log_request():
    log_file.write(f"{request.method} {request.path} {dict(request.form) if request.form else ''}\n")


# Set user_id on request if user is logged in, or else set it to None.
# test hashtag
@app.before_request
def check_authentication():
    if 'user_id' in request.cookies:
        request.user_id = int(request.cookies['user_id'])
    else:
        request.user_id = None

# The main page
# @app.route("/")
# def index():
#     quotes = db.execute("select id, text, attribution from quotes order by id").fetchall()
#     return templates.main_page(quotes, request.user_id, request.args.get('error'))
# changed to

@app.route("/")
def index():
    quotes = db.execute("SELECT id, text, attribution FROM quotes ORDER BY id").fetchall()
    error_message = escape(request.args.get('error', ''))  # Explicitly escape user input
    
    # Correct the tuple structure for escaped_quotes
    escaped_quotes = [{'id': q['id'], 'text': escape(q['text']), 'attribution': escape(q['attribution'])} for q in quotes]  # Escape quotes

    return templates.main_page(escaped_quotes, request.user_id, error_message)



# The quote comments page
@app.route("/quotes/<int:quote_id>")
def get_comments_page(quote_id):
    quote = db.execute(f"select id, text, attribution from quotes where id={quote_id}").fetchone()
    comments = db.execute(f"select text, datetime(time,'localtime') as time, name as user_name from comments c left join users u on u.id=c.user_id where quote_id={quote_id} order by c.id").fetchall()
    return templates.comments_page(quote, comments, request.user_id)


# Post a new quote
@app.route("/quotes", methods=["POST"])
def post_quote():
    with db:
        # this was the code first
        # db.execute(f"""insert into quotes(text,attribution) values("{request.form['text']}","{request.form['attribution']}")""")
        # changed to :
        db.execute("INSERT INTO quotes(text, attribution) VALUES (%s, %s)", (request.form['text'], request.form['attribution']))
    return redirect("/#bottom")


# Post a new comment
@app.route("/quotes/<int:quote_id>/comments", methods=["POST"])
def post_comment(quote_id):
    with db:
        db.execute("""INSERT INTO quotes(text, attribution) VALUES (%s, %s)""", (request.form['text'], request.form['attribution']))
    return redirect(f"/quotes/{quote_id}#bottom")


# Sign in user
@app.route("/signin", methods=["POST"])
def signin():
    username = request.form["username"].lower()
    password = request.form["password"]

    #user = db.execute(f"select id, password from users where name='{username}'").fetchone()
    # changed to
    user = db.execute("SELECT id, password FROM users WHERE name = %s", (username,)).fetchone()
    if user: # user exists
        if password != user['password']:
            # wrong! redirect to main page with an error message
            return redirect('/?error='+urllib.parse.quote("Invalid password!"))
        user_id = user['id']
    else: # new sign up
        with db:
            #cursor = db.execute(f"insert into users(name,password) values('{username}', '{password}')")
            #changed to
            cursor = db.execute("INSERT INTO users(name, password) VALUES (%s, %s)", (username, password))
            user_id = cursor.lastrowid
    
    response = make_response(redirect('/'))
    # this was the code first
    # response.set_cookie('user_id', str(user_id))
    # changed to
    response.set_cookie('user_id', str(user_id), httponly=True, secure=True, samesite='Lax')
    return response


# Sign out user
@app.route("/signout", methods=["GET"])
def signout():
    response = make_response(redirect('/'))
    response.delete_cookie('user_id')
    return response
