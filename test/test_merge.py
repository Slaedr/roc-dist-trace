#!/usr/bin/env python3

import os
import json
import unittest
from context import chrome_trace_merge
from chrome_trace_merge.merge import merge_traces


class MergeTest(unittest.TestCase):

    def setUp(self):
        pass

    def compare_traces(self, testdir):
        inputfiles = [testdir + "/0/results.json", testdir + "/4/results.json", testdir + "/8/results.json"]
        ref_outputfile = testdir + "/merged.json"
        ref_outdict = {}
        with open(ref_outputfile, 'r') as f:
            outfiles = f.read()
            ref_outdict = json.loads(outfiles)

        outdict = merge_traces(inputfiles)

        nevents = len(outdict["traceEvents"])
        print("No. events/sections in output is " + str(nevents))
        self.assertTrue(nevents == len(ref_outdict["traceEvents"]))
        for i in range(nevents):
            if outdict['traceEvents'][i] != ref_outdict["traceEvents"][i]:
                print("Event {} with name {} has mismatch!".format(i, outdict["traceEvents"][i]["name"]))
            self.assertTrue(outdict['traceEvents'][i] == ref_outdict["traceEvents"][i])
        self.assertTrue(outdict["otherData"] == ref_outdict["otherData"])

    def test_0(self):
        testdir = "./test0"
        if not os.path.isdir(testdir):
            testdir = "./test/test0"
        self.compare_traces(testdir)


if __name__ == "__main__":
    unittest.main()
