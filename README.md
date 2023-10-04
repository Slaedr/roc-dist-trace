Script to merge JSON traces, particularly those created by `rocprof --hip-trace --roctx-trace`.

Use `python3 chrome-trace-merge/merge.py -h` for usage.

The script primarily accomplishes:
- Modifies names of timeline groups to include the rank
- Makes the PIDs of the timeline groups unique so that different ranks remain separate
- Modifies names of `DataFlow` events to separate those belonging to different ranks
- Modifies TIDs of the timelines to separate events on different GPU streams and queues

Currently tested with trace outputs from rocprof 5.4.3.

Notes on chrome tracing:
- It normalizes the time stamps in the JSON file being visualized by subtracting the minimum time stamp from all entries.
