#!/usr/bin/env python3
"""
Simple script to run the FastAPI server
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
