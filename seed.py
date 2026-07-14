from datetime import datetime, timedelta
import random

from app import create_app, db
from app.models import (
    User,
    Goal,
    Habit,
    HabitLog,
    TodoItem,
    DailyProgress
)

app = create_app()

with app.app_context():

    print("Suppression des anciennes données...")

    HabitLog.query.delete()
    Habit.query.delete()
    Goal.query.delete()
    TodoItem.query.delete()
    DailyProgress.query.delete()
    User.query.delete()

    db.session.commit()

    # =====================================================
    # UTILISATEUR
    # =====================================================

    user = User(
        username="ludovic",
        email="ludovic@test.com",
        theme="light",
        current_streak=18
    )

    user.set_password("password")

    db.session.add(user)
    db.session.commit()

    # =====================================================
    # OBJECTIFS
    # =====================================================

    objectifs = [

        Goal(
            user_id=user.id,
            title="Améliorer ma santé",
            description="Créer une routine quotidienne saine.",
            type="long_terme",
            task_limit=5
        ),

        Goal(
            user_id=user.id,
            title="Développer mes compétences Python",
            description="Coder chaque jour.",
            type="long_terme",
            task_limit=6
        ),

        Goal(
            user_id=user.id,
            title="Lire davantage",
            description="Lire au moins 20 minutes par jour.",
            type="court_terme",
            task_limit=3
        )

    ]

    db.session.add_all(objectifs)
    db.session.commit()

    # =====================================================
    # HABITUDES
    # =====================================================

    habitudes = [

        Habit(
            user_id=user.id,
            goal_id=objectifs[0].id,
            title="Boire 2L d'eau",
            why="Mieux hydrater mon corps",
            expected_result="Plus d'énergie",
            schedule_days="Lun,Mar,Mer,Jeu,Ven,Sam,Dim",
            schedule_time="08:00",
            duration=5,
            current_streak=14,
            max_streak=21
        ),

        Habit(
            user_id=user.id,
            goal_id=objectifs[0].id,
            title="Faire 30 minutes de sport",
            why="Améliorer ma condition physique",
            expected_result="Perdre du poids",
            schedule_days="Lun,Mer,Ven",
            schedule_time="18:00",
            duration=30,
            current_streak=7,
            max_streak=15
        ),

        Habit(
            user_id=user.id,
            goal_id=objectifs[1].id,
            title="Coder 1 heure",
            why="Devenir développeur confirmé",
            expected_result="Créer des applications",
            schedule_days="Lun,Mar,Mer,Jeu,Ven",
            schedule_time="20:00",
            duration=60,
            current_streak=20,
            max_streak=25
        ),

        Habit(
            user_id=user.id,
            goal_id=objectifs[2].id,
            title="Lire 20 minutes",
            why="Développer mes connaissances",
            expected_result="Lire 12 livres cette année",
            schedule_days="Tous les jours",
            schedule_time="21:00",
            duration=20,
            current_streak=12,
            max_streak=18
        )

    ]

    db.session.add_all(habitudes)
    db.session.commit()

    # =====================================================
    # LOGS DES HABITUDES (30 jours)
    # =====================================================

    aujourd_hui = datetime.utcnow()

    for habit in habitudes:

        streak = 0

        for i in range(30):

            jour = aujourd_hui - timedelta(days=i)

            # 80 % de réussite
            if random.random() < 0.80:

                db.session.add(

                    HabitLog(
                        habit_id=habit.id,
                        date_completed=jour
                    )

                )

                streak += 1

    db.session.commit()

    # =====================================================
    # TODO LIST
    # =====================================================

    todos = [

        TodoItem(
            user_id=user.id,
            title="Préparer le petit déjeuner",
            description="Repas équilibré",
            creneau="matin",
            deadline=datetime.utcnow().date()
        ),

        TodoItem(
            user_id=user.id,
            title="Réviser Flask",
            description="Routes et Blueprints",
            creneau="apres-midi",
            deadline=datetime.utcnow().date()
        ),

        TodoItem(
            user_id=user.id,
            title="Faire une marche",
            description="45 minutes",
            creneau="soir",
            deadline=datetime.utcnow().date()
        ),

        TodoItem(
            user_id=user.id,
            title="Méditation",
            description="10 minutes",
            creneau="soir",
            deadline=datetime.utcnow().date(),
            is_completed=True,
            completed_at=datetime.utcnow()
        )

    ]

    db.session.add_all(todos)
    db.session.commit()

    # =====================================================
    # PROGRESSION SUR 30 JOURS
    # =====================================================

    for i in range(30):

        date = datetime.utcnow().date() - timedelta(days=i)

        progression = DailyProgress(

            user_id=user.id,

            date=date,

            completion_rate=random.randint(55, 100)

        )

        db.session.add(progression)

    db.session.commit()

    print("===================================")
    print("Base de données alimentée avec succès.")
    print("Utilisateur : ludovic@test.com")
    print("Mot de passe : password")
    print("3 objectifs")
    print("4 habitudes")
    print("30 jours de statistiques")
    print("4 tâches")
    print("===================================")