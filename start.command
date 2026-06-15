#!/bin/bash
cd "$(dirname "$0")"
lsof -ti tcp:8767 | xargs kill -9 2>/dev/null
sleep 0.3
python3 server.py &
sleep 0.8
open "http://localhost:8767"
