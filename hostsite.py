import os
from flask import Flask, request, redirect, render_template, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import base64
from PIL import Image
import io

def run():
    # Initialize the Flask app
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = 'players'  # Replace with your game directory
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Secret key for secure sessions (change this to a random string)
    app.secret_key = 'your-secret-key-here'  # Changed from the inappropriate original

    # Helper function to check file extension
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    # Helper function to sanitize filename while preserving original format
    def sanitize_filename(filename):
        # Only remove truly dangerous characters, keep spaces and case
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        sanitized = filename.strip()
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        # Remove leading/trailing dots to prevent hidden files
        sanitized = sanitized.strip('.')
        return sanitized

    @app.route('/')
    def upload_form():
        return render_template('upload.html')

    @app.route('/upload', methods=['POST'])
    def upload_file():
        try:
            if 'file' not in request.files:
                flash('No file uploaded')
                return redirect(request.url)

            file = request.files['file']
            filename = request.form.get('filename', '').strip()

            if not filename:
                flash('Please provide a filename')
                return redirect(request.url)

            if file.filename == '':
                flash('No file selected')
                return redirect(request.url)

            if file and allowed_file(file.filename):
                # Sanitize the filename while preserving original format
                clean_name = sanitize_filename(filename)
                
                # Get the file extension from the uploaded file
                file_extension = file.filename.rsplit('.', 1)[1].lower()
                
                # For canvas uploads, the file will be a PNG blob
                if file.filename == 'image.png':
                    file_extension = 'png'
                
                # Create the full filename
                full_filename = f"{clean_name}.{file_extension}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], full_filename)
                
                # Check if file already exists
                counter = 1
                original_name = clean_name
                while os.path.exists(save_path):
                    clean_name = f"{original_name} ({counter})"
                    full_filename = f"{clean_name}.{file_extension}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], full_filename)
                    counter += 1
                
                # Save the file
                file.save(save_path)
                
                # Optional: Optimize the image
                try:
                    with Image.open(save_path) as img:
                        # Convert to RGB if necessary (for JPEG compatibility)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            if file_extension.lower() == 'jpg' or file_extension.lower() == 'jpeg':
                                # Create a white background for JPEG
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = background
                        
                        # Optimize and save
                        img.save(save_path, optimize=True, quality=85)
                except Exception as e:
                    print(f"Image optimization failed: {e}")
                    # File is already saved, so continue
                
                flash(f'Image successfully uploaded as {full_filename}')
                return redirect(url_for('upload_form'))
            else:
                flash('Invalid file type. Please upload an image file.')
                return redirect(request.url)
                
        except Exception as e:
            flash(f'Upload failed: {str(e)}')
            return redirect(request.url)

    @app.route('/api/validate-filename', methods=['POST'])
    def validate_filename():
        """API endpoint to validate filename availability"""
        data = request.get_json()
        filename = data.get('filename', '').strip()
        
        if not filename:
            return jsonify({'valid': False, 'message': 'Filename is required'})
        
        clean_name = sanitize_filename(filename)
        
        # Check common extensions
        for ext in ['png', 'jpg', 'jpeg', 'gif']:
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{clean_name}.{ext}")
            if os.path.exists(full_path):
                return jsonify({'valid': False, 'message': f'File {clean_name}.{ext} already exists'})
        
        return jsonify({'valid': True, 'cleaned_name': clean_name})

    @app.route('/gallery')
    def gallery():
        """View uploaded images"""
        try:
            files = []
            if os.path.exists(app.config['UPLOAD_FOLDER']):
                for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                    if allowed_file(filename):
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file_size = os.path.getsize(file_path)
                        files.append({
                            'name': filename,
                            'size': f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                        })
            
            return render_template('gallery.html', files=files)
        except Exception as e:
            flash(f'Error loading gallery: {str(e)}')
            return redirect(url_for('upload_form'))

    @app.route('/delete/<filename>')
    def delete_file(filename):
        """Delete an uploaded file"""
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
            if os.path.exists(file_path):
                os.remove(file_path)
                flash(f'File {filename} deleted successfully')
            else:
                flash(f'File {filename} not found')
        except Exception as e:
            flash(f'Error deleting file: {str(e)}')
        
        return redirect(url_for('gallery'))

    # Error handlers
    @app.errorhandler(413)
    def too_large(e):
        flash('File is too large. Maximum size is 16MB.')
        return redirect(request.url)

    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        flash('An internal server error occurred. Please try again.')
        return redirect(url_for('upload_form'))

    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == "__main__":
    run()