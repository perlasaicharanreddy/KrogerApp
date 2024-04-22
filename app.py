from flask import Flask, request, render_template, redirect, session, url_for
import os
import re
import mysql.connector
import pandas as pd
from mysql.connector import errorcode
from flask_session import Session

app = Flask(__name__)
app.secret_key = '@dkjgfjgfhkj jxbjljv kjxgvljklkj'
dir_path = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(dir_path, 'static', 'files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


config = {
    'host': 'deepaserver.mysql.database.azure.com',
    'user': 'sudha',
    'password': 'Sai@2000',
    'database': 'cloudcomputing',
    'port': 3306,
}

def get_https_url(item,data):
    return url_for(item,username=data,_external=True, _scheme='http')

@app.route('/',methods=['GET','POST'])
def homepage():
    msg=''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username'] 
        password = request.form['password']
        conn = mysql.connector.connect(**config)
        print("connection established")
        cur = conn.cursor()
        print(username,password)
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password, ))
        user = cur.fetchone()
        if user: 
            session['loggedin'] = True
            session['username'] = username
            return redirect(get_https_url('profile',username))
        else:
            # Account doesnt exist
            msg = 'Incorrect username/password!'
    return render_template("homepage.html",msg=msg)
    

@app.route('/logout')
def logout():
   session.pop('username', None)
   return render_template("homepage.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        conn = mysql.connector.connect(**config)
        cur = conn.cursor()
        print(username, password, email)
        cur.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cur.fetchone()
        if user:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cur.execute('INSERT INTO users VALUES (%s, %s,%s)', (username, password, email))
            conn.commit()
            session['loggedin'] = True
            session['username'] = username
            return redirect(get_https_url('profile',username))
    return render_template("register.html",msg=msg)
            

@app.route('/profile/<string:username>',methods=['GET','POST'])
def profile(username):
    if 'loggedin' in session:
        return render_template('profile.html',username=username) 
    return redirect(get_https_url('homepage'))

@app.route('/Search', methods=['GET','POST'])
def Search():
    msg = ''
    if request.method == 'POST' and 'search' in request.form :
        print("came to search[POST]")
        number = request.form['search']
        if not re.match(r'\d+', number):
             msg = "enter a valid household number"
        else:
            conn = mysql.connector.connect(**config)
            cur = conn.cursor()
            cur.execute("SELECT h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, p.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY,t.SPEND, t.UNITS, t.STORE_R, t.WEEK_NUM, t.YEAR, h.L, h.AGE_RANGE,h.MARITAL,h.INCOME_RANGE, h.HOMEOWNER, h.HSHD_COMPOSITION, h.HH_SIZE, h.CHILDREN FROM households AS h JOIN transactions AS t ON h.HSHD_NUM = t.HSHD_NUM JOIN Products AS p ON t.PRODUCT_NUM = p.PRODUCT_NUM where h.HSHD_NUM=%s ORDER BY h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, p.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY",(number,))
            data=cur.fetchall()
            if data:
                return render_template('Search.html', data= data)
            else:
                msg="Not Data Found for the input "
                return render_template('Search.html', msg=msg)
        return render_template('Search.html', msg=msg)
    else:
        print("came to search[GET]")
        conn = mysql.connector.connect(**config)
        print("connected to database")
        cur = conn.cursor()
        testquery="SELECT h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, p.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY,t.SPEND, t.UNITS, t.STORE_R, t.WEEK_NUM, t.YEAR, h.L, h.AGE_RANGE,h.MARITAL,h.INCOME_RANGE, h.HOMEOWNER, h.HSHD_COMPOSITION, h.HH_SIZE, h.CHILDREN FROM households AS h JOIN transactions AS t ON h.HSHD_NUM = t.HSHD_NUM JOIN Products AS p ON t.PRODUCT_NUM = p.PRODUCT_NUM ORDER BY h.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, p.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY"
        cur.execute(testquery)
        print("test query executed")
        data=cur.fetchmany(1000)
        print("data fetched")
        return render_template('Search.html', data= data)
    

@app.route('/dashboard')
def dashboard():
   return render_template("dashboard.html")

@app.route('/upload', methods=['GET','POST'])
def upload():
    msg = ''
    if request.method == 'POST':
        hdata=request.files['households']
        tdata=request.files['transactions']
        pdata=request.files['products']
        conn = mysql.connector.connect(**config)
        cur = conn.cursor()
        if hdata.filename == '' or tdata.filename == '' or pdata.filename == '' :
            msg='No Files passed'
            return render_template('upload.html', msg=msg)
        else:
            #household data
            file_path = os.path.join(app.config['UPLOAD_FOLDER'],hdata.filename)
            hdata.save(file_path)
            col_names=['HSHD_NUM','L','AGE_RANGE','MARITAL','INCOME_RANGE','HOMEOWNER','HSHD_COMPOSITION','HH_SIZE','CHILDREN']
            csvData = pd.read_csv(file_path,names=col_names,header=0)
            query='INSERT INTO households (HSHD_NUM,L,AGE_RANGE,MARITAL,INCOME_RANGE,HOMEOWNER,HSHD_COMPOSITION,HH_SIZE,CHILDREN) VALUES'
            for i,row in csvData.iterrows():
                if(pd.isna(row['CHILDREN'])):
                    query += '{},'.format((row['HSHD_NUM'],row['L'],row['AGE_RANGE'],row['MARITAL'],row['INCOME_RANGE'],row['HOMEOWNER'],row['HSHD_COMPOSITION'],row['HH_SIZE'],'null'))
                else :
                    query += '{},'.format((row['HSHD_NUM'],row['L'],row['AGE_RANGE'],row['MARITAL'],row['INCOME_RANGE'],row['HOMEOWNER'],row['HSHD_COMPOSITION'],row['HH_SIZE'],row['CHILDREN']))
            query = query[:len(query)-1]
            cur.execute(query)


            #transaction data
            file_path = os.path.join(app.config['UPLOAD_FOLDER'],tdata.filename)
            tdata.save(file_path)
            print("file path",file_path)
            col_names=['BASKET_NUM','HSHD_NUM','PURCHASE_','PRODUCT_NUM','SPEND','UNITS','STORE_R','WEEK_NUM','YEAR']
            csvData = pd.read_csv(file_path,names=col_names,header=0,nrows=10000)
            query='INSERT INTO transactions (BASKET_NUM,PURCHASE_,SPEND,UNITS,STORE_R,WEEK_NUM,YEAR,HSHD_NUM,PRODUCT_NUM) VALUES'
            for i,row in csvData.iterrows():
                query += '{},'.format((row['BASKET_NUM'],row['PURCHASE_'],row['SPEND'],row['UNITS'],row['STORE_R'],row['WEEK_NUM'],row['YEAR'],row['HSHD_NUM'],row['PRODUCT_NUM']))
            query = query[:len(query)-1]
            cur.execute(query)


            # Products data
            file_path = os.path.join(app.config['UPLOAD_FOLDER'],pdata.filename)
            pdata.save(file_path)
            col_names=['PRODUCT_NUM','DEPARTMENT','COMMODITY','BRAND_TY','NATURAL_ORGANIC_FLAG']
            csvData = pd.read_csv(file_path,names=col_names,header=0)
            query='INSERT INTO products (PRODUCT_NUM,DEPARTMENT,COMMODITY,BRAND_TY,NATURAL_ORGANIC_FLAG) VALUES'
            for i,row in csvData.iterrows():
                query += '{},'.format((row['PRODUCT_NUM'],row['DEPARTMENT'],row['COMMODITY'],row['BRAND_TY'],row['NATURAL_ORGANIC_FLAG']))
            query = query[:len(query)-1]
            cur.execute(query)
            
            conn.commit()
            msg='Sucessfully Inserted data !!!!!'
            print(msg)
            return render_template("upload.html", msg=msg)
    else:
        msg="unable to insert data"
        return render_template("upload.html")
    
    
if __name__=="__main__":
    app.run(host="0.0.0.0",port=8001)