import argparse
import json

def adjust_events(all_df_lists, pid_rank_mult, ranks, sync_tss):
    """ Adjusts data according to global PID multiplier, GPU queues/streams and sync time stamps.

    Adjusts TIDs to reflect separate GPU queues/streams.
    """
    tid_maps = [{} for rank in ranks]

    for df_list in all_df_lists:
        for irank, df in enumerate(df_list):

            for event in df:
                # Adjust timstamp
                if "ts" in event:
                    event["ts"] = int(event["ts"]) - sync_tss[irank] + sync_tss[0]

                if "args" in event:
                    # Check stream IDs and tids
                    if "stream-id" in event["args"]:
                        newtid = int(event["args"]["queue-id"]) * 10 + int(event["args"]["stream-id"])
                        # push (pid,tid)->new_tid map to this rank's list
                        tid_maps[irank][(event["pid"], event["tid"])] = newtid
                        # update this event's tid
                        event["tid"] = str(newtid)
                    # Adjust ns times
                    if "BeginNs" in event["args"]:
                        event["args"]["BeginNs"] = int(event["args"]["BeginNs"]) - (sync_tss[irank] - sync_tss[0])*1000
                        event["args"]["EndNs"] = int(event["args"]["EndNs"]) - (sync_tss[irank] - sync_tss[0])*1000
                if event["ph"] in "stf":
                    # correct TIDs of flow events
                    pids = str(event["pid"])
                    tids = str(event["tid"])
                    if (pids,tids) in tid_maps[irank]:
                        event["tid"] = int(tid_maps[irank][(pids,tids)])

                # Process pids
                newpid = int(event["pid"]) + irank * pid_rank_mult
                if event["ph"] in "stf":
                    event["pid"] = newpid
                    event["name"] = event["name"] + " r" + str(ranks[irank])
                else:
                    event["pid"] = newpid # str


def process_sections(rank_sections_list, ranks):
    """ Get the global list of section dicts.
    
    We assume that the rank pids are already ints, not strings.
    The output sections are sorted to have lower ranks first.

    @param rank_sections_list  List of dicts mapping section names to pids for all ranks.
    @param ranks  List of rank IDs for the different processes.
    @return  Global list of section dicts for the global trace.
    @return  PID multiplier for making the PIDs unique.
    """
    max_pid = 10
    for ranksections in rank_sections_list:
        for sec_name, pid in ranksections.items():
            max_pid = max(max_pid, int(pid))

    max_pid += 1
    gl_sections = []
    rank_ids = []
    max_sort_index = 0
    for irank, rank_sections_pids in enumerate(rank_sections_list):
        for orig_name, orig_pid in rank_sections_pids.items():
            gl_sec = {"args":{}, "ph":"M", "name":"process_name", "sort_index":10}
            gl_sec["pid"] = int(orig_pid) + max_pid * irank
            gl_sec["args"]["name"] = orig_name + " r" + str(ranks[irank])
            if "Markers" in orig_name:
                gl_sec["sort_index"] = 0
            elif "CPU" in orig_name:
                gl_sec["sort_index"] = 1
            elif "COPY" in orig_name:
                gl_sec["sort_index"] = 2
            elif "GPU" in orig_name:
                gpu_id = int(orig_name[-1])
                gl_sec["sort_index"] = gpu_id + 3
            max_sort_index = max(gl_sec["sort_index"], max_sort_index)
            gl_sections.append(gl_sec)
            rank_ids.append(irank)
    
    max_sort_index += 1
    for irank, section in zip(rank_ids, gl_sections):
        section["sort_index"] = section["sort_index"] + irank * max_sort_index

    return gl_sections, max_pid


class ClockSyncMissing(Exception):
    def __init__(self, rank):
        super().__init__("Could not found clock sync event in rank {}!".format(rank))


def merge_traces(input_files):
    outdict = {"traceEvents": []}

    ranks = []
    dur_events = []
    marker_events = []
    flow_events = []
    ranks_sections = []
    sync_tss = []

    for irank, rankfile in enumerate(input_files):
        rank = int(rankfile.split("/")[-2])
        ranks.append(rank)
        rank_data = {}
        with open(rankfile, 'r') as f:
            rankfilecontents = f.read()
            rank_data = json.loads(rankfilecontents)
        outdict["otherData"] = rank_data["otherData"]
        # Get list of events
        rank_events = rank_data["traceEvents"]
        rank_section_pids = {}
        rank_pid_section_names = {}
        # Array of HIP, COPY and GPU duration events
        rank_durs_dictarr = []
        # Array of roctx marker events
        rank_markers_dictarr = []
        rank_flow_dictarr = []
        rank_min_ts = -1

        found_clock_sync = False

        for event in rank_events:
            if len(event) == 0:
                continue
            pid = int(event["pid"])
            #if "ts" in event:
            #    if rank_min_ts == -1:
            #        rank_min_ts = int(event["ts"])
            #    else:
            #        rank_min_ts = min(rank_min_ts, int(event["ts"]))
            if event["ph"] == "M":
                # First few should be names of types
                rank_section_pids[event["args"]["name"]] = pid
                rank_pid_section_names[pid] = event["args"]["name"]
            elif event["ph"] == "X":
                # This is a complete duration event. Add to resp. duration dict
                if rank_pid_section_names[pid] != "Markers and Ranges":
                    rank_durs_dictarr.append(event)
                else:
                    if event["name"] == "App_clock_sync":
                        sync_tss.append(int(event["ts"]) + int(event["dur"]))
                        print("Found clock sync on rank {}".format(rank))
                        found_clock_sync = True
                    rank_markers_dictarr.append(event)
            elif event["ph"] == "s" or event["ph"] == "t":
                # Flow event
                rank_flow_dictarr.append(event)

        rank_events = None
        rank_data = None

        if not found_clock_sync:
            raise ClockSyncMissing(rank)

        dur_events.append(rank_durs_dictarr)
        marker_events.append(rank_markers_dictarr)
        flow_events.append(rank_flow_dictarr)
        ranks_sections.append(rank_section_pids)

    print("Found ranks " + str(ranks))
    assert(len(ranks) == len(ranks_sections))
    assert(len(ranks) == len(dur_events))
    assert(len(ranks) == len(marker_events))
    assert(len(ranks) == len(flow_events))
    assert(len(ranks) == len(sync_tss))

    # Add this rank's section names to global names
    # Process names and PIDs
    gl_sections, pid_rank_multiplier = process_sections(ranks_sections, ranks)

    adjust_events((dur_events, marker_events, flow_events), pid_rank_multiplier, ranks, sync_tss)

    outdict["traceEvents"] = outdict["traceEvents"] + gl_sections
    for irank, rank in enumerate(ranks):
        # Assemble global dict
        dur_dat = dur_events[irank]
        marker_dat = marker_events[irank]
        flow_dat = flow_events[irank]
        outdict["traceEvents"] = outdict["traceEvents"] + dur_dat + marker_dat + flow_dat

    return outdict

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output_file", required=True,
                        help="JSON file for merged output")
    parser.add_argument("files", nargs='+', help="Input JSON files")
    #args, unknown = parser.parse_known_args()
    args = parser.parse_args()

    outdict = merge_traces(args.files)

    with open(args.output_file, 'w') as f:
        json.dump(outdict, f, indent=2)
