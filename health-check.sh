#!/bin/bash

# health-check.sh - Comprehensive health check for all services

set -e

PORT=${PORT:-6080}

echo "Running health check on port $PORT..."

# Check if supervisord is running
if ! pgrep supervisord > /dev/null; then
    echo "ERROR: supervisord not running"
    exit 1
fi

# Check if Xvfb is running
if ! pgrep Xvfb > /dev/null; then
    echo "ERROR: Xvfb not running"
    exit 1
fi

# Check if x11vnc is running
if ! pgrep x11vnc > /dev/null; then
    echo "ERROR: x11vnc not running"
    exit 1
fi

# Check if noVNC is listening on the port
if ! netcat -z localhost $PORT; then
    echo "ERROR: noVNC not listening on port $PORT"
    exit 1
fi

# Try to connect to the HTTP endpoint
if ! curl -f -s "http://localhost:$PORT/" > /dev/null 2>&1; then
    # Try alternative endpoints
    if ! curl -f -s "http://localhost:$PORT/vnc.html" > /dev/null 2>&1; then
        if ! curl -f -s "http://localhost:$PORT/vnc_lite.html" > /dev/null 2>&1; then
            echo "ERROR: HTTP endpoints not responding"
            exit 1
        fi
    fi
fi

echo "All health checks passed"
exit 0
