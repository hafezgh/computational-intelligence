# Hanabi - The Final Project of the Computational Intelligence Course @PoliTO

The games of the simplest version of Hanabi can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf).

For a more extensive study of the game, its human conventions based on the theory of mind, and its numerous variants, see [this link](https://hanabi.github.io/). Here, we will use the no-variant version of Hanabi with 2 to 5 players.

The developers of this website also have an online server for playing Hanabi, see [here](https://hanab.live/), or join their discord server [here](https://discord.gg/FADvkJp).

## Considerations

Hanabi is an emerging challenge in the area of multi-agent reinforcement learning (MARL) that has also captured the attention of Deep Mind (see [here](https://deepmind.com/research/open-source/hanabi-learning-environment)). As discussed in [their article](https://arxiv.org/abs/1902.00506), currently no MARL method can outperform hand-coded bots in Hanabi. Even these hand-coded bots are only effective in the self-play setting where all players follow the same policy. Both bots and MARL agents fail in the ad-hoc setting where each agent learns and follows its policy independently from the other players.

In this project, at first, I approached the problem by hard-coding some rules (similar to the theory of mind techniques that humans use when playing Hanabi). These rules achieve a reasonable performance in the self-play setting with different number of players. To add some intelligence, I came up with an offline q-learning setting. The q-values are constantly updated during the games, and are also sometimes involved in decision-making. Perhaps, after a large number of games, we can extract each agent's q-table, and run the game according to them (although even more complex approaches such as deep q-networks (DQN) have failed in the ad-hoc setting).

## Instructions

First start the game server by using the following command in a terminal:

```bash
python server.py <min_num_players>
```

Argumanets:

+ player_name, __optional__: (str) The game does not start until a minimum number of player has been reached. Default = 2

Afterwards, to add each player to a tournament, run the following in a separate terminal:

```bash
python controller.py <player_name> <verbose> <num_games_limit>
```

Arguments:

+ player_name: (str) The player's given name
+ verbose, __optional__: (bool: 0 or 1) Whether or not to print players observations and actions on each turn. Default = 0 (False)
+ num_games_limit, __optional__: (int) The number of games to play in the tournament (if None the tournament will continue indefinitely). Default = None

You will need to type "read" in each terminal to start the tournament.
