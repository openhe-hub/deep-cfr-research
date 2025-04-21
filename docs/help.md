### Env Config
1. conda create -n deep_cfr python=3.8
2. pip install requests
3. download pytorch (corresponding cuda version)
4. pip install PokerRL
5. pip install ray
### Possible Bugs After Cloning Original Repo 
1. About redis params: redis_max_memory => _redis_max_memory
2. Train without distributed GPUs: DISTRIBUTED=False
3. Dont want Pycrayon, port not found, comment `Driver.py中 self.crayon = CrayonWrapper(...)`
4. Create the corresponding log folder, `${project}/logs/${name}`, where `${project}` is the project root directory, and `${name}` is the `name` parameter in `TrainingProfile`.
5. In `Driver.py`, modify `self._t_prof.path_log_storage` to a local path (there might be a better solution).
### Logs
Bug: Creating a new log folder and modifying the local path in the code can resolve the error, but it cannot successfully record logs.  
The project's logs are exported from the Buffer to the UI. Since TensorBoard is unavailable, the code needs to be modified to export logs locally.
### Agent Training Checkpoints
Write a state dict for each object, persist each iteration using pickle, and then read it for analysis.  
* `TrainingProfile` will not be persisted for now.
### Slumbot Eval Records
1. assets/slumbot/record.txt: record cards, actions, hand win in each hand
2. assets/slumbot/output_record.txt: action output from model on every street
### Some Scripts
1. test/test_adv_loss.ipynb: visualize loss curves
2. test/test_exploitability.ipynb: visualize exploitability curve
3. test/test_slumbot_match.ipynb: show match winning curves and data
4. test/test_poker_bckt.ipynb: statistics about model action and bucket db
5. script/mem.sh: show current memory ranking when training / evaluation 

### TensorBoard
The original project supports TensorBoard, but we don't use TensorBoard here
