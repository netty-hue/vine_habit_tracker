from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, TodoItem, Goal, Habit
from app.forms import InscriptionForm, ConnexionForm, TacheForm

main = Blueprint("main", __name__)


# ---------------- ACCUEIL ----------------

@main.route("/")
def index():
    return render_template("acceuil/index.html")


# ---------------- INSCRIPTION ----------------

@main.route("/inscription", methods=["GET", "POST"])
def inscription():

    form = InscriptionForm()

    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for("main.inscription"))

        utilisateur = User(
            username=form.nom.data,
            email=form.email.data
        )

        utilisateur.set_password(form.mot_de_passe.data)

        db.session.add(utilisateur)
        db.session.commit()

        login_user(utilisateur)

        flash("Compte créé avec succès.", "success")

        return redirect(url_for("main.home"))

    return render_template("connexion/register.html", form=form)


# ---------------- CONNEXION ----------------

@main.route("/login", methods=["GET", "POST"])
def login():

    form = ConnexionForm()

    if form.validate_on_submit():

        utilisateur = User.query.filter_by(
            email=form.email.data
        ).first()

        if utilisateur and utilisateur.check_password(form.mot_de_passe.data):

            login_user(utilisateur)

            return redirect(url_for("main.home"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("connexion/login.html", form=form)


# ---------------- DECONNEXION ----------------

@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


# ---------------- DASHBOARD ----------------

@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("data/dashboard.html")


# ---------------- GOAL ----------------

@main.route("/goal", methods=["GET", "POST"])
@login_required
def goal():

    form = TacheForm()

    if form.validate_on_submit():

        nouvelle_tache = TodoItem(
            title=form.titre.data,
            user_id=current_user.id
        )

        db.session.add(nouvelle_tache)
        db.session.commit()

        return redirect(url_for("main.goal"))

    taches = TodoItem.query.filter_by(
        user_id=current_user.id
    ).all()

    return render_template(
        "data/goal.html",
        form=form,
        taches=taches
    )


@main.route("/tache/<int:tache_id>/terminer")
@login_required
def terminer_tache(tache_id):

    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id == current_user.id:

        tache.is_completed = not tache.is_completed

        db.session.commit()

    return redirect(url_for("main.goal"))


@main.route("/tache/<int:tache_id>/supprimer")
@login_required
def supprimer_tache(tache_id):

    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id == current_user.id:

        db.session.delete(tache)

        db.session.commit()

    return redirect(url_for("main.goal"))


# ---------------- SETTINGS ----------------

@main.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        theme = request.form.get("theme")

        # Mise à jour du nom
        if username and username != current_user.username:
            current_user.username = username

        # Mise à jour de l'email
        if email and email != current_user.email:

            utilisateur = User.query.filter_by(email=email).first()

            if utilisateur:
                flash("Cet email est déjà utilisé.", "danger")
                return redirect(url_for("main.settings"))

            current_user.email = email

        # Mot de passe
        if password and password.strip():
            current_user.set_password(password)

        # Thème
        if theme in ["light", "dark"]:
            current_user.theme = theme

        db.session.commit()

        flash("Paramètres enregistrés avec succès.", "success")

        return redirect(url_for("main.settings"))

    return render_template("settings.html")


# ---------------- HOME ----------------

@main.route("/home")
@login_required
def home():

    habits = Habit.query.filter_by(user_id=current_user.id).all()

    total_habits = len(habits)

    completed_today = 0

    streak = 0

    events = [
        {
            "title": t.title,
            "start": t.created_at.strftime("%Y-%m-%d")
        }
        for t in TodoItem.query.filter_by(user_id=current_user.id).all()
    ]

    return render_template(
        "acceuil/home.html",
        habits=habits,
        total_habits=total_habits,
        completed_today=completed_today,
        streak=streak,
        events=events
    )