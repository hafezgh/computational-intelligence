from agent import HanabiAgent
from sys import argv, stdout


def run(player_name, verbose_action_, num_games_limit_):
    agent = HanabiAgent(player_name, verbose_action=verbose_action_, num_games_limit=num_games_limit_)
    print(f"\nThe tournament finished after a total number of {agent.num_games} games with average score of {agent.average_score}.\n")

if __name__ == '__main__':
    ### Sample input: python controller.py p1 True False 100
    if len(argv) not in [2,3,4]:
        raise Exception("Invalid run command! The terminal command should be "
        " \'python controller.py <playerName> <verbose> <num_games_limit>\'. "
        "Verbose arg is optional and the default value is 0 (it should be 0 or 1). The tournament will go on for ever "
        "if the number of games is not provided.")
    player_name= argv[1]
    if len(argv) == 3:
        try:
            verbose_action = int(argv[2])
        except:
            raise ValueError("Verbose should be an integers!")
        num_games_limit = None
    elif len(argv) == 4:
        try:
            verbose_action = int(argv[2])
            num_games_limit = int(argv[3])
        except:
            raise ValueError("Number of games and verbose should be integers!")
    else:
        verbose_action = False
        num_games_limit = None
    run(player_name, verbose_action, num_games_limit)