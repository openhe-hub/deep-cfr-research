### Repo
* https://github.com/openhe-hub/grouped-poker-rl
* https://github.com/openhe-hub/deep-cfr-research

### Python Env Setup
* pip install requests
* pip install PokerRL
* pip install ray
* install cuda driver & corresponding pytorch

### In Poker RL
* Add 'rl/neural/MainPokerModuleFlatResv3.py'
* Modify 'game/bet_sets.py', add these lines:
![alt text](assets/b8.png)
* Or just replace {PYTHON_HOME}/site-packages/PokerRL with this repo

### In DeepCFR
* Add 'eval_agentSINGLE.pkl' latest version
* Add 'cache-train.json'
* Modify 'TrainingProfile.py':
1. Add these 3 properties:
    ![alt text](assets/tp1.png)
2. Add these 
    ![alt text](assets/tp2.png)
* Modify these buffer files(in workers/), add 'resnet' type:  
  1. DeepCFR/workers/la/buffers/AdvReservoirBuffer.py
    ![alt text](assets/buffer1.png)
  2. DeepCFR/workers/la/buffers/AvrgReservoirBuffer.py
    ![alt text](assets/buffer2.png)
  3. DeepCFR/workers/la/buffers/_ReservoirBufferBase.py
    ![alt text](assets/buffer3.png)
* No change in interactive.py