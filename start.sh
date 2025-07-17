#!/bin/bash

export CHROME_BIN=/opt/chrome/chrome
export PATH=$PATH:/opt/chrome/

streamlit run app.py --server.port=$PORT --server.enableCORS=false
