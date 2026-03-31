## IN-12: Add due date filtering to the Todo list endpoint

**Jira Ticket:** [IN-12](https://anandinfinity0007.atlassian.net/browse/IN-12)

## Summary
Add date filtering capabilities to the Todo list endpoint with optional due_before and due_after query parameters

## Implementation Plan

**Step 1: Update Route Handler for Date Filtering**  
Modify the GET /todos route to parse and validate due_before and due_after query parameters. Implement date parsing using datetime.fromisoformat() for ISO 8601 validation.
Files: `routes/todos.py`

**Step 2: Implement Repository Query Filtering**  
Update the Todo repository query method to apply date range filters conditionally. Use SQLAlchemy filter conditions to implement due_before and due_after logic.
Files: `repositories/todo_repository.py`

**Step 3: Add Date Validation Middleware**  
Create input validation to return HTTP 422 for invalid date formats. Use try/except with datetime.fromisoformat() to detect parsing errors.
Files: `middleware/validation.py`

**Step 4: Implement Comprehensive Unit Tests**  
Write pytest test cases covering: all todos, todos with due_before, todos with due_after, todos in date range, and invalid date format scenarios.
Files: `tests/test_todos.py`

**Risk Level:** LOW — Low risk modification to existing endpoint. Changes are additive and do not remove existing functionality. Primary risks include potential query performance impact and precise date parsing/validation.

**Deployment Notes:**
- Ensure backward compatibility
- No database schema changes required

## Proposed Code Changes

### `routes/todos.py` (modify)
Modify the route handler to parse and validate optional due_before and due_after query parameters. Pass these parameters to the repository method for filtering.
```python
@@ -1,10 +1,22 @@
 from flask import Blueprint, jsonify, request
 from repositories.todo_repository import TodoRepository
+from datetime import datetime
+from middleware.validation import validate_date_format
 
 todos_bp = Blueprint('todos', __name__)
 
 @todos_bp.route('/todos', methods=['GET'])
 def list_todos():
+    # Parse optional date filter parameters
+    due_before = request.args.get('due_before')
+    due_after = request.args.get('due_after')
+
+    # Validate date formats if provided
+    if due_before:
+        validate_date_format(due_before)
+    if due_after:
+        validate_date_format(due_after)
+
     todo_repository = TodoRepository()
-    todos = todo_repository.list_todos()
+    todos = todo_repository.list_todos(
+        due_before=due_before,
+        due_after=due_after
+    )
     return jsonify([todo.to_dict() for todo in todos])

```

### `repositories/todo_repository.py` (modify)
Update the list_todos method to conditionally apply date range filters using SQLAlchemy query conditions. Convert input dates to datetime for comparison.
```python
@@ -1,10 @@
 from sqlalchemy import select
 from models.todo import Todo
+from datetime import datetime
 
 class TodoRepository:
-    def list_todos(self):
+    def list_todos(self, due_before=None, due_after=None):
         with self.session() as session:
-            query = select(Todo)
+            query = select(Todo)
+            
+            # Apply date filtering conditions
+            if due_before:
+                query = query.where(Todo.due_date <= datetime.fromisoformat(due_before).date())
+            
+            if due_after:
+                query = query.where(Todo.due_date >= datetime.fromisoformat(due_after).date())
+            
             return session.execute(query).scalars().all()

```

### `middleware/validation.py` (create)
Create a middleware function to validate date formats, raising an HTTP 422 error for invalid inputs.
```python
from datetime import datetime
from flask import abort

def validate_date_format(date_str):
    """Validate ISO 8601 date format and raise HTTP 422 for invalid formats.
    
    Args:
        date_str (str): Date string to validate
    
    Raises:
        HTTPException: 422 Unprocessable Entity if date is invalid
    """
    try:
        datetime.fromisoformat(date_str).date()
    except ValueError:
        abort(422, description=f"Invalid date format. Use ISO 8601 (YYYY-MM-DD): {date_str}")

```

### `tests/test_todos.py` (modify)
Add comprehensive unit tests to cover all date filtering scenarios, including edge cases and invalid input validation.
```python
@@ -1,20 +1,65 @@
 import pytest
 from datetime import date, timedelta
 from repositories.todo_repository import TodoRepository
+from routes.todos import list_todos
+from flask import Flask
 
 def test_list_todos():
     todo_repository = TodoRepository()
     todos = todo_repository.list_todos()
     assert len(todos) > 0
 
+def test_list_todos_due_before():
+    app = Flask(__name__)
+    with app.test_request_context('/todos?due_before=2023-12-31'):
+        response = list_todos()
+        todos = response.json
+        assert all(todo['due_date'] <= '2023-12-31' for todo in todos)
+
+def test_list_todos_due_after():
+    app = Flask(__name__)
+    with app.test_request_context('/todos?due_after=2023-01-01'):
+        response = list_todos()
+        todos = response.json
+        assert all(todo['due_date'] >= '2023-01-01' for todo in todos)
+
+def test_list_todos_date_range():
+    app = Flask(__name__)
+    with app.test_request_context('/todos?due_after=2023-01-01&due_before=2023-12-31'):
+        response = list_todos()
+        todos = response.json
+        assert all('2023-01-01' <= todo['due_date'] <= '2023-12-31' for todo in todos)
+
+def test_invalid_date_format():
+    app = Flask(__name__)
+    with pytest.raises(Exception) as excinfo:
+        with app.test_request_context('/todos?due_before=invalid-date'):
+            list_todos()
+    assert '422' in str(excinfo.value)
+
 def test_todo_repository_date_filtering():
     todo_repository = TodoRepository()
-    # Add specific test cases for date filtering
+    
+    # Test filtering todos due before a specific date
+    before_todos = todo_repository.list_todos(due_before='2023-12-31')
+    assert all(todo.due_date <= date(2023, 12, 31) for todo in before_todos)
+    
+    # Test filtering todos due after a specific date
+    after_todos = todo_repository.list_todos(due_after='2023-01-01')
+    assert all(todo.due_date >= date(2023, 1, 1) for todo in after_todos)
+    
+    # Test filtering todos i
... (truncated — see full diff in files)
```

**New Dependencies:**
- `datetime library for date parsing and validation`

## Test Suggestions

Framework: `pytest`

- **test_list_todos_with_due_before_filter** — Verify todos are filtered correctly with due_before parameter
- **test_list_todos_with_due_after_filter** — Verify todos are filtered correctly with due_after parameter
- **test_list_todos_with_both_date_filters** — Verify todos are filtered correctly with both due_before and due_after parameters
- **test_validate_date_filter_invalid_format** *(edge case)* — Verify validation middleware raises error for invalid date format
- **test_list_todos_with_no_matching_dates** *(edge case)* — Verify repository returns empty list when no todos match date filters
- **test_validate_date_filter_future_dates** — Verify validation of future dates in filter parameters

## Confluence Documentation References

- [Template - Product requirements](https://anandinfinity0007.atlassian.net/wiki/spaces/SD/pages/196763) — Generic template with no specific relevance to the Todo list endpoint filtering ticket

**Suggested Documentation Updates:**

- API Documentation
- Todos Endpoint Specification

## AI Confidence Scores
Plan: 85%, Code: 90%, Tests: 90%

---
> ⚠️ **This PR was generated by AI (Claude via AWS Bedrock) and requires thorough human review
> before merging. Verify all logic, test coverage, and edge cases independently.**
>
> _Generated by [Artoo](https://github.com/Telomere-techsupp/SDLCWorker) — by Telomere LLC_
> _© 2025-2026 Telomere LLC. All rights reserved._