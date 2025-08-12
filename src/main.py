#!/usr/bin/env python3
"""
Main entry point for the banner PDF/TIFF application.
Imports and runs handlers.main() when module is executed directly.
"""

import sys
import logging
from pathlib import Path

# Add src directory to Python path for proper imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from handlers import main as handlers_main
except ImportError as e:
    print(f"Error importing handlers module: {e}")
    print("Make sure handlers.py exists in the src directory")
    sys.exit(1)

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )

def setup_application():
    """Initialize application settings and configuration."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting banner PDF/TIFF application")
    
    # Add any additional application setup here
    # (database connections, configuration loading, etc.)
    
    return logger

def main():
    """Main application entry point with error handling and polling setup."""
    try:
        logger = setup_application()
        
        # Run the main handler function
        logger.info("Calling handlers.main()")
        handlers_main()
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
