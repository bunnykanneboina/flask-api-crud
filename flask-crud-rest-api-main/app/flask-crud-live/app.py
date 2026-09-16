from flask import Flask, request, jsonify, make_response, render_template
from flask_sqlalchemy import SQLAlchemy
from os import environ
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = environ.get("DB_URL", "sqlite:///incidents.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    incident_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Open")
    priority = db.Column(db.String(20), nullable=False, default="Medium")
    affected_system = db.Column(db.String(120), nullable=False)
    reported_by = db.Column(db.String(100), nullable=False)
    assigned_to = db.Column(db.String(100), nullable=False)
    detection_date = db.Column(db.DateTime, nullable=False)
    resolution_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def json(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "incident_type": self.incident_type,
            "severity": self.severity,
            "status": self.status,
            "priority": self.priority,
            "affected_system": self.affected_system,
            "reported_by": self.reported_by,
            "assigned_to": self.assigned_to,
            "detection_date": self.detection_date.isoformat() if self.detection_date else None,
            "resolution_date": self.resolution_date.isoformat() if self.resolution_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/test", methods=["GET"])
def test():
    return make_response(jsonify({"message": "Cybersecurity Incident API is running"}), 200)


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def validate_incident_data(data, partial=False):
    required = [
        "title", "description", "incident_type", "severity", "status",
        "priority", "affected_system", "reported_by", "assigned_to", "detection_date"
    ]

    if not data:
        return "Request body is required"

    if not partial:
        missing = [field for field in required if not data.get(field)]
        if missing:
            return "Missing required fields: " + ", ".join(missing)

    for field in ["severity", "status", "priority", "incident_type"]:
        if field in data and not str(data[field]).strip():
            return f"{field} cannot be empty"

    if "detection_date" in data and data.get("detection_date") and not parse_date(data["detection_date"]):
        return "Invalid detection date"

    if "resolution_date" in data and data.get("resolution_date") and not parse_date(data["resolution_date"]):
        return "Invalid resolution date"

    allowed_severity = {"Low", "Medium", "High", "Critical"}
    allowed_status = {"Open", "Investigating", "Contained", "Resolved", "Closed"}
    allowed_priority = {"Low", "Medium", "High", "Critical"}

    if data.get("severity") not in allowed_severity:
        return "Invalid severity"
    if data.get("status") not in allowed_status:
        return "Invalid status"
    if data.get("priority") not in allowed_priority:
        return "Invalid priority"

    return None


@app.route("/incidents", methods=["POST"])
def create_incident():
    try:
        data = request.get_json(silent=True)
        error = validate_incident_data(data)
        if error:
            return make_response(jsonify({"message": error}), 400)

        last_incident = Incident.query.order_by(Incident.id.desc()).first()
        next_number = (last_incident.id + 1) if last_incident else 1
        incident_id = f"INC-{next_number:03d}"

        while Incident.query.filter_by(incident_id=incident_id).first():
            next_number += 1
            incident_id = f"INC-{next_number:03d}"

        incident = Incident(
            incident_id=incident_id,
            title=str(data["title"]).strip(),
            description=str(data["description"]).strip(),
            incident_type=str(data["incident_type"]).strip(),
            severity=data["severity"],
            status=data["status"],
            priority=data["priority"],
            affected_system=str(data["affected_system"]).strip(),
            reported_by=str(data["reported_by"]).strip(),
            assigned_to=str(data["assigned_to"]).strip(),
            detection_date=parse_date(data["detection_date"]),
            resolution_date=parse_date(data.get("resolution_date"))
        )

        db.session.add(incident)
        db.session.commit()
        return make_response(jsonify({"message": "Incident reported successfully", "incident": incident.json()}), 201)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "Error reporting incident"}), 500)


@app.route("/incidents", methods=["GET"])
def get_incidents():
    try:
        query = Incident.query
        severity = request.args.get("severity")
        status = request.args.get("status")
        keyword = request.args.get("keyword", "").strip()

        if severity and severity != "All":
            query = query.filter_by(severity=severity)
        if status and status != "All":
            query = query.filter_by(status=status)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                db.or_(
                    Incident.incident_id.ilike(pattern),
                    Incident.title.ilike(pattern),
                    Incident.incident_type.ilike(pattern),
                    Incident.affected_system.ilike(pattern),
                    Incident.reported_by.ilike(pattern),
                    Incident.assigned_to.ilike(pattern)
                )
            )

        incidents = query.order_by(Incident.id.desc()).all()
        return make_response(jsonify([incident.json() for incident in incidents]), 200)
    except Exception:
        return make_response(jsonify({"message": "Error getting incidents"}), 500)


@app.route("/incidents/<int:id>", methods=["GET"])
def get_incident(id):
    try:
        incident = db.session.get(Incident, id)
        if not incident:
            return make_response(jsonify({"message": "Incident not found"}), 404)
        return make_response(jsonify({"incident": incident.json()}), 200)
    except Exception:
        return make_response(jsonify({"message": "Error getting incident"}), 500)


@app.route("/incidents/<int:id>", methods=["PUT"])
def update_incident(id):
    try:
        incident = db.session.get(Incident, id)
        if not incident:
            return make_response(jsonify({"message": "Incident not found"}), 404)

        data = request.get_json(silent=True)
        error = validate_incident_data(data, partial=True)
        if error:
            return make_response(jsonify({"message": error}), 400)

        fields = [
            "title", "description", "incident_type", "severity", "status",
            "priority", "affected_system", "reported_by", "assigned_to"
        ]

        for field in fields:
            if field in data:
                setattr(incident, field, str(data[field]).strip() if isinstance(data[field], str) else data[field])

        if "detection_date" in data:
            incident.detection_date = parse_date(data["detection_date"])
        if "resolution_date" in data:
            incident.resolution_date = parse_date(data["resolution_date"])

        if incident.status in {"Resolved", "Closed"} and not incident.resolution_date:
            incident.resolution_date = datetime.utcnow()
        elif incident.status not in {"Resolved", "Closed"}:
            incident.resolution_date = None

        db.session.commit()
        return make_response(jsonify({"message": "Incident managed successfully", "incident": incident.json()}), 200)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "Error updating incident"}), 500)


@app.route("/incidents/<int:id>", methods=["DELETE"])
def archive_incident(id):
    try:
        incident = db.session.get(Incident, id)
        if not incident:
            return make_response(jsonify({"message": "Incident not found"}), 404)

        db.session.delete(incident)
        db.session.commit()
        return make_response(jsonify({"message": "Incident archived successfully"}), 200)
    except Exception:
        db.session.rollback()
        return make_response(jsonify({"message": "Error archiving incident"}), 500)


@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        total = Incident.query.count()
        open_count = Incident.query.filter_by(status="Open").count()
        investigating = Incident.query.filter_by(status="Investigating").count()
        resolved = Incident.query.filter(Incident.status.in_(["Resolved", "Closed"])).count()
        critical = Incident.query.filter_by(severity="Critical").count()
        high = Incident.query.filter_by(severity="High").count()

        return make_response(jsonify({
            "total_incidents": total,
            "open_incidents": open_count,
            "investigating_incidents": investigating,
            "resolved_incidents": resolved,
            "critical_incidents": critical,
            "high_incidents": high
        }), 200)
    except Exception:
        return make_response(jsonify({"message": "Error getting dashboard statistics"}), 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 4000)), debug=True)
