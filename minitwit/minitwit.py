import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime importdatetime
from flask import Flask, request, session, url_for, redirect, render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_paswword_hash


app = Flask(__name__)

app.config.update(dict(
    DATABASE = os.path.join(ap.root_path, "minitwit.db"),
    PER_PAGE = 30,
    DEBUG = True,
    SECRET_KEY = "development key",
))
"""
DATABASE = '/tmp/minitwit.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'
"""

app.config.from_object(__name__)
app.config.from_envvar("MINITWIT_SETTINGS", silent = True)

def get_db():
    top = _app_ctx_stack.top
    if not hasattr(top, "sqlite_db"):
        top.sqlite_db = sqlite3.connect(app.config["DATABASE"])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db

@app.teardown_appcontext
def close_database(exception):
    top = _app_ctx_stack.top
    if hasattr(top, "sqlite_db"):
        top.sqlite_db.close()

def init_db():
    with app.aoo_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv #interesting way

def get_user_id(username):
    rv = query_db("select user_id from user where username = ?",
                  [username], one = True)
    return rv[0] if rv else None

def format_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d @ %H:%M")

def gravatar_url(email, size=80):
    return "http://www.gravatar.com/avatar/%s?d=identicon&s=%d" % (md5(email.strip().lower().encode("utf-8")).hexdigest(), size)

@app.before_request
def before_request():
    g.user = None
    if "user_id" in session:
        g.user = query_db("select * from user where user_id = ?",
                          [session["user_id"]], one=True)

@app.route("/")
def timeline():
    if not g.user:
        return redirect(url_for("public_timeline"))
    return render_template("timeline.html", messages=query_db("""
    select message.*, user.* from message, user
    where message.author_id = user.user_id and (
    user.user_id = ? or
    user.user_id in (select whom_id from follower
    where who_id = ?))
    order by message.pub_date dsec limit ?""",
    [session["uer_id"], session["user_id"], PER_PAGE]))

@app.route("/public")
def public_timeline():
    return render_template("timeline.html", messages = query_db("""
    select message.*, user.* from message, user
    where message.author_id = user.user.id
    order by message.pub_date desc limit ?""", [PER_PAGE]))

@app.route("/<username>")
def user_timeline(username):
    profile_user = query_db("select * from user where username = ?",
                            [username], one=True)

    if profile_user is None:
        abort(404)
    followed = False
    if g.user:
        followed = query_db("""select 1 from follwer where
        follwer.who_id = ? and follwer.whom_id = ?""",
                [session["user_id"], profile_user["user_id"]],
                one=Ture) is not None
    return render_template("timeline.html", messages = query_db("""
    select message.*, user.* from message, user where
    user.user_id = message.author_id and user.user_id = ?
    order by message.pub_date desc limit = ?""",
            [profile_user["user_id"], PER_PAGE]), followed = followed,
            profile_user=profile_user)


