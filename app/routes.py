from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, TodoItem, Goal, Habit
from app.forms import InscriptionForm, ConnexionForm, TacheForm
from datetime import date

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

        # connexion automatique
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
    return render_template("data/dashboard.html",
        current_streak=0,
        best_streak=0,
        month_completion_rate=0,
        log_data={},

        # last 30 days — empty for now, real data comes after check-in is built
        daily_rates={},

        # 
        monthly_rates={
            "Jan": 0, "Feb": 0, "Mar": 0,
            "Apr": 0, "May": 0, "Jun": 0
        }
    )

# ── GOALS ────────────────────────────────────────────────────────

@main.route("/goal/create", methods=["POST"])
@login_required
def create_goal():
    title       = request.form.get("goal_title")
    description = request.form.get("goal_description")
    goal_type   = request.form.get("goal_type", "court_terme")
    task_limit  = request.form.get("goal_task_limit", 5)

    nouveau_goal = Goal(
        title=title,
        description=description,
        type=goal_type,
        task_limit=int(task_limit),
        user_id=current_user.id
    )
    db.session.add(nouveau_goal)
    db.session.commit()
    flash("Objectif créé avec succès !", "success")
    return redirect(url_for("main.goal"))


@main.route("/goal/<int:goal_id>/archiver")
@login_required
def archiver_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id == current_user.id:
        goal.is_archived = True
        db.session.commit()
        flash("Objectif archivé.", "info")
    return redirect(url_for("main.goal"))


@main.route("/goal/<int:goal_id>/supprimer")
@login_required
def supprimer_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id == current_user.id:
        db.session.delete(goal)
        db.session.commit()
        flash("Objectif supprimé.", "info")
    return redirect(url_for("main.goal"))


# ── HABITS ───────────────────────────────────────────────────────

@main.route("/habit/create", methods=["POST"])
@login_required
def create_habit():
    nouvelle_habitude = Habit(
        title=request.form.get("habit_title"),
        why=request.form.get("habit_why"),
        expected_result=request.form.get("habit_expected_result"),
        schedule_days=request.form.get("habit_schedule_days"),
        duration=request.form.get("habit_duration") or None,
        goal_id=request.form.get("habit_goal_id"),
        user_id=current_user.id
    )
    db.session.add(nouvelle_habitude)
    db.session.commit()
    flash("Habitude ajoutée !", "success")
    return redirect(url_for("main.goal"))


@main.route("/habit/<int:habit_id>/supprimer")
@login_required
def supprimer_habitude(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id == current_user.id:
        db.session.delete(habit)
        db.session.commit()
        flash("Habitude supprimée.", "info")
    return redirect(url_for("main.goal"))


@main.route("/habit/<int:habit_id>/modifier", methods=["GET", "POST"])
@login_required
def modifier_habitude(habit_id):
    habit = Habit.query.get_or_404(habit_id)
    if habit.user_id != current_user.id:
        return redirect(url_for("main.goal"))

    if request.method == "POST":
        habit.title           = request.form.get("habit_title")
        habit.why             = request.form.get("habit_why")
        habit.expected_result = request.form.get("habit_expected_result")
        habit.schedule_days   = request.form.get("habit_schedule_days")
        habit.duration        = request.form.get("habit_duration") or None
        db.session.commit()
        flash("Habitude modifiée.", "success")
        return redirect(url_for("main.goal"))

    return render_template("data/modifier_habitude.html", habit=habit)


# ── TÂCHES ───────────────────────────────────────────────────────

@main.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    if request.method == "POST":
        # Vérifier la limite de tâches par jour
        goal_id    = request.form.get("task_goal_id")
        creneau    = request.form.get("task_creneau", "matin")
        today      = date.today()

        # Compter les tâches du jour pour cet objectif
        # (limite définie dans l'objectif)
        existing = TodoItem.query.filter_by(
            user_id=current_user.id
        ).filter(TodoItem.created_at >= today).count()

        # Récupérer la limite depuis l'objectif si dispo
        goal_obj   = Goal.query.get(goal_id) if goal_id else None
        task_limit = goal_obj.task_limit if goal_obj else 5

        if existing >= task_limit:
            flash(f"Limite de {task_limit} tâches par jour atteinte pour cet objectif. Reste focalisé !", "danger")
            return redirect(url_for("main.goal"))

        nouvelle_tache = TodoItem(
            title=request.form.get("titre"),
            creneau=creneau,
            deadline=request.form.get("task_deadline") or None,
            user_id=current_user.id
        )
        db.session.add(nouvelle_tache)
        db.session.commit()
        return redirect(url_for("main.goal"))

    taches        = TodoItem.query.filter_by(user_id=current_user.id).all()
    goals_actifs  = Goal.query.filter_by(user_id=current_user.id, is_archived=False).all()
    goals_archives = Goal.query.filter_by(user_id=current_user.id, is_archived=True).all()
    habits        = Habit.query.filter_by(user_id=current_user.id).all()

    return render_template("data/goal.html",
        taches=taches,
        goals_actifs=goals_actifs,
        goals_archives=goals_archives,
        habits=habits
    )
# ---------------- SETTINGS ----------------

@main.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    if request.method == "POST":

        flash("Paramètres enregistrés avec succès.")

        return redirect(url_for("main.settings"))

    return render_template("data/settings.html")

@main.route("/home")
@login_required
def home():

    habits = Habit.query.filter_by(user_id=current_user.id).all()

    total_habits = len(habits)

    completed_today = 0

    streak = 0

    # Récupération des tâches pour le calendrier
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