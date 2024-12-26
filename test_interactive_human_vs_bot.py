from PokerRL.game.InteractiveGame import InteractiveGame
from DeepCFR.EvalAgentDeepCFR import EvalAgentDeepCFR


if __name__ == '__main__':
    eval_agent = EvalAgentDeepCFR.load_from_disk(
        path_to_eval_agent='./assets/big_leduc/eval_agentAVRG_NET.pkl'
    )

    print(f'game cls = {eval_agent.env_bldr.env_cls}')

    game = InteractiveGame(
        env_cls=eval_agent.env_bldr.env_cls,
        env_args=eval_agent.env_bldr.env_args,
        seats_human_plays_list=[0],
        eval_agent=eval_agent,
    )

    game.start_to_play()