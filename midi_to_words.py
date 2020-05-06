'''
rough MIDI Parser
'''
from os import listdir
from os.path import join
import abinascii
from typing import Tuple, Dict, Optional, NamedTuple

from io import BytesIO


class Header(NamedTuple):
    format: int
    tracks: int
    division: bytes



def bytes_to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='big')


# def get_var_num(data: bytes) -> Tuple[int, bytes]:
#         print('Finding num:', data[:30])
#         dtime_bytes = bytearray([])
#         i = 0
#         while data[i] >> 8 != 0:
#             dtime_bytes.append(data[i])
#             i += 1
    
#         dtime = bytes_to_int(dtime_bytes)
#         print('>>>>', data[:i+10])
#         return (dtime, data[i + 1:])

def print_binary(b: bytes):
    for byte in b:
        print('{0:08b}'.format(byte))


def print_hex(b: bytes):
    print(binascii.hexlify(b))


def get_var_num(tmpstr: bytes) -> Tuple[int, bytes]:
    sum = 0 
    i = 0 
    while 1: 
        x = tmpstr[i] 
        i = i + 1 
        sum = (sum << 7) + (x & 0x7F) 
        if not (x & 0x80):
            return sum, tmpstr[i:]


def parse_track(track_data: bytes):
    print('=== Parsing Track ===')
    track_data = track_data
    while len(track_data) > 0:
        dtime, track_data = get_var_num(track_data)
        print('*****', track_data[:20])
        curr_byte = track_data[:1]
        if curr_byte.startswith(b'\xFF'):
            text_event_flags = {
                b'\x01': 'Text',
                b'\x02': 'Copyright Notice',
                b'\x03': 'Track Name',
                b'\x04': 'Instrument Name',
                b'\x05': 'Lyric',
                b'\x06': 'Marker',
                b'\x07': 'Cue Point'
            }
            meta_flag = track_data[1:2]

            if meta_flag in text_event_flags:
                text_len = bytes_to_int(track_data[2:3])
                text = track_data[3:3 + text_len]
                print('Meta:', text)
                track_data = track_data[3 + text_len:]

            elif track_data.startswith(b'\xFF\x20\x01'):
                print('MIDI Channel Prefix')
                cc = bytes_to_int(track_data[3:4])
                track_data = track_data[4:]
            elif track_data.startswith(b'\xFF\x2F\x00'):
                print('End of Track')
                track_data = track_data[3:]
            
            elif track_data.startswith(b'\xFF\x51\x03'):
                t = bytes_to_int(track_data[3:6])
                # print('Set Tempo:', t)
                track_data = track_data[6:]

            elif track_data.startswith(b'\xFF\x54\x05'):
                print('SMTPE Offset:')
                hh = track_data[3:4]
                mm = track_data[4:5]
                ss = track_data[5:6]
                fr = track_data[6:7]
                ff = track_data[7:8]
                # t = bytes_to_int(track_data[3:6])
                track_data = track_data[8:]

            elif track_data.startswith(b'\xFF\x58\x04'):
                print('Time Signature')
                nn = bytes_to_int(track_data[3:4])
                dd = 2 ** bytes_to_int(track_data[4:5])
                cc = bytes_to_int(track_data[5:6]) # typically 24
                bb = bytes_to_int(track_data[6:7]) # typically 8
                print((nn, dd, cc, bb))
                track_data = track_data[7:]
            
            elif track_data.startswith(b'\xFF\x59\x02'):
                print('Key Signature')
                sf = int.from_bytes(track_data[3:4], byteorder='big', signed=True)
                mi = bytes_to_int(track_data[4:5])
                assert sf >= -7 and sf <= 7
                assert mi == 0 or mi == 1
                print((sf, mi))
                track_data = track_data[5:]

            elif track_data.startswith(b'\xFF\x7F'):
                print('Sequencer-Specific Event')
                evt_len = bytes_to_int(track_data[2:3])
                # TODO: register event id
                evt_data = track_data[3:3 + evt_len]
                track_data = track_data[3 + evt_len:]
            
            else:
                # print_hex(curr_byte)
                # print_hex(meta_flag)
                raise Exception('Uncaught meta event')
        elif track_data[0] >> 4 == 0x8:
            n = track_data[0] % 8
            kk = bytes_to_int(track_data[1:2])
            vv = bytes_to_int(track_data[2:3])
            assert kk >= 0 and kk <= 127
            assert vv >= 0 and vv <= 127
            print('Note off:', (n, kk, vv))
            track_data = track_data[3:]
        elif track_data[0] >> 4 == 0x9:
            n = track_data[0] % 8
            kk = bytes_to_int(track_data[1:2])
            vv = bytes_to_int(track_data[2:3])
            assert kk >= 0 and kk <= 127
            assert vv >= 0 and vv <= 127
            print('Note on:', (n, kk, vv))
            track_data = track_data[3:]
        elif track_data[0] >> 4 == 0xB:
            # Ref: http://personal.kent.edu/~sbirch/Music_Production/MP-II/MIDI/midi_control_change_messages.htm
            n = track_data[0] % 8
            cc = track_data[1:2]
            nn = bytes_to_int(track_data[2:3])
            assert n >= 0 and n <= 127
            print('Controller Change:', (n, cc, nn))
            track_data = track_data[3:]
            print('>>>', track_data[:50])
        elif track_data[0] >> 4 == 0xC:
            n = track_data[0] % 8
            pp = bytes_to_int(track_data[1:2])
            print('Program Change:', (n, pp))
            track_data = track_data[2:]


        else:
            print(track_data[0] >> 4)
            print_hex(track_data[0:1])
            print(track_data[:20])
            raise Exception('Uncaught & unknown event')

        # track_data = track_data[1:]

            

midi_dir = './mozart'
midi_files = [join(midi_dir, x) for x in listdir(midi_dir)]


with open(midi_files[5], 'rb') as f:
    data = BytesIO(f.read())
    data.seek(0, 0)
    
    header_data: Optional[Header] = None
    tracks_data = []

    curr_byte = data.read(4)
    while curr_byte:
        # hex_data = binascii.hexlify(curr_byte)
        if curr_byte == b'MThd':
            header_length = bytes_to_int(data.read(4))
            assert header_length == 6
            header_data = Header(
                bytes_to_int(data.read(2)),
                bytes_to_int(data.read(2)),
                data.read(2))

        elif curr_byte == b'MTrk':
            track_length = bytes_to_int(data.read(4))
            # track_data = BytesIO(data.read(track_length))
            # track_data = parse_track(f.read(track_length))
            tracks_data.append(parse_track(data.read(track_length)))


        curr_byte = data.read(4)
    
    assert header_data
    assert len(tracks_data) == header_data.tracks