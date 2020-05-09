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
fluidsynth.init(str(cwd / "Velocity Grand Piano.sf2"), 'alsa')
n = Note("C-5")
n.channel = 1
n.velocity = 100
fluidsynth.play_Note(n)

# time.sleep(1)
fluidsynth.play_Note(Note('A-5'))
time.sleep(1)
fluidsynth.play_Note(Note('C-5'))
# fluidsynth.stop_Note(Note("C-5"))


# e = Bar('E', (6, 8))
# e.place_notes("A-4", 4)
# fluidsynth.play_Bar(e, 1, 150)

time.sleep(2)
