from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, TodoItem, Goal, Habit, HabitLog, DailyProgress
from app.forms import InscriptionForm, ConnexionForm, TacheForm
from datetime import datetime, date, timedelta
from sqlalchemy import func

main = Blueprint("main", __name__)


# ---------------- ACCUEIL ----------------

from flask_login import current_user

@main.route("/")
def index():

    if current_user.is_authenticated:
        return redirect(url_for("main.login"))

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



@main.route("/login", methods=["GET", "POST"])
def login():

    form = ConnexionForm()

    if form.validate_on_submit():

        print("Formulaire valide")

        utilisateur = User.query.filter_by(
            email=form.email.data
        ).first()

        if utilisateur:
            print("Utilisateur trouvé :", utilisateur.email)
        else:
            print("Utilisateur introuvable")

        if utilisateur and utilisateur.check_password(form.mot_de_passe.data):

            print("Connexion réussie")

            login_user(utilisateur)

            return redirect(url_for("main.home"))

        print("Mot de passe incorrect")

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
    today = datetime.utcnow().date()
    start_of_month = today.replace(day=1)

    # --- KPI 1 & 2 : Séries (Directement depuis l'User et ses habitudes)
    current_streak = current_user.current_streak or 0
    # On récupère le record max parmi toutes les habitudes de l'utilisateur
    best_habit_streak = db.session.query(func.max(Habit.max_streak)).filter_by(user_id=current_user.id).scalar() or 0

    # --- KPI 3 : Taux de complétion du mois en cours (via DailyProgress)
    monthly_progress_records = DailyProgress.query.filter(
        DailyProgress.user_id == current_user.id,
        DailyProgress.date >= start_of_month
    ).all()
    
    if monthly_progress_records:
        month_completion_rate = round(sum(r.completion_rate for r in monthly_progress_records) / len(monthly_progress_records))
    else:
        month_completion_rate = 0

    # --- KPI Extra : Productivité To-Do (Tâches réalisées)
    total_todos = TodoItem.query.filter_by(user_id=current_user.id).count()
    completed_todos = TodoItem.query.filter_by(user_id=current_user.id, is_completed=True).count()
    todo_completion_rate = round((completed_todos / total_todos) * 100) if total_todos > 0 else 0

    # --- HEATMAP DATA (HabitLog des 365 derniers jours)
    one_year_ago = today - timedelta(days=364)
    logs = db.session.query(
        func.date(HabitLog.date_completed).label('date'),
        func.count(HabitLog.id).label('count')
    ).join(Habit).filter(
        Habit.user_id == current_user.id,
        HabitLog.date_completed >= one_year_ago
    ).group_by(func.date(HabitLog.date_completed)).all()

    log_data = {str(log.date): log.count for log in logs}

    # --- LINE CHART DATA (Progression des 30 derniers jours via DailyProgress)
    last_30_days = [today - timedelta(days=i) for i in range(29, -1, -1)]
    daily_rates = {}
    
    # On pré-remplit à 0 pour éviter les trous dans le graphique
    for d in last_30_days:
        daily_rates[d.strftime('%d %b')] = 0

    progress_30_days = DailyProgress.query.filter(
        DailyProgress.user_id == current_user.id,
        DailyProgress.date >= today - timedelta(days=29)
    ).order_by(DailyProgress.date.asc()).all()

    for p in progress_30_days:
        daily_rates[p.date.strftime('%d %b')] = round(p.completion_rate)

    # --- BAR CHART DATA (6 derniers mois via DailyProgress)
    monthly_rates = {}
    for i in range(5, -1, -1):
        # On remonte de x mois
        first_day_of_target_month = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
        month_name = first_day_of_target_month.strftime('%b')
        
        # Moyenne du taux de complétion pour ce mois cible
        avg_rate = db.session.query(func.avg(DailyProgress.completion_rate)).filter(
            DailyProgress.user_id == current_user.id,
            func.strftime('%Y-%m', DailyProgress.date) == first_day_of_target_month.strftime('%Y-%m')
        ).scalar()
        
        monthly_rates[month_name] = round(avg_rate) if avg_rate is not None else 0

    return render_template(
        "data/dashboard.html",
        current_streak=current_streak,
        best_streak=best_habit_streak,
        month_completion_rate=month_completion_rate,
        todo_completion_rate=todo_completion_rate, # Nouveau KPI envoyé au template
        log_data=log_data,
        daily_rates=daily_rates,
        monthly_rates=monthly_rates
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

@main.route("/tache/<int:tache_id>/terminer")
@login_required
def terminer_tache(tache_id):
    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(url_for("main.goal"))

    # Basculer l'état de la tâche
    tache.is_completed = not tache.is_completed

    if tache.is_completed:
        tache.completed_at = datetime.utcnow()
        flash("Tâche terminée !", "success")
    else:
        tache.completed_at = None
        flash("Tâche remise en cours.", "info")

    db.session.commit()

    return redirect(url_for("main.goal"))

@main.route("/tache/<int:tache_id>/supprimer")
@login_required
def supprimer_tache(tache_id):
    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(url_for("main.goal"))

    db.session.delete(tache)
    db.session.commit()

    flash("Tâche supprimée.", "success")

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
        
        deadline_str = request.form.get("task_deadline")

        deadline = None
        if deadline_str:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()

        nouvelle_tache = TodoItem(
            title=request.form.get("titre"),
            creneau=creneau,
            deadline=deadline,
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
        form = TacheForm(),                   
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

        current_user.nom = request.form.get("nom")
        current_user.email = request.form.get("email")

        ancien = request.form.get("ancien_password")
        nouveau = request.form.get("nouveau_password")
        confirmation = request.form.get("confirmation_password")

        if nouveau:

            if not current_user.check_password(ancien):
                flash("Ancien mot de passe incorrect.", "danger")
                return redirect(url_for("main.settings"))

            if nouveau != confirmation:
                flash("Les mots de passe ne correspondent pas.", "danger")
                return redirect(url_for("main.settings"))

            current_user.set_password(nouveau)

        db.session.commit()

        flash("Vos informations ont été mises à jour.", "success")

        return redirect(url_for("main.settings"))

    return render_template("settings.html")


# ---------------- HOME ----------------

from datetime import date, timedelta

@main.route("/home")
@login_required
def home():

    habits = Habit.query.filter_by(user_id=current_user.id).all()
    total_habits = len(habits)

    today = date.today()

    # Toutes les tâches de l'utilisateur
    tasks = TodoItem.query.filter_by(user_id=current_user.id).all()

    # Nombre de tâches terminées aujourd'hui
    completed_today = 0
    dates = set()

    for task in tasks:
        if task.is_completed and task.completed_at:
            completed_date = task.completed_at.date()
            dates.add(completed_date)

            if completed_date == today:
                completed_today += 1

    # Calcul du streak
    streak = 0
    current_day = today

    while current_day in dates:
        streak += 1
        current_day -= timedelta(days=1)

    # Événements du calendrier
    events = []

    for task in tasks:

        # Date à afficher dans le calendrier
        if task.deadline:
            event_date = task.deadline
        else:
            event_date = task.created_at.date()

        events.append({
            "title": task.title,
            "start": event_date.strftime("%Y-%m-%d"),
            "allDay": True,
            "color": "#22c55e" if task.is_completed else "#8b5cf6"
        })

    return render_template(
        "acceuil/home.html",
        habits=habits,
        total_habits=total_habits,
        completed_today=completed_today,
        streak=streak,
        events=events
    )