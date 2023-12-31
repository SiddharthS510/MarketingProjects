# -*- coding: utf-8 -*-
"""EDLSTM_scoring_good.ipynb


"""

from __future__ import absolute_import, division, print_function

import os
import matplotlib.pyplot as plt

# Authenticate to GCS.
from google.colab import auth
auth.authenticate_user()

project_id = 'project1'

# Create the service client.
from googleapiclient.discovery import build
gcs_service = build('storage', 'v1')

from apiclient.http import MediaIoBaseDownload

# Copy raw data from bucket to /tmp directory
bucket_name = 'bucket-kctung75034-1'
file_name = 'small_train_data.csv'
path_and_file = '/tmp/'+file_name

with open(path_and_file, 'wb') as f:
  # Download the file from a given Google Cloud Storage bucket.
  request = gcs_service.objects().get_media(bucket=bucket_name,
                                            object=file_name)
  media = MediaIoBaseDownload(f, request)

  done = False
  while not done:
    # _ is a placeholder for a progress object that we ignore.
    # (Our file is small, so we skip reporting progress.)
    _, done = media.next_chunk()        
  
print('Download complete')

# Read and split raw data
from sklearn.cross_validation import train_test_split
import numpy as np

data_path = path_and_file

# Vectorize the data.

with open(data_path, 'r') as f:
    lines = f.read().split('\n')
    data = np.array(lines)
    
    train_dat ,remained = train_test_split(data,test_size=0.4) 
    validation_dat, test_dat = train_test_split(remained, test_size = 0.5)

# convert split data back to list
train_lines = list(train_dat)
validation_lines = list(validation_dat)
test_lines = list(test_dat)

# Set up all data to build a corpus
input_texts = []
target_texts = []
input_words = set()
target_words = set()

for line in lines:
  try:
    _, input_text, target_text = line.split("\t")
    # We use "tab" as the "start sequence" character
    # for the targets, and "\n" as "end sequence" character.
    target_text = '<start>' + " " + target_text + " " + '<stop>'   
    input_texts.append(input_text)
    target_texts.append(target_text)
    for word in input_text.split():
        if word not in input_words:
            input_words.add(word)
    for word in target_text.split():
        if word not in target_words:
            target_words.add(word)
  except:
    pass

# Build the corpus.
# sort word list, 0 reserves for unknown.
vocab = list(set(input_words).union(set(target_words)))
#vocab.insert(0, "out_of_vocab")
#vocab.insert(0, "\t")
#vocab.insert(0, "\n")

def create_corpus_dict(word_list):
  token_index = dict(
    [(word, i) for i, word in enumerate(word_list)])
  return token_index

corpus_dict = create_corpus_dict(vocab)

def split_input_and_target(line_list):
    input_texts = []
    target_texts = []
    
    try:

        for line in line_list:
            _, input_text, target_text = line.split('\t')
            # We use "tab" as the "start sequence" character
            # for the targets, and "\n" as "end sequence" character.
            target_text = '<start>' + " " + target_text + " " + '<stop>' 
            input_texts.append(input_text)
            target_texts.append(target_text)
            
    except:
      pass
    
    return input_texts, target_texts

# split each set of lines into input and target separately.
train_input_texts, train_target_texts  = split_input_and_target(train_lines)
validation_input_texts, validation_target_texts  = split_input_and_target(validation_lines)
test_input_texts, test_target_texts  = split_input_and_target(test_lines)

def get_array_specs(input_texts,target_texts, input_vocab, target_vocab):
    
    # input and target may have different vocab and different token count.
    input_vocab = sorted(list(input_vocab))
    target_vocab = sorted(list(target_vocab))
    num_encoder_tokens = len(input_vocab)
    num_decoder_tokens = len(target_vocab)
    max_encoder_seq_length = max([len(txt.split()) for txt in input_texts]) # number of words in each string.
    max_decoder_seq_length = max([len(txt.split()) for txt in target_texts])
    
    return num_encoder_tokens, num_decoder_tokens, max_encoder_seq_length, max_decoder_seq_length

# input and target use same vocab corpus.
num_encoder_tokens, num_decoder_tokens, max_encoder_seq_length, max_decoder_seq_length = get_array_specs(train_input_texts,train_target_texts, vocab, vocab)

num_encoder_tokens

