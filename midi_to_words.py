'''
rough MIDI Parser
https://github.com/colxi/midi-parser-js/wiki/MIDI-File-Format-Specifications
'''
from os import listdir
from os.path import join
import binascii
from typing import Tuple, Dict, Optional, NamedTuple
from io import BytesIO

midi_dir = './mozart'
midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]


def to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def read_variable_int(infile):
    delta = 0

    while True:
        byte = infile[0]
        delta = (delta << 7) | (byte & 0x7f)
        if byte < 0x80:
            return (delta, infile[1:])
        infile = infile[1:]


def read_event(b: bytes, last_event=None):
    event_type = b[0]
    if event_type == 0xff:
        text_event_flags = {
            b'\x01': 'Text',
            b'\x02': 'Copyright Notice',
            b'\x03': 'Track Name',
            b'\x04': 'Instrument Name',
            b'\x05': 'Lyric',
            b'\x06': 'Marker',
            b'\x07': 'Cue Point',
            b'\x2f': 'End of track'
        }
        meta_flag = b[1:2]

        if meta_flag in text_event_flags:
            text_len = to_int(b[2:3])
            text = b[3:3 + text_len]
            return ((text_event_flags[meta_flag], text), b[3 + text_len:])
        elif meta_flag == b'\x20':
            raise NotImplementedError('MIDI Channel Prefix')
        elif meta_flag == b'\x51':
            t = to_int(b[3:6])
            assert t >= 0 and t <= 8355711
            return (('Set Tempo', t), b[6:])
        elif meta_flag == b'\x54':
            raise NotImplementedError('SMTPE Offset')
        elif meta_flag == b'\x58':
            nn = to_int(b[3:4])
            dd = 2 ** to_int(b[4:5])
            cc = to_int(b[5:6])  # typically 24
            bb = to_int(b[6:7])  # typically 8
            assert nn >= 0 and nn <= 255
            assert dd >= 0 and dd <= 255
            assert cc >= 0 and cc <= 255
            assert bb >= 1 and bb <= 255
            return (('Time Signature:', (nn, dd, cc, bb)), b[7:])

        elif meta_flag == b'\x59':
            sf = int.from_bytes(b[3:4], byteorder='big', signed=True)
            mi = to_int(b[4:5])
            assert sf >= -7 and sf <= 7
            assert mi == 0 or mi == 1
            return(('Key Signature:', (sf, mi)), b[5:])

        elif meta_flag == b'\x7F':
            raise NotImplementedError('Sequencer-Specific Event')

        else:
            raise Exception('Uncaught meta event')
    else:
        event_types = {
            0x8: 'note off',
            0x9: 'note on',
            0xA: 'note aftertouch',
            0xB: 'controller',
            0xC: 'program change',
            0xD: 'change value',
            0xE: 'pitch bend'
        }
        val = event_type >> 4
        p1 = to_int(b[1:2])
        p2 = to_int(b[2:3])
        if val in [0x8, 0x9, 0xA, 0xB, 0xE]:
            return ((event_types[val], p1, p2), b[3:])
        elif val in [0xC, 0xD]:
            return ((event_types[val], p1, None), b[2:])
        elif val < 0x8:
            if last_event[2] is None:
                return ((last_event[0], to_int(b[0:1]), None), b[1:])
            else:
                return ((last_event[0], to_int(b[0:1]), to_int(b[1:2])), b[2:])

    raise Exception('failed to parse event:', b[:20])


def parse_track(b: bytes):
    events = [None]
    lv = None
    while len(b) > 0:
        delta, b = read_variable_int(b)
        if len(b) == 0:
            break
        evt, b = read_event(b, last_event=events[-1])
        events.append(evt)

    print(events)
    count = 0
    for e in events:
        if e and e[0] == 'note on':
            count += 1
    print(count)

file_path = midi_files[0]
print(file_path)
with open(file_path, 'rb') as f:
    f.seek(0, 0)
    while f.peek(4) is not b'':
        chunk_type = f.read(4)
        chunk_len = to_int(f.read(4))
        chunk_data = f.read(chunk_len)

        if chunk_type == b'MThd':
            pass
        elif chunk_type == b'MTrk' and chunk_len > 0:
            parse_track(chunk_data)
