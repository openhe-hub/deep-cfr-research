# The API utilizes HTTP POST requests.  Requests and responses have a JSON body.
# There are three endpoints:
#   /api/login
#   /api/new_hand
#   /api/act
# To initiate a new hand, send a request to /api/new_hand.  To take an action, send a
# request to /api/act.
#
# The body of a sample request to /api/new_hand:
#   {"token": "a2f42f44-7ff6-40dd-906b-4c2f03fcee57"}
# The body of a sample request to /api/act:
#   {"token": "a2f42f44-7ff6-40dd-906b-4c2f03fcee57", "incr": "c"}
#
# A sample response from /api/new_hand or /api/act:
#   {'old_action': '', 'action': 'b200', 'client_pos': 0, 'hole_cards': ['Ac', '9d'], 'board': [], 'token': 'a2f42f44-7ff6-40dd-906b-4c2f03fcee57'}
#
# Note that if the bot is first to act, then the response to /api/new_hand will contain the
# bot's initial action.
#
# A token should be passed into every request.  With the exception that on the initial request to
# /api/new_hand, the token may be missing.  But all subsequent requests should contain a token.
# The token can in theory change over the course of a session (usually only if there is a long
# pause) so always check if there is a new token in a response and use it going forward.
#
# A client_pos of 0 indicates that you are the big blind (second to act preflop, first to act
# postflop).  1 indicates you are the small blind.
#
# Sample action that you might get in a response looks like this:
#   b200c/kk/kk/kb200
# An all-in can contain streets with no action.  For example:
#   b20000c///
#
# "k" indicates "check", "c" indicates "call", "f" indicates "fold" and "b" indicates "bet"
# (either an initial bet or a raise).
#
# Bet sizes are the number of chips that the player has put into the pot *on that street* (only).
# Consider this action:
#
#   b200c/kb400
#
# The flop bet here is a pot-size bet to 400 because there are 400 chips in the pot after the
# preflop action.  If the bet is called, then each player will have put a total of 600 chips into
# the pot counting both the preflop and the flop.
# 
# Slumbot plays with blinds of 50 and 100 and a stack size of 200 BB (20,000 chips).  The stacks
# reset after each hand.

import requests
import sys
import toml

from interactive import InteractiveGame
from DeepCFR.EvalAgentDeepCFR import EvalAgentDeepCFR

host = 'slumbot.com'

NUM_STREETS = 4
SMALL_BLIND = 50
BIG_BLIND = 100
STACK_SIZE = 20000

class MyBot:
    def __init__(self):
        self.eval_agent = EvalAgentDeepCFR.load_from_disk(
            path_to_eval_agent='./assets/eval/10/eval_agentSINGLE.pkl'
        )

        print(self.eval_agent.env_bldr.env_args.bet_sizes_list_as_frac_of_pot)

        self.game = InteractiveGame(
            env_cls=self.eval_agent.env_bldr.env_cls,
            env_args=self.eval_agent.env_bldr.env_args,
            seats_human_plays_list=[],
            eval_agent=self.eval_agent,
        )

        self.game.init()
        self.is_first = True
        self.cnt_diff = 0
    
    def reset(self, player_id, hole_cards):
        if not self.is_first:
            self.game._seats_human_plays_list = [1, 0][player_id] # rev, player id = slumbot, model id = my bot
        else:
            self.game._seats_human_plays_list = player_id
        self.game.reset(player_id, hole_cards)
    
    def play_slumbot(self, action: str, data: dict):
        self.game.play_slumbot(action, data, self.is_first)

    def play_my_bot(self, data: dict) -> str:
        return self.game.play_my_bot(data, self.is_first)


def ParseAction(action):
    """
    Returns a dict with information about the action passed in.
    Returns a key "error" if there was a problem parsing the action.
    pos is returned as -1 if the hand is over; otherwise the position of the player next to act.
    street_last_bet_to only counts chips bet on this street, total_last_bet_to counts all
      chips put into the pot.
    Handles action with or without a final '/'; e.g., "ck" or "ck/".
    """
    st = 0
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
        if c == 'k':
            if last_bet_size > 0:
                return {'error': 'Illegal check'}
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
                    st += 1
                street_last_bet_to = 0
                check_or_call_ends_street = False
            else:
                pos = (pos + 1) % 2
                check_or_call_ends_street = True
        elif c == 'c':
            if last_bet_size == 0:
                return {'error': 'Illegal call'}
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
                    return {'error': 'Extra characters at end of action'}
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
                        return {'error': 'Missing slash'}
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
        elif c == 'f':
            if last_bet_size == 0:
                return {'error', 'Illegal fold'}
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
        elif c == 'b':
            j = i
            while i < sz and action[i] >= '0' and action[i] <= '9':
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

def NewHand(token):
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

def Act(token, action):
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

    if 'error_msg' in r:
        print('Error: %s' % r['error_msg'])
        raise Exception(r['error_msg'])
        # sys.exit(-1)
        
    return r

