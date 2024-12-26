# The body of a sample request to /api/new_hand:
#   {"token": "a2f42f44-7ff6-40dd-906b-4c2f03fcee57"}
# The body of a sample request to /api/act:
#   {"token": "a2f42f44-7ff6-40dd-906b-4c2f03fcee57", "incr": "c"}

# "k" indicates "check", "c" indicates "call", "f" indicates "fold" and "b" indicates "bet"

import requests
import sys
import argparse

sys.path.append('..')
from texasholdem.env.game import GameEnv
from texasholdem.evaluation.simulation import load_card_play_models
import random
import multiprocessing as mp


host = 'slumbot.com'

NUM_STREETS = 4
SMALL_BLIND = 50
BIG_BLIND = 100
STACK_SIZE = 20000
LETTER2SUIT = {'s': '\u2660', 'h': '\033[91m\u2665\033[0m', 'd': '\033[91m\u2666\033[0m', 'c': '\u2663'}
ACTION2STR = {'k': 'check\u2261\33[94mk\033[0m', 'c': 'call\u2261\33[94mc\033[0m',
              'f': 'fold\u2261\33[94mf\033[0m', 'b': 'bet\u2261\33[94mb\033[0m'}
CARD2NUM = { 'Ah': 1, '2h': 2, '3h': 3, '4h': 4, '5h': 5, '6h': 6, '7h': 7, '8h': 8, '9h': 9, 'Th': 10, 'Jh': 11, 'Qh': 12, 'Kh': 13, 
            'Ad': 14, '2d': 15, '3d': 16, '4d': 17, '5d': 18, '6d': 19, '7d': 20, '8d': 21, '9d': 22, 'Td': 23, 'Jd': 24, 'Qd': 25, 'Kd': 26, 
            'Ac': 27, '2c': 28, '3c': 29, '4c': 30, '5c': 31, '6c': 32, '7c': 33, '8c': 34, '9c': 35, 'Tc': 36, 'Jc': 37, 'Qc': 38, 'Kc': 39, 
            'As': 40, '2s': 41, '3s': 42, '4s': 43, '5s': 44, '6s': 45, '7s': 46, '8s': 47, '9s': 48, 'Ts': 49, 'Js': 50, 'Qs': 51, 'Ks': 52 }
NUM2ACTION = { 0: 'xm', 1: 'dm', 2: 'k', 3: 'c', 4: 'b', 5: 'b_', 6: 'f' }
DISPLAY_INFO = 0
CLIENT_TYPE = 0  # 0: random, 1: deep agent
CLIENT_NAMES = ['RANDOM', 'DMC']