num_decoder_tokens

#create zero-hot holder for input text list
import numpy as np

def create_zero_hot_holder(input_texts, max_encoder_seq_length, max_decoder_seq_length,num_encoder_tokens,num_decoder_tokens):
  encoder_input_data = np.zeros(
    (len(input_texts), max_encoder_seq_length, num_encoder_tokens),
    dtype='float32')
  decoder_input_data = np.zeros(
    (len(input_texts), max_decoder_seq_length, num_decoder_tokens),
    dtype='float32')
  decoder_target_data = np.zeros(
    (len(input_texts), max_decoder_seq_length, num_decoder_tokens),
    dtype='float32')
            
  return encoder_input_data, decoder_input_data, decoder_target_data

encoder_input_data_zero, decoder_input_data_zero, decoder_target_data_zero = create_zero_hot_holder(train_input_texts, max_encoder_seq_length, max_decoder_seq_length, num_encoder_tokens,num_decoder_tokens)

from keras.models import Model
from keras.layers import Input, LSTM, Dense
latent_dim = 256 
# Define an input sequence and process it.
encoder_inputs = Input(shape=(None, num_encoder_tokens))
encoder = LSTM(latent_dim, return_state=True)
encoder_outputs, state_h, state_c = encoder(encoder_inputs)
# We discard `encoder_outputs` and only keep the states.
encoder_states = [state_h, state_c]

def one_hot_encoding(encoder_input_data, decoder_input_data, decoder_target_data, input_texts, target_texts, input_corpus, target_corpus):
    for i, (input_text, target_text) in enumerate(zip(input_texts, target_texts)):
        for t, word in enumerate(input_text.split()):
            encoder_input_data[i, t, input_corpus[word]] = 1.
        for t, word in enumerate(target_text.split()):
            # decoder_target_data is ahead of decoder_input_data by one timestep
            decoder_input_data[i, t, target_corpus[word]] = 1.
            if t > 0:
                # decoder_target_data will be ahead by one timestep
                # and will not include the start character.
                decoder_target_data[i, t - 1, target_corpus[word]] = 1.
                
    return encoder_input_data, decoder_input_data, decoder_target_data

encoder_input_data, decoder_input_data, decoder_target_data = one_hot_encoding(encoder_input_data_zero, decoder_input_data_zero, decoder_target_data_zero, train_input_texts, train_target_texts, corpus_dict, corpus_dict)

# Define an input sequence and process it.
encoder_inputs = Input(shape=(None, num_encoder_tokens))
encoder = LSTM(latent_dim, return_state=True)
encoder_outputs, state_h, state_c = encoder(encoder_inputs)
# We discard `encoder_outputs` and only keep the states.
encoder_states = [state_h, state_c]

# Set up the decoder, using `encoder_states` as initial state.
decoder_inputs = Input(shape=(None, num_decoder_tokens))
# We set up our decoder to return full output sequences,
# and to return internal states as well. We don't use the
# return states in the training model, but we will use them in inference.
decoder_lstm = LSTM(latent_dim, return_sequences=True, return_state=True)
decoder_outputs, _, _ = decoder_lstm(decoder_inputs,
                                     initial_state=encoder_states)
decoder_dense = Dense(num_decoder_tokens, activation='softmax')
decoder_outputs = decoder_dense(decoder_outputs)

# Define the model that will turn
# `encoder_input_data` & `decoder_input_data` into `decoder_target_data`
model = Model([encoder_inputs, decoder_inputs], decoder_outputs)
model.compile(optimizer='adam', loss='categorical_crossentropy')

model.summary()

epoch_num = 10
batch_size_num = 64
import time
timestr = time.strftime("%Y%m%d-%H%M%S")
print(timestr)
model_name = 'ed_lstm_'+timestr
print(model_name)
model_structure = '/tmp/' + model_name + '.json'
model_weights = '/tmp/' + model_name + '.h5'
model_checkpoint = '/tmp/' + model_name + '_ckpt.h5'

from keras.callbacks import ModelCheckpoint
checkpoint = ModelCheckpoint(model_checkpoint, monitor='val_acc', verbose=1,
save_best_only=True, mode='min')
model.fit([encoder_input_data, decoder_input_data], decoder_target_data,
          batch_size=batch_size_num,
          epochs=epoch_num,
          validation_split=0.2,
          callbacks=[checkpoint], verbose=2)

