#!/usr/bin/env python3

import os, os.path
import pathlib
import shutil
import subprocess
import threading
import gi
from urllib.parse import unquote, urlparse
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# get ui objects
builder = Gtk.Builder.new_from_file('file_select.ui')
win = builder.get_object('win')
ok_button = builder.get_object('button-ok')
file_chooser = builder.get_object('file-chooser')
err_label = builder.get_object('err-label')
label = builder.get_object('label')
def action():
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    ok_handler_id = None

    def maybe_choose_folder(_):
        path = unquote(urlparse(file_chooser.get_uri()).path)
        if not os.path.exists(path+"/Beat Saber.exe"): # not beat saber!
            GLib.idle_add(err_label.set_text, "This does not look like a Beat Saber installation!")
            return

        # yes beat saber!
        desktop_file = f"""[Desktop Entry]
Type=Application
Name=Beat Saber OneClick Install
Exec={os.getcwd()+'/bs-oneclick.py'} %u
StartupNotify=false
MimeType=x-scheme-handler/beatsaver;x-scheme-handler/modelsaber;x-scheme-handler/bsplaylist
NoDisplay=true
"""
        with open('bs-oneclick.desktop', 'w') as f:
            f.write(desktop_file)
        with open('bs-path.txt', 'w') as f:
            f.write(path)

        ok_button.disconnect(ok_handler_id)

        # move desktop file to applications
        app_dir = pathlib.Path('~/.local/share/applications').expanduser()
        app_dir.mkdir(parents=True, exist_ok=True)
        full_path = app_dir / 'bs-oneclick.desktop'
        # specifying full path so that shutil overwrites existing version
        shutil.move(src=pathlib.Path.cwd()/'bs-oneclick.desktop', dst=full_path)

        # set default mime type
        subprocess.run(['xdg-mime','default', full_path,
            'x-scheme-handler/beatsaver','x-scheme-handler/modelsaber','x-scheme-handler/bsplaylist'])

        GLib.idle_add(label.set_text, "Beat Saber OneClick has been installed. Enjoy!")
        GLib.idle_add(file_chooser.set_sensitive, False)
        ok_button.connect('clicked', Gtk.main_quit)

    def new_folder(_):
        GLib.idle_add(err_label.set_text,"")

    def work():
        nonlocal ok_handler_id
        ok_handler_id = ok_button.connect('clicked', maybe_choose_folder)
        file_chooser.connect('selection-changed', new_folder)

    threading.Thread(target=work).start()

if __name__ == "__main__":
    action()
    Gtk.main()
