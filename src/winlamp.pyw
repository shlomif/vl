# coding: utf-8
import os
import sys
import time
import socket
import webbrowser
from uuid import getnode as get_mac
from threading import Thread
from time import sleep

# Local
from client import PY2, FakeLamp
from pulser import Pulser
from optparse import OptionParser

WINDOWS = 'nt' == os.name

# Fill the 2<>3 gap
if PY2:
    from Queue import Queue
    from Tkinter import Tk, Canvas, Menu, mainloop, BitmapImage
    import tkMessageBox
    messagebox = tkMessageBox
else:
    from tkinter import Tk, Canvas, Menu, messagebox, mainloop, BitmapImage
    from queue import Queue

print('Running in ' + ('Python 2.7' if PY2 else 'Python 3.x') + ' mode.')

running = True

pulser = Pulser(primary=(0, 0, 255))

mac = repr(hex(get_mac()))[3:-1]

parser = OptionParser()
parser.add_option("-c", "--controller",
                  dest="controller",
                  help="controller hostname [default: %default]",
                  default="api.cilamp.se")
parser.add_option("-p", "--port",
                  dest="port",
                  help="controller port [default: %default]",
                  default=4040)
parser.add_option("-i", "--cimid",
                  dest="cimid",
                  help="Lamp ID [default: %default]",
                  default=mac)
parser.add_option("-l", "--log",
                  dest="logfile",
                  help="Log commands received to file",
                  default=None)
(options, args) = parser.parse_args()

print("--MANUAL--")
parser.print_help()
print("----------")

CIMID = options.cimid


def log(msg):
    if options.logfile:
        import datetime
        now = datetime.datetime.now()
        fullmsg = now.strftime("%Y-%M-%d %H:%M:%S") + " " + msg
        print(fullmsg)
        with open(options.logfile, 'a') as f:
            f.write(fullmsg + '\n')


# priority of ID:
# 1. command line
# 2. winlamp.id file
# 3. default (succinct MAC)
# (the OptionParser handles case 1 and 3;
# algo below hacks itself into 2!)
if CIMID == mac:
    idfile = 'winlamp.id'
    if os.path.exists('winlamp.id'):
        print(".id file found, using it.")
        with open(idfile) as f:
            CIMID = f.read().strip()


def command_handler(commandline):
    global pulser
    commandline = commandline.decode('utf8')
    log("received command '%s.'" % commandline)
    parts = commandline.split(' ')
    cmd = parts[0]
    if cmd == 'color':
        print("Static color mode.")
        assert len(parts) == 4
        rgb = tuple(map(int, parts[1:]))
        pulser = Pulser(primary=rgb)
    if cmd == 'pulse_1':
        print("Single pulsing color mode.")
        assert len(parts) == 5
        rgb = tuple(map(int, parts[1:4]))
        hz = float(parts[-1])
        print("%s Hz." % hz)
        pulser = Pulser(primary=rgb, hz=hz)
    if cmd == 'pulse_2':
        print("Two color pulse mode.")
        assert len(parts) == 8
        rgb1 = tuple(map(int, parts[1:4]))
        rgb2 = tuple(map(int, parts[4:7]))
        hz = float(parts[-1])
        print("%s Hz." % hz)
        pulser = Pulser(primary=rgb1, secondary=rgb2, hz=hz)

CONTROLLER_HOST = options.controller
CONTROLLER_PORT = int(options.port)
API_HOST = CONTROLLER_HOST
API_PORT = 8080
LAMP_URL = 'https://%s/v1/%s/' % (API_HOST, CIMID)


def colorapi_url(r, g, b):
    return LAMP_URL + 'color=%d,%d,%d' % (r, g, b)


def state_changed(new_state):
    print("Connection state changed to: " + new_state)
    if new_state in ["CONNECTING", "DISCONNECTED"]:
        global pulser
        pulser = Pulser(primary=(50, 50, 200),
                        secondary=(50, 200, 50),
                        hz=0.25)


fakelamp = FakeLamp(CONTROLLER_HOST, CONTROLLER_PORT, CIMID,
                    command_handler, state_changed)
fakelamp.start()

manual = 'ID: %s\n\nMake lamp red:\n%s\n' % (CIMID, colorapi_url(255, 0, 0))
print(manual)

master = Tk()

ox = 0
oy = 0


def lmb_down(ev):
    # Drag-to-move hack
    global ox, oy
    (ox, oy) = (ev.x, ev.y)


