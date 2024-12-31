# Copyright (c) 2019 Eric Steinberger
import copy
import time

import numpy as np

from typing import Tuple
from PokerRL.game.Poker import Poker

class InteractiveGame:
    """
    This class facilitates play between a user against an EvalAgent or against himself in any poker game.
    """

    def __init__(self, env_cls, env_args, seats_human_plays_list, eval_agent=None):
        """

        Args:
            env_cls (PokerEnv subclass):    the subclass of PokerEnv (not instance!) that the EvalAgent was trained on
                                            or more generally, you want to play in.

            env_args (PokerEnvArgs, DiscretizedPokerEnvArgs, or LimitPokerEnvArgs):
                                            The arguments object corresponding to the environment

            seats_human_plays_list (list):  a list of ints that indicates which seats on the table are played by the
                                            human in the command line. If you pass an empty list, you can watch the AI
                                            play against itself, or you can pass a list with all seats to play against
                                            yourself. The most common use-case, however, is to pass some seats and
                                            play against the agent.

            eval_agent (EvalAgentBase):     The wrapped agent. You only need to pass one if ""seats_human_plays_list""
                                            doesn't cover all seats on the table.
        """
        if len(seats_human_plays_list) < env_args.n_seats:
            assert eval_agent is not None

        self._env = env_cls(env_args=env_args, is_evaluating=True, lut_holder=env_cls.get_lut_holder())
        self._env.reset()

        self._eval_agent = eval_agent

        self._seats_human_plays_list = seats_human_plays_list
        self._winnings_per_seat = [0 for _ in range(self._env.N_SEATS)]

    @property
    def seats_human_plays_list(self):
        return copy.deepcopy(self._seats_human_plays_list)

    @property
    def winnings_per_seat(self):
        return copy.deepcopy(self._winnings_per_seat)

    def init(self, render_mode="TEXT", limit_numpy_digits=True):
        if limit_numpy_digits:
            np.set_printoptions(precision=5, suppress=True)
    
    def reset(self, player_id, hold_cards):
        self._env.reset()
        if self._eval_agent is not None:
            self._eval_agent.reset(deck_state_dict=self._env.cards_state_dict())
        self._env.seats[player_id].hand = np.array([self.card2arr(card) for card in hold_cards])
        self._env.seats[[1, 0][player_id]].hand = np.array([])
        self._env.render(mode="TEXT")

    def play_slumbot(self, action: str, data: dict):
        current_player_id = 0
        action_tuple = self._env.bot_api_ask_action(self.slumbot_to_model(action))

        if self._eval_agent is not None:
            print(f"[Slumbot Input] action = {action_tuple}, curr player id = {current_player_id}")
            self._eval_agent.notify_of_processed_tuple_action(action_he_did=action_tuple,
                                                                          p_id_acted=current_player_id)
        
        self._env.current_round = data['street']
        self._env.board = np.array([self.card2arr(card) for card in data['hole_cards']])
        self.main_pot = data['street_last_bet']
        self.side_pots = data['total_last_bet']

    def play_my_bot(self, data: dict):
        current_player_id = 0
        a_idx, frac = self._eval_agent.get_action_frac_tuple(step_env=True)
        if a_idx == 2:
            action_tuple = [2, self._env.get_fraction_of_pot_raise(fraction=frac,
                                                                               player_that_bets=current_player_id)]
        else:
            action_tuple = [a_idx, -1]
                    
        print(f"[Mybot] {action_tuple}")
        return self.model_to_slumbot(action_tuple)

    def start_to_play(self, render_mode="TEXT", limit_numpy_digits=True):
        # ______________________________________________ one episode _______________________________________________
        self._env.render(mode=render_mode)
        while True:
            current_player_id = self._env.current_player.seat_id

            # if self._eval_agent is not None:
            #     assert np.array_equal(self._env.board, self._eval_agent._internal_env_wrapper.env.board)
            #     assert np.array_equal(np.array(self._env.side_pots),
            #                               np.array(self._eval_agent._internal_env_wrapper.env.side_pots))
            #     assert self._env.current_player.seat_id == \
            #                self._eval_agent._internal_env_wrapper.env.current_player.seat_id
            #     assert self._env.current_round == self._eval_agent._internal_env_wrapper.env.current_round

            # Human acts
            # if current_player_id in self._seats_human_plays_list:
                

            # Agent acts
            # else:


            obs, rews, done, info = self._env._step(processed_action=action_tuple)
            self._env.render(mode=render_mode)

            if done:
                break

            for s in range(self._env.N_SEATS):
                self._winnings_per_seat[s] += np.rint(rews[s] * self._env.REWARD_SCALAR)

            print("")
            print("Current Winnings per player:", self._winnings_per_seat)


    def model_to_slumbot(self, action_tuple: Tuple[int, int]) -> str:
        action = action_tuple[0]
        bet_sz = action_tuple[1]
        incr = ''

        if action == Poker.FOLD:
            incr = 'f'
        elif action == Poker.CHECK_CALL:
            if bet_sz == -1:
                incr = 'k'
            else:
                incr = 'c'
        elif action == Poker.BET_RAISE:
            incr = f'b{abs(bet_sz)}'
        
        return incr

    def slumbot_to_model(self, action: str) -> int:
        if action == 'f':
            return Poker.FOLD
        elif action == 'k' or action == 'c':
            return Poker.CHECK_CALL
        elif action.startswith('b'):
            return Poker.BET_RAISE
    
    def card2arr(str, card: str) -> np.array:
        assert len(card) == 2, "Card string must be exactly 2 characters."

        RANK_DICT = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        SUIT_DICT = {'h': 0, 'd': 1, 's': 2, 'c': 3}

        rank = RANK_DICT.get(card[0])
        suit = SUIT_DICT.get(card[1])

        assert rank is not None, f"Invalid rank: {card[0]}"
        assert suit is not None, f"Invalid suit: {card[1]}"

        return np.array([rank, suit])


