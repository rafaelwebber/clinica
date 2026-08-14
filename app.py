from flask import Flask
from db import SessionLocal, engine, Base

from api.admin import bp as admin

app = Flask(__name__)

Base.metadata.create_all(bind=engine)

# @app.route.route("/")
# def home():
#     return "ok"

app.register_blueprint(admin)

if __name__ == "__main__":
    app.run(debug=True)