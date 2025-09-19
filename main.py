import flask
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__, static_folder='static', template_folder='templates')


@app.route('/')
def mainpage():
    return(render_template('main.html'))

@app.route('/login')
def loginpage():
    return(render_template('login.html'))

@app.route('/registration')
def registerpage():
    return(render_template('register.html'))




@app.errorhandler(404)
def notfound(e):
    return(render_template('404.html')), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)