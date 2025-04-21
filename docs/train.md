### Training 
1. use `paper_experiment_**.py` for train, including: 
   * big_leduc
   * fhp
   * limited
   * discrete (unlimited with bet set)
2. training outputs:
   * loss: assets/adv_loss/adv_loss_{player_id}.txt
   * checkpoint: assets/eval/{n}
   * exploitability: assets/single.txt
3. training params:
   * DISTRIBUTED: if distributed
   * n_learner_actor_workers: cpu workers num
   * eval_agent_export_freq: frequency of evaluation
   * nn_type: feedforward/rnn/resnet
   * game_cls: game type, see PokerRL.game.games
   * n_traversals_per_iter: generating data size
   * n_batches_**_training: num batch
   * device_**: cuda or cpu
   * evaluation: h2h example(use 2k hands eval, every 5 epoch)
        ```py
        h2h_args=H2HArgs(
            n_hands=2000,
        ),
        eval_methods={
            "h2h": 5,
        },
        ```
  