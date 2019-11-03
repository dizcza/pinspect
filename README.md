# Pretty inspect

Inspired by the complexity of [Neo](https://github.com/NeuralEnsemble/python-neo).

When browsing/inspecting an object, you want to collect all methods and attributes that match the key.

#### Example

Browsing the direct methods in `neo.io.BlackrockIO` and looking for the ways of extracting `epoch`s, you found `read_epoch()` method. But calling this method produces `AssertionError`. You need to go deeper.
1. Run `pip install pinspect neo`
2. In python,

```python
import neo
from neo.io import BlackrockIO
from pinspect import find

session = BlackrockIO('/home/ulianych/PycharmProjects/other/blackrockio/sampleData')
matches = find(session, 'epoch')  # a list of strings
print('\n'.join(matches))
```

Output:

```
BlackrockIO._rescale_epoch_duration(raw_duration, dtype)
BlackrockIO.read_epoch(**kargs)
BlackrockIO.read_segment().construct_subsegment_by_unit().epochs
BlackrockIO.read_segment().epochs
BlackrockIO.rescale_epoch_duration(raw_duration, dtype='float64')
BlackrockIO.write_epoch(ep, **kargs)
```