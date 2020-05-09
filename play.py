# http://bspaans.github.io/python-mingus/
# Make sure to install FluidSynth: https://github.com/FluidSynth/fluidsynth/wiki/Download
# OS X: `brew install fluid-synth`
# Ubuntu/Debian: `sudo apt-get install fluidsynth`
# Also install SoundFonts, I got one from here: https://rkhive.com/piano.html
from os import listdir
from os.path import join


from parse_midi import Midi
from parse_midi import MessageType
import parse_midi
import mingus.core.notes as notes
from mingus.containers import Note
from mingus.midi import fluidsynth

from pathlib import Path
import time


# TODO: try using Alsa, else use default
# fluidsynth.init(str(cwd / 'Steinway Grand Piano 1.2.sf2'))
fluidsynth.init(str(Path.cwd() / "Velocity Grand Piano.sf2"), 'alsa')


midi_dir = './midi_files'
midi_paths = [join(midi_dir, x) for x in listdir(midi_dir)]

fp = midi_paths[1]
print(fp)
m = Midi.from_file(fp)


event_times = []
ticks_per_qbeat = parse_midi.to_int(m.header.division) & 0x7fff

tempo = 120
for track in m.tracks:
    t: float = 0.0
    for evt in track.events:
        if evt.status == MessageType.Set_Tempo:
            tempo = parse_midi.to_int(evt.data)  # seconds / qbeat

        secs_per_tick = ticks_per_qbeat / tempo * 4
        t += evt.dtime * secs_per_tick
        event_times.append((t, evt))

event_times = sorted(event_times, key=lambda x: x[0])

start_time = time.time()
for t, evt in event_times:
    dtime = max(t - (time.time() - start_time), 0)
    time.sleep(dtime)
    if evt.status == MessageType.Note_On:
        note = evt.data[0]
        vel = evt.data[1]
        channel = evt.channel
        if vel == 0:
            # TODO: check this is being called
            fluidsynth.stop_Note(Note(note))
        else:
            n = Note(note)
            n.channel = 1
            n.velocity = vel
            fluidsynth.play_Note(n, channel=channel)

#     elif evt.status == MessageType.Note_Off and len(evt.data) > 0:
#         note = evt.data[0]
#         if note not in active_notes:
#             raise Exception('Released non-playing note')
#         duration = (active_notes[note], t)
#         note_times.append((note, duration))
#         fluidsynth.stop_Note(Note(note))

