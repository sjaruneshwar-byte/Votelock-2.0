import os

def print_vvpat(candidate_name, symbol, election_name):
    """Optional ESC/POS serial printer adapter. Install pyserial separately and enable it in .env."""
    try:
        import serial
    except ImportError:
        return "pyserial-not-installed"
    port=os.getenv("THERMAL_PRINTER_PORT","/dev/ttyUSB0"); baud=int(os.getenv("THERMAL_PRINTER_BAUDRATE","9600"))
    text=("\x1b@"+"\x1bE\x01"+f"{election_name}\n"+"VVPAT - DEMO RECORD\n"+"\x1bE\x00"+"-"*32+"\n"+f"Candidate: {candidate_name} {symbol}\n"+"Vote Recorded Successfully\n"+"Please verify the printed record.\n"+"-"*32+"\n\n")
    with serial.Serial(port,baudrate=baud,timeout=2) as printer:
        printer.write(text.encode("utf-8","replace")); printer.flush()
    return "printed"
