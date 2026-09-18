"""REST API Router for Decarbonization Scenario Simulator."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.simulator import LeverDefinition, SimulationRequest, SimulationResponse
from app.services.scenario_simulator import ScenarioSimulator

router = APIRouter()


@router.get("/levers", response_model=list[LeverDefinition])
async def get_simulator_levers(
    session: AsyncSession = Depends(get_db),
) -> list[LeverDefinition]:
    """Retrieve catalog of standard enterprise decarbonization interventions."""
    simulator = ScenarioSimulator(session)
    return simulator.get_lever_catalog()


@router.post("/simulate", response_model=SimulationResponse)
async def run_decarbonization_simulation(
    request: SimulationRequest,
    session: AsyncSession = Depends(get_db),
) -> SimulationResponse:
    """Simulate what-if decarbonization levers and compute MACC ROI rankings."""
    simulator = ScenarioSimulator(session)
    return await simulator.simulate(request)
