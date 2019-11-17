# Pretty inspect

Inspired by the complexity of [Neo](https://github.com/NeuralEnsemble/python-neo).

When browsing/inspecting an object, you want to collect all methods and attributes that match the key.

### Example

Browsing the direct methods in `neo.io.BlackrockIO` and looking for the ways of extracting `epoch`s, you found `read_epoch()` method. But calling this method produces `AssertionError`. You need to go deeper.
1. Run `pip install pinspect neo`
2. Download BlackRock [sampledata.zip](http://www.blackrockmicro.com/wp-content/software/sampledata.zip)

```
wget http://www.blackrockmicro.com/wp-content/software/sampledata.zip
unzip sampledata.zip
```

3. In python,

```python
from neo.io import BlackrockIO
from pinspect import find

session = BlackrockIO('sampleData')
graph = find(session, 'epoch', verbose=True)
```

Output:

```
BlackrockIO.read()[0].segments[0].epochs -> 'list of size 0'
BlackrockIO.read()[0].segments[0].spiketrains[0].sampling_period -> 'Epoch'
BlackrockIO.read()[0].segments[0].events[0].to_epoch() -> 'Epoch'
```

### Requirements

1. Python 3.6+
2. [requirements.txt](requirements.txt)
