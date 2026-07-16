from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, TodoItem, Goal, Habit, HabitLog, DailyProgress, Notification
from app.forms import InscriptionForm, ConnexionForm, TacheForm
from datetime import datetime, date, timedelta, time
from sqlalchemy import func

main = Blueprint("main", __name__)


# ---------------- ACCUEIL ----------------

@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.login"))  # CORRIGÉ : Redirige vers home si connecté

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
    return redirect(url_for("main.login"))


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
        todo_completion_rate=todo_completion_rate,
        log_data=log_data,
        daily_rates=daily_rates,
        monthly_rates=monthly_rates
    )


# ── GOALS & TÂCHES (MODIFIÉ ET OPTIMISÉ) ───────────────────────────────────

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
        task_limit=int(task_limit) if task_limit else 5,
        user_id=current_user.id
    )
    db.session.add(nouveau_goal)
    db.session.commit()
    flash("Objectif créé avec succès !", "success")
    return redirect(url_for("main.goal"))


@main.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    if request.method == "POST":
        try:
            # 1. Récupération de l'objectif lié à la tâche
            goal_id = request.form.get("task_goal_id")
            goal_id = int(goal_id) if goal_id and goal_id.isdigit() else None
            
            # Récupération de l'intervalle de temps
            start_time_str = request.form.get("task_start_time")
            end_time_str = request.form.get("task_end_time")
            
            start_time_obj = None
            end_time_obj = None
            
            if start_time_str:
                try:
                    start_time_obj = datetime.strptime(start_time_str, "%H:%M").time()
                except ValueError:
                    pass
            if end_time_str:
                try:
                    end_time_obj = datetime.strptime(end_time_str, "%H:%M").time()
                except ValueError:
                    pass

            # Récupération de la date limite (par défaut : aujourd'hui)
            deadline_str = request.form.get("task_deadline")
            if deadline_str:
                try:
                    final_deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
                except ValueError:
                    final_deadline = date.today()
            else:
                final_deadline = date.today()

            # Sécurité : Si la date limite est dans le passé, on la réajuste à aujourd'hui
            if final_deadline < date.today():
                final_deadline = date.today()

            # Récupération des jours sélectionnés
            selected_days = request.form.getlist("task_days")
            selected_days_ints = [int(d) for d in selected_days if d.isdigit()]

            # Récupérer l'objectif pour la limite de tâches quotidienne (gestion du cas Optionnel/None)
            task_limit = 5
            if goal_id:
                goal_obj = Goal.query.get(goal_id)
                if goal_obj and hasattr(goal_obj, 'task_limit') and goal_obj.task_limit is not None:
                    task_limit = goal_obj.task_limit

            titre_tache = request.form.get("titre")
            if not titre_tache:
                flash("Le titre de la tâche est requis.", "danger")
                return redirect(url_for("main.goal"))

            # --- SÉCURITÉ ANTI-FLOOD ADAPTÉE ---
            if not selected_days_ints:
                today_midnight = datetime.combine(date.today(), time.min)
                existing_today = TodoItem.query.filter_by(
                    user_id=current_user.id, 
                    goal_id=goal_id,
                    deadline=date.today()
                ).filter(TodoItem.created_at >= today_midnight).count()

                if existing_today >= task_limit:
                    flash(f"Limite de {task_limit} tâches atteinte pour aujourd'hui sur cet objectif.", "danger")
                    return redirect(url_for("main.goal"))
            
            # Si l'utilisateur a sélectionné des jours de la semaine spécifiques
            if selected_days_ints:
                current_date = date.today()
                taches_creees = 0
                
                # On boucle du jour actuel jusqu'à la date limite
                while current_date <= final_deadline:
                    if current_date.weekday() in selected_days_ints:
                        # On vérifie si la limite pour ce jour précis est respectée
                        tasks_on_day = TodoItem.query.filter_by(
                            user_id=current_user.id,
                            goal_id=goal_id,
                            deadline=current_date
                        ).count()

                        if tasks_on_day < task_limit:
                            nouvelle_tache = TodoItem(
                                title=titre_tache,
                                start_time=start_time_obj,
                                end_time=end_time_obj,
                                deadline=current_date,
                                goal_id=goal_id,
                                user_id=current_user.id
                            )
                            db.session.add(nouvelle_tache)
                            taches_creees += 1
                    current_date += timedelta(days=1)
                
                if taches_creees > 0:
                    db.session.commit()
                    flash(f"{taches_creees} actions planifiées !", "success")
                else:
                    flash("Aucune tâche n'a pu être planifiée (limite atteinte ou mauvaise période).", "warning")
            else:
                # Planification unique standard à la date limite choisie
                tasks_on_deadline = TodoItem.query.filter_by(
                    user_id=current_user.id,
                    goal_id=goal_id,
                    deadline=final_deadline
                ).count()

                if tasks_on_deadline >= task_limit:
                    flash(f"La limite de tâches pour le {final_deadline.strftime('%d/%m')} est atteinte.", "danger")
                    return redirect(url_for("main.goal"))

                nouvelle_tache = TodoItem(
                    title=titre_tache,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    deadline=final_deadline,
                    goal_id=goal_id,
                    user_id=current_user.id
                )
                db.session.add(nouvelle_tache)
                db.session.commit()
                flash("Action planifiée avec succès !", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Une erreur est survenue : {str(e)}", "danger")
            
        return redirect(url_for("main.goal"))

    # --- PARTIE GET (AFFICHAGE SÉCURISÉ ET TRIÉ) ---
    goals_actifs = Goal.query.filter_by(user_id=current_user.id, is_archived=False).all()
    goals_archives = Goal.query.filter_by(user_id=current_user.id, is_archived=True).all()
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    today = date.today()

    # Récupération et tri robuste en Python
    taches_raw = TodoItem.query.filter_by(user_id=current_user.id).all()
    
    # Tri 100% robuste : si start_time est None, on utilise une heure maximale par défaut
    taches = sorted(
        taches_raw, 
        key=lambda t: t.start_time if t.start_time is not None else time(23, 59, 59)
    )
    
    return render_template(
        "data/goal.html",  # Reste "data/goal.html" ou "goal.html" selon l'arborescence de tes templates
        taches=taches, 
        goals_actifs=goals_actifs, 
        goals_archives=goals_archives, 
        habits=habits, 
        today=today
    )


@main.route("/goal/<int:goal_id>/archiver")
@login_required
def archiver_goal(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    if goal.user_id == current_user.id:
        goal.is_archived = True
        db.session.commit()
        flash("Objectif archivé.", "info")
    return redirect(url_for("main.goal"))


@main.route("/tache/<int:tache_id>/terminer", methods=["GET", "POST"])
@login_required
def terminer_tache(tache_id):
    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(request.referrer or url_for("main.goal"))

    # Sécurité pour les tâches futures
    if tache.deadline and tache.deadline > date.today():
        flash("Tu ne peux pas valider une tâche future !", "danger")
        return redirect(request.referrer or url_for("main.goal"))

    # Inverse l'état de complétion
    tache.is_completed = not tache.is_completed

    if tache.is_completed:
        tache.completed_at = datetime.utcnow()
        flash("Tâche terminée !", "success")
    else:
        tache.completed_at = None
        flash("Tâche remise en cours.", "info")

    db.session.commit()
    
    # CORRECTION : Redirige sur la page active actuelle (évite le retour sur 'goal')
    return redirect(request.referrer or url_for("main.goal"))

@main.route("/tache/<int:tache_id>/supprimer")
@login_required
def supprimer_tache(tache_id):
    tache = TodoItem.query.get_or_404(tache_id)

    if tache.user_id != current_user.id:
        flash("Action non autorisée.", "danger")
        return redirect(request.referrer or url_for("main.goal"))

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


# ── LISTE DES TÂCHES (MODIFIÉ ET NETTOYÉ) ─────────────────────────────────

@main.route('/taches', methods=['GET'])
@login_required
def list_taches():
    today_val = date.today()
    
    # 1. On récupère les tâches (TodoItem) de l'utilisateur connecté
    taches = TodoItem.query.filter_by(user_id=current_user.id).order_by(TodoItem.start_time.asc()).all()
    
    # 2. On récupère ses objectifs (Goals) actifs
    goals_actifs = Goal.query.filter_by(user_id=current_user.id, is_archived=False).all()
    
    # 3. On récupère ses habitudes (Habits)
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    return render_template('data/tache.html', 
            taches=taches, 
            goals_actifs=goals_actifs, 
            habits=habits, 
            today=today_val)

# ── API NOTIFICATIONS ─────────────────────────────────

@main.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    # On récupère les 10 dernières notifications non lues
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False)\
                                      .order_by(Notification.created_at.desc())\
                                      .limit(10).all()
    
    return jsonify([{
        "id": n.id,
        "message": n.message,
        "type": n.type,
        "created_at": n.created_at.strftime("%d/%m %H:%M")
    } for n in notifications])


@main.route("/api/notifications/unread-count", methods=["GET"])
@login_required
def get_unread_notif_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"count": count})


@main.route("/api/notifications/read/<int:notif_id>", methods=["POST"])
@login_required
def read_notification(notif_id):
    notification = Notification.query.get_or_404(notif_id)
    if notification.user_id != current_user.id:
        return jsonify({"error": "Action non autorisée"}), 403
    
    notification.is_read = True
    db.session.commit()
    return jsonify({"status": "success"})


@main.route("/api/notifications/read-all", methods=["POST"])
@login_required
def read_all_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    for notif in notifications:
        notif.is_read = True
    db.session.commit()
    return jsonify({"status": "success"})


@main.route("/api/theme/toggle", methods=["POST"])
@login_required
def toggle_theme():
    # Change le thème en DB
    current_user.theme = "dark" if current_user.theme == "light" else "light"
    db.session.commit()
    return jsonify({"status": "success", "theme": current_user.theme})


# ============================================
# FONCTION HELPER : Crée des notifications n'importe où
# ============================================
def create_notification(user_id, message, type="info"):
    """
    Appelle cette fonction n'importe où dans tes routes (ex: lors de la validation d'une tâche ou d'un streak)
    pour notifier automatiquement ton utilisateur !
    """
    notif = Notification(user_id=user_id, message=message, type=type)
    db.session.add(notif)
    db.session.commit()