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
import json

# TODO: try using Alsa, else use default
# fluidsynth.init(str(cwd / 'Steinway Grand Piano 1.2.sf2'))
fluidsynth.init(str(Path.cwd() / "Velocity Grand Piano.sf2"), 'alsa')


midi_dir = './midi_files'
midi_paths = [join(midi_dir, x) for x in listdir(midi_dir)]

fp = midi_paths[1]
print(fp)
m = Midi.from_file(fp)


# start_time = time.time()
# for t, evt in m.abs_times():
#     dtime = max(t - (time.time() - start_time), 0)
#     time.sleep(dtime)
#     if evt.status == MessageType.Note_On:
#         note = evt.data[0]
#         vel = evt.data[1]
#         channel = evt.channel
#         if vel == 0:
#             # TODO: check this is being called
#             fluidsynth.stop_Note(Note(note))
#         else:
#             n = Note(note)
#             n.channel = 1
#             n.velocity = vel
#             fluidsynth.play_Note(n, channel=channel)

# ! NOT NEEDED:
#     elif evt.status == MessageType.Note_Off and len(evt.data) > 0:
#         note = evt.data[0]
#         if note not in active_notes:
#             raise Exception('Released non-playing note')
#         duration = (active_notes[note], t)
#         note_times.append((note, duration))
#         fluidsynth.stop_Note(Note(note))

def play_word(word, synth, word_duration=0.01):
    # word_duration = 10
    for note in word:
        n = Note(int(note['midi']))
        n.velocity = int(note['vel'])
        fluidsynth.play_Note(n, channel=1)
    time.sleep(word_duration)


sentences = json.loads(open('sentences.json', 'r').read())
# w = sentences['./midi_files/mz_545_3.mid'][10]
# play_word(w, fluidsynth, 10)
s = sentences['./midi_files/mz_545_3.mid']
print(len(s))
for word in s:
    play_word(word, fluidsynth, 0.25)

