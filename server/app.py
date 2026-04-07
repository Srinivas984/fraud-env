"""
app.py — FastAPI application with OpenEnv-compliant endpoints.
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import JSONResponse
import json

from server.models import FraudAction, FraudObservation
from server.env_logic import FraudEnvironment


app = FastAPI(
    title="Fraud Detection Environment",
    description="OpenEnv-compatible fraud detection RL environment",
    version="1.0.0"
)

# Global environment
environment = FraudEnvironment()


@app.post("/reset")
async def reset(body: dict = Body(default={})):
    """
    Reset environment and return initial observation.
    
    Args:
        body: Dict with optional 'task_name' key
    
    Returns:
        dict with "observation" and "info"
    """
    try:
        task_name = body.get("task_name", "single_fraud") if isinstance(body, dict) else "single_fraud"
        obs = await environment.reset(options={"task": task_name})
        return {
            "observation": obs.model_dump(),
            "info": {"episode_id": environment._state.episode_id, "task": task_name}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(action: FraudAction):
    """
    Process agent action.
    
    Args:
        action: FraudAction with decision field
    
    Returns:
        dict with "observation", "reward", "done", "info"
    """
    try:
        result = await environment.step(action)
        return {
            "observation": result.observation.model_dump(),
            "reward": result.reward,
            "done": result.done,
            "info": result.info
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/state")
async def get_state():
    """
    Get current episode state.
    
    Returns:
        dict with episode metadata
    """
    return {
        "episode_id": environment._state.episode_id,
        "step_count": environment._state.step_count,
        "task_name": environment._task_name,
        "step_idx": environment._step_idx,
        "total_steps": len(environment._transactions) if environment._transactions else 0
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.
    Handles reset and step messages in JSON format.
    """
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            try:
                if message.get("type") == "reset":
                    task_name = message.get("task_name", "single_fraud")
                    obs = await environment.reset(options={"task": task_name})
                    response = {
                        "type": "reset",
                        "observation": obs.model_dump(),
                        "info": {
                            "episode_id": environment._state.episode_id,
                            "task": task_name
                        }
                    }
                    await websocket.send_json(response)
                
                elif message.get("type") == "step":
                    decision = message.get("decision", "allow")
                    action = FraudAction(decision=decision)
                    result = await environment.step(action)
                    response = {
                        "type": "step",
                        "observation": result.observation.model_dump(),
                        "reward": result.reward,
                        "done": result.done,
                        "info": result.info
                    }
                    await websocket.send_json(response)
                
                else:
                    await websocket.send_json({
                        "error": "Unknown message type. Use 'reset' or 'step'."
                    })
            
            except Exception as e:
                await websocket.send_json({
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")


def main():
    """Entry point for running the server."""
    import uvicorn
    
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )


if __name__ == "__main__":
    main()