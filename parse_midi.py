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

    @staticmethod
    def from_bytes(b: BufferedReader, running_status: Optional[bytes]) -> 'Event':
        dtime = read_variable_int(b)
        status = b.read(1)
        if status == b'\xff':
            _type = b.read(1)
            msg_len = to_int(b.read(1))
            data = b.read(msg_len)
            return Event(_type, data, 0)

        if status < b'\x80' and running_status:
            # TODO: FIX THIS
            n = to_int(running_status) % 16
            evt_value = to_int(running_status) >> 4
            if evt_value in [0xC, 0xD]:
                data = status
            else:
                # TODO: capture the status byte too
                data = b.read(1)
            return Event(running_status, data, dtime)

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
        running_status = None
        events = []
        while b.peek(1):
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
        return Header(
            to_int(b.read(2)),
            to_int(b.read(2)),
            b.read(2)
        )


file_path = midi_files[1]
with open(file_path, 'rb') as midi_file:
    fio = FileIO(midi_file.fileno())
    midi_buffer = BufferedReader(fio)
    # with BufferedReader(midi_file) as midi_buffer:
    while midi_buffer.peek(4) is not b'':
        chunk_type = midi_buffer.read(4)
        chunk_len = to_int(midi_buffer.read(4))
        chunk_buff = BufferedReader(BytesIO(midi_buffer.read(chunk_len))) 
        if chunk_type == b'MThd':
            header = Header.from_bytes(chunk_buff)
            print(header)
        elif chunk_type == b'MTrk' and chunk_len > 0:
            track = Track.from_bytes(chunk_buff)
            
            for e in track.events:
                if to_int(e.status) >> 4 == 0x9:
                    print(e)
                # break
