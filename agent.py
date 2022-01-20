
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
    def __init__(self, name, num_players=None, board_info=None, **kwargs):
        self.name = name
        self.num_players = num_players
        self.info = board_info # {'players': {'pi_name': {'turn': turn, 'cards': [list of Card objs]}},
                                     #'table_cards': {'red':3, 'blue':0, 'yellow':2, 'green':1, 'white':5}}
                                     #'discard_pile': {'red':[3,3,2], 'blue':[], 'yellow':[1,4], 'green':[], 'white':[5]}
                                     #'rem_clues': 6, 'rem_mistakes': 1}
        self.my_turn = False
        self.idx = -1
        self.current_player = None
        self.status = 'Lobby'
        self.policy = {} # {action: value}
        self.run = True
        self.available_actions = None

    def parse_game_data(self, data):
        if data.currentPlayer == self.name:
            self.my_turn = True

        self.current_player = data.currentPlayer
        
        if self.num_players == None:
            self.info = {}
            player_names = [player.name for player in data.players]
            self.info['players'] = dict.fromkeys(player_names, {})
            self.num_players = len(data.players)
            self.info['table_cards'] = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0, 'white': 0}
            self.info['discard_pile'] = {'red': [], 'yellow': [], 'green': [], 'blue': [], 'white': []}
            self.info['rem_mistakes'] = 3
            self.info['rem_clues'] = 8
        for idx, player in enumerate(data.players):
            if player.name == self.name:
                self.idx = idx
                self.info['players'][player.name]['turn'] = idx
                self.info['players'][player.name]['cards'] = []
            else:
                self.info['players'][player.name]['turn'] = idx
                self.info['players'][player.name]['cards'] = player.hand

        self.info['rem_mistakes'] = 3 - data.usedStormTokens
        self.info['rem_clues'] = 8 - data.usedNoteTokens

        for color in data.tableCards:
            if len(data.tableCards[color]) > 0:
                self.info['table_cards'][color] = max([c.value for c in data.tableCards[color]])

        for card in data.discardPile:
            self.info['discard_pile'][card.color].append(card.value)
        
            
    def update_policy(self,):
        # info {'players': {'pi_name': {'turn': turn, 'cards': [list of Card objs]}},
                                     #'table_cards': {'red':3, 'blue':0, 'yellow':2, 'green':1, 'white':5}}
                                     #'discard_pile': {'red':[3,3,2], 'blue':[], 'yellow':[1,4], 'green':[], 'white':[5]}
                                     #'rem_clues': 6, 'rem_mistakes': 1}
        ### Calculating available hints
        ### actions: '('d', 1)' --> discard cart 1, '('p', 0)' --> play cart zero,
        ### '('h', 'p2', 'red') --> hint player p2 'red', ('h', 'p1', 5) --> hint player p2 number '5'
        self.policy = {('p',0): 0, ('p', 1): 0, ('p', 2): 0, ('p', 3): 0, ('p', 4): 0}  # {action: value}, playing is always permissible
        if self.info['rem_clues'] > 0:
            # hint actions
            hints_set = set()
            for player in self.info['players']:
                if player != self.name: 
                    for card in self.info['players'][player]['cards']:
                        hints_set.add(('h', player, card.color))
                        hints_set.add(('h', player, card.value))
            for action in hints_set:
                self.policy[action] = 0
        if self.info['rem_clues'] != 8:
            # discard actions
            self.policy.update({('d',0): 0, ('d', 1): 0, ('d', 2): 0, ('d', 3): 0, ('d', 4): 0})

    def select_action(self,):
        actions = list(self.policy.keys())
        a = random.choice(actions)
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
        while self.run:
            if self.status == 'Lobby':
                ### Wait in the lobby until the game starts
                pass
            else:
                # if need_info == True:
                #     command = 'show'
                #     need_info = False
                # else:
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                while self.my_turn == False:
                    time.sleep(0.01)
                    s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                s.send(GameData.ClientGetGameStateRequest(playerName).serialize())
                self.my_turn = False
                #time.sleep(0.01)
                agent.update_policy()
                action = self.select_action()
                command = self.action_to_command(action)
                print(command)
            # Choose data to send
            if command == "exit":
                self.run = False
                os._exit(0)
            elif command == "ready" and self.status == 'Lobby':
                s.send(GameData.ClientPlayerStartRequest(self.name).serialize())
                while self.status == 'Lobby':
                    ### Wait in the lobby until the game starts
                    continue
            elif command.split(" ")[0] == "discard" and self.status == 'Game':
                try:
                    cardStr = command.split(" ")
                    cardOrder = int(cardStr[1])
                    s.send(GameData.ClientPlayerDiscardCardRequest(self.name, cardOrder).serialize())
                except:
                    print("Maybe you wanted to type 'discard <num>'?")
                    continue
            elif command.split(" ")[0] == "play" and self.status == 'Game':
                try:
                    cardStr = command.split(" ")
                    cardOrder = int(cardStr[1])
                    s.send(GameData.ClientPlayerPlayCardRequest(self.name, cardOrder).serialize())
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
                    s.send(GameData.ClientHintData(self.name, destination, t, value).serialize())
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
playerName = argv[1]

