import os
import fitz  # PyMuPDF
from PIL import Image
from typing import List, Tuple, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFConverter:
    """Class to handle PDF to TIFF conversion"""
    
    def __init__(self, dpi: int = 300, output_format: str = 'TIFF'):
        """
        Initialize the PDF converter
        
        Args:
            dpi (int): Resolution for conversion (default: 300)
            output_format (str): Output format (default: 'TIFF')
        """
        self.dpi = dpi
        self.output_format = output_format.upper()
        
    def pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            List[Image.Image]: List of PIL Images, one per page
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        images = []
        
        try:
            # Open the PDF file
            pdf_document = fitz.open(pdf_path)
            logger.info(f"Processing PDF with {len(pdf_document)} pages")
            
            # Convert each page to an image
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                
                # Create a matrix for the DPI scaling
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                
                # Render page to pixmap
                pixmap = page.get_pixmap(matrix=mat)
                
                # Convert pixmap to PIL Image
                img_data = pixmap.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                
                images.append(img)
                logger.info(f"Converted page {page_num + 1}")
                
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error converting PDF: {str(e)}")
            raise
            
        return images
    
    def save_images(self, images: List[Image.Image], output_path: str, 
                   filename_prefix: str = "page") -> List[str]:
        """
        Save images to files
        
        Args:
            images (List[Image.Image]): List of PIL Images
            output_path (str): Directory to save images
            filename_prefix (str): Prefix for output filenames
            
        Returns:
            List[str]: List of saved file paths
        """
        os.makedirs(output_path, exist_ok=True)
        saved_files = []
        
        for i, img in enumerate(images):
            filename = f"{filename_prefix}_{i+1:03d}.{self.output_format.lower()}"
            filepath = os.path.join(output_path, filename)
            
            try:
                # Convert to RGB if necessary (TIFF requires RGB)
                if img.mode != 'RGB' and self.output_format == 'TIFF':
                    img = img.convert('RGB')
                    
                img.save(filepath, format=self.output_format)
                saved_files.append(filepath)
                logger.info(f"Saved: {filepath}")
                
            except Exception as e:
                logger.error(f"Error saving image {filename}: {str(e)}")
                raise
                
        return saved_files
    
    def convert_pdf(self, pdf_path: str, output_dir: str, 
                   filename_prefix: Optional[str] = None) -> List[str]:
        """
        Complete conversion process from PDF to images
        
        Args:
            pdf_path (str): Path to input PDF file
            output_dir (str): Directory to save converted images
            filename_prefix (str, optional): Prefix for output files
            
        Returns:
            List[str]: List of saved file paths
        """
        if filename_prefix is None:
            # Use PDF filename as prefix
            basename = os.path.splitext(os.path.basename(pdf_path))[0]
            filename_prefix = basename
            
        logger.info(f"Starting conversion: {pdf_path}")
        
        # Convert PDF to images
        images = self.pdf_to_images(pdf_path)
        
        # Save images
        saved_files = self.save_images(images, output_dir, filename_prefix)
        
        logger.info(f"Conversion complete. Saved {len(saved_files)} files.")
        return saved_files

    @staticmethod
    def get_pdf_info(pdf_path: str) -> dict:
        """
        Get information about a PDF file
        
        Args:
            pdf_path (str): Path to PDF file
            
        Returns:
            dict: Dictionary containing PDF information
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
        try:
            pdf_document = fitz.open(pdf_path)
            info = {
                'page_count': len(pdf_document),
                'metadata': pdf_document.metadata,
                'file_size': os.path.getsize(pdf_path)
            }
            pdf_document.close()
            return info
            
        except Exception as e:
            logger.error(f"Error getting PDF info: {str(e)}")
            raise

# Import io for BytesIO
import io