def parse_action(action):
    """
    Returns a dict with information about the action passed in.
    Returns a key "error" if there was a problem parsing the action.
    pos is returned as -1 if the hand is over; otherwise the position of the player next to act.
    street_last_bet_to only counts chips bet on this street, total_last_bet_to counts all
      chips put into the pot.
    Handles action with or without a final '/'; e.g., "ck" or "ck/".
    """
    st = 0  # street indexer
    street_last_bet_to = BIG_BLIND
    total_last_bet_to = BIG_BLIND
    last_bet_size = BIG_BLIND - SMALL_BLIND
    last_bettor = 0
    sz = len(action)
    pos = 1
    if sz == 0:
        return {
            'st': st,
            'pos': pos,
            'street_last_bet_to': street_last_bet_to,
            'total_last_bet_to': total_last_bet_to,
            'last_bet_size': last_bet_size,
            'last_bettor': last_bettor,
        }

    check_or_call_ends_street = False
    i = 0
    while i < sz:
        if st >= NUM_STREETS:
            return {'error': 'Unexpected error'}

        c = action[i]
        i += 1
        if c == 'k':  # action: check
            if last_bet_size > 0:
                return {'error': 'Illegal check <- last_best_size is greater than 0'}

            if check_or_call_ends_street:
                # After a check that ends a pre-river street, expect either a '/' or end of string.
                if st < NUM_STREETS - 1 and i < sz:
                    if action[i] != '/':
                        return {'error': 'Missing slash'}
                    i += 1
                if st == NUM_STREETS - 1:
                    # Reached showdown
                    pos = -1
                else:
                    pos = 0
                    st += 1  # progress to the next street
                street_last_bet_to = 0
                check_or_call_ends_street = False
            else:
                pos = (pos + 1) % 2  # advance to the next player
                check_or_call_ends_street = True
        elif c == 'c':  # action: call
            if last_bet_size == 0:
                return {'error': 'Illegal call <- last_bet_size is 0'}
            if total_last_bet_to == STACK_SIZE:
                # Call of an all-in bet
                # Either allow no slashes, or slashes terminating all streets prior to the river.
                if i != sz:
                    for st1 in range(st, NUM_STREETS - 1):
                        if i == sz:
                            return {'error': 'Missing slash (end of string)'}
                        else:
                            c = action[i]
                            i += 1
                            if c != '/':
                                return {'error': 'Missing slash'}
                if i != sz:
                    return {'error': 'Extra characters at end of an action (call)'}
                st = NUM_STREETS - 1
                pos = -1
                last_bet_size = 0
                return {
                    'st': st,
                    'pos': pos,
                    'street_last_bet_to': street_last_bet_to,
                    'total_last_bet_to': total_last_bet_to,
                    'last_bet_size': last_bet_size,
                    'last_bettor': last_bettor,
                }
            if check_or_call_ends_street:
                # After a call that ends a pre-river street, expect either a '/' or end of string.
                if st < NUM_STREETS - 1 and i < sz:
                    if action[i] != '/':
                        return {'error': 'Missing slash after a street-ending call'}
                    i += 1
                if st == NUM_STREETS - 1:
                    # Reached showdown
                    pos = -1
                else:
                    pos = 0
                    st += 1
                street_last_bet_to = 0
                check_or_call_ends_street = False
            else:
                pos = (pos + 1) % 2
                check_or_call_ends_street = True
            last_bet_size = 0
            last_bettor = -1
        elif c == 'f':  # action: fold
            if last_bet_size == 0:
                return {'error', 'Illegal fold <- last_bet_size is 0'}
            if i != sz:
                return {'error': 'Extra characters at end of action'}
            pos = -1
            return {
                'st': st,
                'pos': pos,
                'street_last_bet_to': street_last_bet_to,
                'total_last_bet_to': total_last_bet_to,
                'last_bet_size': last_bet_size,
                'last_bettor': last_bettor,
            }
        elif c == 'b':  # action: bet
            j = i
            while i < sz and '0' <= action[i] <= '9':
                i += 1
            if i == j:
                return {'error': 'Missing bet size'}
            try:
                new_street_last_bet_to = int(action[j:i])
            except (TypeError, ValueError):
                return {'error': 'Bet size not an integer'}
            new_last_bet_size = new_street_last_bet_to - street_last_bet_to

            # Validate that the bet is legal
            remaining = STACK_SIZE - total_last_bet_to
            if last_bet_size > 0:
                min_bet_size = last_bet_size
                # Make sure minimum opening bet is the size of the big blind.
                if min_bet_size < BIG_BLIND:
                    min_bet_size = BIG_BLIND
            else:
                min_bet_size = BIG_BLIND
            # Can always go all-in
            if min_bet_size > remaining:
                min_bet_size = remaining
            if new_last_bet_size < min_bet_size:
                return {'error': 'Bet too small'}
            max_bet_size = remaining
            if new_last_bet_size > max_bet_size:
                return {'error': 'Bet too big'}
            last_bet_size = new_last_bet_size
            street_last_bet_to = new_street_last_bet_to
            total_last_bet_to += last_bet_size
            last_bettor = pos
            pos = (pos + 1) % 2
            check_or_call_ends_street = True
        else:
            return {'error': 'Unexpected character in action'}

    return {
        'st': st,
        'pos': pos,
        'street_last_bet_to': street_last_bet_to,
        'total_last_bet_to': total_last_bet_to,
        'last_bet_size': last_bet_size,
        'last_bettor': last_bettor,
    }
    # END of parse_action()


