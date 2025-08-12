import subprocess
import tempfile
import os
from typing import Optional, Tuple


def pdf_to_tiff_ghostscript(
    input_pdf_bytes: bytes,
    dpi: int = 96,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
    icc_profile_path: Optional[str] = None
) -> Tuple[bytes, str]:
    """
    Convert PDF to TIFF using Ghostscript.
    
    Args:
        input_pdf_bytes: PDF file content as bytes
        dpi: Output DPI (default: 96)
        first_page: First page to convert (1-indexed, optional)
        last_page: Last page to convert (1-indexed, optional)
        icc_profile_path: Path to ICC profile (optional, default checks /app/profiles/CoatedFOGRA39.icc)
    
    Returns:
        Tuple of (tiff_bytes, output_filename)
    
    Raises:
        subprocess.CalledProcessError: If Ghostscript conversion fails
        RuntimeError: If conversion fails or file operations fail
    """
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as input_temp:
        input_temp.write(input_pdf_bytes)
        input_temp_path = input_temp.name
    
    with tempfile.NamedTemporaryFile(suffix='.tiff', delete=False) as output_temp:
        output_temp_path = output_temp.name
    
    try:
        # Build Ghostscript command
        gs_cmd = [
            'gs',
            '-dNOPAUSE',
            '-dBATCH',
            '-dSAFER',
            '-sDEVICE=tiff32nc',
            '-sCompression=lzw',
            f'-r{dpi}',
            '-sProcessColorModel=DeviceCMYK',
            '-sColorConversionStrategy=CMYK',
            '-dOverrideICC'
        ]
        
        # Add page range if specified
        if first_page is not None:
            gs_cmd.append(f'-dFirstPage={first_page}')
        if last_page is not None:
            gs_cmd.append(f'-dLastPage={last_page}')
        
        # Add ICC profile if provided and exists
        if icc_profile_path is None:
            # Check default ICC profile path
            default_icc_path = '/app/profiles/CoatedFOGRA39.icc'
            if os.path.exists(default_icc_path):
                icc_profile_path = default_icc_path
        
        if icc_profile_path and os.path.exists(icc_profile_path):
            gs_cmd.append(f'-sOutputICCProfile={icc_profile_path}')
        
        # Add output and input files
        gs_cmd.extend([f'-sOutputFile={output_temp_path}', input_temp_path])
        
        # Run Ghostscript
        try:
            result = subprocess.run(
                gs_cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout for large files
            )
        except subprocess.CalledProcessError as e:
            # Truncate stderr for error message (max 500 chars)
            error_msg = e.stderr[:500] if e.stderr else 'Unknown Ghostscript error'
            raise RuntimeError(f'Ghostscript conversion failed: {error_msg}') from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError('Ghostscript conversion timed out after 5 minutes') from e
        
        # Read the output TIFF file
        if not os.path.exists(output_temp_path) or os.path.getsize(output_temp_path) == 0:
            raise RuntimeError('Ghostscript did not produce output file')
        
        with open(output_temp_path, 'rb') as f:
            tiff_bytes = f.read()
        
        # Generate output filename
        # Extract basename from original filename or use 'converted'
        basename = 'converted'
        
        # Format page range for filename
        if first_page is not None and last_page is not None:
            pages_str = f'_p{first_page}-{last_page}'
        elif first_page is not None:
            pages_str = f'_p{first_page}+'
        elif last_page is not None:
            pages_str = f'_p1-{last_page}'
        else:
            pages_str = ''
        
        output_filename = f'{basename}{pages_str}_{dpi}dpi.tiff'
        
        return tiff_bytes, output_filename
    
    finally:
        # Clean up temporary files
        try:
            if os.path.exists(input_temp_path):
                os.unlink(input_temp_path)
        except OSError:
            pass
        
        try:
            if os.path.exists(output_temp_path):
                os.unlink(output_temp_path)
        except OSError:
            pass
