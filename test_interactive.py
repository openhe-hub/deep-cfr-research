from interactive0 import InteractiveGame
from DeepCFR.EvalAgentDeepCFR import EvalAgentDeepCFR

if __name__ == '__main__':
    eval_agent = EvalAgentDeepCFR.load_from_disk(
        path_to_eval_agent='./assets/eval/10/eval_agentSINGLE.pkl'
    )

    # print(f'bet set = {eval_agent.env_bldr.env_args.bet_sizes_list_as_frac_of_pot}')

    game = InteractiveGame(
        env_cls=eval_agent.env_bldr.env_cls,
        env_args=eval_agent.env_bldr.env_args,
        seats_human_plays_list=[0],
        eval_agent=eval_agent,
    )

    game.start_to_play()