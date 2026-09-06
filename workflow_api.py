import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, jsonify, request


WORKFLOW_FILE = os.environ.get("WORKFLOW_FILE", "workflows.json")
VALID_STATUSES = {"pending", "in_progress", "completed", "submitted"}


def load_workflows(file_path=WORKFLOW_FILE):
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_workflows(workflows, file_path=WORKFLOW_FILE):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(workflows, file, indent=2)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def create_app(file_path=WORKFLOW_FILE):
    app = Flask(__name__)

    def read_workflows():
        return load_workflows(file_path)

    def write_workflows(workflows):
        save_workflows(workflows, file_path)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/workflows")
    def list_workflows():
        status = request.args.get("status")
        workflows = read_workflows()
        if status:
            if status not in VALID_STATUSES:
                return jsonify({"error": "Invalid workflow status."}), 400
            workflows = [workflow for workflow in workflows if workflow["status"] == status]
        return jsonify(workflows)

    @app.post("/api/workflows")
    def add_workflow():
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title", "")).strip()
        if not title:
            return jsonify({"error": "title is required."}), 400

        workflow = {
            "id": str(uuid4()),
            "title": title,
            "description": str(payload.get("description", "")).strip(),
            "status": "pending",
            "created_at": now_iso(),
            "completed_at": None,
            "submitted_at": None,
        }
        workflows = read_workflows()
        workflows.append(workflow)
        write_workflows(workflows)
        return jsonify(workflow), 201

    @app.post("/api/workflows/<workflow_id>/complete")
    def complete_workflow(workflow_id):
        workflows = read_workflows()
        workflow = next((item for item in workflows if item["id"] == workflow_id), None)
        if workflow is None:
            return jsonify({"error": "Workflow not found."}), 404
        if workflow["status"] == "submitted":
            return jsonify({"error": "Submitted workflows cannot be changed."}), 409

        workflow["status"] = "completed"
        workflow["completed_at"] = now_iso()
        write_workflows(workflows)
        return jsonify(workflow)

    @app.post("/api/workflows/<workflow_id>/submit")
    def submit_workflow(workflow_id):
        workflows = read_workflows()
        workflow = next((item for item in workflows if item["id"] == workflow_id), None)
        if workflow is None:
            return jsonify({"error": "Workflow not found."}), 404
        if workflow["status"] != "completed":
            return jsonify({"error": "Only completed workflows can be submitted."}), 409

        workflow["status"] = "submitted"
        workflow["submitted_at"] = now_iso()
        write_workflows(workflows)
        return jsonify(workflow)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)