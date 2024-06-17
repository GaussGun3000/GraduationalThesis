from flask import Flask
from app import create_app

app = create_app()


@app.route('/')
def hello_world():  # put application's code here
    return 'API module is running'


if __name__ == '__main__':
    app.run()
