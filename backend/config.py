import os

class Config:
    SECRET_KEY = 'w1udc9hnwud0nu9h10snusad9zn9-n'  # Replace with a secure secret key
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OAUTHLIB_INSECURE_TRANSPORT = True  # Only for development (HTTP). Remove in production.
