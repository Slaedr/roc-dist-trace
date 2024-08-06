Script to merge JSON traces, particularly those created by `rocprof --hip-trace --roctx-trace`.


The script primarily accomplishes:
- Re-adjusts begin times of all events according to a "clock sync" event that is required to exist in each rank's trace.
- Modifies names of timeline groups to include the rank.
- Makes the PIDs of the timeline groups unique so that different ranks remain separate.
- Modifies names of `DataFlow` events to separate those belonging to different ranks.
- Modifies TIDs of the timelines to separate events on different GPU streams and queues.

Currently tested with trace outputs from rocprof 5.4.3.

Notes on chrome tracing:
- It normalizes the time stamps in the JSON file being visualized by subtracting the minimum time stamp from all entries.

Usage
-----
The trace, on each rank, must contain a clock sync event that is guaranteed to occur at the same time on all ranks. This can be done, for example, with a set of "ping-pong" messages using MPI. While there will be some error associated with this kind of synchronization, hopefully the error is small relative to the duration of major kernels in the applications. This event much be logged with roctx with the name `App_clock_sync`.
Once such traces are available, they can be merged with `merge.py`. Use `python3 chrome-trace-merge/merge.py -h` for usage.
