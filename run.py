from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Import and create app
from dj_online_studio import create_app
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))

    # Run app with debug mode in development
    debug = os.environ.get('FLASK_ENV') == 'development'

    app.run(host='0.0.0.0', port=port, debug=debug)
