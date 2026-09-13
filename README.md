# VoteLock — Review 1

Smart electronic voting prototype with admin dashboard, voter credentials, QR verification, camera capture, ballot recording and optional thermal-printer/VVPAT integration.

## Run
1. Create a virtual environment.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `SECRET_KEY`. SMTP is optional for lab demo; without SMTP the OTP is printed in the terminal.
4. `python app.py`

Admin: `/register` → OTP → `/login`
Voter: `/voter/login`
Admin QR scanner: `/qr/scanner`

For Raspberry Pi thermal printing, install `pyserial`, set `THERMAL_PRINTER_ENABLED=true`, and configure the serial port in `.env`.
