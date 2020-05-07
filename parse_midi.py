'''
a rough MIDI Parser

Reference:
https://github.com/colxi/midi-parser-js/wiki/MIDI-File-Format-Specifications

Max Sun 2020
'''
from os import listdir
from os.path import join
import binascii
from typing import Tuple, Dict, Optional, NamedTuple, List
from io import BytesIO, BufferedReader, FileIO


def to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def read_variable_int(infile: BufferedReader) -> int:
    delta = 0
    while True:
        byte = to_int(infile.read(1))
        delta = (delta << 7) | (byte & 0x7f)
        if byte < 0x80:
            return delta


midi_dir = './mozart'
midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]


class Event(NamedTuple):
    status: bytes
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
        x = to_int(self.status) >> 4
        if self.status == b'\xff':
            return 'META: %s' % str(self.data)
        elif x in status_map:
            params = []
            for byte in self.data:
                params.append(byte)
            return '%s: %s' % (status_map[x], str(params))

        raise Exception('Error while printing Event!')        

    @staticmethod
    def from_bytes(b: BufferedReader, running_status: Optional[bytes]) -> 'Event':
        dtime = read_variable_int(b)
        status = b.read(1)
        if status == b'\xff':
            _type = b.read(1)
            msg_len = to_int(b.read(1))
            data = b.read(msg_len)
            return Event(status, data, 0)

        if status < b'\x80' and running_status:
            # TODO: FIX THIS
            n = to_int(running_status) % 16
            evt_value = to_int(running_status) >> 4
            if evt_value in [0xC, 0xD]:
                data = status
            else:
                # TODO: capture the status byte too
                data = b.read(1)

            return Event(running_status, status + data, dtime)

        if to_int(status) >> 4 in [0x8, 0x9, 0xA, 0xB, 0xC, 0xD, 0xE]:
            n = to_int(status) % 16
            evt_value = to_int(status) >> 4
            if evt_value in [0xC, 0xD]:
                data = b.read(1)
            else:
                data = b.read(2)
            return Event(status, data, dtime)

        raise Exception('Failed to read event:', status)


class Track(NamedTuple):
    metadata: Dict
    events: List[Event]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Track':
        chunk_len = to_int(b.read(4))
        start_pos = b.tell()
        running_status = None
        events = []
        while b.tell() - start_pos < chunk_len:
            event = Event.from_bytes(b, running_status)
            running_status = event.status
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


file_path = midi_files[9]
with open(file_path, 'rb') as midi_file:
    fio = FileIO(midi_file.fileno())
    midi_buffer = BufferedReader(fio)
    while midi_buffer.peek(4):
        chunk_type = midi_buffer.read(4)
        if chunk_type == b'MThd':
            header = Header.from_bytes(midi_buffer)
            print(header)
        elif chunk_type == b'MTrk':
            track = Track.from_bytes(midi_buffer)
            print(track)
