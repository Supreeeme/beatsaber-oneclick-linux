#!/usr/bin/env python3

import os
import pathlib
import re
import sys
import urllib.request
from urllib.parse import unquote
import zipfile
import tempfile
import json
import threading
import shutil
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GLib, Notify

# get ui objects
script_path = pathlib.Path(__file__).resolve().parent
builder = Gtk.Builder.new_from_file(str(script_path/'song_install.ui'))
win = builder.get_object('window')
bar = builder.get_object('bar')
label = builder.get_object('text')
ok_button = builder.get_object('button-ok')
cancel_button = builder.get_object('button-cancel')

# class for passing song download status between threads
class SongDLStatus:
    def __init__(self):
        self.complete = False
        self.cur = 0
        self.max_size = 0
        self.new_chunk_event = threading.Event()
        self.finish = threading.Event()

    def new_chunk(self, new_size, max_size):
        self.cur = new_size
        self.max_size = max_size
        self.new_chunk_event.set()

    def set_song_name(self, name):
        self.name = name

def file_dl(req: urllib.request.Request, file_to_write, status: SongDLStatus = None):
    """Downloads a file. Can take a SongDLStatus to update the status bar"""
    with urllib.request.urlopen(req) as dl:
        size = int(dl.getheader("Content-Length"))
        chunk = 1024*3 # arbitrary
        bytes_read = 0.0
        while (bytes_read < size):
            file_to_write.write(dl.read(chunk))
            bytes_read += chunk
            if status: status.new_chunk(bytes_read, size)
    if status: status.complete = True

def song_dl(key: str, status: SongDLStatus = None):
    # disable ok_button
    GLib.idle_add(ok_button.set_sensitive, False)

    # create song directory
    song_dir = key + "-dir"
    os.mkdir(song_dir)
    os.chdir(song_dir)

    # download song zip
    song_url = f"https://beatsaver.com/api/download/key/{key}"
    req = urllib.request.Request(song_url, headers={"User-Agent":"OneClick Linux!"})
    with tempfile.NamedTemporaryFile() as temp:
        file_dl(req, temp, status)
        # extract song zip
        zipfile.ZipFile(temp).extractall()

    # rename directory
    info = json.load(open("info.dat" if os.path.exists("info.dat") else "Info.dat"))
    song_name = info["_songName"]
    author = info["_levelAuthorName"]
    os.chdir("..")
    os.rename(song_dir, f"{key} ({song_name} - {author})")

    if status: 
        status.finish.set()
        status.set_song_name(song_name)
    
def cancel(cancel_button, song_name):
    Gtk.main_quit()
    Notify.Notification(summary=f"{song_name} not installed.").show()
    # uhhhh
    exit(1)

def finalize():
    """Final actions after successful download. Enables OK button."""

    GLib.idle_add(ok_button.set_sensitive, True)
    GLib.idle_add(ok_button.grab_focus)
    ok_button.connect('clicked', Gtk.main_quit)
    GLib.idle_add(cancel_button.set_sensitive, False)

def song_install():
    """Installs a song (beatsaver:// URI)"""

    # threading event for blocking on re-downloads
    re_dl_event = threading.Event()
    def re_dl(_, key, dir_name):
        shutil.rmtree(dir_name) # remove already installed song
        re_dl_event.set()

    os.chdir("Beat Saber_Data/CustomLevels")
    
    # check if installed
    key = sys.argv[1].replace('beatsaver://', '')
    installed = [k for k in os.listdir() if key in k]
    if len(installed) > 0:
        # extract song name from existing directory
        song_name = re.match('\w+ \(([^-]+).*', installed[0]).group(1).strip()
        GLib.idle_add(label.set_text, f"You already have this song ({song_name}) downloaded!\nWould you like to redownload it?")
        re_dl_id = ok_button.connect('clicked', re_dl, key, installed[0])
        cancel_button.connect('clicked', cancel, song_name)
        re_dl_event.wait()
        ok_button.disconnect(re_dl_id)

    GLib.idle_add(label.set_text, "Downloading song...")
    status = SongDLStatus()
    # run download in separate thread, so we can update progress bar
    threading.Thread(target=song_dl, args=(key, status)).start()
    # progress bar
    while not status.complete:
        status.new_chunk_event.wait()
        status.new_chunk_event.clear()
        GLib.idle_add(bar.set_fraction, status.cur/status.max_size)

    status.finish.wait() # wait for completion

    GLib.idle_add(label.set_text, f"{status.name} downloaded!")
    finalize()

