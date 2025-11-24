# Necessary for toolset functions:
# Semantic Name (e.g. calculate_mortgage vs. calc_m)
# Type Hints (e.g. count: int)
# Docstring Logic (Explains what the tool does and when to use it)
# Docstring Args (Explains constraints [e.g., "Must be YYYY-MM-DD" or "Must be in USD"])

from typing import Union # Union is used to have tuples as a typecast for function arguments

def look_north_south_east_west() -> str:
    """
    Orients itself using the compass html element. Zooms out, then clicks through the compass in the directions of all 4 cardinal directions to get a complete 360 degree view of your environment.
    
    Use this tool whenever you move to a new location so that you can better understand your environment and decide the best action to take.

    Args:
        None

    Returns:
        str: A description of the environment, noting any points of interest that could help the agent decide the best action to take and correctly respond to the prompt.
    """
    raise NotImplementedError()