def new_hand(token):
    data = {}
    if token:
        data['token'] = token
    # Use verify=false to avoid SSL Error
    # If porting this code to another language, make sure that the Content-Type header is
    # set to application/json.
    response = requests.post(f'https://{host}/api/new_hand', headers={}, json=data)
    success = getattr(response, 'status_code') == 200
    if not success:
        print('Status code: %s' % repr(response.status_code))
        try:
            print('Error response: %s' % repr(response.json()))
        except ValueError:
            pass
        sys.exit(-1)

    try:
        r = response.json()
    except ValueError:
        print('Could not get JSON from response')
        sys.exit(-1)

    if 'error_msg' in r:
        print('Error: %s' % r['error_msg'])
        sys.exit(-1)
        
    return r


def act(token, action):
    data = {'token': token, 'incr': action}
    # Use verify=false to avoid SSL Error
    # If porting this code to another language, make sure that the Content-Type header is
    # set to application/json.
    response = requests.post(f'https://{host}/api/act', headers={}, json=data)
    success = getattr(response, 'status_code') == 200
    if not success:
        print('Status code: %s' % repr(response.status_code))
        try:
            print('Error response: %s' % repr(response.json()))
        except ValueError:
            pass
        sys.exit(-1)

    try:
        r = response.json()
    except ValueError:
        print('Could not get JSON from response')
        sys.exit(-1)

    # if 'error_msg' in r:
    #     print('Error: %s' % r['error_msg'])
    #     sys.exit(-1)
        
    return r


def enrich_cards(cards):
    return [('10' if s[0] == 'T' else s[0]) + LETTER2SUIT[s[1]] for s in cards]


