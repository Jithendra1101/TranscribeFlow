from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv
import os
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from transcribe import transcribe_audio
from summarize import summarize_text


# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///users.db')
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'upload')
app.config['TRANSCRIBES_FOLDER'] = os.path.join(os.path.dirname(__file__), 'transcribes')
app.config['MAX_CONTENT_LENGTH'] = 35 * 1024 * 1024  # 35MB max upload

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Server-side one-time result store (keyed by UUID, cleared after one GET)
# Fine for single-worker dev/demo use; swap for Redis/DB in production.
_result_store: dict = {}

class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(150), unique=True, nullable=False)
	email = db.Column(db.String(150), unique=True, nullable=False)
	password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))


def process_audio_upload(uploaded_file):
	if uploaded_file is None:
		return {
			'success': False,
			'status_code': 400,
			'error': 'No file provided in request under key "audio".'
		}

	if uploaded_file.filename == '':
		return {
			'success': False,
			'status_code': 400,
			'error': 'No selected file.'
		}

	filename = secure_filename(uploaded_file.filename)
	os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
	os.makedirs(app.config['TRANSCRIBES_FOLDER'], exist_ok=True)

	uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
	uploaded_file.save(uploaded_path)

	transcription_result = transcribe_audio(uploaded_path, app.config['TRANSCRIBES_FOLDER'])
	if not transcription_result['success']:
		return {
			'success': False,
			'status_code': 500,
			'error': f"Transcription failed: {transcription_result['error']}"
		}

	transcript = transcription_result['text']
	try:
		summary = summarize_text(transcript)
	except Exception as exc:
		return {
			'success': False,
			'status_code': 500,
			'error': f'Summarization failed: {str(exc)}'
		}

	return {
		'success': True,
		'status_code': 200,
		'original_filename': filename,
		'txt_filename': transcription_result['filename'],
		'transcript': transcript,
		'summary': summary
	}



# --- Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
	if request.method == 'POST':
		username = request.form['username']
		email = request.form['email']
		password = request.form['password']
		if User.query.filter((User.username == username) | (User.email == email)).first():
			flash('Username or email already exists')
			return render_template('signup.html')
		hashed_pw = generate_password_hash(password)
		user = User(username=username, email=email, password=hashed_pw)
		db.session.add(user)
		db.session.commit()
		flash('Signup successful! Please login.')
		return redirect(url_for('login'))
	return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		user = User.query.filter_by(username=username).first()
		if not user:
			user = User.query.filter_by(email=username).first()
		if user and check_password_hash(user.password, password):
			login_user(user)
			return redirect(url_for('home'))
		flash('Invalid username/email or password')
	return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
	if request.method == 'POST':
		upload_result = process_audio_upload(request.files.get('audio'))
		if upload_result['success']:
			# Store large result server-side; put only a tiny UUID key in the cookie
			result_id = str(uuid.uuid4())
			_result_store[result_id] = {
				'transcript': upload_result['transcript'],
				'summary': upload_result['summary'],
				'original_filename': upload_result['original_filename'],
				'txt_filename': upload_result['txt_filename'],
			}
			session['result_id'] = result_id
			return redirect(url_for('home'))
		else:
			flash(upload_result['error'])
			return redirect(url_for('home'))

	# GET – pop result from server-side store (gone on next refresh)
	result_id = session.pop('result_id', None)
	result = _result_store.pop(result_id, None) if result_id else None
	return render_template(
		'home.html',
		success=result is not None,
		transcribed_text=result['transcript'] if result else None,
		summary_text=result['summary'] if result else None,
		original_filename=result['original_filename'] if result else None,
		txt_filename=result['txt_filename'] if result else None,
	)


@app.route('/upload', methods=['POST'])
@login_required
def upload_audio_api():
	upload_result = process_audio_upload(request.files.get('audio'))
	if not upload_result['success']:
		return jsonify({'error': upload_result['error']}), upload_result['status_code']

	return jsonify({
		'transcript': upload_result['transcript'],
		'summary': upload_result['summary'],
		'transcript_file': upload_result['txt_filename'],
		'original_filename': upload_result['original_filename']
	}), 200

if __name__ == '__main__':
	with app.app_context():
		db.create_all()
	app.run(debug=True)
