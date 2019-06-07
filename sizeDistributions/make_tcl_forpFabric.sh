#!/bin/bash

python3 prep-for-pFabric.py FacebookKeyValue_Sampled.txt W1
python3 prep-for-pFabric.py Google_SearchRPC.txt W2
python3 prep-for-pFabric.py Google_AllRPC.txt W3
python3 prep-for-pFabric.py Facebook_HadoopDist_All.txt W4
python3 prep-for-pFabric.py DCTCP_MsgSizeDist.txt W5

