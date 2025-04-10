# Copyright (c) 2019 Eric Steinberger
import copy
import time
import json
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
        self.min_bet_sz = 0

        self.cache_path = './assets/tmp/cache-train.json'

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
        # self._env.render(mode="TEXT")
        self.min_bet_sz = 0

    def play_slumbot(self, action: str, data: dict, is_first: bool):
        # self._env.render(mode="TEXT")
        # set
        self._env.current_round = data['street']
        self._env.board = np.array([self.card2arr(card) for card in data['board_cards']])
        self.main_pot = data['street_last_bet']
        self.min_bet_sz = max(self.min_bet_sz, self.main_pot)
        self.side_pots = data['total_last_bet']
        # detect
        current_player_id = 1 if is_first else 0 
        # action_tuple = self._env.bot_api_ask_action(self.slumbot_to_model(action))
        action_tuple = self.slumbot_to_model(action)

        if self._eval_agent is not None:
            print(f"[Slumbot Input] action = {action_tuple}, curr player id = {current_player_id}, street id = {self._env.current_round}")
            self._eval_agent.notify_of_processed_tuple_action(action_he_did=action_tuple,
                                                                          p_id_acted=current_player_id)

    def play_my_bot(self, data: dict, is_first: bool):
        # self._env.render(mode="TEXT")
        # set
        print(f"[Mybot] data input = {data}")
        self._env.current_round = data['street']
        self._env.board = np.array([self.card2arr(card) for card in data['board_cards']])
        self.main_pot = data['street_last_bet']
        self.min_bet_sz = max(self.min_bet_sz, self.main_pot)
        self.side_pots = data['total_last_bet']

        self.save_to_cache(
            hole_cards=data['hole_cards'],
            board_cards=data['board_cards']
        )
        # detect
        current_player_id = 0 if is_first else 1
        a_idx, frac = self._eval_agent.get_action_frac_tuple(step_env=True)
        if a_idx == 2:
            action_tuple = [2, self._env.get_fraction_of_pot_raise(fraction=frac,
                                                                player_that_bets=current_player_id)]
        else:
            action_tuple = [a_idx, -1]
                    
        print(f"[Mybot] action tuple = {action_tuple}, street id = {self._env.current_round}")
        return self.model_to_slumbot(action_tuple, data)

    def start_to_play(self, render_mode="TEXT", limit_numpy_digits=True):
        # ______________________________________________ one episode _______________________________________________
        self._env.render(mode=render_mode)
        while True:
            current_player_id = self._env.current_player.seat_id
            obs, rews, done, info = self._env._step(processed_action=action_tuple)
            self._env.render(mode=render_mode)

            if done:
                break

            for s in range(self._env.N_SEATS):
                self._winnings_per_seat[s] += np.rint(rews[s] * self._env.REWARD_SCALAR)

            print("")
            print("Current Winnings per player:", self._winnings_per_seat)


    def model_to_slumbot(self, action_tuple: Tuple[int, int], data: dict) -> str:
        action = action_tuple[0]
        bet_sz = action_tuple[1]
        incr = ''

        if action == Poker.FOLD:
            incr = 'f'
        elif action == Poker.CHECK_CALL:
            if bet_sz == -1 and data['street_last_bet'] > 0:
                incr = 'c'
            else:
                incr = 'k'
        elif action == Poker.BET_RAISE:
            if data['street_last_bet'] > 0:
                incr = f"b{max(abs(bet_sz), data['street_last_bet']*2)}"
            else:
                incr = f"b{max(abs(bet_sz), self.min_bet_sz)}"
            # incr = f"b{abs(bet_sz)}"
        
        return incr

    def slumbot_to_model(self, action: str, size: float=0.0) -> Tuple[int, float]:
        if action == 'f':
            return [Poker.FOLD, 0]
        elif action == 'k' or action == 'c':
            return [Poker.CHECK_CALL, 0]
        elif action.startswith('b'):
            size = int(action[1:])
            return [Poker.BET_RAISE, size]
    
    def card2arr(self, card: str) -> np.array:
        assert len(card) == 2, "Card string must be exactly 2 characters."

        RANK_DICT = {'2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, 'T': 8, 'J': 9, 'Q': 10, 'K': 11, 'A': 12}
        SUIT_DICT = {'h': 0, 'd': 1, 's': 2, 'c': 3}

        rank = RANK_DICT.get(card[0])
        suit = SUIT_DICT.get(card[1])

        assert rank is not None, f"Invalid rank: {card[0]}"
        assert suit is not None, f"Invalid suit: {card[1]}"

        return np.array([rank, suit])

    def save_to_cache(self, hole_cards, board_cards):
        with open(self.cache_path, 'w') as f:
            json.dump({
                'use_cache': True,
                'hole_cards': hole_cards,
                'board_cards': board_cards,
            }, f, indent=4, ensure_ascii=False)

