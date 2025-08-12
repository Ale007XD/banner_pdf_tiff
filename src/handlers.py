import os
import uuid
from flask import request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from .convert import PDFConverter
from .config import Config
import logging
import zipfile
from typing import Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """
    Check if file extension is allowed
    
    Args:
        filename (str): Name of the file
        
    Returns:
        bool: True if file extension is allowed
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def handle_file_upload() -> Dict[str, Any]:
    """
    Handle PDF file upload and return file info
    
    Returns:
        Dict[str, Any]: Response dictionary with file info or error
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return {
                'success': False,
                'error': 'No file uploaded'
            }
            
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            return {
                'success': False,
                'error': 'No file selected'
            }
            
        # Check if file type is allowed
        if not allowed_file(file.filename):
            return {
                'success': False,
                'error': f'File type not allowed. Allowed types: {", ".join(Config.ALLOWED_EXTENSIONS)}'
            }
            
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        filename = f"{unique_id}_{original_filename}"
        
        # Save file
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        # Get file info
        file_size = os.path.getsize(filepath)
        
        logger.info(f"File uploaded successfully: {filename}")
        
        return {
            'success': True,
            'message': 'File uploaded successfully',
            'file_info': {
                'filename': filename,
                'original_filename': original_filename,
                'file_size': file_size,
                'file_path': filepath,
                'unique_id': unique_id
            }
        }
        
    except RequestEntityTooLarge:
        return {
            'success': False,
            'error': f'File too large. Maximum size: {Config.MAX_CONTENT_LENGTH / 1024 / 1024}MB'
        }
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return {
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }

