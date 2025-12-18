
# These will not always be available, it depends on the available panoramas at each location.
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

def go_north() -> str:
    """
    Interacts with the html arrow button element that makes the agent go north, giving a new position and new panorama.

    Use this tool when you decide that it's best to go north after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_northeast() -> str:
    """
    Interacts with the html arrow button element that makes the agent go northeast, giving a new position and new panorama.

    Use this tool when you decide that it's best to go northeast after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_east() -> str:
    """
    Interacts with the html arrow button element that makes the agent go east, giving a new position and new panorama.

    Use this tool when you decide that it's best to go east after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_southeast() -> str:
    """
    Interacts with the html arrow button element that makes the agent go southeast, giving a new position and new panorama.

    Use this tool when you decide that it's best to go southeast after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()


def go_south() -> str:
    """
    Interacts with the html arrow button element that makes the agent go south, giving a new position and new panorama.

    Use this tool when you decide that it's best to go south after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_southwest() -> str:
    """
    Interacts with the html arrow button element that makes the agent go southwest, giving a new position and new panorama.

    Use this tool when you decide that it's best to go southwest after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_west() -> str:
    """
    Interacts with the html arrow button element that makes the agent go west, giving a new position and new panorama.

    Use this tool when you decide that it's best to go west after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

def go_northwest() -> str:
    """
    Interacts with the html arrow button element that makes the agent go northwest, giving a new position and new panorama.

    Use this tool when you decide that it's best to go northwest after reasoning the best course of action to solve the prompt.

    Args:
        None

    Returns:
        None
    """

    raise NotImplementedError()

