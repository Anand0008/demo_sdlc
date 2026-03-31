from flask import Flask
from api_design_standards.auth import auth_bp
from api_design_standards.security_headers import apply_security_headers
from health_check_and_readiness_probe.health import health_bp
from request_tracing_x_request_id.middleware import apply_request_id
from database_schema_and_migrations.cache import cache
from app.routes.todos import todos_bp
from app.database import init_db

app = Flask(__name__)

# Register middleware
apply_security_headers(app)
apply_request_id(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(health_bp)
app.register_blueprint(todos_bp, url_prefix="/todos")

# Initialize database
with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