# Save model
model.save('/tmp/'+ model_name)

# Next: inference mode (sampling).
# Here's the drill:
# 1) encode input and retrieve initial decoder state
# 2) run one step of decoder with this initial state
# and a "start of sequence" token as target.
# Output will be the next target token
# 3) Repeat with the current target token and current states

# Define sampling models
encoder_model = Model(encoder_inputs, encoder_states)

decoder_state_input_h = Input(shape=(latent_dim,))
decoder_state_input_c = Input(shape=(latent_dim,))
decoder_states_inputs = [decoder_state_input_h, decoder_state_input_c]
decoder_outputs, state_h, state_c = decoder_lstm(
    decoder_inputs, initial_state=decoder_states_inputs)
decoder_states = [state_h, state_c]
decoder_outputs = decoder_dense(decoder_outputs)
decoder_model = Model(
    [decoder_inputs] + decoder_states_inputs,
    [decoder_outputs] + decoder_states)

# Reassign variables for convenience
input_token_index = corpus_dict
target_token_index = corpus_dict

# Reverse-lookup token index to decode sequences back to
# something readable.
reverse_input_char_index = dict(
    (i, char) for char, i in input_token_index.items())
reverse_target_char_index = dict(
    (i, char) for char, i in target_token_index.items())

# input and target use same vocab corpus. This time is for holdout (test) data
test_num_encoder_tokens, test_num_decoder_tokens, test_max_encoder_seq_length, test_max_decoder_seq_length = get_array_specs(test_input_texts,test_target_texts, vocab, vocab)

test_num_encoder_tokens

test_num_decoder_tokens

# create zero-hot holders for holdout data
test_encoder_input_data_zero, test_decoder_input_data_zero, test_decoder_target_data_zero = create_zero_hot_holder(test_input_texts, test_max_encoder_seq_length, test_max_decoder_seq_length, test_num_encoder_tokens,test_num_decoder_tokens)

# one-hot encode holdout data
test_encoder_input_data, test_decoder_input_data, test_decoder_target_data = one_hot_encoding(test_encoder_input_data_zero, test_decoder_input_data_zero, test_decoder_target_data_zero, test_input_texts, test_target_texts, corpus_dict, corpus_dict)

test_encoder_input_data.shape

# step 1. encoder model predicts states_value by using one-hot inputs.
states_value = encoder_model.predict(test_encoder_input_data)

np.array(states_value).shape   # shape (state/value, observations, latent_dim)

# step 2. create a target_seq holder, with first position being initialized with the < start > token.

# Generate empty target sequence of length 1.
target_seq = np.zeros((test_encoder_input_data.shape[0], test_max_encoder_seq_length, num_decoder_tokens))
# Populate the first character of target sequence with the start character.
target_seq[:, 0, target_token_index['<start>']] = 1.

target_seq.shape

# step 3. decoder model can use target_seq holder and states_value to predict output_tokens, h, c.
output_tokens, h, c = decoder_model.predict([target_seq] + states_value)

output_tokens.shape # (observations, max sequence length, onehot corpus size)

# step 4. decoder output_tokens go through argmax to get integer index.
integer_list = output_tokens.argmax(axis=2)

integer_list.shape

# step 5. integer index is used to do reverse lookup to get to the corresponding word.
translated_array = np.vectorize(reverse_input_char_index.get)(integer_list)

translated_array[:10]

translated_list = translated_array.tolist()

translated_list[3]

translated_list = translated_array.tolist()
stop_word_list = ['<start>', '<stop>']
translated_list[3]
txt_holder = []
a = [item for item in translated_list[3] if item not in stop_word_list]

def extract_items(translated_words_list, exclusion_word_list):
  return [item for item in translated_words_list if item not in exclusion_word_list]

exclude_word_list = ['<start>', '<stop>']
truncated_list = []
for a_list in translated_list:
  truncated_list.append(extract_items(a_list, exclude_word_list))

predicted_list = []
for small_list in truncated_list:
    small_list_str = ' '.join(small_list)
    predicted_list.append(small_list_str)

truncated_list[:10]

predicted_list[:10]

len(predicted_list)

len(test_target_texts)

t1 = test_target_texts[:10]

