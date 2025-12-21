from fastapi import APIRouter, Body, Query
from backend.state import global_instruction_store
from backend.models import InstructionEnvelope

router = APIRouter()


@router.post("/instruction/push")
def push_instruction(payload: dict = Body(...)):
    """
    Push an instruction for the frontend to consume.
    Overwrites any pending instruction.
    """
    global_instruction_store.push(payload)
    return {"status": "ok"}


@router.get("/instruction/next", response_model=InstructionEnvelope)
def pop_instruction(timeout: float = Query(0.0, ge=0.0, le=60.0)):
    """
    Pop the next pending instruction (if any). Returns null when none available.
    If timeout > 0, waits up to timeout seconds for a new instruction.
    """
    if timeout > 0:
        instr = global_instruction_store.wait_for_instruction(timeout)
    else:
        instr = global_instruction_store.pop()
    return {"instruction": instr}


