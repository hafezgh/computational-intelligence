from agent import HanabiAgent
from sys import argv, stdout


def run(player_name, verbose_action_, verbose_full_, num_games_limit_):
    print(verbose_action_, verbose_full_, num_games_limit_)
    agent = HanabiAgent(player_name, verbose_action=verbose_action_, verbose_full=verbose_full_, num_games_limit=num_games_limit_)
    print(f"\nThe tournament finished! The total number of {agent.num_games} with average score of {agent.average_score} were played.\n")

if __name__ == '__main__':
    ### Sample input: python controller.py p1 True False 100
    if len(argv) not in [2,3,4,5]:
        raise Exception("Invalid run command! The terminal command should be "
        " \'python controller.py <playerName> <verbose_action> <verbose_full> <num_games_limit>\'. "
        "Verbose args are optional and their default value is False. The tournament will go on for ever "
        "if the number of games is not provided.")
    player_name= argv[1]
    if len(argv) == 3:
        verbose_action = argv[2]
        verbose_full = False
    elif len(argv) == 4:
        verbose_action = argv[2]
        verbose_full = argv[3]
    elif len(argv) == 5:
        try:
            num_games_limit = int(argv[4])
        except:
            raise ValueError("The number of games should be an integer.")
        verbose_action = argv[2]
        verbose_full = argv[3]
    else:
        verbose_action = True
        verbose_full = False
        num_games_limit = None
    run(player_name, verbose_action, verbose_full, num_games_limit)