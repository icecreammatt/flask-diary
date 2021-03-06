from diary import app, models, db, forms, lm, pages, utils
from flask import g, session, render_template, redirect, url_for, flash, request, send_from_directory
from flask.ext.login import login_required, logout_user, login_user
from werkzeug import secure_filename
import os
import shutil


@app.before_request
def check_user_status():
  """
  Check global user_id
  """
  g.user = None
  if "user_id" in session:
    g.user = models.User.query.get(session["user_id"])
    g.diaries = g.user.sorted_diaries()


@lm.user_loader
def load_user(user_id):
  """
  LoginManager method
  """
  return models.User.query.get(user_id)


@app.route("/pages/<path:path>/")
def page(path):
    page = pages.get_or_404(path)
    template = page.meta.get("template", "page.html")
    return render_template(template, page=page)


@app.route("/favicon.ico")
def favicon():
  return send_from_directory(os.path.join(app.root_path, "static"),
                             "favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/")
@login_required
def diary_index():
  """
  Shows all available diaries, includes a form to create a new one.
  """
  if g.diaries and g.diaries.first():
    return redirect(url_for("post_index", diary_slug=g.diaries.first().slug))

  return render_template("diary_index.html", diaries=g.diaries)


@app.route("/create/", methods=["POST", "GET"])
@login_required
def diary_create():
  """
  Create a new diary for the current user
  """
  form = forms.DiaryForm()

  if form.validate_on_submit():
    diary = models.Diary(request.form["title"])
    diary.owner_id = g.user.id
    diary.users.append(g.user)

    db.session.add(diary)
    db.session.commit()
    flash("Dagboek toegevoegd")
    return redirect(url_for("post_index", diary_slug=diary.slug))
  # else:
  #   flash("Dagboek is niet correct ingevoerd")

  return render_template("diary_form.html", form=form)


@app.route("/<path:diary_slug>/edit/", methods=["POST", "GET"])
@login_required
def diary_edit(diary_slug):
  """
  Edit diary for the current user
  """
  diary = g.user.get_diary(diary_slug).first_or_404()
  form = forms.DiaryForm(obj=diary)

  if form.validate_on_submit():
    form.populate_obj(diary)
    diary.create_slug()

    db.session.add(diary)
    db.session.commit()
    flash("Dagboek gewijzigd")
    return redirect(url_for("post_index", diary_slug=diary.slug))
  # else:
  #   flash("Dagboek is niet correct ingevoerd")

  return render_template("diary_form.html", form=form)


@app.route("/delete/<int:diary_id>/")
@login_required
def diary_delete(diary_id):
  """
  Delete a diary
  """
  diary = models.Diary.query.get(diary_id)
  if diary.owner_id == g.user.id:
    db.session.delete(diary)
    db.session.commit()
    flash("Dagboek verwijderd")
  else:
    flash("U heeft hier geen rechten toe.")
  return redirect(url_for("diary_index"))


@app.route("/<path:diary_slug>/")
@login_required
def post_index(diary_slug):
  """
  Shows all available posts in the current diary, includes a form to add a new
  post to this diary.
  """
  diary = g.user.get_diary(diary_slug).first_or_404()
  posts = diary.sorted_posts()

  return render_template("post_index.html", diary=diary, posts=posts)


@app.route("/<path:diary_slug>/create/", methods=["GET", "POST"])
@login_required
def post_create(diary_slug):
  """
  POST-method to create a new post
  """
  diary = g.user.get_diary(diary_slug).first_or_404()
  form = forms.PostForm()

  if form.validate_on_submit():
    post = models.Post(diary.id, request.form["title"])
    post.user_id = g.user.id
    post.diary_id = diary.id

    form.populate_obj(post)

    db.session.add(post)
    db.session.commit()

    flash("Bericht toegevoegd")
    return redirect(url_for("post_index", diary_slug=diary.slug, post_id=post.id))
  # else:
  #   flash("Bericht is niet correct ingevoerd")

  return render_template("post_form.html", form=form, diary=diary)


@app.route("/<path:diary_slug>/<path:post_slug>/edit/", methods=["GET", "POST"])
@login_required
def post_edit(diary_slug, post_slug):
  """
  POST-method to edit post
  """
  diary = g.user.get_diary(diary_slug).first_or_404()
  post = diary.get_post(post_slug).first_or_404()

  form = forms.PostForm(obj=post)

  if form.validate_on_submit():
    form.populate_obj(post)
    post.create_slug(diary.id)
    db.session.add(post)
    db.session.commit()

    flash("Bericht gewijzigd")
    return redirect(url_for("post_index", diary_slug=diary.slug, post_id=post.id))
  # else:
  #   flash("Bericht is niet correct ingevoerd")

  return render_template("post_form.html", form=form, diary=diary)


