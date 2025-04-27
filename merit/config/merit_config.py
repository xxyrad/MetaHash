# Subnet Hyperparameters
TEMPO = 360  # Number of blocks per epoch
MERIT_NETUID = 73  # NetUID of the Merit Subnet

# Ping Settings
PING_TIMEOUT = 10  # Timeout per ping attempt (seconds)
PING_RETRIES = 2   # Number of retries if ping fails
PING_SUCCESS_BONUS = 1.0  # Bonus points for successful ping
PING_FAILURE_PENALTY = 0.25  # Penalty points for failed ping after retries

# Health Scoring
HEALTH_INITIAL = 1.0  # Starting health score
HEALTH_MAX = 10.0  # Maximum achievable health score
HEALTH_INCREASE = 0.1  # Health increase per successful epoch
HEALTH_DECREASE = 0.25  # Health penalty per epoch failure

# Results Settings
EPOCH_RESULTS_DIR = "epoch_results"  # Where epoch JSONs are saved
MAX_EPOCH_FILES = 48  # Keep only last 48 epoch result files

# Recovery State Files
STATE_FILE = ".merit_state.json"
HEALTH_FILE = ".merit_health.json"

# Network Setting
NETWORK = "finney"  # Default Bittensor network
