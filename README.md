# solana_whale_watcher

Utilities for monitoring Solana accounts.

## Usage as a module

The watcher can be run as a module with `python -m app.watcher` or imported in
your own code:

```python
from app.watcher import monitor_solana

results = await monitor_solana(max_events=5, threshold_SOL=0.001)
```
