Script to merge JSON traces, particularly those created by `rocprof --hip-trace --roctx-trace`.

For each file, we need to change the pids of the event types. Each file will have "Markers and Ranges", "CPU HIP API", "COPY" and "GPU0", "GPU4" or similar.
In the final merged file, we want the union of all event types, where duplicates are renamed to include their rank. Eg., with two ranks 0 and 4, we would have
"Markers and Ranges r0", "CPU HIP API r0", "COPY r0" and "GPU0 r0", "GPU4 r0",
"Markers and Ranges r4", "CPU HIP API r4", "COPY r4" and "GPU0 r4", "GPU4 r4".
Each of these is assigned a unique pid.
For each event in a file, we need to transform the pid to be the one corresponding to the event-type in the current rank.
