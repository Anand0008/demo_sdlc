from flask import Blueprint, request, jsonify
from app.database import get_db
from app.models import Todo

todos_bp = Blueprint("todos", __name__)

@todos_bp.route("/", methods=["GET"])
def list_todos():
    db = get_db()
    try:
        todos = db.query(Todo).all()
        return jsonify([
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "completed": t.completed,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "due_date": t.due_date.isoformat() if t.due_date else None
            } for t in todos
        ]), 200
    finally:
        db.close()

@todos_bp.route("/", methods=["POST"])
def create_todo():
    # Read title and description from request JSON or form args (to cover the guide's test parameters)
    data = request.get_json(silent=True) or {}
    title = data.get("title") or request.args.get("title")
    description = data.get("description") or request.args.get("description")
    
    if not title:
        return jsonify({"detail": "Title is required"}), 422
        
    db = get_db()
    try:
        todo = Todo(
            title=title,
            description=description
        )
        db.add(todo)
        db.commit()
        db.refresh(todo)
        return jsonify({
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "completed": todo.completed,
            "created_at": todo.created_at.isoformat() if todo.created_at else None,
            "due_date": todo.due_date.isoformat() if todo.due_date else None
        }), 201
    finally:
        db.close()

@todos_bp.route("/<int:todo_id>/complete", methods=["PUT"])
def complete_todo(todo_id):
    db = get_db()
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            return jsonify({"detail": "Todo not found"}), 404
        todo.completed = True
        db.commit()
        return jsonify({
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "completed": todo.completed,
            "created_at": todo.created_at.isoformat() if todo.created_at else None,
            "due_date": todo.due_date.isoformat() if todo.due_date else None
        }), 200
    finally:
        db.close()
