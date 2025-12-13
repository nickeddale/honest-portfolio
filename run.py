from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Respect FLASK_DEBUG environment variable, default to True for development
    debug_mode = os.environ.get('FLASK_DEBUG', '1') != '0'
    use_reloader = os.environ.get('FLASK_USE_RELOADER', str(debug_mode)) != '0'
    app.run(debug=debug_mode, port=5000, use_reloader=use_reloader)
