import mingus.core.notes as notes
from mingus.containers import Note
from mingus.midi import fluidsynth

from pathlib import Path
import time
# http://bspaans.github.io/python-mingus/
# Make sure to install FluidSynth: https://github.com/FluidSynth/fluidsynth/wiki/Download
# OS X: `brew install fluid-synth`
# Ubuntu/Debian: `sudo apt-get install fluidsynth`
# Also install SoundFonts, I got one from here: https://rkhive.com/piano.html

cwd = Path.cwd()
# TODO: try using Alsa, else use default
# fluidsynth.init(str(cwd / "Velocity Grand Piano.sf2"), 'alsa')
fluidsynth.init(str(cwd / 'Steinway Grand Piano 1.2.sf2'))


from os import listdir
from os.path import join


from parse_midi import Midi
from parse_midi import MessageType
import parse_midi

midi_dir = './midi_files'
midi_paths = [join(midi_dir, x) for x in listdir(midi_dir)]
# midi_paths[:5]

fp = midi_paths[12]
print(fp)
m = Midi.from_file(fp)
track1 = m.tracks[1]
active_notes = {}
t = 0
note_times = []

# # TODO: account for velocity somehow!

TICKS_PER_BEAT = None

#TODO: dont do this lol
# assert m.header.division[0] <
if m.header.division[0] == 0x1:
    # frames / second
    print('DIVISION:', m.header.division)
    h = parse_midi.to_int(m.header.division)
    print(h & 0x8000)
    print(h & 0x7fff)
    # ticks/beat = delta position / quarter note
    TICKS_PER_BEAT = h & 0x7fff
    fps = m.header.division[1] >> 7 & 1 # frames per second flag
    # tpf = int.from_bytes(m.header.division, byteorder='big', signed=True)# ticks per frame
    # print(fps, tpf)
elif m.header.division == 0x0:
    print(h & 0x7F00)
    # ticks / beat

    raise NotImplementedError('ticks per beat header')

for evt in m.tracks[0].events:
    if evt.status == MessageType.SMPTE_Offset:
        print('>>>', evt)
    if evt.status == MessageType.Time_Sig:
        print(evt)
        nn = evt.data[0]
        dd = evt.data[1]
        cc = evt.data[2]
        bb = evt.data[3]
        print(nn, 2**dd, cc, bb)
    elif evt.status == MessageType.Set_Tempo:
        # tempo = microsec / quarter note
        tempo = parse_midi.to_int(evt.data[0:3])
        # seconds / quarter note:

        # 500000 = 120 bpm
        # tempo = tempo / 1000000
        # tempo = (tempo / 500000) * 120 # BPM
        print('Tempo:', tempo)
        # microsec / tick
        mst = tempo / TICKS_PER_BEAT
        # seconds / tick
        st = mst / 1000000
        print(st)

print(m.header)
for evt in track1.events:
    t += evt.dtime
    print(evt.dtime)
    time.sleep(evt.dtime * 0.0016)

    if evt.status == MessageType.Note_On  and len(evt.data) > 0:
        note = evt.data[0]
        vel = evt.data[1]
        if vel == 0:
            duration = (active_notes[note], t)
            note_times.append((note, duration))
            fluidsynth.stop_Note(Note(note))
        else:
            # print(hex(note), Note(note))
            active_notes[note] = t
            n = Note(note)
            n.channel = 1
            n.velocity = vel
            # print(vel)
            fluidsynth.play_Note(n)


    elif evt.status == MessageType.Note_Off and len(evt.data) > 0:
        note = evt.data[0]
        if note not in active_notes:
            raise Exception('Released non-playing note')
        duration = (active_notes[note], t)
        note_times.append((note, duration))
        fluidsynth.stop_Note(Note(note))

