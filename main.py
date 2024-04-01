# from __init__ import create_app
#
# app = create_app()
# # main driver function
# if __name__ == '__main__':
#     app.run(debug=True)
# from flask import Flask

from flask import Flask, render_template
from views import views


def create_app():
    app = Flask("Fish Tank camera webserver")
    app.config['SECRET_KEY'] = 'secret'
    # app.register_blueprint(views)

    return app


# EB looks for an 'application' callable by default.
application = create_app()


@application.route('/', methods=['POST', 'GET'])
def mainPage():
    return render_template('Base.html')


@application.route('/Stream', methods=['POST', 'GET'])
def streamPage():
    return render_template('Base.html')


# run the app.
if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.

    application.debug = True
    application.run()