def lmb_move(ev):
    global ox, oy
    x = master.winfo_pointerx() - ox
    y = master.winfo_pointery() - oy
    master.geometry("+%d+%d" % (x, y))

winsize = 64  # Tribute to C64 :)
canvas = Canvas(master, width=winsize, height=winsize, highlightthickness=0,
                bd=0, relief='ridge')
i = canvas.create_rectangle(0, 0, winsize-1, winsize-1,
                            fill="blue", outline="black")

canvas.pack(padx=0, pady=0)
canvas.configure(bg="white")
canvas.bind("<Button-1>", lmb_down)
canvas.bind("<B1-Motion>", lmb_move)

bmpsize_px = 32

bmpdata = """
0xaf,0x6d,0xeb,0xd6,0x55,0xdb,0xb6,0x2f,
0xaf,0xaa,0x6a,0x6d,0x55,0x7b,0xd7,0x1b,
0xad,0xd6,0xb5,0xae,0xad,0x55,0x6f,0x05,
0xad,0xba,0xab,0xd6,0xaa,0xd5,0x5f,0x93,
0xad,0x76,0x7d,0x67,0x5a,0xd5,0xd7,0xa3,
0xad,0xbd,0xfe,0xea,0x5a,0xab,0x69,0xb3,
0xad,0x55,0xde,0xd8,0x2e,0x2b,0xb5,0x6a,
0x69,0x4b,0x3f,0xb4,0x9e,0x92,0xb5,0xed,
0xd5,0xca,0x9c,0xb4,0x5a,0xa1,0x2a,0x6d,
0xad,0x6c,0x5f,0xda,0x2c,0x91,0xbb,0xf6,
0xad,0xaa,0x96,0xaa,0x5a,0xca,0x9d,0xfe,
0x2c,0xa5,0x2a,0xd3,0x9a,0x8a,0x4f,0xfd,
0x2c,0x25,0x4a,0x6b,0x4d,0x45,0x9f,0xba,
0x1a,0xaa,0x7a,0xb5,0xaa,0x44,0x6b,0x5b,
0x1a,0x55,0xfd,0x5e,0x4e,0xa2,0x6b,0x59,
0x9a,0xa4,0xde,0x4a,0x4a,0xd2,0xf5,0xaa,
0xaf,0x6d,0xeb,0xd6,0x55,0xdb,0xb6,0x2f,
0xaf,0xaa,0x6a,0x6d,0x55,0x7b,0xd7,0x1b,
0xad,0xd6,0xb5,0xae,0xad,0x55,0x6f,0x05,
0xad,0xba,0xab,0xd6,0xaa,0xd5,0x5f,0x93,
0xad,0x76,0x7d,0x67,0x5a,0xd5,0xd7,0xa3,
0xad,0xbd,0xfe,0xea,0x5a,0xab,0x69,0xb3,
0xad,0x55,0xde,0xd8,0x2e,0x2b,0xb5,0x6a,
0x69,0x4b,0x3f,0xb4,0x9e,0x92,0xb5,0xed,
0xd5,0xca,0x9c,0xb4,0x5a,0xa1,0x2a,0x6d,
0xad,0x6c,0x5f,0xda,0x2c,0x91,0xbb,0xf6,
0xad,0xaa,0x96,0xaa,0x5a,0xca,0x9d,0xfe,
0x2c,0xa5,0x2a,0xd3,0x9a,0x8a,0x4f,0xfd,
0x2c,0x25,0x4a,0x6b,0x4d,0x45,0x9f,0xba,
0x1a,0xaa,0x7a,0xb5,0xaa,0x44,0x6b,0x5b,
0x1a,0x55,0xfd,0x5e,0x4e,0xa2,0x6b,0x59,
0x9a,0xa4,0xde,0x4a,0x4a,0xd2,0xf5,0xaa,
0xaf,0x6d,0xeb,0xd6,0x55,0xdb,0xb6,0x2f,
0xaf,0xaa,0x6a,0x6d,0x55,0x7b,0xd7,0x1b,
0xad,0xd6,0xb5,0xae,0xad,0x55,0x6f,0x05,
0xad,0xba,0xab,0xd6,0xaa,0xd5,0x5f,0x93,
0xad,0x76,0x7d,0x67,0x5a,0xd5,0xd7,0xa3,
0xad,0xbd,0xfe,0xea,0x5a,0xab,0x69,0xb3,
0xad,0x55,0xde,0xd8,0x2e,0x2b,0xb5,0x6a,
0x69,0x4b,0x3f,0xb4,0x9e,0x92,0xb5,0xed,
0xd5,0xca,0x9c,0xb4,0x5a,0xa1,0x2a,0x6d,
0xad,0x6c,0x5f,0xda,0x2c,0x91,0xbb,0xf6,
0xad,0xaa,0x96,0xaa,0x5a,0xca,0x9d,0xfe,
0x2c,0xa5,0x2a,0xd3,0x9a,0x8a,0x4f,0xfd,
0x2c,0x25,0x4a,0x6b,0x4d,0x45,0x9f,0xba,
0x1a,0xaa,0x7a,0xb5,0xaa,0x44,0x6b,0x5b,
0x1a,0x55,0xfd,0x5e,0x4e,0xa2,0x6b,0x59,
0x9a,0xa4,0xde,0x4a,0x4a,0xd2,0xf5,0xaa,
0xaf,0x6d,0xeb,0xd6,0x55,0xdb,0xb6,0x2f,
0xaf,0xaa,0x6a,0x6d,0x55,0x7b,0xd7,0x1b,
0xad,0xd6,0xb5,0xae,0xad,0x55,0x6f,0x05,
0xad,0xba,0xab,0xd6,0xaa,0xd5,0x5f,0x93,
0xad,0x76,0x7d,0x67,0x5a,0xd5,0xd7,0xa3,
0xad,0xbd,0xfe,0xea,0x5a,0xab,0x69,0xb3,
0xad,0x55,0xde,0xd8,0x2e,0x2b,0xb5,0x6a,
0x69,0x4b,0x3f,0xb4,0x9e,0x92,0xb5,0xed,
0xd5,0xca,0x9c,0xb4,0x5a,0xa1,0x2a,0x6d,
0xad,0x6c,0x5f,0xda,0x2c,0x91,0xbb,0xf6,
0xad,0xaa,0x96,0xaa,0x5a,0xca,0x9d,0xfe,
0x2c,0xa5,0x2a,0xd3,0x9a,0x8a,0x4f,0xfd,
0x2c,0x25,0x4a,0x6b,0x4d,0x45,0x9f,0xba,
0x1a,0xaa,0x7a,0xb5,0xaa,0x44,0x6b,0x5b,
0x1a,0x55,0xfd,0x5e,0x4e,0xa2,0x6b,0x59,
0x9a,0xa4,0xde,0x4a,0x4a,0xd2,0xf5,0xaa,
"""
BITMAP = """
#define im_width %d
#define im_height %d
static char im_bits[] = {
%s
};
""" % (bmpsize_px, bmpsize_px, bmpdata)

