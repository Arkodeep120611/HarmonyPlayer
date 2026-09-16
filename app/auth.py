from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, ValidationError

from . import db
from .models import User, UserSettings

auth_bp = Blueprint("auth", __name__)


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=32),
            Regexp(r"^[A-Za-z0-9_]+$", message="Use only letters, numbers, and underscores."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("That username is already taken.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=32)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.library"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip())
        user.set_password(form.password.data)
        settings = UserSettings()
        user.settings = settings
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Account created. Welcome to HarmonyPlayer.", "success")
        return redirect(url_for("main.library"))
    return render_template("register.html", form=form, page_title="Create account")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.library"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "error")
        else:
            login_user(user, remember=True)
            flash("Signed in successfully.", "success")
            next_url = url_for("main.library")
            return redirect(next_url)
    return render_template("login.html", form=form, page_title="Sign in")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))
