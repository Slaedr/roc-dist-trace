#!/usr/bin/env python3

import os
import json
import unittest
from context import chrome_trace_merge
from chrome_trace_merge.merge import merge_traces

max_name_len = 100


class MergeTest(unittest.TestCase):

    def setUp(self):
        pass

    def compare_traces(self, testdir, ranks):
        inputfiles = [testdir + "/" + str(rank) + "/results.json" for rank in ranks]
        ref_outputfile = testdir + "/merged.json"
        ref_outdict = {}
        with open(ref_outputfile, 'r') as f:
            outfiles = f.read()
            ref_outdict = json.loads(outfiles)

        outdict = merge_traces(inputfiles)

        nevents = len(outdict["traceEvents"])
        print("No. events/sections in output is {} and that for ref is {}.".format(
            nevents, len(ref_outdict["traceEvents"]))
              )
        self.assertTrue(nevents == len(ref_outdict["traceEvents"]))
        for i in range(nevents):
            # Adjust for name and args truncation
            refev = ref_outdict["traceEvents"][i]
            refev["name"] = refev["name"][:max_name_len]
            if "args" in refev:
                if "Name" in refev["args"]:
                    refev["args"]["Name"] = refev["args"]["Name"][:max_name_len]
                if "args" in refev["args"]:
                    refev["args"]["args"] = refev["args"]["args"][:max_name_len]
            # Compare
            if outdict['traceEvents'][i] != ref_outdict["traceEvents"][i]:
                print("Event {} with name {} has mismatch!".format(i, outdict["traceEvents"][i]["name"]))
                print(outdict['traceEvents'][i])
                print(ref_outdict['traceEvents'][i])
            self.assertTrue(outdict['traceEvents'][i] == ref_outdict["traceEvents"][i])
        self.assertTrue(outdict["otherData"] == ref_outdict["otherData"])

    def test_0(self):
        testdir = "./test0"
        if not os.path.isdir(testdir):
            testdir = "./test/test0"
        self.compare_traces(testdir, [0, 4, 8])

    def test_1(self):
        testdir = "./test1"
        if not os.path.isdir(testdir):
            testdir = "./test/test1"
        self.compare_traces(testdir, [0, 1, 2, 8, 103])

    def test_2(self):
        testdir = "./test_neg"
        if not os.path.isdir(testdir):
            testdir = "./test/test_neg"
        self.compare_traces(testdir, [0, 1])


if __name__ == "__main__":
    unittest.main()
