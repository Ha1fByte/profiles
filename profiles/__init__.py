import os
import requests
import subprocess
import csh_ldap 

import flask_migrate
from flask import Flask, render_template, jsonify, request, redirect, send_from_directory
from flask_uploads import UploadSet, configure_uploads, IMAGES
from flask_pyoidc.flask_pyoidc import OIDCAuthentication
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func


app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Get app config from absolute file path
if os.path.exists(os.path.join(os.getcwd(), "config.py")):
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.py"))
else:
    app.config.from_pyfile(os.path.join(os.getcwd(), "config.env.py"))

auth = OIDCAuthentication(app, issuer=app.config["OIDC_ISSUER"],
                          client_registration_info=app.config["OIDC_CLIENT_CONFIG"])


# LDAP
_ldap = csh_ldap.CSHLDAP(app.config['LDAP_BIND_DN'], app.config['LDAP_BIND_PASS'])

photos = UploadSet('photos', IMAGES)

app.config['UPLOADED_PHOTOS_DEST'] = 'static/img'
configure_uploads(app, photos)

from profiles.utils import before_request, get_member_info, process_image
from profiles.ldap import ldap_update_profile, get_image, ldap_get_active_members, ldap_get_all_members, ldap_get_member, ldap_search_members, ldap_is_active, ldap_get_eboard, _ldap_get_group_members, ldap_get_group_desc


@app.route("/", methods=["GET"])
@auth.oidc_auth
@before_request
def home(info=None):
    return redirect("/profile/" + info["uid"],
                              code = 302)


@app.route("/profile/<uid>", methods=["GET"])
@auth.oidc_auth
@before_request
def profile(uid=None, info=None):
    return render_template("profile.html", 
    						  info=info, 
    						  member_info=get_member_info(uid))


@app.route("/results", methods=["POST"])
@auth.oidc_auth
@before_request
def results(uid=None, info=None):
    if request.method == "POST":
    	searched = request.form['query']
    	return redirect("/search/{}".format(searched), 302)


@app.route("/search", methods=["GET"])
@auth.oidc_auth
@before_request
def search(searched=None, info=None):
    # return jsonify(ldap_search_members(searched))
    searched = request.args.get("q")
    return render_template("listing.html", 
    						  info=info, 
    						  title = "Search Results: "+searched,
    						  members=ldap_search_members(searched))


@app.route("/group/<group>", methods=["GET"])
@auth.oidc_auth
@before_request
def group(group=None, info=None):
    group_desc = ldap_get_group_desc(group)

    if "eboard" == group:
    	return render_template("listing.html", 
    						    info=info,
    						    title = group_desc,
    						    members=ldap_get_eboard())
    else:
    	return render_template("listing.html", 
    						    info=info, 
    						    title = group_desc,
    						    members=_ldap_get_group_members(group))


@app.route("/update", methods=["POST"])
@auth.oidc_auth
@before_request
def update(uid=None, info=None):
    if request.method == "POST"  and 'photo' in request.files:
        return process_image(request.files['photo'])
    else:
        ldap_update_profile(request.form, info['uid'])
        return ""


@app.route('/upload', methods=['GET', 'POST'])
@auth.oidc_auth
@before_request
def upload(uid=None, info=None):
    if request.method == 'POST' and 'photo' in request.files and process_image(request.files['photo'], info['uid']):
        return redirect('/', 302)
    return redirect('/', 302)


@app.route("/logout")
@auth.oidc_logout
def logout():
    return redirect("/", 302)


@app.route("/image/<uid>", methods=["GET"])
def image(uid):
    return get_image(uid);
