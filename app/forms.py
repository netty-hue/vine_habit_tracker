from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class InscriptionForm(FlaskForm):
    nom = StringField("Nom complet", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    mot_de_passe = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=6)])
    confirmation = PasswordField(
        "Confirmer le mot de passe",
        validators=[DataRequired(), EqualTo("mot_de_passe", message="Les mots de passe ne correspondent pas")]
    )
    submit = SubmitField("S'inscrire")


class ConnexionForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    mot_de_passe = PasswordField("Mot de passe", validators=[DataRequired()])
    submit = SubmitField("Se connecter")


class TacheForm(FlaskForm):
    titre = StringField("Nouvelle tâche", validators=[DataRequired(), Length(max=140)])
    submit = SubmitField("Ajouter")
