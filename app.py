from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import os
import shutil
import zipfile
import moviepy.editor as mp

app = Flask(__name__)

# Configuración para permitir archivos de hasta 500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Carpetas para los archivos
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

video_count = 0  # Número total de videos a subir
uploaded_files = []  # Lista de archivos subidos
trim_seconds = 0  # Segundos a recortar

@app.route('/')
def home():
    """Página de inicio con el botón de empezar"""
    return render_template('welcome.html')

@app.route('/set_video_count_page', methods=['GET', 'POST'])
def set_video_count_page():
    """Página donde el usuario indica cuántos videos quiere subir"""
    return render_template('set_video_count.html')

@app.route('/set_video_count', methods=['POST'])
def set_video_count():
    """Define cuántos videos se subirán y redirige a la subida del primer video."""
    global video_count, uploaded_files
    num_videos = request.form.get("num_videos")
    
    if not num_videos or not num_videos.isdigit():
        return jsonify({"error": "Debes proporcionar un número válido de videos."}), 400
    
    video_count = int(num_videos)
    uploaded_files.clear()
    return redirect(url_for('upload_page', video_index=1))

@app.route('/upload_page/<int:video_index>')
def upload_page(video_index):
    """Página para subir videos uno por uno."""
    return render_template('upload.html', video_index=video_index, total_videos=video_count)

@app.route('/upload', methods=['POST'])
def upload():
    """Sube un video y redirige al siguiente paso o al siguiente video."""
    if 'file' not in request.files:
        return jsonify({"message": "No se encontró archivo"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "Nombre de archivo no válido"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    uploaded_files.append(file_path)

    if len(uploaded_files) < video_count:
        return redirect(url_for('upload_page', video_index=len(uploaded_files) + 1))
    else:
        return redirect(url_for('trim_page'))

@app.route('/trim_page')
def trim_page():
    """Página donde el usuario elige cuántos segundos recortar."""
    return render_template('trim.html')

@app.route('/process', methods=['POST'])
def process_videos():
    """Procesa los videos y los recorta"""
    global trim_seconds
    try:
        trim_seconds = int(request.form.get('trim_seconds', 0))
    except ValueError:
        return jsonify({"message": "Debe ingresar un número válido de segundos."}), 400
    
    if not uploaded_files:
        return jsonify({"message": "No hay videos para procesar."}), 400
    
    shutil.rmtree(PROCESSED_FOLDER, ignore_errors=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    
    for file_path in uploaded_files:
        try:
            clip = mp.VideoFileClip(file_path)
            duration = max(0, clip.duration - trim_seconds)
            new_clip = clip.subclip(0, duration)
            output_path = os.path.join(PROCESSED_FOLDER, os.path.basename(file_path))
            new_clip.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=4, preset="ultrafast")
        except Exception as e:
            return jsonify({"message": f"Error al procesar {file_path}: {str(e)}"}), 500
    
    return redirect(url_for('download_page'))

@app.route('/download_page')
def download_page():
    """Página de descarga del archivo ZIP."""
    return render_template('download.html')

@app.route('/download', methods=['GET'])
def download_zip():
    """Crea y permite la descarga del archivo ZIP"""
    zip_path = os.path.join(PROCESSED_FOLDER, 'processed_videos.zip')
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(PROCESSED_FOLDER):
            for file in files:
                if file != 'processed_videos.zip':
                    zipf.write(os.path.join(root, file), file)
    return send_file(zip_path, as_attachment=True)

@app.route('/reset', methods=['POST'])
def reset():
    """Elimina los archivos y reinicia el proceso"""
    shutil.rmtree(UPLOAD_FOLDER, ignore_errors=True)
    shutil.rmtree(PROCESSED_FOLDER, ignore_errors=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(PROCESSED_FOLDER, exist_ok=True)
    global uploaded_files, video_count
    uploaded_files.clear()
    video_count = 0
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
