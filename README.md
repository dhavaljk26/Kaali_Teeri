# Kaali_Teeri
Game of 3 of spades

## Requirements for installation
```
pip3 install flask flask-sqlalchemy flask-login
```

## To create the db.sqlite file (database) open a Python Shell/REPL
```
from Kaali_Teeri import db, create_app
app=create_app()
with app.app_context():
    db.create_all()
```

## To run the app
```
export FLASK_APP=Kaali_Teeri
export FLASK_DEBUG=1
flask run
```
