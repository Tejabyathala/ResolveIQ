
import sys
from pathlib import Path

# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.config_loader import load_business_rules


rules = load_business_rules()

print("\nPRIORITY CONFIGURATION")
print("======================")
print(rules["priority"])

print("\nTEAM ROUTING CONFIGURATION")
print("=========================")
print(rules["routing"])

print("\nSLA CONFIGURATION")
print("=================")
print(rules["sla"])