def play_x_hand(token, game_env, num_hands, q):  # client_pos = first_player
    winnings_total = 0
    sb_folds = 0
    sb_cards_pos_f = {}
    sb_0f = 0
    sb_1f = 0
    for h in range(num_hands):
        client_pos = h % 2
        game_env.card_play_init_no_data() # modified to *not* use `card_play_data`
        r = new_hand(token)
        new_token = r.get('token')
        if new_token:
            token = new_token
        player_n_bets = {0: 100, 1: 0} if client_pos == 0 else {0: 100, 1: 200}
        slumbot_pos = (client_pos + 1) % 2
        
        while True:
            if DISPLAY_INFO:
                print('-' * 80)
            action = r.get('action')
            hole_cards = r.get('hole_cards')
            board = r.get('board')
            winnings = r.get('winnings')

            hole_cards_enriched = enrich_cards(hole_cards)
            board_enriched = enrich_cards(board)
            if CLIENT_TYPE == 1:
                if game_env.info_sets['p' + str(client_pos + 1)].player_hand_cards is None:
                    game_env.info_sets['p' + str(client_pos + 1)].player_hand_cards = [CARD2NUM[hole_cards[0]], CARD2NUM[hole_cards[1]]]

                    # fast forward the first 2 blinds, *after* loading the client's hole cards
                    if client_pos == 0:  # UtG, SB
                        game_env.step_s(as_deep_agent=True, desired_action=[0])
                    else:  # UtG+1, BB
                        game_env.step_s(as_deep_agent=False, desired_action=[0])
                        game_env.step_s(as_deep_agent=True, desired_action=[1])

            if DISPLAY_INFO:        
                print('INFO::r: ', r)

            betting_round = 'N/A'
            board_size = len(board)
            if board_size == 0:
                if DISPLAY_INFO:
                    if client_pos == 1:
                        print('Client position: UtG+1, BB')
                    elif client_pos == 0:
                        print('Client position: UtG, SB')
                betting_round = 'pre-flop'
            elif board_size == 3:
                betting_round = 'flop'
                if CLIENT_TYPE == 1:
                    if len(game_env.community_cards) != 3:
                        game_env.community_cards = [CARD2NUM[board[_]] for _ in range(board_size)]
            elif board_size == 4:
                betting_round = 'turn'
                if CLIENT_TYPE == 1:
                    if len(game_env.community_cards) != 4:
                        game_env.community_cards = [CARD2NUM[board[_]] for _ in range(board_size)]
            elif board_size == 5:
                betting_round = 'river'
                if CLIENT_TYPE == 1:
                    if len(game_env.community_cards) != 5:
                        game_env.community_cards = [CARD2NUM[board[_]] for _ in range(board_size)]
            
            if DISPLAY_INFO:
                print('Client hole cards: %s|%s' % (hole_cards_enriched[0], hole_cards_enriched[1]))
                print('Betting round: %s' % betting_round)

                if board_size:
                    print('Board: ', end='')
                    for _ in board_enriched:
                        print(_+'|', end='')
                    print()

            if winnings is not None:
                if DISPLAY_INFO:
                    print('Hand winnings: %i' % winnings)
               
                if betting_round == 'pre-flop' and winnings > 0 and len(action):
                    if action[-1] == 'f' or len(action) >= 2 and action[-1] == '/' and action[-2] == 'f':
                        sb_folds += 1
                        sb_cards_pos_f[r.get('bot_hole_cards')[0] + r.get('bot_hole_cards')[1]] = [h, slumbot_pos]
                        if slumbot_pos == 0:
                            sb_0f += 1
                        elif slumbot_pos == 1:
                            sb_1f += 1

                game_env.reset()
                winnings_total += winnings  # the current hand ends here
                break

            # Need to check or call
            a = parse_action(action)
            if DISPLAY_INFO:
                print('INFO::a: ', a)

            if 'error' in a:
                print('Error parsing action %s: %s' % (action, a['error']))
                sys.exit(-1)

            action_1 = '' if action == '' else action[-1]
            slumbot_called = False
            if a['last_bettor'] == -1:
                legal_actions = ['c', 'f', 'b', 'b_']

                if len(action) >= 2 and slumbot_pos == 1 and action_1 == '/' and action[-2] == 'c'\
                    or len(action) >= 3 and slumbot_pos == 0 and action[-3] == 'c':
                    player_n_bets[slumbot_pos] = player_n_bets[client_pos]  # slumbot chose to call
                    slumbot_called = True
            elif a['last_bettor'] == client_pos:
                legal_actions = ['c', 'b', 'b_', 'k']
            elif a['last_bettor'] == slumbot_pos:  # Update slumbot's bet if it is the last bettor
                legal_actions = ['c', 'f', 'b', 'b_']
                # player_n_bets[slumbot_pos] += a['total_last_bet_to']
                # player_n_bets[slumbot_pos] += a['street_last_bet_to']
                # slumbot_bet_to = player_n_bets[slumbot_pos] + a['street_last_bet_to']
                # player_n_bets[slumbot_pos] = slumbot_bet_to if slumbot_bet_to > player_n_bets[client_pos] else (player_n_bets[slumbot_pos] + a['street_last_bet_to'])
                # player_n_bets[slumbot_pos] = min(max(player_n_bets.values()) + a['street_last_bet_to'], STACK_SIZE)
                player_n_bets[slumbot_pos] = min(player_n_bets[slumbot_pos] + a['street_last_bet_to'], STACK_SIZE)

                # if player_n_bets[client_pos] == max(player_n_bets.values()) and player_n_bets[client_pos] < STACK_SIZE:
                #     legal_actions.append('k')

                if player_n_bets[slumbot_pos] >= STACK_SIZE:
                    legal_actions = ['c', 'f']
            else:
                print('Error parsing last bettor %s' % a['last_bettor'])
                sys.exit(-1)

            # additional adjustments
            if len(action) == 0:  # UtG's 1st action right after the blinds
                legal_actions = ['f', 'b', 'b_', 'c']
            else:
                if action_1 == '/' and 'f' in legal_actions:
                    legal_actions.remove('f')  # illegal fold after a street-ending call or check

                if len(action) >= 2 and action_1 == '/':
                    if action[-2] == 'c' or action[-2] == 'k':
                        legal_actions = ['b', 'b_', 'k']

                if action_1 == 'k':
                    if 'c' in legal_actions:
                        legal_actions.remove('c')  # illegal call after a check

                    if 'f' in legal_actions:
                        legal_actions.remove('f')  # illegal fold after a check

                    if 'k' not in legal_actions:
                        legal_actions.append('k')

            min_bet_clipped = min(max(player_n_bets.values()) * 2, STACK_SIZE) - player_n_bets[client_pos]  # client's perspective
            min_bet = max(player_n_bets.values()) * 2 - player_n_bets[client_pos]
            

            if CLIENT_TYPE == 0:
                my_action = random.choice(legal_actions)
                if my_action[0] == 'b':
                    my_action = 'b'  # ban all in -> bet size too big
                    player_n_bets[client_pos] += min_bet_clipped  # raiseX2 ('b')
                    my_action += str(min_bet)
                   
            elif CLIENT_TYPE == 1:
                # Parse + execute Slumbot's action
                his_last_action = []  # 0: small blind; 1: big blind; 2: check; 3: call; 4: raise(x2); 5: raise(all in); 6: fold
                old_action = r.get('old_action')
                
                amount_bet = 0
                if old_action == '':
                    if action_1 == 'f':
                        his_last_action = [6]  # fold
                    else:
                        if client_pos == 0:
                            his_last_action = [1] 
                        else:
                            if a['last_bettor'] == 0:                            
                                if a['total_last_bet_to'] + player_n_bets[0] < STACK_SIZE:
                                    his_last_action = [4]  # raise
                                    amount_bet = a['total_last_bet_to']
                                else:
                                    his_last_action = [5]  # all in
                                    amount_bet = STACK_SIZE - max(player_n_bets.values())
                            else:  # cannot check as UtG
                                his_last_action = [3]  # call
                elif len(action) > 0:
                    if action_1 == '/' or action_1 == 'k':
                        his_last_action = [2]  # check
                    elif action_1.isdigit():
                        if player_n_bets[slumbot_pos] < STACK_SIZE:
                            his_last_action = [4]  # raise
                            amount_bet = min_bet
                        else:
                            his_last_action = [5]  # all in
                            amount_bet = STACK_SIZE - max(player_n_bets.values())
                    
                    if slumbot_called:  # call
                        his_last_action = [3]
                game_env.step_s(as_deep_agent=False, desired_action=his_last_action, bet_amount=amount_bet)
                        
                try:
                    my_action = NUM2ACTION[game_env.step_s(as_deep_agent=True)]
                except TypeError:
                    if DISPLAY_INFO:
                        print('Error parsing the deep agent\'s action...\nr: %s\ngame_env.step_s() returned: %s' 
                            % (r, str(game_env.step_s(as_deep_agent=True))))

                if len(my_action):
                    if my_action not in legal_actions:
                        if DISPLAY_INFO:
                            print('Choosing my_action randomly from legal actions %s as the chosen %s is illegal' % (str(legal_actions), my_action))
                        my_action = random.choice(legal_actions)
                    
                        if my_action == 'b_':  # ban all in
                            my_action = 'b'

                    if my_action[0] == 'b':
                        player_n_bets[client_pos] += min_bet_clipped  # raiseX2 ('b')
                        my_action += str(min_bet)
                        
                        # if len(my_action) == 1:
                        #     player_n_bets[client_pos] += min_bet  # raiseX2 ('b')
                        #     my_action += str(min_bet)
                        # else:
                        #     all_in_amount = STACK_SIZE - max(player_n_bets.values())
                        #     my_action = 'b' + str(all_in_amount)
                        #     player_n_bets[client_pos] += all_in_amount  # all in ('b_')
                
            if len(my_action) and my_action[0] == 'c':  # call
                player_n_bets[client_pos] = player_n_bets[slumbot_pos]

            r = act(token, my_action)
            delta_bet = 0
            while 'error_msg' in r:
                if r['error_msg'] == 'Bet size too big':
                    delta_bet -= 100
                my_action = 'b' + str(int(my_action[1:]) + delta_bet)
                r = act(token, my_action)

        # END of `while True:`
    
    # q.put(winnings_total)
    q.put((winnings_total,
           sb_folds,
           sb_cards_pos_f,
           sb_0f,
           sb_1f,
           ))

        
