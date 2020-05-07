'''
rough MIDI Parser
https://github.com/colxi/midi-parser-js/wiki/MIDI-File-Format-Specifications
'''
from os import listdir
from os.path import join
import binascii
from typing import Tuple, Dict, Optional, NamedTuple, List
from io import BytesIO, BufferedReader

midi_dir = './mozart'
midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]


class Header(NamedTuple):
    format_type: int
    num_tracks: int
    division: bytes


class Event(NamedTuple):
    type: str
    data: Dict
    dtime: int

    def __repr__(self) -> str:
        return '[%s, %s, %s]' % (self.type, self.data, self.dtime)


def to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def read_variable_int(infile: BufferedReader) -> int:
    delta = 0
    while True:
        byte = to_int(infile.read(1))
        delta = (delta << 7) | (byte & 0x7f)
        if byte < 0x80:
            return delta


def read_meta_event(b: BufferedReader):
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
    flag = b.read(1)

    if flag in text_event_flags:
        text_len = to_int(b.read(1))
        text = b.read(text_len)
        return Event(text_event_flags[flag], {'msg': text}, 0)
    elif flag == b'\x20':
        raise NotImplementedError('MIDI Channel Prefix')
    elif flag == b'\x51':
        b.read(1)
        t = to_int(b.read(3))
        return Event('Set Tempo', {'tempo': t}, 0)
    elif flag == b'\x54':
        raise NotImplementedError('SMTPE Offset')
    elif flag == b'\x58':
        b.read(1)
        nn = to_int(b.read(1))
        dd = to_int(b.read(1))
        cc = to_int(b.read(1))
        bb = to_int(b.read(1))
        return Event('Time Signature:', {
            'nn': nn,
            'dd': 2 ** dd,
            'cc': cc,
            'bb': bb
        }, 0)

    elif flag == b'\x59':
        b.read(1)
        sf = int.from_bytes(b.read(1), byteorder='big', signed=True)
        mi = to_int(b.read(1))
        return Event('Key Signature:', {
            'sf': sf,
            'mi': mi
        }, 0)

    elif flag == b'\x7F':
        raise NotImplementedError('Sequencer-Specific Event')

    raise Exception('Uncaught meta event')


def read_event(b: BufferedReader, last_event=None) -> Event:
    if b.peek(1) is b'':
        return None
    status = ord(b.read(1))
    if status == 0xff:
        return read_meta_event(b)
    event_types = {
        0x8: 'note off',
        0x9: 'note on',
        0xA: 'note aftertouch',
        0xB: 'controller',
        0xC: 'program change',
        0xD: 'change value',
        0xE: 'pitch bend'
    }
    # status = status >> 4
    if status >> 4 in [0x8, 0x9, 0xA, 0xB, 0xE]:
        return Event(
            event_types[status >> 4],
            {'p1': to_int(b.read(1)), 'p2': to_int(b.read(1))},
            0)
    elif status >> 4 in [0xC, 0xD]:
        return Event(
            event_types[status >> 4],
            {'p1': to_int(b.read(1))},
            0)
    elif last_event:
        print(hex(status))
        if 'p2' not in last_event.data:
            return Event(
                last_event.type,
                {'p1': to_int(b.read(1))},
                0)   
        return Event(
            last_event.type,
            {'p1': to_int(b.read(1)), 'p2': to_int(b.read(1))},
            0)

    print('>>>', last_event, status, status == 0xfd)
    raise Exception('failed to parse event:', b.read(20))


def parse_track(b: BufferedReader) -> List[Event]:
    events: List[Event] = []
    lv = None
    while b.peek(1) != b'':
        delta = read_variable_int(b)
        evt = read_event(b, last_event=events[-1] if len(events) > 0 else None)
        events.append(evt)
    return events


file_path = midi_files[1]
with open(file_path, 'rb') as f:
    with BufferedReader(f) as b:
        header = None
        track_data = []
        b.seek(0, 0)
        while b.peek(4) is not b'':
            chunk_type = b.read(4)
            chunk_len = to_int(b.read(4))
            if chunk_type == b'MThd':
                assert chunk_len == 6
                header = Header(
                    to_int(b.read(2)), to_int(b.read(2)), b.read(2)
                )
            elif chunk_type == b'MTrk' and chunk_len > 0:
                track_buffer = BufferedReader(BytesIO(b.read(chunk_len)))
                track_data.append(parse_track(track_buffer))


        assert len(track_data) == header.num_tracks
        assert header

    from pprint import pprint
    # pprint(track_data[2])
    for track in track_data:
        print('----')
        for evt in track:
            if evt.type == 'Track Name':
                print(evt)
            if evt.type == 'note on':
                print(evt)