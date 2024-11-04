import subprocess

# Define your condition
condition = True  # Set this to whatever condition you need to check

if condition:
    print("Condition met, launching secondary script...")
    subprocess.run(["python", "secondary_script.py"])
else:
    print("Condition not met, skipping secondary script.")
