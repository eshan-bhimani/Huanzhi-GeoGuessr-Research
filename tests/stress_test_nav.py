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
    """Prints a message to the terminal."""
    # print(msg)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "stress_test_nav_log.txt")
    with open(log_file, "a") as f:
        f.write(msg + "\n")

def get_process_memory():
    """Calculates the current process memory usage (RSS) in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

class NavigationStressTester:
    def __init__(self, num_agents: int = 100, csv_path: str = "BenchmarkDataset.csv"):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)
        
        if csv_path == "BenchmarkDataset.csv":
            csv_path = os.path.join(root_dir, "BenchmarkDataset.csv")
            
        self.num_agents = num_agents
        self.csv_path = csv_path
        self.log_dir = os.path.join(script_dir, "agent_logs_nav")
        self.locations = self._load_locations(num_agents)
        self.agents = []
        self.stats = {"success": 0, "failure": 0, "no_pathway": 0}
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def _load_locations(self, count):
        locations = []
        if not os.path.exists(self.csv_path):
            msg_log(f"Error: {self.csv_path} not found.")
            return []
            
        with open(self.csv_path, mode='r', encoding='utf-8') as f:
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

    def initialize_pool(self):
        """Initializes 100 agents (pages) in the single browser instance."""
        msg_log(f"--- Initializing {self.num_agents} Agents in a Single Browser Pool ---")
        start_mem = get_process_memory()
        
        for i in range(len(self.locations)):
            output_dir = os.path.join(self.log_dir, f"agent_{i+1}")
            try:
                inst = StreetViewInstance(output_dir=output_dir)
                lat, lng = self.locations[i]
                inst.teleport(lat, lng)
                
                # Verify initial accuracy
                save_path = inst.save_panorama()
                if save_path and not save_path.startswith("Error"):
                    self.stats["success"] += 1
                else:
                    self.stats["failure"] += 1
                
                self.agents.append(inst)
            except Exception as e:
                msg_log(f"Error initializing Agent {i+1}: {e}")
                self.stats["failure"] += 1
            
            if (i + 1) % 10 == 0:
                current_mem = get_process_memory()
                msg_log(f"Initialized {i+1} agents... (Current RAM: {current_mem:.2f} MB)")

        end_mem = get_process_memory()
        msg_log(f"Pool Initialization Complete. RAM used for 100 agents: {end_mem - start_mem:.2f} MB")

    def run_simulation(self, turns_per_agent: int = 1):
        """Runs the simulation by looping through agents sequentially."""
        msg_log(f"--- Running Interleaved Simulation ({turns_per_agent} turns each) ---")
        start_time = time.time()
        
        for turn in range(turns_per_agent):
            msg_log(f"\nStarting Global Turn {turn+1}...")
            for i, inst in enumerate(self.agents):
                try:
                    # Move logic
                    pathways = inst.get_possible_pathways()
                    if pathways:
                        target = random.choice(pathways)
                        result = inst.go_to_node(target['id'])
                        
                        if "Navigated to" in result:
                            # Verify accuracy with a save
                            save_path = inst.save_panorama()
                            if save_path and not save_path.startswith("Error"):
                                self.stats["success"] += 1
                            else:
                                msg_log(f"Agent {i+1} Save FAILED after move.")
                                self.stats["failure"] += 1
                        else:
                            msg_log(f"Agent {i+1} Move FAILED: {result}")
                            self.stats["failure"] += 1
                    else:
                        self.stats["no_pathway"] += 1
                except Exception as e:
                    msg_log(f"Agent {i+1} Turn {turn+1} ERROR: {e}")
                    self.stats["failure"] += 1
                    
                if (i + 1) % 20 == 0:
                    msg_log(f"Turn {turn+1}: Progressing through agent {i+1}...")

        duration = time.time() - start_time
        msg_log(f"\n--- Simulation Complete in {duration:.2f}s ---")
        msg_log(f"Accuracy Stats: {self.stats['success']} Successes, {self.stats['failure']} Failures, {self.stats['no_pathway']} No Pathways found.")
        
        if self.stats["failure"] == 0 and self.stats["success"] > 0:
            msg_log("ACCURACY TEST PASSED: All calls were accurate and successful.")
        else:
            msg_log(f"ACCURACY TEST COMPLETED with {self.stats['failure']} failures.")

    def cleanup(self):
        msg_log("Cleaning up browser resources...")
        for inst in self.agents:
            inst.close()
        browser_manager.close_all()
        msg_log("Cleanup complete.")

if __name__ == "__main__":
    # Configure for 100 agents in a single pool (1 run)
    num_agents = 90
    turns_per_agent = 4 # Keep it short for a quick accurate-call validation across the pool
    
    tester = NavigationStressTester(num_agents=num_agents)
    
    try:
        tester.initialize_pool()
        tester.run_simulation(turns_per_agent=turns_per_agent)
    except KeyboardInterrupt:
        msg_log("\nSimulation interrupted by user.")
    finally:
        tester.cleanup()
    
    final_mem = get_process_memory()
    msg_log(f"Final RAM used: {final_mem:.2f} MB")
