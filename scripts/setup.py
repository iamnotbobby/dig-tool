import subprocess
import sys
import os

def run_command(command, description):
    print(f"\n{description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {description} failed")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    else:
        print(f"✓ {description} completed successfully")

def main():
    if sys.platform != "win32":
        print("❌ Error: This tool is designed for Windows only.")
        print("Dig Tool requires Windows-specific dependencies and features.")
        print("Please use a Windows system to run this application.")
        sys.exit(1)
    
    print("Dig Tool Setup Script")
    print("=" * 50)
    
    development_mode = input("Do you want to install for development? (y/n): ").lower().strip()
    is_dev = development_mode in ['y', 'yes']
    
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    run_command("python -m venv env", "Creating virtual environment")
    
    if sys.platform == "win32":
        pip_path = "env\\Scripts\\pip.exe"
        python_path = "env\\Scripts\\python.exe"
    else:
        pip_path = "env/bin/pip"
        python_path = "env/bin/python"
    
    run_command(f"{pip_path} install virtualenv", "Installing virtualenv")
    
    if is_dev:
        run_command(f"{pip_path} install -e .", "Installing Dig Tool in development mode")
        print("\n🚀 Development setup complete!")
        activate_cmd = "env\\Scripts\\activate" if sys.platform == "win32" else "source env/bin/activate"
        print(f"Activate environment: {activate_cmd}")
        print(f"Run application: {python_path} main.py")
    else:
        run_command(f"{pip_path} install .", "Installing Dig Tool")
        print("\n🚀 Setup complete!")
        print(f"Run application: {python_path} main.py")

if __name__ == "__main__":
    main()
