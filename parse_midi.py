'''
a very basic MIDI Parser
Max Sun 2020
'''
from os import listdir
from os.path import join
from typing import Dict, Optional, NamedTuple, List
from io import BufferedReader, FileIO
from enum import Enum


def to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


def read_variable_int(buff: BufferedReader) -> int:
    delta: int = 0
    byte = buff.read(1)
    while byte >= b'\x80':
        delta = (delta << 7) | (to_int(byte) & 0x7f)
        byte = buff.read(1)
    return delta


class EventType(Enum):
    Note_Off = 0x8
    Note_On = 0x9
    Note_Aftertouch = 0xA
    Controller = 0xB
    Program = 0xC
    Channel_Aftertouch = 0xD
    Pitch = 0xE


class MetaEventType(Enum):
    Sequence_Num = 0x00
    Text_Event = 0x01
    Copyright = 0x02
    Track_Name = 0x03
    Instr_Name = 0x04
    Lyrics = 0x05
    Marker = 0x06
    Cue_Point = 0x07
    Midi_Channel_Prefix = 0x20
    End_Track = 0x2f
    Set_Tempo = 0x51
    SMPTE_Offset = 0x54
    Time_Sig = 0x58
    Key_Sig = 0x59


class Event(NamedTuple):
    status: bytes
    channel: int
    data: bytes
    delta_time: int

    def __repr__(self) -> str:
        status = to_int(self.status) >> 4
        params = []
        for byte in self.data:
            params.append(byte)
        return '%s: %s' % (EventType(status), str(params))

    @staticmethod
    def from_bytes(b: BufferedReader, last_event: Optional['Event']) -> 'Event':
        dtime = read_variable_int(b)
        status = b.read(1)
        if status == b'\xff':
            msg_type = b.read(1)
            msg_len = to_int(b.read(1))
            data = b.read(msg_len)
            # TODO: Find out what channel meta events should be on
            return MetaEvent(msg_type, -1, data, dtime)

        if status < b'\x80' and last_event:
            return Event(
                last_event.status,
                last_event.channel,
                status + b.read(len(last_event.data) - 1),
                dtime)

        channel = to_int(status) % 16
        value = to_int(status) >> 4
        if value in [0x8, 0x9, 0xA, 0xB, 0xE]:
            return Event(status, channel, b.read(2), dtime)
        elif value in [0xC, 0xD]:
            return Event(status, channel, b.read(1), dtime)
        else:
            raise Exception('Unable to read Event!')


class MetaEvent(Event):

    def __repr__(self) -> str:
        status = to_int(self.status)
        return '%s: %s' % (MetaEventType(status), str(self.data))


class Track(NamedTuple):
    metadata: Dict
    events: List[Event]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Track':
        chunk_len = to_int(b.read(4))
        start_pos = b.tell()
        events: List[Event] = []
        while b.tell() - start_pos < chunk_len:
            last_event = events[-1] if len(events) > 0 else None
            event = Event.from_bytes(b, last_event)
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
        while b.peek(4):
            chunk_type = b.read(4)
            if chunk_type == b'MThd':
                header = Header.from_bytes(b)
            elif chunk_type == b'MTrk':
                track = Track.from_bytes(b)
                tracks.append(track)
        if header is None:
            raise Exception('Failed to find header!')
        return Midi(header, tracks)

    @staticmethod
    def from_file(path: str) -> 'Midi':
        with open(path, 'rb') as f:
            fio = FileIO(f.fileno())
            buff = BufferedReader(fio)
            return Midi.from_bytes(buff)


if __name__ == '__main__':
    midi_dir = './midi_files'
    midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]

    file_path = midi_files[9]
    with open(file_path, 'rb') as midi_file:
        fio = FileIO(midi_file.fileno())
        midi_buffer = BufferedReader(fio)
        midi = Midi.from_bytes(midi_buffer)
        print(midi)