def login(username, password):
    data = {"username": username, "password": password}
    # If porting this code to another language, make sure that the Content-Type header is
    # set to application/json.
    response = requests.post(f'https://{host}/api/login', json=data)
    success = getattr(response, 'status_code') == 200
    if not success:
        print('Status code: %s' % repr(response.status_code))
        try:
            print('Error response: %s' % repr(response.json()))
        except ValueError:
            pass
        sys.exit(-1)

    try:
        r = response.json()
    except ValueError:
        print('Could not get JSON from response')
        sys.exit(-1)

    if 'error_msg' in r:
        print('Error: %s' % r['error_msg'])
        sys.exit(-1)
        
    token = r.get('token')
    if not token:
        print('Did not get token in response to /api/login')
        sys.exit(-1)
    return token


def main():
    parser = argparse.ArgumentParser(description='Slumbot API example')
    parser.add_argument('--username', type=str)
    parser.add_argument('--password', type=str)
    parser.add_argument('--num_hands', type=int, default=2)
    parser.add_argument('--num_workers', type=int, default=5)
    args = parser.parse_args()
    username = args.username
    password = args.password
    
    # To avoid SSLError:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    card_play_model_path_dict = {'p1': '../best_models/p1.ckpt', 'p2': '../best_models/p2.ckpt'}
    players = load_card_play_models(card_play_model_path_dict)
    
    num_hands = args.num_hands
    num_workers = args.num_workers

    ctx = mp.get_context('spawn')
    q = ctx.SimpleQueue()
    processes = []
    
    for _ in range(5):
        env = GameEnv(players, rotate_dealer=True)
        if username and password:
            token = login(username, password)
        else:
            token = None

        p = ctx.Process(
                target=play_x_hand,
                args=(token, env, num_hands, q))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    # Collecting results
    winnings = 0
    slumbot_num_folds = 0
    slumbot_cards_pos_folded = {}
    slumbot_0f = 0
    slumbot_1f = 0
    for _ in range(num_workers):
        # winnings += q.get()
        result = q.get()
        winnings += result[0]
        slumbot_num_folds += result[1]
        slumbot_cards_pos_folded.update(result[2])
        slumbot_0f += result[3]
        slumbot_1f += result[4]

    bb100 = round(winnings / BIG_BLIND / num_hands / num_workers * 100)
    print('>>>Total winnings: %i, or %s BB/100, after %i games, using %s client' % (
        winnings, ('\033[91m' if bb100 < 0 else '\033[92m') + str(bb100) + '\033[0m', 
        num_hands * num_workers, CLIENT_NAMES[CLIENT_TYPE]))
    # ^^ the standard measure is milli-big-blinds per hand (or per game), or mbb/g, 
    # where one milli-big-blind is 1/1000 of one big blind
    
    print('>>>Slumbot folded {} times out of {} hands (p0f|p1f:::{}|{}) with the following hole cards --> [hand#, pos] \n{}'.format(
        slumbot_num_folds, num_hands * num_workers, slumbot_0f, slumbot_1f, slumbot_cards_pos_folded))
    

if __name__ == '__main__':
    main()
