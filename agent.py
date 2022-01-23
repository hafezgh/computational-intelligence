
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
    def __init__(self, name, verbose_action=False, num_games_limit=None, num_players=None, board_info=None, **kwargs):
        self.name = name
        self.num_players = num_players
        self.info = board_info # {'players': {'pi_name': {'turn': turn, 'cards': [list of Card objs]}},
                                     #'table_cards': {'red':3, 'blue':0, 'yellow':2, 'green':1, 'white':5}}
                                     #'discard_pile': {'red':[3,3,2], 'blue':[], 'yellow':[1,4], 'green':[], 'white':[5]}
                                     #'rem_clues': 6, 'rem_mistakes': 1}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_turn = False
        self.current_player = None
        self.sleeptime = 0.01
        self.status = 'Lobby'
        self.policy = {} # {action: value}
        self.available_actions = []
        self.verbose_action = verbose_action
        ### actions: ('d', 1) --> discard cart 1, ('p', 0) --> play cart zero,
        ### ('h', 'p2', 'red') --> hint player p2 'red', ('h', 'p1', 5) --> hint player p2 number '5'
        self.action = None
        self.run = True
        # state: (last_round, coarse_coded_rem_clues, 3-rem_storm_tokens, coarse_coded_current_score, have_clued_in_my_hand)
        self.state = (0, 0, 0, 0, 0)
        self.q_table = {self.state: [0.,0.,0.]}     # idx 0 is discard, idx 2 is hint, and idx 2 is play
        self.gamma = 0.9
        self.alpha = 0.1
        self.available_actions = []
        self.player_idx = {}
        self.idx_player = {}
        self.last_round = False
        self.current_score = 0
        self.my_cards_clued = 0
        self.hint_history = set()
        self.num_deck_cards = -1
        self.num_games_limit = num_games_limit
        self.num_games = 0
        self.average_score = 0.
        self.my_cards = [(None, None), (None, None), (None, None), (None, None), (None, None)]

        while self.run:
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
                print("Tournament starts!")
                self.s.send(GameData.ClientPlayerReadyData(self.name).serialize())
                self.status = 'Game'
            if type(data) is GameData.ServerGameStateData:
                dataOk = True
                self.parse_game_data(data)
            if type(data) is GameData.ServerActionInvalid:
                dataOk = True
                # print("Invalid action performed. Reason:")
                # print(data.message)
            if type(data) is GameData.ServerActionValid:
                dataOk = True
                self.discard_feedback(data)

            if type(data) is GameData.ServerPlayerMoveOk:
                dataOk = True
                self.play_feedback(data)

            if type(data) is GameData.ServerPlayerThunderStrike:
                dataOk = True
                self.misplay_feedback(data)

            if type(data) is GameData.ServerHintData:
                dataOk = True
                self.parse_hint_data(data)
            if type(data) is GameData.ServerInvalidDataReceived:
                dataOk = True
                if self.verbose_action:
                    print(data.data)
            if type(data) is GameData.ServerGameOver:
                dataOk = True   
                self.process_game_over(data.score)
                stdout.flush()
                #run = False
            if not dataOk:
                if self.verbose_action:
                    print("Unknown or unimplemented data type: " +  str(type(data)))
            stdout.flush()
    
    def coarse_coding_rem_clues(self):
        rem_clues = self.info['rem_clues']
        if rem_clues == 8:
            return 0
        if rem_clues == 0:
            return 1
        if rem_clues in [1,2]:
            return 2
        if rem_clues in [3,4,5]:
            return 3
        return 4

    def coarse_coding_score(self):
        self.current_score = sum(self.info['table_cards'].values())
        if self.current_score < 5:
            return 0
        if self.current_score >=5 and self.current_score < 10:
            return 1
        if self.current_score >=10 and self.current_score < 20:
            return 2
        return 3

    def process_game_over(self, score):
        tab_cards = self.info['table_cards']
        print(f"\nThis game is over with final score {score}. "
        f"{max(self.num_deck_cards, 0)} cards remained in the deck. The final table cards: {tab_cards}. ")
        ## reward
        if score == 0:
            reward = -20
        else:
            reward = score
        # Updat the q-table
        next_state = (0, 0, 0, 0, 0)
        self.q_table[self.state][0] = self.q_table[self.state][0] + self.alpha*(reward\
            + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                    self.q_table[self.state][0])
        self.state = next_state
        self.info = None
        self.my_turn = False
        self.current_player = None
        self.available_actions = []
        self.hint_history = set()
        self.action = None
        self.available_actions = None
        self.last_round = False
        self.turn = None
        self.my_cards_clued = 0
        self.current_score = 0
        self.num_deck_cards = -1
        self.my_cards = [(None, None), (None, None), (None, None), (None, None), (None, None)]
        self.num_games += 1
        self.average_score = (self.average_score * (self.num_games-1)+score)/self.num_games
        print(f"Games played so far: {self.num_games}. Average score in the tournament so far: {self.average_score}")
        print("Beginning a new game...")
        ## For DEBUGGING
        #tmp = input()
        if self.num_games_limit != None:
            if self.num_games >= self.num_games_limit:
                self.run = False


    def misplay_feedback(self, data):
        self.num_deck_cards -= 1
        self.info['rem_mistakes'] -= 1
        if data.handLength < 5:
            self.last_round = True
        if data.lastPlayer == self.name:
            if self.verbose_action:
                print("Card misplayed!")
            if self.my_cards[data.cardHandIndex][0] != None or self.my_cards[data.cardHandIndex][0] != None:
                self.my_cards_clued -= 1
            self.my_cards[data.cardHandIndex] = (None, None)
        ## reward
        reward = -10.

        next_state = (int(self.last_round), self.coarse_coding_rem_clues(),\
                3-self.info['rem_mistakes'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.,0.,0.]
        ## Updat the q-table
        self.q_table[self.state][2] = self.q_table[self.state][2] + self.alpha*(reward\
            + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                    self.q_table[self.state][2])
        self.state = next_state

    def play_feedback(self, data):
        self.num_deck_cards -= 1
        #TODO (Apparantly not supported by the server!)
        # if data.card.value == 5 and self.info['rem_clues'] < 8:
        #     self.info['rem_clues'] += 1
        if data.handLength < 5:
            self.last_round = True
        if data.lastPlayer == self.name:
            if self.verbose_action:
                print("Card played successfully!")
            if self.my_cards[data.cardHandIndex][0] != None or self.my_cards[data.cardHandIndex][0] != None:
                self.my_cards_clued -= 1
            self.my_cards[data.cardHandIndex] = (None, None)
        
        reward = 10.

        next_state = (int(self.last_round), self.coarse_coding_rem_clues(),\
                3-self.info['rem_mistakes'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.,0.,0.]
        self.q_table[self.state][2] = self.q_table[self.state][2] + self.alpha*(reward\
            + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                    self.q_table[self.state][2])
        self.state = next_state


    def discard_feedback(self, data):
        self.num_deck_cards -= 1
        self.info['rem_clues'] += 1
        if data.handLength < 5:
            self.last_round = True
        ## Give reward and update the q-table
        if data.lastPlayer == self.name:
            if self.verbose_action:
                print("Card discarded!")
            if self.my_cards[data.cardHandIndex][0] != None or self.my_cards[data.cardHandIndex][0] != None:
                self.my_cards_clued -= 1
            self.my_cards[data.cardHandIndex] = (None, None)

        if self.info['table_cards'][data.card.color] >= data.card.value:
            reward = 8
        elif data.card.value == 1 and self.info['discard_pile'][data.card.color][data.card.value]+1 == 3:
            reward = -7
        elif data.card.value in [2,3,4] and self.info['discard_pile'][data.card.color][data.card.value]+1 == 2:
            reward = -6
        elif data.card.value==5 and self.info['discard_pile'][data.card.color][data.card.value]+1 == 1:
            reward = -5
        else:
            reward = 9-self.info['rem_clues']

        next_state = (int(self.last_round), self.coarse_coding_rem_clues(),\
            3-self.info['rem_mistakes'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.,0.,0.]
        self.q_table[self.state][0] = self.q_table[self.state][0] + self.alpha*(reward\
            + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                    self.q_table[self.state][0])
        self.state = next_state

    def parse_hint_data(self, data):
        hint = {'giver': data.source, 'receiver': data.destination, 'type': data.type,\
            'val': data.value, 'positions': data.positions}
        self.info['rem_clues'] -= 1
        if hint['receiver'] == self.name:
            for i in hint['positions']:
                ### THEORY OF MIND: To avoid misplays, we only memorize the first position
                if hint['type'] == 'value':
                    if self.my_cards[i][0] == None and self.my_cards[i][1] == None:
                        self.my_cards_clued += 1
                    self.my_cards[i] = (hint['val'], self.my_cards[i][1])
                else:
                    if self.my_cards[i][0] == None and self.my_cards[i][1] == None:
                        self.my_cards_clued += 1
                    self.my_cards[i] = (self.my_cards[i][0], hint['val'])
                break
        
        self.hint_history.add((data.source, data.destination, data.type, data.value))

        reward = self.info['rem_clues']-self.num_players

        next_state = (int(self.last_round), self.coarse_coding_rem_clues(),\
                3-self.info['rem_mistakes'], self.coarse_coding_score(), int(self.my_cards_clued > 0))
        if next_state not in self.q_table:
            self.q_table[next_state] = [0.,0.,0.]
        self.q_table[self.state][1] = self.q_table[self.state][1] + self.alpha*(reward\
            + self.gamma*self.q_table[next_state][np.argmax(self.q_table[next_state])] -\
                    self.q_table[self.state][1])
        self.state = next_state

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
            self.num_deck_cards = int(50 - self.num_players*5)
            self.info['table_cards'] = {'red': 0, 'yellow': 0, 'green': 0, 'blue': 0, 'white': 0}
            self.info['discard_pile'] = {'red': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'yellow': {1: 0, 2: 0, 3:0, 4:0, 5:0},\
                 'green': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'blue': {1: 0, 2: 0, 3:0, 4:0, 5:0}, 'white': {1: 0, 2: 0, 3:0, 4:0, 5:0}}
            self.info['rem_mistakes'] = 3
            self.info['rem_clues'] = 8
            for i in range(len(data.players)):
                self.info['players'][data.players[i].name]['turn'] = i
                self.info['players'][data.players[i].name]['cards'] = data.players[i].hand
                self.player_idx[data.players[i].name] = i
                self.idx_player[i] = data.players[i].name
                if data.players[i].name == self.name:
                    self.turn = i

        for i in range(len(data.players)):
            self.info['players'][data.players[i].name]['cards'] = data.players[i].hand

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
        ### actions: ('d', 1) --> discard cart 1, ('p', 0) --> play cart zero,
        ### ('h', 'p2', 'red') --> hint player p2 'red', ('h', 'p1', 5) --> hint player p2 number '5'
        self.available_actions = [('p',0), ('p', 1), ('p', 2), ('p', 3), ('p', 4)]  # playing is always permissible
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
            if self.last_round:
                self.available_actions.extend([('d',0), ('d', 1), ('d', 2), ('d', 3), ('d', 4)])
                
    def is_hint_safe(self, hint):
        cards = self.info['players'][hint[1]]['cards']
        if hint[2] == 'value':
            for i in range(hint[4]):
                if cards[i].value == hint[3]:
                    return False
        else:
            for i in range(hint[4]):
                if cards[i].color == hint[3]:
                    return False
        return True
    
    def compare_hints(self, value_hint, color_hint):
        cards = self.info['players'][value_hint[1]]['cards']
        touched_v = 0
        touched_c = 0
        for card in cards:
            if card.value == value_hint[3]:
                touched_v += 1
            if card.color == color_hint[3]:
                touched_c += 1
        if touched_v<=touched_c:
            return 0
        return 1

    def select_action(self,):
        ### hard-coded stuff
        ## Iterate over your cards and play the most recent hinted card
        for idx, card in enumerate(self.my_cards):
            ## prioritize completely known cards over others (and play, discard, or keep it)
            if card[0] != None and card[1] != None:
                ## play
                if self.info['table_cards'][card[1]]+1 == card[0]:
                    return ('p', idx)
                ## discard the useless card if possible
                elif self.info['table_cards'][card[1]]+1 > card[0] and self.info['rem_clues'] < 8:
                    return ('d', idx)
            ## Prioritize value hints over color hints 
            if card[0] != None:
                ## Check if there exists a deck that actually fits this hint and then play; otherwise try to discard it.
                for color in ['red', 'green', 'blue', 'yellow', 'white']:
                    if self.info['table_cards'][color]+1 == card[0]:
                        return ('p', idx)
                if self.info['rem_clues'] < 8:
                    return ('d', idx)
            if card[1] != None:
                ## Check if there exists a deck that actually fits this hint and then play; otherwise try to discard it.
                for color in ['red', 'green', 'blue', 'yellow', 'white']:
                    if self.info['table_cards'][color] != 5:
                        return ('p', idx)
                if self.info['rem_clues'] < 8:
                    return ('d', idx)

        ## Iterate over your teammates' hands and hint any immediate play (hint first to the opponents that play sooner.)
        ## Care ADDED about other cards that may be touched!
        if self.info['rem_clues'] > 0:
            next_player_idx = (self.turn + 1) % self.num_players
            for i in range(self.num_players-1):
                p_name = self.idx_player[next_player_idx]
                p_cards = self.info['players'][p_name]['cards']
                for i, card in enumerate(p_cards):
                    if self.info['table_cards'][card.color]+1 == card.value:
                        hint_value = (self.name, p_name, 'value', card.value, i)
                        hint_color = (self.name, p_name, 'color', card.color, i)
                        ## Give a hint that touches fewer cards
                        if self.compare_hints(hint_value, hint_color) == 0:
                            ### THEORY OF MIND: To avoid misplays, we only give hints that do not touch dangerous cards before the hinted one
                            if self.is_hint_safe(hint_value):
                                return ('h', p_name, hint_value[3])

                        if self.is_hint_safe(hint_color):
                            return ('h', p_name, hint_color[3])

                next_player_idx = (next_player_idx + 1) % self.num_players

        ## Last round (play the newest card if we have more than one storm tokens available)
        if self.last_round:
            if self.info['rem_mistakes'] > 1:
                return ('p', 0)

        ## Discard your last unclued card
        if self.info['rem_clues'] < 8:
            for i in range(len(self.my_cards)-1, -1, -1):
                if self.my_cards[i][0] == None and self.my_cards[i][1] == None:
                    if i == 4 and self.last_round:
                        return ('d', i-1)
                    else:
                        return ('d', i-1)

        ### Using the q-table (that is being updated constantly) to choose an action as a last resort 
        a = np.argmax(self.q_table[self.state])
        if a == 1 and self.info['rem_clues'] == 0:
            a = 0
        if a == 0 and self.info['rem_clues'] == 8:
            a = 1

        if a == 0:
            ## dicard
            for idx, card in enumerate(self.my_cards):
                if card[0] == None and card[1] == None:
                    return ('d', idx)
            for idx, card in enumerate(self.my_cards):
                if card[0] == None or card[1] == None:
                    return ('d', idx)
            if self.last_round:
                return ('d', 3)
            else:
                return ('d', 4)

        if a == 1:
            ## hint; Hint color to the last card of the furthest player to delay any possible misplay.
            if self.turn == 0:
                furthest_player_idx = self.num_players-1
            else:
                furthest_player_idx = self.turn-1
            p_name = self.idx_player[furthest_player_idx]
            if self.last_round:
                card = self.info['players'][self.idx_player[furthest_player_idx]]['cards'][3]
            else:
                card = self.info['players'][self.idx_player[furthest_player_idx]]['cards'][4]
            hint_color = (self.name, p_name, 'value', card.color)
            return ('h', p_name, hint_color[3])
        
        if a == 2:
            ## Play your newest card
            return ('p', 0)

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

    def print_observation(self):
        print("\nMy name: " + self.name)
        print("My cards")
        print(self.my_cards)
        print("Other players hands: ")
        for p in self.info['players']:
            if p != self.name:
                print(p)
                for card in self.info['players'][p]['cards']:
                    print(f'({card.color}, {card.value})')
        print("Table cards: ")
        print(self.info['table_cards'])
        print("Discard pile: ")
        print(self.info['discard_pile'])
        print("Note tokens used: " + str(8-self.info['rem_clues']) + "/8")
        print("Storm tokens used: " + str(3-self.info['rem_mistakes']) + "/3")
        print('')
        stdout.flush()

    def play(self):
        command = input() ## Give the ready command
        init_obs = True
        while self.run:
            if self.status == 'Lobby':
                ### Wait in the lobby until the game starts
                pass
            else:
                if init_obs or self.info == None:
                    self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                    init_obs = False
                while self.my_turn == False:
                    time.sleep(self.sleeptime)
                    self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                self.s.send(GameData.ClientGetGameStateRequest(self.name).serialize())
                #time.sleep(self.sleeptime)
                self.my_turn = False
                self.action = self.select_action()
                command = self.action_to_command(self.action)
                if self.verbose_action:
                    self.print_observation()
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
            else:
                print("Unknown command: " + command)
                continue
            stdout.flush()