agent = HanabiAgent(playerName)


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    request = GameData.ClientPlayerAddData(playerName)
    s.connect((HOST, PORT))
    s.send(request.serialize())
    data = s.recv(DATASIZE)
    data = GameData.GameData.deserialize(data)
    if type(data) is GameData.ServerPlayerConnectionOk:
        print("Connection accepted by the server. Welcome " + playerName)
    print("[" + playerName + " - " + agent.status + "]: ", end="")
    Thread(target=agent.play).start()
    while agent.run:
        dataOk = False
        data = s.recv(DATASIZE)
        if not data:
            continue
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            dataOk = True
            print("Ready: " + str(data.acceptedStartRequests) + "/"  + str(data.connectedPlayers) + " players")
            data = s.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerStartGameData:
            dataOk = True
            print("Game start!")
            s.send(GameData.ClientPlayerReadyData(playerName).serialize())
            agent.status = 'Game'
        if type(data) is GameData.ServerGameStateData:
            dataOk = True
            agent.parse_game_data(data)

            # print("Current player: " + data.currentPlayer)
            # print("Player hands: ")
            # for p in data.players:
            #     print(p.toClientString())
            # print("Table cards: ")
            # for pos in data.tableCards:
            #     print(pos + ": [ ")
            #     for c in data.tableCards[pos]:
            #         print(c.toClientString() + " ")
            #     print("]")
            # print("Discard pile: ")
            # for c in data.discardPile:
            #     print("\t" + c.toClientString())            
            # print("Note tokens used: " + str(data.usedNoteTokens) + "/8")
            # print("Storm tokens used: " + str(data.usedStormTokens) + "/3")
        if type(data) is GameData.ServerActionInvalid:
            dataOk = True
            print("Invalid action performed. Reason:")
            print(data.message)
        if type(data) is GameData.ServerActionValid:
            dataOk = True
            print("Action valid!")
            print("Current player: " + data.player)
        if type(data) is GameData.ServerPlayerMoveOk:
            dataOk = True
            print("Nice move!")
            print("Current player: " + data.player)
        if type(data) is GameData.ServerPlayerThunderStrike:
            dataOk = True
            print("OH NO! The Gods are unhappy with you!")
        if type(data) is GameData.ServerHintData:
            dataOk = True
            agent.parse_hint_data(data)
            print("Hint type: " + data.type)
            print("Player " + data.destination + " cards with value " + str(data.value) + " are:")
            for i in data.positions:
                print("\t" + str(i))
        if type(data) is GameData.ServerInvalidDataReceived:
            dataOk = True
            print(data.data)
        if type(data) is GameData.ServerGameOver:
            dataOk = True
            agent.final_score
            print(data.message)
            print(data.score)
            print(data.scoreMessage)
            stdout.flush()
            #run = False
            print("Ready for a new game!")
        if not dataOk:
            print("Unknown or unimplemented data type: " +  str(type(data)))
        #print("[" + playerName + " - " + agent.status + "]: ", end="")
        stdout.flush()

