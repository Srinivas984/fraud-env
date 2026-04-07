#!/usr/bin/env python3
"""
Final submission verification for OpenEnv Fraud Detection Environment.
Run this to verify all components are working correctly.
"""

import os
import sys

def main():
    print("=" * 70)
    print("FINAL SUBMISSION VERIFICATION - OPENENV FRAUD DETECTION".center(70))
    print("=" * 70)
    
    # 1. File structure
    print("\n[1] FILE STRUCTURE VERIFICATION")
    files = [
        'requirements.txt',
        'Dockerfile',
        'openenv.yaml',
        'README.md',
        'inference.py',
        'server/app.py',
        'server/models.py',
        'server/env_logic.py',
        'server/tasks.py',
        'server/graders.py'
    ]
    
    all_present = True
    for f in files:
        exists = os.path.exists(f)
        status = "✓" if exists else "✗"
        print(f"    {status} {f}")
        if not exists:
            all_present = False
    
    # 2. Import test
    print("\n[2] PYTHON IMPORT TEST")
    try:
        from server import app, models, env_logic, tasks, graders
        print("    ✓ All modules import successfully")
    except Exception as e:
        print(f"    ✗ Import failed: {e}")
        return False
    
    # 3. Key classes
    print("\n[3] PYDANTIC MODELS VERIFICATION")
    models_to_check = [
        ('Transaction', models.Transaction),
        ('UserProfile', models.UserProfile),
        ('FraudAction', models.FraudAction),
        ('FraudObservation', models.FraudObservation)
    ]
    for name, cls in models_to_check:
        print(f"    ✓ {name}")
    
    # 4. Task registry
    print("\n[4] TASK REGISTRY VERIFICATION")
    for task_name, task_info in tasks.TASK_REGISTRY.items():
        print(f"    ✓ {task_name} (difficulty: {task_info['difficulty']})")
    
    # 5. Reward table
    print("\n[5] REWARD TABLE VERIFICATION") 
    expected_keys = [
        ('fraud', 'block'),
        ('fraud', 'flag'),
        ('fraud', 'allow'),
        ('legit', 'allow'),
        ('legit', 'flag'),
        ('legit', 'block')
    ]
    for key in expected_keys:
        if key in graders.REWARD_TABLE:
            value = graders.REWARD_TABLE[key]
            print(f"    ✓ {key} → {value:+.1f}")
        else:
            print(f"    ✗ {key} MISSING")
            return False
    
    # 6. Endpoint verification
    print("\n[6] FASTAPI ENDPOINTS CHECK")
    app_instance = app.app
    routes = [
        ("/reset", "POST"),
        ("/step", "POST"),
        ("/state", "GET"),
        ("/health", "GET"),
        ("/ws", "WebSocket")
    ]
    
    for route, method in routes:
        found = False
        for r in app_instance.routes:
            if hasattr(r, 'path') and r.path == route:
                found = True
                break
        status = "✓" if found else "○"
        print(f"    {status} {method:8} {route}")
    
    # 7. File metrics
    print("\n[7] CODE METRICS")
    total_lines = 0
    for f in ['server/app.py', 'server/env_logic.py', 'server/tasks.py', 'server/graders.py']:
        if os.path.exists(f):
            size = os.path.getsize(f)
            try:
                with open(f, encoding='utf-8', errors='ignore') as file:
                    lines = len(file.readlines())
            except:
                lines = 0
            print(f"    {f:25} {lines:4d} lines ({size:6d} bytes)")
            total_lines += lines
    
    print(f"\n    Total project code: {total_lines} lines")
    
    # 8. Requirements check
    print("\n[8] DEPENDENCIES CHECK")
    with open('requirements.txt') as f:
        deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"    ✓ {len(deps)} dependencies specified:")
    for dep in deps[:5]:
        print(f"      • {dep}")
    if len(deps) > 5:
        print(f"      ... and {len(deps)-5} more")
    
    # 9. Final status
    print("\n" + "=" * 70)
    if all_present:
        print("✓ SUBMISSION READY FOR HACKATHON SUBMISSION".center(70))
        print("\nNext steps:")
        print("  1. git add .")
        print("  2. git commit -m 'Ready for OpenEnv hackathon'")
        print("  3. Push to competition repository")
        print("\nFor judges:")
        print("  1. docker build -t fraud-detection .")
        print("  2. docker run -p 7860:7860 fraud-detection")
        print("  3. python inference.py single_fraud")
    else:
        print("✗ SUBMISSION INCOMPLETE - MISSING FILES".center(70))
        return False
    
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
