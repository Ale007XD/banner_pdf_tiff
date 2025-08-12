import os
from flask import Flask, request, jsonify, send_file, render_template_string
from werkzeug.exceptions import RequestEntityTooLarge
from .config import config, Config
from .handlers import (
    handle_file_upload,
    handle_pdf_conversion,
    handle_download_request,
    handle_cleanup,
    get_conversion_status
)
import logging
from typing import Dict, Any

def create_app(config_name: str = None) -> Flask:
    """
    Application factory function
    
    Args:
        config_name (str): Configuration name ('development', 'production', 'testing')
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    
    # Determine configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))
    
    # Initialize configuration
    Config.init_app(app)
    
    # Set up logging
    if not app.debug and not app.testing:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s %(message)s'
        )
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register routes
    register_routes(app)
    
    return app

def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the Flask app
    
    Args:
        app (Flask): Flask application instance
    """
    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        return jsonify({
            'success': False,
            'error': f'File too large. Maximum size allowed: {app.config["MAX_CONTENT_LENGTH"] / 1024 / 1024:.1f}MB'
        }), 413
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method not allowed'
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

def register_routes(app: Flask) -> None:
    """
    Register all routes for the Flask app
    
    Args:
        app (Flask): Flask application instance
    """
    
    @app.route('/', methods=['GET'])
    def index():
        """Home page with simple upload form"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PDF to TIFF Converter</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .container { background: #f5f5f5; padding: 30px; border-radius: 10px; }
                .upload-area { border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; }
                .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; }
                .btn:hover { background: #0056b3; }
                .progress { display: none; margin: 20px 0; }
                .result { margin: 20px 0; padding: 20px; border-radius: 5px; }
                .success { background: #d4edda; color: #155724; }
                .error { background: #f8d7da; color: #721c24; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>PDF to TIFF Converter</h1>
                <p>Upload a PDF file and convert it to high-quality TIFF images.</p>
                
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="upload-area">
                        <input type="file" id="fileInput" name="file" accept=".pdf" required>
                        <p>Select a PDF file to convert</p>
                    </div>
                    
                    <div>
                        <label>DPI (Quality): 
                            <select name="dpi">
                                <option value="150">150 DPI (Standard)</option>
                                <option value="300" selected>300 DPI (High Quality)</option>
                                <option value="600">600 DPI (Very High Quality)</option>
                            </select>
                        </label>
                    </div>
                    
                    <div style="margin: 20px 0;">
                        <button type="submit" class="btn">Convert to TIFF</button>
                    </div>
                </form>
                
                <div id="progress" class="progress">
                    <p>Processing... Please wait.</p>
                </div>
                
                <div id="result"></div>
            </div>
            
            <script>
                document.getElementById('uploadForm').addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    const progressDiv = document.getElementById('progress');
                    const resultDiv = document.getElementById('result');
                    
                    progressDiv.style.display = 'block';
                    resultDiv.innerHTML = '';
                    
                    try {
                        // Upload file
                        const uploadResponse = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const uploadResult = await uploadResponse.json();
                        
                        if (!uploadResult.success) {
                            throw new Error(uploadResult.error);
                        }
                        
                        // Convert file
                        const convertResponse = await fetch('/api/convert', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                unique_id: uploadResult.file_info.unique_id,
                                dpi: parseInt(formData.get('dpi'))
                            })
                        });
                        
                        const convertResult = await convertResponse.json();
                        
                        if (!convertResult.success) {
                            throw new Error(convertResult.error);
                        }
                        
                        // Show success and download link
                        resultDiv.innerHTML = `
                            <div class="result success">
                                <h3>Conversion Successful!</h3>
                                <p>Converted ${convertResult.conversion_info.file_count} pages</p>
                                <a href="/api/download/${convertResult.conversion_info.unique_id}" class="btn">Download ZIP</a>
                            </div>
                        `;
                        
                    } catch (error) {
                        resultDiv.innerHTML = `
                            <div class="result error">
                                <h3>Error</h3>
                                <p>${error.message}</p>
                            </div>
                        `;
                    } finally {
                        progressDiv.style.display = 'none';
                    }
                });
            </script>
        </body>
        </html>
        """
        return render_template_string(html_template)
    
    @app.route('/api/upload', methods=['POST'])
    def api_upload():
        """Handle file upload"""
        result = handle_file_upload()
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/convert', methods=['POST'])
    def api_convert():
        """Handle PDF conversion"""
        try:
            data = request.get_json()
            if not data or 'unique_id' not in data:
                return jsonify({
                    'success': False,
                    'error': 'Missing unique_id in request'
                }), 400
            
            unique_id = data['unique_id']
            dpi = data.get('dpi', Config.DEFAULT_DPI)
            output_format = data.get('format', Config.DEFAULT_FORMAT)
            
            # Find the uploaded file
            upload_files = [
                f for f in os.listdir(Config.UPLOAD_FOLDER)
                if f.startswith(unique_id)
            ]
            
            if not upload_files:
                return jsonify({
                    'success': False,
                    'error': 'Upload file not found'
                }), 404
            
            file_path = os.path.join(Config.UPLOAD_FOLDER, upload_files[0])
            
            result = handle_pdf_conversion(
                file_path=file_path,
                unique_id=unique_id,
                dpi=dpi,
                output_format=output_format
            )
            
            return jsonify(result), 200 if result['success'] else 400
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Conversion request failed: {str(e)}'
            }), 500
    
    @app.route('/api/download/<unique_id>', methods=['GET'])
    def api_download(unique_id: str):
        """Handle file download"""
        try:
            download_type = request.args.get('type', 'zip')
            
            result = handle_download_request(unique_id, download_type)
            
            if not result['success']:
                return jsonify(result), 404
            
            download_info = result['download_info']
            
            if download_info['download_type'] == 'zip':
                return send_file(
                    download_info['file_path'],
                    as_attachment=True,
                    download_name=download_info['filename']
                )
            else:
                # For individual files, return info about available files
                return jsonify(result)
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Download failed: {str(e)}'
            }), 500
    
    @app.route('/api/status/<unique_id>', methods=['GET'])
    def api_status(unique_id: str):
        """Get conversion status"""
        result = get_conversion_status(unique_id)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/api/cleanup/<unique_id>', methods=['DELETE'])
    def api_cleanup(unique_id: str):
        """Clean up files for a conversion"""
        result = handle_cleanup(unique_id)
        return jsonify(result), 200 if result['success'] else 400
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'PDF to TIFF Converter',
            'version': '1.0.0'
        })

# Create app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
