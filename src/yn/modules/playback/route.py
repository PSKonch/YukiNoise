"""

# 1. Core playback
POST /playback/start
POST /playback/progress     # { session_id, position, duration }
POST /playback/pause
POST /playback/resume
POST /playback/stop
POST /playback/change_position  # { session_id, position }

# 2. State (for clients)
GET  /playback/current      # returns current playback state (session_id, position, duration, is_paused)

"""