@app.route("/<path:diary_slug>/delete/<int:post_id>/")
@login_required
def post_delete(diary_slug, post_id):
  post = models.Post.query.get(post_id)

  if post.user_id == g.user.id:
    target_dir = os.path.join(app.config["UPLOAD_FOLDER"], "{0}".format(post.id))
    if os.path.exists(target_dir):
      shutil.rmtree(target_dir)

    db.session.delete(post)
    db.session.commit()
    flash("Bericht verwijderd")
  else:
    flash("U heeft hier geen rechten toe.")
  return redirect(url_for("post_index", diary_slug=diary_slug))


@app.route("/<path:diary_slug>/<path:post_slug>/upload/", methods=["GET", "POST"])
@login_required
def picture_upload(diary_slug, post_slug):
  """
  POST-method to upload a picture
  """
  diary = g.user.get_diary(diary_slug).first_or_404()
  post = diary.get_post(post_slug).first_or_404()

  form = forms.PictureForm()

  if form.validate_on_submit():
    picture = models.Picture(request.form["title"])
    picture.post_id = post.id
    picture_file = request.files["file"]

    if picture_file and utils.allowed_file(picture_file.filename):
      filename = secure_filename(picture_file.filename).lower()
      target_dir = os.path.join(app.config["UPLOAD_FOLDER"], "{0}".format(post.id))
      if not os.path.exists(target_dir):
        os.makedirs(target_dir)

      picture_file.save(os.path.join(target_dir, filename))
      utils.generate_thumb(
        os.path.join(target_dir, filename),
        os.path.join(target_dir, "thumb_{0}".format(filename)),
        (app.config["THUMBNAIL_WIDTH"], app.config["THUMBNAIL_HEIGHT"]))
      picture.file_url = url_for("uploaded_file", post_id=post.id, filename=filename)
      picture.thumb_url = url_for("uploaded_file", post_id=post.id, filename="thumb_{0}".format(filename))

    if picture.file_url:
      db.session.add(picture)
      db.session.commit()
      flash("Afbeelding opgeslagen")
    else:
      flash("Dit is geen afbeelding of er ging iets fout")

    return redirect(url_for("post_index", diary_slug=diary.slug, post_id=post.id))
  # else:
  #   flash("Bericht is niet correct ingevoerd")

  return render_template("picture_form.html", form=form, diary=diary, post=post)


@app.route("/<path:diary_slug>/<post_slug>/delete/<int:picture_id>/")
@login_required
def picture_delete(diary_slug, post_slug, picture_id):
  diary = g.user.get_diary(diary_slug).first_or_404()
  post = diary.get_post(post_slug).first_or_404()
  picture = models.Picture.query.get(picture_id)

  if picture and post.user_id == g.user.id:
    target_dir = os.path.join(app.config["UPLOAD_FOLDER"], "{0}".format(post.id))
    picture_file = os.path.join(target_dir, os.path.basename(picture.file_url))
    thumb_file = os.path.join(target_dir, os.path.basename(picture.thumb_url))

    if os.path.exists(thumb_file):
      # remove file
      os.remove(thumb_file)

    if os.path.exists(picture_file):
      # remove file
      os.remove(picture_file)

      # remove empty dir
      files = os.listdir(target_dir)
      if len(files) == 0:
        os.rmdir(target_dir)

    db.session.delete(picture)
    db.session.commit()
    flash("Afbeelding verwijderd")
  else:
    flash("U heeft hier geen rechten toe.")
  return redirect(url_for("post_index", diary_slug=diary_slug, post_id=post.id))


@app.route("/login/", methods=["GET", "POST"])
def login():
  form = forms.LoginForm()
  if form.validate_on_submit():
    # login and validate the user...
    email = request.form["emailaddress"].lower()
    user = models.User.query.filter(models.User.emailaddress == email).first()
    if user is not None and user.is_password_correct(request.form["password"]):
      remember_me = False
      if "remember_me" in request.form:
        remember_me = request.form["remember_me"]
      login_user(user, remember_me)
      flash("U bent ingelogd")
      return form.redirect("diary_index")
    else:
      flash("Inloggegevens niet correct ingevoerd")

  return render_template("login.html", form=form)


@app.route("/logout/")
@login_required
def logout():
  logout_user()
  return redirect(url_for("login"))
