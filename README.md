# Photo Face Organizer 📸🤖

An open-source desktop application that automatically detects, recognizes, and organizes photos into person and group folders.

## Features
- **Automatic Face Detection & Recognition**: Scans photos to detect human faces and match them against created profiles.
- **Individual & Compulsory Group Profiles**: Group folders require all compulsory members to be detected together in a single photo.
- **File Audit Reconciliation**: Verifies that 100% of discovered photos are accounted for with zero data loss.
- **Unknown Faces Clustering**: Groups unrecognized faces so you can create new profiles with one click.
- **Cross-Platform**: Supports Linux, Windows, and macOS.

## Quick Installation & Launch

### Option 1: Install via Pip directly from GitHub
```bash
pip install git+https://github.com/technoharsh21/photo-face-organizer.git
photo-face-organizer
```

### Option 2: Run from Source
```bash
git clone https://github.com/technoharsh21/photo-face-organizer.git
cd photo-face-organizer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt || pip install PySide6 face_recognition Pillow
python app.py
```

## License
MIT License
