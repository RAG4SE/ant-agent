#!/usr/bin/env python3
"""
Test script for the example.py - 验证功能是否正常工作
"""

import subprocess
import sys
import os
from pathlib import Path

def test_example():
    """Test the example.py script."""
    
    print("🧪 Testing Ant Agent Example...")
    
    # Change to ant-agent directory
    ant_agent_dir = Path("/Users/mac/repo/ant-agent")
    os.chdir(ant_agent_dir)
    
    try:
        # Run the example script
        print("🚀 Running example.py...")
        result = subprocess.run(
            [sys.executable, "example.py"],
            capture_output=True,
            text=True,
            timeout=60  # 1分钟超时
        )
        
        print("📊 Return code:", result.returncode)
        print("📤 STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("📤 STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Example executed successfully!")
            
            # 检查是否产生了轨迹文件
            trajectory_file = Path("trajectory.json")
            if trajectory_file.exists():
                print(f"📊 Trajectory file created: {trajectory_file}")
                print(f"📏 File size: {trajectory_file.stat().st_size} bytes")
            else:
                print("⚠️  No trajectory file found")
                
            return True
        else:
            print("❌ Example failed!")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Example timed out after 60 seconds!")
        return False
    except Exception as e:
        print(f"❌ Error running example: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_example()
    sys.exit(0 if success else 1)