t1

truth_holder = []
for item in test_target_texts:
    words = ''
    for word in item.split(' '):
        if word not in exclude_word_list:
            words += ' '
            words += word
            
    truth_holder.append(words)

truth_holder[:10]

assert len(truth_holder) == len(predicted_list)

s = len(predicted_list)
holdout_results_holder = np.zeros((s, 3), dtype='int8') # columns will be actual, predicted, tabulation

target_word = 'visit'
for i, (truth_target_texts, predicted_sentence) in enumerate(zip(truth_holder, predicted_list)):
      #print('i= %s, sentence = %s' % (i,predicted_sentence))
  
      truth_string = ''.join(truth_holder)
      eval_string = ''.join(predicted_list)
  
      if target_word in truth_string:
          holdout_results_holder[i][0] = 1
    
      if target_word in eval_string:
          holdout_results_holder[i][1] = 1
    
      if holdout_results_holder[i][0] == holdout_results_holder[i][1]:
          holdout_results_holder[i][-1] = 1

def compare_to_reference(truth_text_list, predicted_text_list, target_word):
  # two lists has to have same number of elements.
  # search for target word in each sentence list.
  # last column is labeled if target_word's condition is same in both lists.
  assert len(truth_text_list) == len(predicted_text_list)
  
  s = len(predicted_text_list)
  holdout_results_holder = np.zeros((s, 3), dtype='int8') # columns are actual, predicted, tabulation


  for i, (truth_target_texts, predicted_sentence) in enumerate(zip(truth_text_list, predicted_text_list)):
      #print('i= %s, sentence = %s' % (i,predicted_sentence))
  
      truth_string = ''.join(truth_target_texts)
      eval_string = ''.join(predicted_sentence)
  
      if target_word in truth_string:
          holdout_results_holder[i][0] = 1
    
      if target_word in eval_string:
          holdout_results_holder[i][1] = 1
    
      if holdout_results_holder[i][0] == holdout_results_holder[i][1]:
          holdout_results_holder[i][-1] = 1
  
  return holdout_results_holder

comp = compare_to_reference(truth_holder, predicted_list, 'visit')

import pandas as pd
def print_classification_report(truth, predicted, target_names_list):
    from sklearn.metrics import classification_report
    # for printing performance of a classifier.
    print(classification_report(truth, predicted, target_names = target_names_list))

df = pd.DataFrame(data=comp, columns = ["visited", "predicted", "tabulation"])
y_actu = pd.Series(df['visited'], name='Actual')
y_pred = pd.Series(df['predicted'], name = 'Predicted')

dl_confusion = pd.crosstab(y_actu, y_pred, rownames=['Actual'], colnames=['Predicted'], margins=True)
dl_confusion

predicted_results = y_pred.tolist()
truth = y_actu.tolist()
print_classification_report(truth, predicted_results, [ 'Actual 0', 'Actual 1'] )

type(dl_confusion)

dl_confusion.to_csv('/tmp/dl_confusion.csv', sep=',')

! ls /tmp

from sklearn.metrics import classification_report
rpt = classification_report(truth, predicted_results, target_names = [ 'Actual 0', 'Actual 1'])

type(rpt)

rpt = print_classification_report(truth, predicted_results, [ 'Actual 0', 'Actual 1'] )

with open("/tmp/classification_report.txt", "w") as text_file:
    text_file.write("%s" % rpt)

with open("/tmp/classification_report.txt", 'r') as f:
    rpt = f.read().split('\n')

rpt

type(rpt)

len(rpt)

df = pd.DataFrame({'col':rpt})

type(train_dat)

import pickle

with open('/tmp/train_dat.pickle', 'wb') as handle:
    pickle.dump(train_dat, handle, protocol=pickle.HIGHEST_PROTOCOL)

with open('/tmp/train_dat.pickle', 'rb') as handle:
    b = pickle.load(handle)

with open('/tmp/validation_dat.pickle', 'wb') as handle:
    pickle.dump(validation_dat, handle, protocol=pickle.HIGHEST_PROTOCOL)

with open('/tmp/test_dat.pickle', 'wb') as handle:
    pickle.dump(test_dat, handle, protocol=pickle.HIGHEST_PROTOCOL)

! ls /tmp ed_lstm_20180708-224041*

