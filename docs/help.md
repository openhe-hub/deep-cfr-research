### 环境配置步骤
1. 新建conda环境
2. pip install requests
3. 对应cuda版本的pytorch
4. pip install PokerRL
5. pip install ray
### 运行demo可能的bug
1. 如有此参数报错：redis_max_memory => _redis_max_memory
2. 非分布式，设置：DISTRIBUTED=False
3. 无配置pycrayon，端口找不到，注释`Driver.py中 self.crayon = CrayonWrapper(...)`这一段
4. 新建对应的日志文件夹，`${project}/logs/${name}`, `${project}`为项目根目录，`${name}`为`TrainingProfile`参数中的name
5. `Driver.py`中更改`self._t_prof.path_log_storage`为本地路径(或许有更好的解决办法)
### 超参数
### 日志
Bug: 新建日志文件夹，并更改代码中的本地路径，可以解决报错，但是不能成功记录日志
项目的日志从Buffer被导出到ui上了，由于TensorBoard不可用，需要改代码导到本地
### Agent训练记录
每个对象写个state dict，每一个iter用pickle持久化，随后读取分析
* TraingingProfile暂时不做持久化
### TensorBoard
暂无
