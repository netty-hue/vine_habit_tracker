from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, Tache
from app.forms import InscriptionForm, ConnexionForm, TacheForm

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


# ---------- AUTHENTIFICATION ----------

@main.route("/inscription", methods=["GET", "POST"])
def inscription():
    form = InscriptionForm()
    if form.validate_on_submit():
        # Vérifie que l'email n'existe pas déjà
        if User.query.filter_by(email=form.email.data).first():
            flash("Cet email est déjà utilisé.", "danger")
            return redirect(url_for("main.inscription"))

        utilisateur = User(nom=form.nom.data, email=form.email.data)
        utilisateur.set_password(form.mot_de_passe.data)
        db.session.add(utilisateur)
        db.session.commit()

        flash("Compte créé avec succès, vous pouvez vous connecter.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


@main.route("/login", methods=["GET", "POST"])
def login():
    form = ConnexionForm()
    if form.validate_on_submit():
        utilisateur = User.query.filter_by(email=form.email.data).first()

        if utilisateur and utilisateur.check_password(form.mot_de_passe.data):
            login_user(utilisateur)
            return redirect(url_for("main.dashboard"))

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("login.html", form=form)


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


# ---------- EXEMPLE CRUD (Tâches) ----------

@main.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    form = TacheForm()
    if form.validate_on_submit():
        nouvelle_tache = Tache(titre=form.titre.data, user_id=current_user.id)
        db.session.add(nouvelle_tache)
        db.session.commit()
        return redirect(url_for("main.dashboard"))

    taches = Tache.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard.html", form=form, taches=taches)


@main.route("/tache/<int:tache_id>/terminer")
@login_required
def terminer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    if tache.user_id == current_user.id:
        tache.terminee = not tache.terminee
        db.session.commit()
    return redirect(url_for("main.dashboard"))


@main.route("/tache/<int:tache_id>/supprimer")
@login_required
def supprimer_tache(tache_id):
    tache = Tache.query.get_or_404(tache_id)
    if tache.user_id == current_user.id:
        db.session.delete(tache)
        db.session.commit()
    return redirect(url_for("main.dashboard"))