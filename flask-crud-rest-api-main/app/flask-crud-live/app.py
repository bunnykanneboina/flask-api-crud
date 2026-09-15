from flask import Flask, request, jsonify, make_response, render_template
from flask_sqlalchemy import SQLAlchemy
from os import environ

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("DB_URL", "sqlite:///users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def json(self):
        return {"id": self.id, "username": self.username, "email": self.email}


with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/test", methods=["GET"])
def test():
    return make_response(jsonify({"message": "test route"}), 200)


@app.route("/users", methods=["POST"])
def create_user():
    try:
        data = request.get_json()
        if not data or "username" not in data or "email" not in data:
            return make_response(jsonify({"message": "username and email are required"}), 400)

        new_user = User(username=data["username"], email=data["email"])
        db.session.add(new_user)
        db.session.commit()
        return make_response(jsonify({"message": "user created"}), 201)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "error creating user"}), 500)


@app.route("/users", methods=["GET"])
def get_users():
    try:
        users = User.query.all()
        return make_response(jsonify([user.json() for user in users]), 200)
    except Exception:
        return make_response(jsonify({"message": "error getting users"}), 500)


@app.route("/users/<int:id>", methods=["GET"])
def get_user(id):
    try:
        user = User.query.filter_by(id=id).first()
        if user:
            return make_response(jsonify({"user": user.json()}), 200)
        return make_response(jsonify({"message": "user not found"}), 404)
    except Exception:
        return make_response(jsonify({"message": "error getting user"}), 500)


@app.route("/users/<int:id>", methods=["PUT"])
def update_user(id):
    try:
        user = User.query.filter_by(id=id).first()
        if not user:
            return make_response(jsonify({"message": "user not found"}), 404)

        data = request.get_json()
        if not data:
            return make_response(jsonify({"message": "no data provided"}), 400)

        user.username = data.get("username", user.username)
        user.email = data.get("email", user.email)
        db.session.commit()
        return make_response(jsonify({"message": "user updated"}), 200)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "error updating user"}), 500)


@app.route("/users/<int:id>", methods=["DELETE"])
def delete_user(id):
    try:
        user = User.query.filter_by(id=id).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            return make_response(jsonify({"message": "user deleted"}), 200)
        return make_response(jsonify({"message": "user not found"}), 404)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "error deleting user"}), 500)


if __name__ == "__main__":
    app.run(debug=True)