def DiffAction(old_action: str, action: str, last_play: str):
    # print(f"{old_action}, {action}, {last_play}")
    diff = action.replace(old_action, "")
    if diff.endswith('/'):
        diff = diff[:-1]
    elif len(diff.split('/')):
        diff = diff.split('/')[-1]
    
    if (diff.startswith(last_play)) and len(diff) > len(last_play):
        diff = diff[len(last_play):]
    
    if (diff.startswith('k')) and len(diff) > 1:
        diff = diff[1:]

    return diff

def GetGameData(resp, parsed_action, is_first):
    data = {
        "old_action": resp.get("action"),
        "hole_cards": resp.get('hole_cards'),
        "board_cards": resp.get('board'),
        "street": parsed_action['st'],
        "seat_id": resp.get('client_pos'),
        'street_last_bet': parsed_action['street_last_bet_to'],
        'total_last_bet': parsed_action['total_last_bet_to'],
        "is_first": is_first,
        "bot_hole_cards": resp.get("bot_hole_cards"),
    }
    return data

def isFirst(resp) -> bool:
    old_action = resp.get('old_action')
    action = resp.get('action') 
    if old_action == '' and action != '':
        return False
    else:
        return True
    
def PlayHand(token, my_bot: MyBot):
    output_record = [[] for i in range(4)]
    r = NewHand(token)
    is_first = isFirst(r)
    old_street_id = 0
    last_play = ''
    my_bot.is_first = is_first
    if not is_first:
        my_bot.reset(0, r.get('hole_cards'))
    else:
        my_bot.reset(1, r.get('hole_cards'))
    # We may get a new token back from /api/new_hand
    new_token = r.get('token')
    if new_token:
        token = new_token
    while True:
        print('-----------------')
        old_action = r.get('old_action')
        action = r.get('action')
        diff_action = DiffAction(old_action, action, last_play)
        client_pos = r.get('client_pos')
        hole_cards = r.get('hole_cards')
        board = r.get('board')
        winnings = r.get('winnings')
        # update data
        a = ParseAction(action)
        data = GetGameData(r, a, is_first)
        street_id = a.get('st')

        if client_pos:
            print('Client pos: %i' % client_pos)
        if winnings is not None:
            print('Hand winnings: %i' % winnings)
            return (token, winnings, data, output_record)
        
        # Need to check or call
        if street_id > old_street_id or (street_id==old_street_id and is_first):
            output = my_bot.play_my_bot(data)
            incr, record = output[0], output[1]
            output_record[street_id].append(record)
            last_play = incr
            print('Sending incremental action: %s' % incr)
            r = Act(token, incr)
            old_street_id = street_id
        else:
            # play slumbot
            my_bot.play_slumbot(diff_action, data)

            if 'error' in a:
                print('Error parsing action %s: %s' % (action, a['error']))
                sys.exit(-1)
            output = my_bot.play_my_bot(data)
            incr, record = output[0], output[1]
            output_record[street_id].append(record)
            last_play = incr
            print('Sending incremental action: %s' % incr)
            r = Act(token, incr)
        print('finish playing round once.')
        
def Login(username, password):
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
    config = toml.load('./config/config.toml')
    username = config['slumbot']['username']
    password = config['slumbot']['password']
    if username and password:
        token = Login(username, password)
    else:
        token = None

    num_hands = 2000
    curr_hands = 0
    winnings = 0
    record_path = './assets/slumbot/record.txt'
    output_record_path = './assets/slumbot/output_record.txt'
    # init bot 
    my_bot = MyBot()
    # clear previous records
    with open(record_path, 'w') as fp:
        pass

    while curr_hands != num_hands:
        try:
            (token, hand_winnings, data, output_record) = PlayHand(token, my_bot)
        except Exception as e:
            print(f"Error in PlayHand: {e}")
            hand_winnings = 0
            continue

        my_bot.cnt_diff += 1 if my_bot.is_first else -1
        if my_bot.cnt_diff > 0 or my_bot.cnt_diff < -1: 
            my_bot.cnt_diff = max(my_bot.cnt_diff, -1)
            my_bot.cnt_diff = min(my_bot.cnt_diff, 0)
            continue 

        winnings += hand_winnings

        with open(record_path, 'a') as fp:
            if hand_winnings > 0 and data['old_action'] == '':
                data['old_action'] = 'f'
            fp.write(f"id = {curr_hands}, is first = {data['is_first']}, hand win = {hand_winnings}, total win = {winnings}, history action = {data['old_action']}, hole cards = {data['hole_cards']}, bot hole cards = {data['bot_hole_cards']}, board cards = {data['board_cards']}\n")
        
        with open(output_record_path, 'a') as fp:
            fp.write(f"{output_record}\n")
        curr_hands += 1

    print('Total winnings: %i' % winnings)
    # print(f'BB/100 = {winnings/BIG_BLIND/num_hands*100}')
    
if __name__ == '__main__':
    main()
