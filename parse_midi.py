'''
a very basic MIDI Parser
Max Sun 2020
# TODO:
- Stop using NamedTuple
'''
from os import listdir
from os.path import join
from typing import Dict, Optional, NamedTuple, List, Union, Tuple
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
    return (delta << 7) | (to_int(byte) & 0x7f)


class MessageType(Enum):
    # Channel Events:
    Note_Off = 0x8
    Note_On = 0x9
    Note_Aftertouch = 0xA
    Controller = 0xB
    Program = 0xC
    Channel_Aftertouch = 0xD
    Pitch = 0xE
    # Meta Events:
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

    def is_meta(self) -> bool:
        return self not in [
            MessageType.Note_Off,
            MessageType.Note_On,
            MessageType.Note_Aftertouch,
            MessageType.Controller,
            MessageType.Program,
            MessageType.Channel_Aftertouch,
            MessageType.Pitch]


class Event(NamedTuple):
    status: MessageType
    channel: int
    data: bytes
    dtime: int

    @staticmethod
    def from_bytes(b: BufferedReader, dtime: int) -> 'Event':

        status = to_int(b.read(1))
        if status == 0xff:
            status = to_int(b.read(1))
            msg_len = to_int(b.read(1))

            return Event(
                MessageType(status),
                0,
                b.read(msg_len), dtime)

        value = status >> 4
        msg_len = 1 if MessageType(value) in [
            MessageType.Program,
            MessageType.Channel_Aftertouch] else 2

        return Event(
            MessageType(value),
            status % 16,
            b.read(msg_len), dtime)


class Track(NamedTuple):

    metadata: Dict
    events: List[Event]

    @staticmethod
    def from_bytes(b: BufferedReader) -> 'Track':
        chunk_len = to_int(b.read(4))
        start_pos = b.tell()
        events: List[Event] = []
        # TODO: stop while on 'Track End' Message
        while b.tell() - start_pos < chunk_len:
            last_event = events[-1] if len(events) > 0 else None

            dtime = read_variable_int(b)
            status_peek = b.peek(1)[:1]

            if status_peek < b'\x80' and isinstance(last_event, Event):
                events.append(Event(
                    last_event.status,
                    last_event.channel,
                    b.read(len(last_event.data)), dtime))
            else:
                events.append(Event.from_bytes(b, dtime))

        return Track({}, events)

    def abs_times(self) -> List[Tuple[int, Event]]:
        event_times = []
        t = 0
        for evt in self.events:
            t += evt.dtime
            event_times.append((t, evt))

        return sorted(event_times, key=lambda x: x[0])



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
                tracks.append(Track.from_bytes(b))
        if header is None:
            raise Exception('Failed to find header!')
        return Midi(header, tracks)

    @staticmethod
    def from_file(path: str) -> 'Midi':
        with open(path, 'rb') as f:
            fio = FileIO(f.fileno())
            buff = BufferedReader(fio)
            return Midi.from_bytes(buff)


    def abs_times(self) -> List[Tuple[float, Event]]:
        ticks_per_qbeat = to_int(self.header.division) & 0x7fff

        tempo_events = [(0, 500000)]
        for track in self.tracks:
            tick_time = 0
            for evt in track.events:
                tick_time += evt.dtime
                if evt.status == MessageType.Set_Tempo:
                    tempo_events.append((tick_time, to_int(evt.data)))
        tempo_events = sorted(tempo_events, key=lambda x: x[0])

        tempo = 120
        results: List[Tuple[float, Event]] = []
        for track in self.tracks:
            time: float = 0.0
            tick_index = 0
            for evt in track.events:
                tick_index += evt.dtime
                tempo = [x for x in tempo_events if x[0] <= tick_index][0][1]
                secs_per_tick = ticks_per_qbeat / tempo
                time += evt.dtime * secs_per_tick
                results.append((time, evt))

        return sorted(results, key=lambda x: x[0])

    def note_times(self):
        note_times = []
        on_notes = {}
        for time, evt in self.abs_times():
            if evt.status in [MessageType.Note_On, MessageType.Note_Off]:
                midi_note = evt.data[0]
                if evt.status == MessageType.Note_Off or evt.data[1] == 0 and midi_note in on_notes:
                    note_times.append({
                        'start': on_notes[midi_note][0],
                        'end': time,
                        'midi': midi_note,
                        'vel': on_notes[midi_note][1]
                    })
                    del on_notes[midi_note]
                else:
                    vel = evt.data[1]
                    on_notes[midi_note] = (time, vel)

            # if evt.status == MessageType.Note_On:
            #     if evt.data[1] == 0 and evt.data[0] in on_notes:
            #         note_times.append((evt, (on_notes[evt.data[0]], time)))
            #         del on_notes[evt.data[0]]
            #     else:
            #         on_notes[evt.data[0]] = time
            # elif evt.status == MessageType.Note_Off:
            #     note_times.append((evt, (on_notes[evt.data[0]], time)))
            #     del on_notes[evt.data[0]]
        return note_times



if __name__ == '__main__':
    midi_dir = './midi_files'
    midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]

    file_path = midi_files[9]
    with open(file_path, 'rb') as midi_file:
        fio = FileIO(midi_file.fileno())
        midi_buffer = BufferedReader(fio)
        midi = Midi.from_bytes(midi_buffer)
        # print(midi.abs_times())
        x = midi.note_times()
        # print(midi.tempo_at_tick(20000))
        print(x)
