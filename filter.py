#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Dec  5 14:26:42 2021

@author: charlottemaistriau
"""

#libraries


import glob
import os
import tensorflow as tf
import pandas as pd
import numpy as np
from sklearn.utils import shuffle

'''
path_fischer = '/content/chess-games-dataset/Data/CSV_FISCHER'
path_morphy = '/content/chess-games-dataset/Data/CSV_MORPHY'
path_capablanca = '/content/chess-games-dataset/Data/CSV_CAPABLANCA'

files_fischer = glob.glob(path_fischer + "/*.csv")
#files_morphy = glob.glob(path_morphy + "/*.csv")
#files_capablanca = glob.glob(path_capablanca + "/*.csv")

            
li = []

for filename in files_fischer:
    df = pd.read_csv(filename, index_col=None, header=0)
    li.append(df)
'''
'''
train = pd.read_csv('filtered_2100_ranking.csv', index_col=None, header=0)
#train = pd.concat(li, axis=0, ignore_index=True)

train = shuffle(train)

print (train.shape)

print (train.head())

#features : 
features = list(train.iloc[:, 0:192].columns)
X = train[features]
y = train['good_move']
categorical_columns = list(X.iloc[:, 0:63].columns)
numerical_columns = list(X.iloc[:, 64:192].columns)
feature_columns = []

for feature_name in categorical_columns:
  vocabulary = X[feature_name].unique()
  feature_columns.append(tf.feature_column.categorical_column_with_vocabulary_list(feature_name, vocabulary))


for feature_name in numerical_columns:
  feature_columns.append(tf.feature_column.numeric_column(feature_name,dtype = tf.float32))


#input function :   
  
def make_input_fn(data_df, label_df, num_epochs = 10, shuffle = True, batch_size = 32):
  def input_function():
    ds = tf.data.Dataset.from_tensor_slices((dict(data_df), label_df))
    if shuffle:
      ds = ds.shuffle(1000)
    ds = ds.batch(batch_size).repeat(num_epochs)
    return ds
  return input_function  
  
#split data into batches :  
  
def split_into_batches(df, batch_size=100000):
  nb_rows = len(df.index)
  intervals = []
  
  for i in range(0, nb_rows + 1, batch_size):
    intervals.append(i)
  
  if(intervals[-1] != nb_rows):
    intervals.append(nb_rows)
  
  batches_X = []
  batches_y = []
  
  for i in range(0, len(intervals) - 1):
    batches_X.append(train.iloc[intervals[i]:intervals[i + 1], :][features])
    batches_y.append(train.iloc[intervals[i]:intervals[i + 1], :]['good_move'])

  return batches_X, batches_y

batches_X, batches_y = split_into_batches(train)


#model : 
linear_est = tf.estimator.LinearClassifier(feature_columns = feature_columns, model_dir='/Users/charlottemaistriau/Downloads')


#train model : 
input_functions = []
for df_X, df_y in zip(batches_X, batches_y):
  input_functions.append(make_input_fn(df_X, df_y))

print(len(input_functions))

# train the model on all the input functions
i = 1
for input_function in input_functions:
  print('<======================================== NEW BATCH ========================================>')
  print('Batch: ' + str(i))
  i = i + 1
  linear_est.train(input_function)
  

# save the model
serving_input_fn = tf.estimator.export.build_parsing_serving_input_receiver_fn(
  tf.feature_column.make_parse_example_spec(feature_columns))

estimator_base_path = '/Users/charlottemaistriau/Downloads'
estimator_path = linear_est.export_saved_model(estimator_base_path, serving_input_fn)
'''
##Python Chess Engine ♟️
#libraries

import chess
import chess.svg
import cairosvg
from cairosvg import svg2png
from collections import OrderedDict
from operator import itemgetter 
import pandas as pd
import numpy as np
import tensorflow as tf
from IPython.display import clear_output
#import cv2
#nfrom google.colab.patches import cv2_imshow

#tensorflow model


#path_to_model = 'saved_model.pb'

global model
model = tf.saved_model.load('/Users/charlottemaistriau/Downloads')


def predict(df_eval, imported_model):
    """Return array of predictions for each row of df_eval
    
    Keyword arguments:
    df_eval -- pd.DataFrame
    imported_model -- tf.saved_model 
    """
    col_names = df_eval.columns
    dtypes = df_eval.dtypes
    predictions = []
    for row in df_eval.iterrows():
      example = tf.train.Example()
      for i in range(len(col_names)):
        dtype = dtypes[i]
        col_name = col_names[i]
        value = row[1][col_name]
        if dtype == 'object':
          value = bytes(value, 'utf-8')
          example.features.feature[col_name].bytes_list.value.extend([value])
        elif dtype == 'float':
          example.features.feature[col_name].float_list.value.extend([value])
        elif dtype == 'int':
          example.features.feature[col_name].int64_list.value.extend([value])
      predictions.append(imported_model.signatures['predict'](examples = tf.constant([example.SerializeToString()])))
    return predictions


def get_board_features(board):
    """Return array of features for a board
    
    Keyword arguments:
    board -- chess.Board()
    """
    board_features = []
    for square in chess.SQUARES:
      board_features.append(str(board.piece_at(square)))
    return board_features


def get_move_features(move):
    """Return 2 arrays of features for a move
    
    Keyword arguments:
    move -- chess.Move
    """
    from_ = np.zeros(64)
    to_ = np.zeros(64)
    from_[move.from_square] = 1
    to_[move.to_square] = 1
    return from_, to_


def get_possible_moves_data(current_board):
    """Return pd.DataFrame of all possible moves used for predictions
    
    Keyword arguments:
    current_board -- chess.Board()
    """
    data = []
    moves = list(current_board.legal_moves)
    for move in moves:
      from_square, to_square = get_move_features(move)
      row = np.concatenate((get_board_features(current_board), from_square, to_square))
      data.append(row)
    
    board_feature_names = chess.SQUARE_NAMES
    move_from_feature_names = ['from_' + square for square in chess.SQUARE_NAMES]
    move_to_feature_names = ['to_' + square for square in chess.SQUARE_NAMES]
    
    columns = board_feature_names + move_from_feature_names + move_to_feature_names
    
    df = pd.DataFrame(data = data, columns = columns)

    for column in move_from_feature_names:
      df[column] = df[column].astype(float)
    for column in move_to_feature_names:
      df[column] = df[column].astype(float)
    return df


def find_best_moves(current_board, model, proportion = 0.5):
    """Return array of the best chess.Move
    
    Keyword arguments:
    current_board -- chess.Board()
    model -- tf.saved_model
    proportion -- proportion of best moves returned
    """
    moves = list(current_board.legal_moves)
    df_eval = get_possible_moves_data(current_board)
    predictions = predict(df_eval, model)
    good_move_probas = []
    
    for prediction in predictions:
      proto_tensor = tf.make_tensor_proto(prediction['probabilities'])
      proba = tf.make_ndarray(proto_tensor)[0][1]
      good_move_probas.append(proba)
    
    dict_ = dict(zip(moves, good_move_probas))
    dict_ = OrderedDict(sorted(dict_.items(), key = itemgetter(1), reverse = True))
    
    best_moves = list(dict_.keys())
 
    return best_moves[0:int(len(best_moves)*proportion)]

#minimax


pawn_white_eval = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                            [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
                            [1.0, 1.0, 2.0, 3.0, 3.0, 2.0, 1.0, 1.0],
                            [0.5, 0.5, 1.0, 2.5, 2.5, 1.0, 0.5, 0.5],
                            [0.0, 0.0, 0.0, 2.0, 2.0, 0.0, 0.0, 0.0],
                            [0.5, -0.5, -1.0, 0.0, 0.0, -1.0, -0.5, 0.5],
                            [0.5, 1.0, 1.0, -2.0, -2.0, 1.0, 1.0, 0.5],
                            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], np.float)

pawn_black_eval = pawn_white_eval[::-1]


knight_white_eval = np.array([[-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0],
                              [-4.0, -2.0, 0.0, 0.0, 0.0, 0.0, -2.0, -4.0],
                              [-3.0, 0.0, 1.0, 1.5, 1.5, 1.0, 0.0, -3.0],
                              [-3.0, 0.5, 1.5, 2.0, 2.0, 1.5, 0.5, -3.0],
                              [-3.0, 0.0, 1.5, 2.0, 2.0, 1.5, 0.0, -3.0],
                              [-3.0, 0.5, 1.0, 1.5, 1.5, 1.0, 0.5, -3.0],
                              [-4.0, -2.0, 0.0, 0.5, 0.5, 0.0, -2.0, -4.0],
                              [-5.0, -4.0, -3.0, -3.0, -3.0, -3.0, -4.0, -5.0]], np.float)

knight_black_eval = knight_white_eval[::-1]


bishop_white_eval = np.array([[-2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0],
                              [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
                              [-1.0, 0.0, 0.5, 1.0, 1.0, 0.5, 0.0, -1.0],
                              [-1.0, 0.5, 0.5, 1.0, 1.0, 0.5, 0.5, -1.0],
                              [-1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0.0, -1.0],
                              [-1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, -1.0],
                              [-1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5, -1.0],
                              [-2.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -2.0]], np.float)

bishop_black_eval = bishop_white_eval[::-1]


rook_white_eval = np.array([[0.0, 0.0, 0.0, 0.0, 0.0,  0.0, 0.0, 0.0],
                            [0.5, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5],
                            [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
                            [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
                            [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
                            [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
                            [-0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -0.5],
                            [ 0.0, 0.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.0]], np.float)

rook_black_eval = rook_white_eval[::-1]


queen_white_eval = np.array([[-2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0],
                             [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0],
                             [-1.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -1.0],
                             [-0.5, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -0.5],
                             [0.0, 0.0, 0.5, 0.5, 0.5, 0.5, 0.0, -0.5],
                             [-1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.0, -1.0],
                             [-1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, -1.0],
                             [-2.0, -1.0, -1.0, -0.5, -0.5, -1.0, -1.0, -2.0]], np.float)

queen_black_eval = queen_white_eval[::-1]


king_white_eval = np.array([[-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
                            [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
                            [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
                            [-3.0, -4.0, -4.0, -5.0, -5.0, -4.0, -4.0, -3.0],
                            [-2.0, -3.0, -3.0, -4.0, -4.0, -3.0, -3.0, -2.0],
                            [-1.0, -2.0, -2.0, -2.0, -2.0, -2.0, -2.0, -1.0],
                            [2.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 2.0],
                            [2.0, 3.0, 1.0, 0.0, 0.0, 1.0, 3.0, 2.0]], np.float)

king_black_eval = king_white_eval[::-1]


def square_to_coord(square):
  """Convert square to coordinates
  """
  return {0:(7,0), 1:(7,1), 2:(7,2), 3:(7,3), 4:(7,4), 5:(7,5), 6:(7,6), 7:(7,7),
          8:(6,0), 9:(6,1), 10:(6,2), 11:(6,3), 12:(6,4), 13:(6,5), 14:(6,6), 15:(6,7), 
          16:(5,0), 17:(5,1), 18:(5,2), 19:(5,3), 20:(5,4), 21:(5,5), 22:(5,6), 23:(5,7),
          24:(4,0), 25:(4,1), 26:(4,2), 27:(4,3), 28:(4,4), 29:(4,5), 30:(4,6), 31:(4,7),
          32:(3,0), 33:(3,1), 34:(3,2), 35:(3,3), 36:(3,4), 37:(3,5), 38:(3,6), 39:(3,7),
          40:(2,0), 41:(2,1), 42:(2,2), 43:(2,3), 44:(2,4), 45:(2,5), 46:(2,6), 47:(2,7),
          48:(1,0), 49:(1,1), 50:(1,2), 51:(1,3), 52:(1,4), 53:(1,5), 54:(1,6), 55:(1,7),
          56:(0,0), 57:(0,1), 58:(0,2), 59:(0,3), 60:(0,4), 61:(0,5), 62:(0,6), 63:(0,7)}[square]


def get_piece_value(piece, square):
  """Return the value of a piece
  """
  x, y = square_to_coord(square)
  
  if(ai_white):
    sign_white = -1
    sign_black = 1
  else:
    sign_white = 1
    sign_black = -1

  if(piece == 'None'):
    return 0
  elif(piece == 'P'):
    return sign_white * (10 + pawn_white_eval[x][y])
  elif(piece == 'N'):
    return sign_white * (30 + knight_white_eval[x][y])
  elif(piece == 'B'):
    return sign_white * (30 + bishop_white_eval[x][y])
  elif(piece == 'R'):
    return sign_white * (50 + rook_white_eval[x][y])
  elif(piece == 'Q'):
    return sign_white * (90 + queen_white_eval[x][y])
  elif(piece == 'K'):
    return sign_white * (900 + king_white_eval[x][y])
  elif(piece == 'p'):
    return sign_black * (10 + pawn_black_eval[x][y])
  elif(piece == 'n'):
    return sign_black * (30 + knight_black_eval[x][y])
  elif(piece == 'b'):
    return sign_black * (30 + bishop_black_eval[x][y])
  elif(piece == 'r'):
    return sign_black * (50 + rook_black_eval[x][y])
  elif(piece == 'q'):
    return sign_black * (90 + queen_black_eval[x][y])
  elif(piece == 'k'):
    return sign_black * (900 + king_black_eval[x][y])


def evaluate_board(board):
  """Return the evaluation of a board
  """
  evaluation = 0
  for square in chess.SQUARES:
    piece = str(board.piece_at(square))
    evaluation = evaluation + get_piece_value(piece, square)
  return evaluation


def minimax(depth, board, alpha, beta, is_maximising_player):
  
  if(depth == 0):
    return - evaluate_board(board)
  elif(depth > 3):
    legal_moves = find_best_moves(board, model, 0.75)
  else:
    legal_moves = list(board.legal_moves)

  if(is_maximising_player):
    best_move = -9999
    for move in legal_moves:
      board.push(move)
      best_move = max(best_move, minimax(depth-1, board, alpha, beta, not is_maximising_player))
      board.pop()
      alpha = max(alpha, best_move)
      if(beta <= alpha):
        return best_move
    return best_move
  else:
    best_move = 9999
    for move in legal_moves:
      board.push(move)
      best_move = min(best_move, minimax(depth-1, board, alpha, beta, not is_maximising_player))
      board.pop()
      beta = min(beta, best_move)
      if(beta <= alpha):
        return best_move
    return best_move


def minimax_root(depth, board, is_maximising_player = True):
  #only search the top 50% moves
  legal_moves = find_best_moves(board, model)
  best_move = -9999
  best_move_found = None

  for move in legal_moves:
    board.push(move)
    value = minimax(depth - 1, board, -10000, 10000, not is_maximising_player)
    board.pop()
    if(value >= best_move):
      best_move = value
      best_move_found = move

  return best_move_found

#  game util

def draw_board(current_board):
  """Draw board

   Keyword arguments:
   current_board -- chess.Board()
  """
  board_img = chess.svg.board(current_board, flipped = ai_white)
  svg2png(bytestring=board_img,write_to='/content/board.png')
  img = cv2.imread('/content/board.png', 1)
  cv2_imshow(img)


def can_checkmate(move, current_board):
  """Return True if a move can checkmate
    
  Keyword arguments:
  move -- chess.Move
  current_board -- chess.Board()
  """
  fen = current_board.fen()
  future_board = chess.Board(fen)
  future_board.push(move)
  return future_board.is_checkmate()


def ai_play_turn(current_board):
  """Handdle the A.I's turn

  Keyword arguments:
  current_board -- chess.Board()
  """
  clear_output()
  draw_board(current_board)
  print('\n')
  print(r""" Hold on,Let me think...""")
  for move in current_board.legal_moves:
    if(can_checkmate(move, current_board)):
      current_board.push(move)
      return

  nb_moves = len(list(current_board.legal_moves))
   
  if(nb_moves > 30):
    current_board.push(minimax_root(4, current_board))
  elif(nb_moves > 10 and nb_moves <= 30):
    current_board.push(minimax_root(5, current_board))
  else:
    current_board.push(minimax_root(7, current_board))
  return


def human_play_turn(current_board):
  """Handle the human's turn

  Keyword arguments:
  current_board = chess.Board()
  """
  clear_output()
  draw_board(current_board)
  print('\n')
  print('\n')
  print('number moves: ' + str(len(current_board.move_stack)))
  move_uci = input('Enter your move: ')
  
  try: 
    move = chess.Move.from_uci(move_uci)
  except:
    return human_play_turn(current_board) 
  if(move not in current_board.legal_moves):
    return human_play_turn(current_board)
  current_board.push(move)
  return


def play_game(turn, current_board):
  """Play through the whole game
    
  Keyword arguments:
  turn -- True for A.I plays first
  current_board -- chess.Board()
  """
  if(current_board.is_stalemate()):
    clear_output()
    print('Stalemate: both A.I and human win')
    return
  else:   
    if(not turn):
      if(not current_board.is_checkmate()):
        human_play_turn(current_board)
        return play_game(not turn, current_board)
      else:
        clear_output()
        draw_board(current_board)
        print('A.I wins')
        return
    else:
      if(not current_board.is_checkmate()):
        ai_play_turn(current_board)
        return play_game(not turn, current_board)
      else:
        clear_output()
        draw_board(current_board)
        print('Human wins')
        return


def play():
  """Init and start the game
  """
  global ai_white
  ai_white = True
  
  board = chess.Board()
  human_first = input('Care to start? [y/n]: ')
  clear_output()
  if(human_first == 'y'):
    ai_white = False
    return play_game(False, board)
  else:
    return play_game(True, board)

#play
play()