def playlist_install():
    """Installs a playlist (bsplaylist:// URI)"""

    url = sys.argv[1].replace('bsplaylist://playlist/', '') # url for downloading
    filename = url.replace('https://bsaber.com/PlaylistAPI/','') # blah blah .bplist
    os.chdir('Playlists')
    # download .bplist file
    with urllib.request.urlopen(url) as resp, open(filename, 'wb') as f:
        shutil.copyfileobj(resp, f)

    info = json.load(open(filename))
    playlistTitle = info["playlistTitle"]
    GLib.idle_add(label.set_text, f"Downloading {playlistTitle}")
    os.chdir('../Beat Saber_Data/CustomLevels')
    num_songs = len(info["songs"])
    cur_song = 0
    for song in info["songs"]:
        song_dl(song['key'])
        cur_song += 1
        GLib.idle_add(bar.set_fraction, cur_song/num_songs)

    GLib.idle_add(label.set_text, f"Downloaded {playlistTitle}")
    finalize()

def other_install():
    """Installs other components (modelsaber:// URI)
    Currently supports sabers (modelsaber://saber/) and platforms (modelsaber://platform/)"""

    def download(url: str):
        status = SongDLStatus()
        filename = unquote(re.search('/([^/]+)$', url)[1])
        request = urllib.request.Request(url, headers={"User-Agent":"OneClick Linux!"})
        with open(filename, 'wb') as file:
            # download in separate thread
            threading.Thread(target=file_dl, args=[request, file, status]).start()

            while not status.complete:
                status.new_chunk_event.wait()
                status.new_chunk_event.clear()
                GLib.idle_add(bar.set_fraction, status.cur/status.max_size)

        GLib.idle_add(label.set_text, f"{filename} downloaded")

    thing = re.search('/([a-z]+)/', sys.argv[1])[1]
    if thing == "saber":
        if (os.path.exists("CustomSabers")):
            os.chdir("CustomSabers")
            GLib.idle_add(label.set_text, "Downloading saber...")
            key = sys.argv[1].replace('modelsaber://saber/', '') # url for downloading
            url = f"https://modelsaber.com/files/saber/{key}"
            download(url)
        else:
            GLib.idle_add(label.set_text, "CustomSabers directory missing. Did you install the CustomSabers mod?")
            GLib.idle_add(bar.set_fraction, 1)

    elif thing == "platform":
        if os.path.exists("CustomPlatforms"):
            os.chdir("CustomPlatforms")
            GLib.idle_add(label.set_text, "Downloading platform...")
            key = sys.argv[1].replace('modelsaber://platform/', '') # url for downloading
            url = f"https://modelsaber.com/files/platform/{key}"
            download(url)
        else:
            GLib.idle_add(label.set_text, "CustomPlatforms directory missing. Did you install the CustomPlatforms mod?")
            GLib.idle_add(bar.set_fraction, 1)

    finalize()

funcs = {
    'beatsaver' : song_install,
    'bsplaylist' : playlist_install,
    'modelsaber' : other_install
}

if __name__ == "__main__":
    Notify.init("OneClick Installer")

    # connect window destruction to closing Gtk loop
    win.connect('destroy', Gtk.main_quit)
    win.show_all()

    def invalid_path_error():
        label.set_text("ERROR: Invalid path from bs-path.txt! Please re-run bs-oneclick-install.py.")
        bar.set_visible(False)
        ok_button.connect('clicked', Gtk.main_quit)
        cancel_button.set_sensitive(False)

    bs_install = None
    try:
        with open(script_path/"bs-path.txt") as file:
            bs_install = pathlib.Path(file.readline())
    except FileNotFoundError: # missing bs-path.txt
        invalid_path_error()
    else:
        # verify bs install path
        if not bs_install.exists() or not pathlib.Path(bs_install / 'Beat Saber.exe').exists():
            invalid_path_error()
        else:
            os.chdir(bs_install)

            try:
                # figure out what we're installing
                uri = re.match('^[a-z]+', sys.argv[1])[0]
            except IndexError: # didn't provide uri! - shouldn't happen
                label.set_text("ERROR: No URI provided!")
                bar.set_visible(False)
                ok_button.connect('clicked', Gtk.main_quit)
                cancel_button.set_sensitive(False)
            else:
                # start work in another thread so Gtk main loop can run
                thread = threading.Thread(target=funcs[uri])
                thread.daemon = True
                thread.start()

    Gtk.main()
