from fastapi import APIRouter, Body
from core.instructions import global_instruction_store
from models.schema import InstructionEnvelope

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
def pop_instruction():
    """
    Pop the next pending instruction (if any). Returns null when none available.
    """
    instr = global_instruction_store.pop()
    return {"instruction": instr}
