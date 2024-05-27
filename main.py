from flask import Flask
from views import views


def create_app():
    app = Flask("Fish Tank camera webserver")
    app.config['SECRET_KEY'] = 'secret'
    app.register_blueprint(views)

    return app


application = create_app()

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000, threaded=True, ssl_context=('/fullchain.pem',
                                                                           '/privkey.pem'))
