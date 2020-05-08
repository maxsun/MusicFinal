'''
a very basic MIDI Parser
Max Sun 2020
'''
from os import listdir
from os.path import join
from typing import Dict, Optional, NamedTuple, List, Union
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

    def data_len(self) -> int:
        if self in [0xC, 0xD]:
            return 1
        return 2

    def parse_data(self, data: bytes):
        p1, p2 = {
            EventType.Note_Off: ('Note', 'Velocity'),
            EventType.Note_On: ('Note', 'Velocity'),
            EventType.Note_Aftertouch: ('Note', 'Amount'),
            EventType.Controller: ('Controller Num', 'Value'),
            EventType.Program: ('Program Num', None),
            EventType.Channel_Aftertouch: ('Amount', None),
            EventType.Pitch: ('LSB', 'MSB')
        }[self]

        if p1 and p2:
            return {p1: data[0], p2: data[1]}
        elif p1:
            return {p1: data[0]}

        raise Exception('Error Parsing Data!')


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

    def parse_data(self, data: bytes):

        if self == MetaEventType.SMPTE_Offset:
            raise NotImplementedError('SPTME Offset Parsing missing!')

        if self == MetaEventType.Time_Sig:
            return str(data)

        if self in [
            MetaEventType.Sequence_Num,
            MetaEventType.Midi_Channel_Prefix,
            MetaEventType.Set_Tempo
        ]:
            return to_int(data)
        
        return str(data)



class Event(NamedTuple):
    status: EventType
    channel: int
    data: bytes

    def __repr__(self) -> str:
        params = []
        for byte in self.data:
            params.append(byte)
        x = self.status.parse_data(self.data)
        return '%s: %s' % (self.status, str(x))

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Event':

        status = b.read(1)

        value = to_int(status) >> 4
        return Event(
            EventType(value),
            to_int(status) % 16,
            b.read(EventType(value).data_len()))


class MetaEvent(NamedTuple):
    status: MetaEventType
    data: bytes

    def __repr__(self) -> str:
        params = []
        for byte in self.data:
            params.append(byte)
        x = self.status.parse_data(self.data)
        return '%s: %s' % (self.status, str(x))


    # TODO: Find out what channel meta events should be on

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'MetaEvent':
        meta_flag = to_int(b.read(1))
        assert meta_flag == 0xff
        msg_type = to_int(b.read(1))
        msg_len = to_int(b.read(1))
        data = b.read(msg_len)
        return MetaEvent(MetaEventType(msg_type), data)


class Track(NamedTuple):

    metadata: Dict
    events: List[Union[Event, MetaEvent]]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Track':
        chunk_len = to_int(b.read(4))
        start_pos = b.tell()
        events: List[Union[Event, MetaEvent]] = []
        while b.tell() - start_pos < chunk_len:
            last_event = events[-1] if len(events) > 0 else None

            dtime = read_variable_int(b)
            status_peek = b.peek(1)[:1]

            # print(hex(to_int(status_peek)))
            if status_peek == b'\xff':
                events.append(MetaEvent.from_bytes(b))
            elif status_peek < b'\x80' and last_event and isinstance(last_event, Event):
                events.append(Event(
                    last_event.status,
                    last_event.channel,
                    b.read(len(last_event.data))))
            else:
                events.append(Event.from_bytes(b))

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