bmp = BitmapImage(data=BITMAP)

# j = canvas.create_image((winsize/2, winsize/2), image=bmp)


def setcolor(r, g, b):
    def byte2hex(b):
        return hex(256+b)[-2:]
    (re, gr, bl) = map(byte2hex, (r, g, b))
    col = "#%s%s%s" % (re, gr, bl)
    canvas.itemconfig(i, fill=col)


def update_color():
    canvas.after(20, update_color)

    (r, g, b) = pulser.seconds(time.time())
    setcolor(r, g, b)

canvas.after(20, update_color)


def show_manual():
    messagebox.showinfo("Quck start", manual)


def show_tester():
    print("Opening web based URL generator in browser...")
    tester_url = 'https://cilamp.se/url-generator/#' + CIMID
    webbrowser.open(tester_url)


def quit_app():
    print("Quitting app.")
    global running
    running = False
    master.after(10, lambda: master.destroy())
    return ""


popup = Menu(master, tearoff=0)
popup.add_command(label="Quick start", command=show_manual)
popup.add_command(label="URL Generator", command=show_tester)
popup.add_separator()
popup.add_command(label="Quit", command=quit_app)


def do_popup(event):
    # display the popup menu
    try:
        popup.tk_popup(event.x_root, event.y_root, 0)
    finally:
        # make sure to release the grab (Tk 8.0a1 only)
        popup.grab_release()


canvas.bind("<Button-2>", do_popup)
canvas.bind("<Button-3>", do_popup)

master.overrideredirect(True)
master.geometry("+250+250")
master.lift()
master.wm_attributes("-topmost", True)
# master.wm_attributes("-disabled", True)
if WINDOWS:
    master.wm_attributes("-transparentcolor", "white")

mainloop()
