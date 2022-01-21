
from sys import argv, stdout
from threading import Thread
import GameData
from sys import argv
import socket
from constants import *
import os
import time
import random
import numpy as np

class HanabiAgent():
    def __init__(self, name, verbose=False, num_players=None, board_info=None, **kwargs):
        self.name = name
        self.num_players = num_players
        self.info = board_info # {'players': {'pi_name': {'turn': turn, 'cards': [list of Card objs]}},
                                     #'table_cards': {'red':3, 'blue':0, 'yellow':2, 'green':1, 'white':5}}
                                     #'discard_pile': {'red':[3,3,2], 'blue':[], 'yellow':[1,4], 'green':[], 'white':[5]}
                                     #'rem_clues': 6, 'rem_mistakes': 1}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_turn = False
        self.current_player = None
        self.status = 'Lobby'
        self.policy = {} # {action: value}
        self.available_actions = []
        self.action = None
        self.run = True
        self.available_actions = None
        self.verbose = verbose

        while True:
            try:
                self.s.connect((HOST, PORT))
                break
            except:
                print("Server refused the connection request! Trying to reconnect...")
                time.sleep(0.001)
        request = GameData.ClientPlayerAddData(self.name)
        self.s.send(request.serialize())
        data = self.s.recv(DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerConnectionOk:
            print("Connection accepted by the server. Welcome " + self.name) 
        print("[" + self.name + " - " + self.status + "]: ", end="")
        Thread(target=self.play).start()
        while self.run:
            dataOk = False
            data = self.s.recv(DATASIZE)
            if not data:
                continue
            data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                dataOk = True
                print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
                data = self.s.recv(DATASIZE)
                data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerStartGameData:
                dataOk = True
                if verbose: print("Game start!")
                self.s.send(GameData.ClientPlayerReadyData(self.name).serialize())
                self.status = 'Game'
            if type(data) is GameData.ServerGameStateData:
                dataOk = True
                self.parse_game_data(data)
                if verbose:
                    print("Current player: " + data.currentPlayer)
                    print("Player hands: ")
                    for p in data.players:
                        print(p.toClientString())
                    print("Table cards: ")
                    for pos in data.tableCards:
                        print(pos + ": [ ")
                        for c in data.tableCards[pos]:
                            print(c.toClientString() + " ")
                        print("]")
                    print("Discard pile: ")
                    for c in data.discardPile:
                        print("\t" + c.toClientString())            
                    print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
                    print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
            if type(data) is GameData.ServerActionInvalid:
                dataOk = True
                if verbose:
                    print("Invalid action performed. Reason:")
                    print(data.message)
            if type(data) is GameData.ServerActionValid:
                dataOk = True
                if verbose:
                    print("Action valid!")
                    print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerMoveOk:
                dataOk = True
                self.play_feedback(data)
                if verbose:
                    print("Nice move!")
                    print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerThunderStrike:
                dataOk = True
                self.misplay_feedback(data)
                if verbose:
                    print("OH NO! The Gods are unhappy with you!")
            if type(data) is GameData.ServerHintData:
                dataOk = True
                self.parse_hint_data(data)
                if verbose:
                    print("Hint type: " + data.type)
                    print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
                    for i in data.positions:
                        print("\t" + str(i))
            if type(data) is GameData.ServerInvalidDataReceived:
                dataOk = True
                if verbose:
                    print(data.data)
            if type(data) is GameData.ServerGameOver:
                dataOk = True
                self.process_game_over(data.score)
                time.sleep(0.1)
                if verbose:
                    print(data.message)
                    print(data.score)
                    print(data.scoreMessage)
                stdout.flush()
                #run = False
                print(f"This game is over with final score {data.score}. Beginning a new game...")
            if not dataOk:
                if verbose:
                    print("Unknown or unimplemented data type: " +  str(type(data)))
            #print("[" + playerName + " - " + self.status + "]: ", end="")
            stdout.flush()

    def process_game_over(self, score):
        self.info = None
        self.my_turn = False
        self.current_player = None
        self.available_actions = []
        self.action = None
        self.available_actions = None

    def misplay_feedback(self, data):
        pass

    def play_feedback(self, data):
        pass

    def parse_hint_data(self, data):
        pass

    def parse_game_data(self, data):
        if data.currentPlayer == self.name:
            self.my_turn = True

        self.current_player = data.currentPlayer
        
        if self.info == None:
            self.info = {}
            player_names = [player.name for player in data.players]
            self.info['players'] = dict()
            for p in player_names:
                self.info['players'][p] = {'turn': -1, 'cards': []}
            self.num_players = len(data.players)
            self.info['table_cards'] = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0, 'white': 0}
            self.info['discard_pile'] = {'red': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'yellow': {1: 0, 2: 0, 3:0, 4:0, 5:0},\
                 'green': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'blue': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'white': {1: 0, 2: 0, 3:0, 4:0, 5:0}}
            self.info['rem_mistakes'] = 3
            self.info['rem_clues'] = 8


        for i in range(len(data.players)):
            self.info['players'][data.players[i].name]['turn'] = i
            self.info['players'][data.players[i].name]['cards'] = data.players[i].hand

        self.info['players'][self.name]['cards'] = []

        self.info['rem_mistakes'] = 3 - data.usedStormTokens
        self.info['rem_clues'] = 8 - data.usedNoteTokens
        for color in data.tableCards:
            if len(data.tableCards[color]) > 0:
                self.info['table_cards'][color] = max([c.value for c in data.tableCards[color]])

        self.info['discard_pile'] = {'red': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'yellow': {1: 0, 2: 0, 3:0, 4:0, 5:0},\
                 'green': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'blue': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'white': {1: 0, 2: 0, 3:0, 4:0, 5:0}}
        for card in data.discardPile:
            self.info['discard_pile'][card.color][card.value] += 1

        # info {'players': {'pi_name': {'turn': turn, 'cards': [list of Card objs]}},
                                #'table_cards': {'red':3, 'blue':0, 'yellow':2, 'green':1, 'white':5}}
                                #'discard_pile': {'red':[3,3,2], 'blue':[], 'yellow':[1,4], 'green':[], 'white':[5]}
                                #'rem_clues': 6, 'rem_mistakes': 1}
        ### Calculating available hints
        ### actions: '('d', 1)' --> discard cart 1, '('p', 0)' --> play cart zero,
        ### '('h', 'p2', 'red') --> hint player p2 'red', ('h', 'p1', 5) --> hint player p2 number '5'
        self.available_actions = [('p',0), ('p', 1), ('p', 2), ('p', 3), ('p', 4)]  # {action: value}, playing is always permissible
        if self.info['rem_clues'] > 0:
            # hint actions
            hints_set = set()
            for player in self.info['players']:
                if player != self.name: 
                    for card in self.info['players'][player]['cards']:
                        hints_set.add(('h', player, card.color))
                        hints_set.add(('h', player, card.value))
            for action in hints_set:
                self.available_actions.append(action)
        if self.info['rem_clues'] != 8:
            # discard actions
            self.available_actions.extend([('d',0), ('d', 1), ('d', 2), ('d', 3), ('d', 4)])
            
    def update_policy(self,):
        pass

    def select_action(self,):
        a = random.choice(self.available_actions)
        return a

    def action_to_command(self, action):
        if action[0] == 'd':  
            # discard
            command = f"discard {action[1]}"
        elif action[0] == 'p':
            # play
            command = f"play {action[1]}"    
        else:
            if type(action[2]) == str:
                # hint color
                command = f"hint color {action[1]} {action[2]}"
            else:
                # hint value
                command = f"hint value {action[1]} {action[2]}"
        return command

    def play(self):
        command = input() ## Give the ready command
        init_obs = True
        while self.run:
            if self.status == 'Lobby':
                ### Wait in the lobby until the game starts
                pass
            else:
                # if need_info == True:
                #     command = 'show'
                #     need_info = False
                # else:
                if init_obs:
                    self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                    init_obs = False
                while self.my_turn == False:
                    time.sleep(0.1)
                    self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                    #print(self.policy)
                self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                time.sleep(0.1)
                self.my_turn = False
                #time.sleep(0.01)
                self.action = self.select_action()
                command = self.action_to_command(self.action)
                if self.verbose:
                #print(self.info)
                    print(command)
            # Choose data to send
            if command == "exit":
                self.run = False
                os._exit(0)
            elif command == "ready" and self.status == 'Lobby':
                self.s.send(GameData.ClientPlayerStartRequest(self.name).serialize())
                while self.status == 'Lobby':
                    ### Wait in the lobby until the game starts
                    continue
            elif command.split(" ")[0] == "discard" and self.status == 'Game':
                try:
                    cardStr = command.split(" ")
                    cardOrder = int(cardStr[1])
                    self.s.send(GameData.ClientPlayerDiscardCardRequest(self.name, cardOrder).serialize())
                except:
                    print("Maybe you wanted to type 'discard <num>'?")
                    continue
            elif command.split(" ")[0] == "play" and self.status == 'Game':
                try:
                    cardStr = command.split(" ")
                    cardOrder = int(cardStr[1])
                    self.s.send(GameData.ClientPlayerPlayCardRequest(self.name, cardOrder).serialize())
                except:
                    print("Maybe you wanted to type 'play <num>'?")
                    continue
            elif command.split(" ")[0] == "hint" and self.status == 'Game':
                try:
                    destination = command.split(" ")[2]
                    t = command.split(" ")[1].lower()
                    if t != "colour" and t != "color" and t != "value":
                        print("Error: type can be 'color' or 'value'")
                        continue
                    value = command.split(" ")[3].lower()
                    if t == "value":
                        value = int(value)
                        if int(value) > 5 or int(value) < 1:
                            print("Error: card values can range from 1 to 5")
                            continue
                    else:
                        if value not in ["green", "red", "blue", "yellow", "white"]:
                            print("Error: card color can only be green, red, blue, yellow or white")
                            continue
                    self.s.send(GameData.ClientHintData(self.name, destination, t, value).serialize())
                except:
                    print("Maybe you wanted to type 'hint <type> <destinatary> <value>'?")
                    continue
            elif command == "":
                continue
                #print("[" + self.name + " - " + self.status + "]: ", end="")
            else:
                print("Unknown command: " + command)
                continue
            stdout.flush()


if len(argv) != 2:
    raise Exception("Invalid run command! The terminal command should be \'python controller.py <playerName>\'")
player_name= argv[1]

agent = HanabiAgent(player_name, verbose=False)
