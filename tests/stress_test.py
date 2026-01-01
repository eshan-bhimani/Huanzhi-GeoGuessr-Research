import os
import sys
import random
import csv
import time
import psutil

# Add parent directory to path to allow importing toolset
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from toolset.instance import StreetViewInstance
from toolset.browser_manager import browser_manager

def msg_log(msg: str):
    # print(msg)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "stress_test_log.txt")
    with open(log_file, "a") as f:
        f.write(msg + "\n")

def load_locations(csv_path: str, count: int = 100):
    """Loads a specified number of locations from the CSV."""
    locations = []
    with open(csv_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                lat = float(row['Latitude'])
                lng = float(row['Longitude'])
                locations.append((lat, lng))
            except (ValueError, KeyError):
                continue
            if len(locations) >= count:
                break
    return locations

def run_stress_test(total_turns: int = 500, num_agents: int = 100):
    msg_log(f"--- Starting Stress Test with {num_agents} Agents ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(os.path.dirname(script_dir), "BenchmarkDataset.csv")
    locations = load_locations(csv_path, count=num_agents)
    if len(locations) < num_agents:
        msg_log(f"Warning: Only found {len(locations)} valid locations in CSV.")
        num_agents = len(locations)

    agents = [0]*num_agents
    msg_log("Initializing agents...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for i in range(num_agents):
        output_dir = os.path.join(script_dir, "agent_logs", f"agent_{i+1}")
        inst = StreetViewInstance(output_dir=output_dir)
        lat, lng = locations[i]
        inst.teleport(lat, lng)
        agents[i] = inst
        if (i + 1) % 10 == 0:
            msg_log(f"Initialized {i+1} agents...")

    msg_log(f"--- Beginning {total_turns} Random Turns ---")
    
    actions = ["pan", "tilt", "zoom", "path_and_go"]
    
    for turn in range(total_turns):
        agent_idx = random.randint(0, num_agents - 1)
        agent = agents[agent_idx]
        action = random.choice(actions)
        
        try:
            if action == "pan":
                angle = random.randint(-90, 90)
                msg_log(f"Turn {turn+1}: Agent {agent_idx+1} PAN {angle}")
                agent.pan(angle)
            
            elif action == "tilt":
                deg = random.randint(-30, 30)
                msg_log(f"Turn {turn+1}: Agent {agent_idx+1} TILT {deg}")
                agent.tilt(deg)
            
            elif action == "zoom":
                rate = random.uniform(0.5, 2.0)
                msg_log(f"Turn {turn+1}: Agent {agent_idx+1} ZOOM {rate:.2f}")
                agent.zoom(rate)
            
            elif action == "path_and_go":
                pathways = agent.get_possible_pathways()
                if pathways:
                    target = random.choice(pathways)
                    msg_log(f"Turn {turn+1}: Agent {agent_idx+1} GO {target['id']}")
                    agent.go_to_node(target['id'])
                else:
                    msg_log(f"Turn {turn+1}: Agent {agent_idx+1} PATH - No pathways found.")
            
            # Save panorama after every action
            save_path = agent.save_panorama()
            msg_log(f"Turn {turn+1}: Agent {agent_idx+1} SAVED to {save_path}")

        except Exception as e:
            msg_log(f"Turn {turn+1}: Agent {agent_idx+1} ERROR: {e}")
    before_close_memory = get_process_memory()
    msg_log("Closing all agents...")
    for agent in agents:
        if hasattr(agent, "close"):
            agent.close()
    
    browser_manager.close_all()
    after_close_memory = get_process_memory()
    msg_log("--- Stress Test Complete ---")
    msg_log(f"Memory before closing: {before_close_memory:.2f} MB")
    msg_log(f"Memory after closing: {after_close_memory:.2f} MB")

def get_process_memory():
    """Calculates the current process memory usage (RSS) in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, "agent_logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    start_time = time.time()
    try:
        run_stress_test(total_turns=500, num_agents=90)
    except KeyboardInterrupt:
        msg_log("\nTest interrupted by user. Closing browser...")
        browser_manager.close_all()
    except Exception as e:
        msg_log(f"\nAn error occurred: {e}")
        browser_manager.close_all()
    finally:
        end_time = time.time()
        duration = end_time - start_time
        memory_mb = get_process_memory()
        msg_log(f"Total execution time: {duration:.2f} seconds")
        msg_log(f"Total RAM used by process: {memory_mb:.2f} MB")
