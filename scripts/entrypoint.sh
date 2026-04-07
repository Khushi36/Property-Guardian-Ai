#!/bin/sh

# Start FastAPI in the background
echo "Starting FastAPI backend..."
python main.py &

# Start Streamlit in the foreground
echo "Starting Streamlit frontend..."
streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
