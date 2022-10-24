import os
import psycopg2
from flask import jsonify, make_response, Flask, flash, render_template, request, url_for, redirect
from werkzeug.utils import secure_filename
import pandas as pd

# Update your folder to save the file will upload
UPLOAD_FOLDER = '/home/tony/PycharmProjects/dockerizing-flask-postgresql/uploads'
ALLOWED_EXTENSIONS = {'xlsx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000


def get_db_connection():
    conn = psycopg2.connect(host='localhost',
                            database='flask_db',
                            user=os.environ['DB_USERNAME'],
                            password=os.environ['DB_PASSWORD'])
    return conn


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/uploader', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            upload_file_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            df = pd.read_excel(upload_file_url)

            conn = get_db_connection()
            cur = conn.cursor()
            for i in df.index:
                cur.execute('SELECT * FROM books')
                for book in cur.fetchall():
                    book_id = int(df['book_id'][i])
                    if book_id == book[0]:
                        # Delete book from books tables
                        cur.execute('DELETE FROM books WHERE id = %s;', (book_id,))
                        cur.execute('DELETE FROM categories WHERE book_id = %s;', (book_id,))

                        cur.execute('INSERT INTO books (title, author, pages_num, review)'
                                    'VALUES (%s, %s, %s, %s) RETURNING id;',
                                    (df['title'][i],
                                     df['author'][i],
                                     int(df['pages_number'][i]),
                                     df['review'][i])
                                    )
                        id_of_new_row = cur.fetchone()[0]
                        cur.execute('INSERT INTO categories (name, book_id)'
                                    'VALUES (%s, %s)',
                                    (df['name'][i], id_of_new_row)
                                    )

            conn.commit()
            cur.close()
            conn.close()

        return make_response(
            jsonify({
                'msg': f"File {filename} uploaded successfully"
            }), 200)


@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM books;')
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', books=books)


@app.route('/create/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        pages_num = int(request.form['pages_num'])
        review = request.form['review']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO books (title, author, pages_num, review)'
                    'VALUES (%s, %s, %s, %s)',
                    (title, author, pages_num, review))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))

    return render_template('create.html')


@app.route('/about/')
def about():
    return render_template('about.html')
