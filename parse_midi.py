'''
a rough MIDI Parser

Reference:
https://github.com/colxi/midi-parser-js/wiki/MIDI-File-Format-Specifications

Max Sun 2020
'''
from os import listdir
from os.path import join
from typing import Dict, Optional, NamedTuple, List
from io import BufferedReader, FileIO


def to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def read_variable_int(buff: BufferedReader) -> int:
    delta = 0
    byte = buff.read(1)
    while byte >= b'\x80':
        delta = (delta << 7) | (to_int(byte) & 0x7f)
        byte = buff.read(1)
    return delta


class Event(NamedTuple):
    status: bytes
    channel: int
    data: bytes
    delta_time: int

    def __repr__(self) -> str:
        status_map = {
            0x8: 'note off',
            0x9: 'note on',
            0xA: 'note aftertouch',
            0xB: 'controller',
            0xC: 'program change',
            0xD: 'channel aftertouch',
            0xE: 'pitch bend',
        }
        status = to_int(self.status) >> 4
        if status == 0xf:
            return 'META: %s' % str(self.data)

        elif status in status_map:
            params = []
            for byte in self.data:
                params.append(byte)
            return '%s: %s' % (status_map[status], str(params))

        raise Exception('Error while printing Event:', str(status))

    @staticmethod
    def from_bytes(b: BufferedReader, prev_evt: Optional['Event']) -> 'Event':
        dtime = read_variable_int(b)
        status = b.read(1)
        if status == b'\xff':
            _type = b.read(1)
            msg_len = to_int(b.read(1))
            data = b.read(msg_len)
            return MetaEvent(_type, -1, data, 0)

        data = b''
        if status < b'\x80' and prev_evt:
            data += status
            status = prev_evt.status

        channel = to_int(status) % 16
        value = to_int(status) >> 4
        if value in [0x8, 0x9, 0xA, 0xB, 0xC, 0xD, 0xE]:
            if value in [0xC, 0xD]:
                data += b.read(1 - len(data))
            else:
                data += b.read(2 - len(data))

        return Event(status, channel, data, dtime)


class MetaEvent(Event):

    def __repr__(self) -> str:
        status_map = {
            0x00: 'sequence number',
            0x01: 'text event',
            0x02: 'copyright notice',
            0x03: 'track name',
            0x04: 'instrument name',
            0x05: 'lyrics',
            0x06: 'marker',
            0x07: 'cue point',
            0x20: 'midi channel prefix',
            0x2f: 'end of track',
            0x51: 'set tempo',
            0x54: 'smpte offset',
            0x58: 'time signature',
            0x59: 'key signature',
        }
        status = to_int(self.status)
        if status in status_map:
            return '%s: %s' % (status_map[status], str(self.data))

        raise Exception('Error while printing Event: ' + str(self.status))


class Track(NamedTuple):
    metadata: Dict
    events: List[Event]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Track':
        chunk_len = to_int(b.read(4))
        start_pos = b.tell()
        events: List[Event] = []
        while b.tell() - start_pos < chunk_len:
            prev_evt = events[-1] if len(events) > 0 else None
            event = Event.from_bytes(b, prev_evt)
            events.append(event)

        return Track({}, events)


class Header(NamedTuple):
    format: int
    tracks: int
    division: bytes

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Header':
        header_len = to_int(b.read(4))
        assert header_len == 6
        return Header(
            to_int(b.read(2)),
            to_int(b.read(2)),
            b.read(2)
        )


class Midi(NamedTuple):
    header: Header
    tracks: List[Track]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Midi':
        header = None
        tracks = []
        while midi_buffer.peek(4):
            chunk_type = midi_buffer.read(4)
            if chunk_type == b'MThd':
                header = Header.from_bytes(midi_buffer)
            elif chunk_type == b'MTrk':
                track = Track.from_bytes(midi_buffer)
                tracks.append(track)
        return Midi(header, tracks)


midi_dir = './mozart'
midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]

file_path = midi_files[9]
with open(file_path, 'rb') as midi_file:
    fio = FileIO(midi_file.fileno())
    midi_buffer = BufferedReader(fio)
    midi = Midi.from_bytes(midi_buffer)
    print(midi)
