from flask import url_for, redirect
from flask.ext.wtf import HiddenField, Form, TextField, TextAreaField, PasswordField, Required
from flask.ext.wtf.html5 import EmailField, DateField
from utils import get_redirect_target, is_safe_url


class DiaryForm(Form):
    title = TextField("Titel", validators=[Required()])


class PostForm(Form):
    title = TextField("Titel", validators=[Required()])
    body = TextAreaField("Tekst", validators=[Required()])
    date = DateField("Datum", validators=[Required()])


class RedirectForm(Form):
  next = HiddenField()

  def __init__(self, *args, **kwargs):
    Form.__init__(self, *args, **kwargs)
    if not self.next.data:
      self.next.data = get_redirect_target() or ""

  def redirect(self, endpoint="diary_index", **values):
    if is_safe_url(self.next.data):
      return redirect(self.next.data)
    target = get_redirect_target()
    return redirect(target or url_for(endpoint, **values))


class LoginForm(RedirectForm):
    emailaddress = EmailField("Emailadres", validators=[Required()])
    password = PasswordField("Wachtwoord", validators=[Required()])