from keras.models import model_from_json

# serialize model to JSON
model_json = model.to_json()
with open("/tmp/model_ed_lstm_20180708-224041.json", "w") as json_file:
    json_file.write(model_json)
# serialize weights to HDF5
model.save_weights("/tmp/model_ed_lstm_20180708-224041.h5")
print("Saved model to disk")

!ls -lrt /tmp



# load json and create model
json_file = open('/tmp/model_ed_lstm_20180708-224041.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
loaded_model = model_from_json(loaded_model_json)
# load weights into new model
loaded_model.load_weights("/tmp/model_ed_lstm_20180708-224041.h5")
print("Loaded model from disk")

fdir = '/tmp/'
fname = 'train_dat.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

fdir = '/tmp/'
fname = 'validation_dat.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

fdir = '/tmp/'
fname = 'test_dat.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

fdir = '/tmp/'
fname = 'model_ed_lstm_20180708-224041.json'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

fdir = '/tmp/'
fname = 'model_ed_lstm_20180708-224041.h5'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

test_encoder_input_data

with open('/tmp/test_encoder_input_data.pickle', 'wb') as handle:
    pickle.dump(test_encoder_input_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'test_encoder_input_data.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

with open('/tmp/states_value.pickle', 'wb') as handle:
    pickle.dump(states_value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'states_value.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

#reverse_input_char_index

with open('/tmp/reverse_input_char_index.pickle', 'wb') as handle:
    pickle.dump(reverse_input_char_index, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'reverse_input_char_index.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

#reverse_target_char_index
with open('/tmp/reverse_target_char_index.pickle', 'wb') as handle:
    pickle.dump(reverse_target_char_index, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'reverse_target_char_index.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

# target_seq
with open('/tmp/target_seq.pickle', 'wb') as handle:
    pickle.dump(target_seq, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'target_seq.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

#output_tokens, h, c these are from output of decoder model predicting test data.
with open('/tmp/output_tokens.pickle', 'wb') as handle:
    pickle.dump(output_tokens, handle, protocol=pickle.HIGHEST_PROTOCOL)
    
fdir = '/tmp/'
fname = 'output_tokens.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

with open('/tmp/h.pickle', 'wb') as handle:
    pickle.dump(h, handle, protocol=pickle.HIGHEST_PROTOCOL)

fdir = '/tmp/'
fname = 'h.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

with open('/tmp/c.pickle', 'wb') as handle:
    pickle.dump(c, handle, protocol=pickle.HIGHEST_PROTOCOL)
    

fdir = '/tmp/'
fname = 'c.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

# truth_holder, predicted_list
with open('/tmp/truth_holder.pickle', 'wb') as handle:
    pickle.dump(truth_holder, handle, protocol=pickle.HIGHEST_PROTOCOL)
    

fdir = '/tmp/'
fname = 'truth_holder.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

# predicted_list
with open('/tmp/predicted_list.pickle', 'wb') as handle:
    pickle.dump(predicted_list, handle, protocol=pickle.HIGHEST_PROTOCOL)
    

fdir = '/tmp/'
fname = 'predicted_list.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

#comp


with open('/tmp/comp.pickle', 'wb') as handle:
    pickle.dump(comp, handle, protocol=pickle.HIGHEST_PROTOCOL)
    

fdir = '/tmp/'
fname = 'comp.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

! ls -lrt /tmp

#ed_lstm_20180708-224041

with open('/tmp/ed_lstm_20180708-224041.pickle', 'wb') as handle:
    pickle.dump(comp, handle, protocol=pickle.HIGHEST_PROTOCOL)
    

fdir = '/tmp/'
fname = 'ed_lstm_20180708-224041.pickle'
full_fname = fdir+fname
#write file to bucket
from googleapiclient.http import MediaFileUpload

media = MediaFileUpload(full_fname, 
                        mimetype='text/plain',
                        resumable=True)

request = gcs_service.objects().insert(bucket='bucket-kctung75034-1', 
                                       name=fname,
                                       media_body=media)

response = None
while response is None:
  # _ is a placeholder for a progress object that we ignore.
  # (Our file is small, so we skip reporting progress.)
  _, response = request.next_chunk()

print('Upload complete')
print('https://console.cloud.google.com/storage/browser?project={}'.format(project_id))

