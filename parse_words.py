import pandas as pd
from os import listdir
from os.path import join
from parse_midi import Midi
import json


def filter_timerange(timed_notes, start, end):
    # returns all notes that occurr during start-end
    return timed_notes[(timed_notes.end > start) & (timed_notes.start < end)]


def get_onset_deltas(timed_notes):
    unique_onsets = pd.Series(timed_notes['start'].unique()).sort_values()
    onset_deltas = (unique_onsets - unique_onsets.shift())[1:]
    return onset_deltas[onset_deltas > 0.000001]


def calc_slice_duration(timed_notes, p=0.05):
    onset_deltas = get_onset_deltas(timed_notes)
    slice_duration = 0
    p = 0
    while p < 0.05:
        count = 0
        for t in onset_deltas:
            if slice_duration >= t:
                count += 1
        p = count / len(onset_deltas)
        slice_duration += 0.00001
    return slice_duration


def slice_notes(timed_notes, slice_duration):
    notes_duration = max(timed_notes['end']) - min(timed_notes['start'])
    num_slices = int(notes_duration // slice_duration + 1)

    slice_to_id = []
    for i in range(num_slices):
        slice_to_id.append({
            'start': i * slice_duration,
            'end': (i + 1) * slice_duration,
            'id': i
        })
    slice_to_id = pd.DataFrame(slice_to_id)

    word_memberships = {}
    for _, note in timed_notes.iterrows():
        slices = filter_timerange(slice_to_id, note['start'], note['end'])
        for slice_id in slices['id']:
            if slice_id in word_memberships:
                word_memberships[slice_id].append(note)
            else:
                word_memberships[slice_id] = [note]

    words = []
    for slice_id in word_memberships.keys():
        words.append(pd.DataFrame(word_memberships[slice_id]))
    return words



def save_sentences(sentences, path='sentences.json'):
    jsonobj = {}
    for fp in sentences.keys():
        jsonobj[fp] = [w.to_dict(orient='records') for w in sentences[fp]]
    open(path, 'w').write(json.dumps(jsonobj))


def open_sentences(path='sentences.json'):
    sents = {}
    obj = json.loads(open(path, 'r').read())
    return obj

# midi_dir = './midi_files'
# file_paths = [join(midi_dir, x) for x in listdir(midi_dir)]
# print('Reading %s midi files...' % len(file_paths))


# sentences = {}
# for i, fp in enumerate(file_paths):

    

#     mid = Midi.from_file(fp)
#     notes_data = pd.DataFrame(mid.note_times())
#     word_duration = calc_slice_duration(notes_data, 0.05)
#     words = slice_notes(notes_data, word_duration)
#     print(i, fp, len(words))
#     sentences[fp] = words
#     save_sentences(sentences)
#     # break

sentences = open_sentences()

all_words = []
for _, sent in sentences.items():
    all_words += sent

immut = []
for word in all_words:
    w = []
    for n in word:
        w.append(n['midi'])
    immut.append(frozenset(w))
 
print(len(all_words))
print(len(set(immut)))

word_to_index = {}
index_to_word = {}

for i, word in enumerate(immut):
    word_to_index[word] = i
    index_to_word[i] = list(immut)

compressed = []
for word in all_words:
    w = []
    for n in word:
        w.append(n['midi'])
    compressed.append(word_to_index[frozenset(w)])

print(len(compressed))
print(compressed[:100])

# open('word_to_index.json', 'w').write(json.dumps(word_to_index))
# open('index_to_word.json', 'w').write(json.dumps(index_to_word))
open('words.txt', 'w').write(', '.join([str(x) for x in compressed]))

# compressed = []
# for word in words:
#     w = frozenset({'n': frozenset(word['midi']), 'v': word['vel'].mean().round(-1)}.items())
#     compressed.append(w)

# print(len(compressed))
