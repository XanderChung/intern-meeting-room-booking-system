import os

# Give the test process its own key before any tests import app.py.
os.environ["SECRET_KEY"] = "test-only-key"