def handle_pdf_conversion(file_path: str, unique_id: str, 
                         dpi: int = None, output_format: str = None) -> Dict[str, Any]:
    """
    Handle PDF to TIFF conversion
    
    Args:
        file_path (str): Path to uploaded PDF file
        unique_id (str): Unique identifier for this conversion
        dpi (int, optional): DPI for conversion
        output_format (str, optional): Output format
        
    Returns:
        Dict[str, Any]: Response dictionary with conversion results or error
    """
    try:
        # Use default values if not provided
        if dpi is None:
            dpi = Config.DEFAULT_DPI
        if output_format is None:
            output_format = Config.DEFAULT_FORMAT
            
        # Validate DPI
        if not isinstance(dpi, int) or dpi < 72 or dpi > 1200:
            return {
                'success': False,
                'error': 'Invalid DPI. Must be between 72 and 1200.'
            }
            
        # Create output directory for this conversion
        output_dir = os.path.join(Config.OUTPUT_FOLDER, unique_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize converter
        converter = PDFConverter(dpi=dpi, output_format=output_format)
        
        # Get PDF info first
        pdf_info = converter.get_pdf_info(file_path)
        
        # Convert PDF
        converted_files = converter.convert_pdf(
            pdf_path=file_path,
            output_dir=output_dir,
            filename_prefix=f"converted_{unique_id}"
        )
        
        # Calculate total output size
        total_size = sum(os.path.getsize(f) for f in converted_files)
        
        logger.info(f"Conversion completed: {len(converted_files)} files created")
        
        return {
            'success': True,
            'message': 'Conversion completed successfully',
            'conversion_info': {
                'unique_id': unique_id,
                'input_info': pdf_info,
                'output_files': converted_files,
                'total_output_size': total_size,
                'file_count': len(converted_files),
                'dpi': dpi,
                'format': output_format,
                'output_directory': output_dir
            }
        }
        
    except Exception as e:
        logger.error(f"Error converting PDF: {str(e)}")
        return {
            'success': False,
            'error': f'Conversion failed: {str(e)}'
        }

def handle_download_request(unique_id: str, download_type: str = 'zip') -> Dict[str, Any]:
    """
    Handle file download requests
    
    Args:
        unique_id (str): Unique identifier for the conversion
        download_type (str): Type of download ('zip' or 'individual')
        
    Returns:
        Dict[str, Any]: Response dictionary with download info or error
    """
    try:
        output_dir = os.path.join(Config.OUTPUT_FOLDER, unique_id)
        
        if not os.path.exists(output_dir):
            return {
                'success': False,
                'error': 'Conversion files not found. They may have been cleaned up.'
            }
            
        # Get list of converted files
        converted_files = [
            os.path.join(output_dir, f) 
            for f in os.listdir(output_dir) 
            if f.lower().endswith(('.tiff', '.tif', '.png', '.jpg', '.jpeg'))
        ]
        
        if not converted_files:
            return {
                'success': False,
                'error': 'No converted files found'
            }
            
        if download_type == 'zip':
            # Create zip file
            zip_filename = f"converted_{unique_id}.zip"
            zip_path = os.path.join(Config.OUTPUT_FOLDER, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in converted_files:
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
                    
            return {
                'success': True,
                'download_info': {
                    'download_type': 'zip',
                    'file_path': zip_path,
                    'filename': zip_filename,
                    'file_count': len(converted_files)
                }
            }
        else:
            return {
                'success': True,
                'download_info': {
                    'download_type': 'individual',
                    'files': converted_files,
                    'file_count': len(converted_files)
                }
            }
            
    except Exception as e:
        logger.error(f"Error preparing download: {str(e)}")
        return {
            'success': False,
            'error': f'Download preparation failed: {str(e)}'
        }

def handle_cleanup(unique_id: str) -> Dict[str, Any]:
    """
    Clean up temporary files for a conversion
    
    Args:
        unique_id (str): Unique identifier for the conversion
        
    Returns:
        Dict[str, Any]: Response dictionary with cleanup results
    """
    try:
        cleaned_files = 0
        
        # Clean up upload files
        upload_files = [
            f for f in os.listdir(Config.UPLOAD_FOLDER) 
            if f.startswith(unique_id)
        ]
        
        for filename in upload_files:
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                cleaned_files += 1
                
        # Clean up output directory
        output_dir = os.path.join(Config.OUTPUT_FOLDER, unique_id)
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                filepath = os.path.join(output_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    cleaned_files += 1
            os.rmdir(output_dir)
            
        # Clean up zip files
        zip_files = [
            f for f in os.listdir(Config.OUTPUT_FOLDER) 
            if f.startswith(f"converted_{unique_id}") and f.endswith('.zip')
        ]
        
        for filename in zip_files:
            filepath = os.path.join(Config.OUTPUT_FOLDER, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                cleaned_files += 1
                
        logger.info(f"Cleanup completed: {cleaned_files} files removed")
        
        return {
            'success': True,
            'message': f'Cleanup completed: {cleaned_files} files removed'
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return {
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }

def get_conversion_status(unique_id: str) -> Dict[str, Any]:
    """
    Get status information for a conversion
    
    Args:
        unique_id (str): Unique identifier for the conversion
        
    Returns:
        Dict[str, Any]: Status information
    """
    try:
        upload_dir = Config.UPLOAD_FOLDER
        output_dir = os.path.join(Config.OUTPUT_FOLDER, unique_id)
        
        # Check if upload file exists
        upload_files = [
            f for f in os.listdir(upload_dir) 
            if f.startswith(unique_id)
        ]
        
        # Check if output files exist
        output_exists = os.path.exists(output_dir)
        output_files = []
        
        if output_exists:
            output_files = [
                f for f in os.listdir(output_dir) 
                if f.lower().endswith(('.tiff', '.tif', '.png', '.jpg', '.jpeg'))
            ]
            
        status = {
            'unique_id': unique_id,
            'upload_files_exist': len(upload_files) > 0,
            'upload_files': upload_files,
            'output_directory_exists': output_exists,
            'converted_files_count': len(output_files),
            'converted_files': output_files,
            'status': 'completed' if output_files else ('uploaded' if upload_files else 'not_found')
        }
        
        return {
            'success': True,
            'status': status
        }
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return {
            'success': False,
            'error': f'Status check failed: {str(e)}'
        }
