#!/usr/bin/env python3
"""
SWE-Agent Trajectory Analysis Script

This script analyzes SWE-Agent trajectories to locate reproduction tests.
A reproduction test is code created by the agent to reproduce/debug the issue.
"""

import json
import os
import re
import glob
from typing import List, Optional


def locate_reproduction_code(instance_id: str) -> List[int]:
    """
    Identifies the steps in a trajectory where the agent creates reproduction tests.
    
    
    
    Args:
        instance_id (str): The ID of the instance to analyze.
        
    Returns:
        List[int]: A list of step indices where reproduction code is created.
    """
    # Find the trajectory file
    traj_file = find_trajectory_file(instance_id)
    if not traj_file:
        print(f"Warning: Could not find trajectory file for {instance_id}")
        return []
    
    # Load the trajectory
    try:
        with open(traj_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading trajectory file {traj_file}: {e}")
        return []
    
    trajectory = data.get('trajectory', [])
    reproduction_steps = []
    
    # Primary keywords that indicate reproduction code in filenames
    filename_keywords = [
        'reproduce',
        'debug',
        'test_',       
        '_test',       
        'verify',
        'check',
        'demo',
        'example',
        'issue',
        'bug',
        'minimal',
        'poc',         
        'script',
        'run_',
        'try_',
    ]
    
    # Thought patterns that indicate reproduction intent
    thought_patterns = [
        r'reproduce the issue',
        r'reproduce the bug',
        r'reproduce the problem',
        r'reproduce the error',
        r'test.*to reproduce',
        r'script to reproduce',
        r'verify the (bug|issue|problem|fix)',
        r'test the (bug|issue|problem|fix)',
        r'confirm the (bug|issue|problem|fix)',
        r'create a (test |reproduction |)script',
        r'let\'?s create a script',
        r'create.*to test',
        r'create.*to verify',
        r'demonstrate the issue',
        r'minimal.*example',
        r'test case',
    ]
    
    for step_idx, step in enumerate(trajectory):
        action = step.get('action', '')
        thought = step.get('thought', '') or ''
        thought_lower = thought.lower()
        
        # Check if this is a file creation action
        if 'str_replace_editor create' not in action:
            continue
        
        # Extract the filepath from the action
        match = re.match(r'str_replace_editor create\s+(\S+)', action)
        if not match:
            continue
        
        filepath = match.group(1)
        filename = os.path.basename(filepath)
        filename_lower = filename.lower()
        
        # Skip non-Python files
        if not filename_lower.endswith('.py'):
            continue
        
        is_reproduction = False
        
        # Check if filename contains reproduction/test keywords
        for keyword in filename_keywords:
            if keyword in filename_lower:
                is_reproduction = True
                break
        
        # Check if the thought indicates reproduction intent
        if not is_reproduction:
            for pattern in thought_patterns:
                if re.search(pattern, thought_lower):
                    is_reproduction = True
                    break
        
        # Check if it's a standalone script in /testbed root
        if not is_reproduction:
            if re.match(r'^/testbed/[^/]+\.py$', filepath):
                if filename_lower not in ['__init__.py', 'setup.py', 'conftest.py']:
                    is_reproduction = True
        
        if is_reproduction:
            reproduction_steps.append(step_idx)
    
    return reproduction_steps


def find_trajectory_file(instance_id: str) -> Optional[str]:
    """
    Find the trajectory file for a given instance ID.
    
    Args:
        instance_id: The instance ID (e.g., "django__django-11141")
        
    Returns:
        The path to the trajectory file, or None if not found.
    """
    # Get the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # First, look for trajectory folder directly in root directory
    instance_dir = os.path.join(script_dir, instance_id)
    if os.path.isdir(instance_dir):
        traj_file = os.path.join(instance_dir, f'{instance_id}.traj')
        if os.path.exists(traj_file):
            return traj_file
    
    # Also check for .traj file directly in root (alternative structure)
    traj_file = os.path.join(script_dir, f'{instance_id}.traj')
    if os.path.exists(traj_file):
        return traj_file
    
    # Fallback: Search in subdirectory structure (for backward compatibility)
    search_dirs = [
        os.path.join(script_dir, 'claude-sonnet-trajs'),
        os.path.join(script_dir, 'Qwen-2.5-Coder-Instruct-trajs'),
    ]
    
    for search_dir in search_dirs:
        # Look for the instance directory
        sub_instance_dir = os.path.join(search_dir, instance_id)
        if os.path.isdir(sub_instance_dir):
            # Find the .traj file
            traj_pattern = os.path.join(sub_instance_dir, f'{instance_id}.traj')
            if os.path.exists(traj_pattern):
                return traj_pattern
    
    return None


def get_all_instance_ids() -> List[str]:
    """
    Get all instance IDs from trajectory folders.
    
    Returns:
        List of instance IDs.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instance_ids = []
    
    # Look for trajectory folders directly in root directory
    for item in os.listdir(script_dir):
        item_path = os.path.join(script_dir, item)
        if os.path.isdir(item_path) and '__' in item:  # Instance IDs contain '__'
            traj_file = os.path.join(item_path, f'{item}.traj')
            if os.path.exists(traj_file):
                instance_ids.append(item)
    
    # If no folders found in root, fallback to subdirectory structure
    if not instance_ids:
        search_dirs = [
            os.path.join(script_dir, 'claude-sonnet-trajs'),
            os.path.join(script_dir, 'Qwen-2.5-Coder-Instruct-trajs'),
        ]
        
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                continue
            for item in os.listdir(search_dir):
                item_path = os.path.join(search_dir, item)
                if os.path.isdir(item_path):
                    # Check if there's a .traj file
                    traj_file = os.path.join(item_path, f'{item}.traj')
                    if os.path.exists(traj_file):
                        instance_ids.append(item)
    
    return sorted(instance_ids)


def generate_log_file(output_file: str = 'locate_reproduction_code.log'):
    """
    Generate the log file with reproduction code locations for all trajectories.
    
    Format:
        -input argument: str->ID of the instance
        -output: [int]-> steps where the reproduction code is created
    
    Args:
        output_file: The output log file name.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)
    
    instance_ids = get_all_instance_ids()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SWE-Agent Trajectory Analysis: Reproduction Code Locations\n")
        f.write("Method: locate_reproduction_code\n")
        f.write("=" * 80 + "\n\n")
        f.write("Format:\n")
        f.write("  -input argument: str->ID of the instance\n")
        f.write("  -output: [int]-> steps where the reproduction code is created\n")
        f.write("\n" + "-" * 80 + "\n\n")
        
        for instance_id in instance_ids:
            steps = locate_reproduction_code(instance_id)
            f.write(f"Instance ID: {instance_id}\n")
            f.write(f"Output: {steps}\n")
            
            f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("End of Report\n")
        f.write("=" * 80 + "\n")
    
    print(f"Log file generated: {output_path}")
    return output_path


def locate_search(instance_id: str) -> List[int]:
    """
    Identifies the steps in a trajectory where the model searches or navigates inside the codebase.
    

    
    Args:
        instance_id (str): The ID of the instance to analyze (e.g., "django__django-11141")
        
    Returns:
        List[int]: A list of step indices (0-based) where search/navigation occurs.
    """
    # Find the trajectory file
    traj_file = find_trajectory_file(instance_id)
    if not traj_file:
        print(f"Warning: Could not find trajectory file for {instance_id}")
        return []
    
    # Load the trajectory
    try:
        with open(traj_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading trajectory file {traj_file}: {e}")
        return []
    
    trajectory = data.get('trajectory', [])
    search_steps = []
    
    # Patterns for SWE-Agent specific search commands
    swe_agent_search_commands = [
        'find_file',
        'search_file',
        'search_dir',
    ]
    
    # Patterns for bash search/navigation commands
    # These patterns match the command at the start or after common prefixes like 'cd ... &&'
    bash_search_patterns = [
        r'\bfind\s+',           # find command
        r'\bgrep\s+',           # grep command (includes grep -n, grep -r, etc.)
        r'\bcat\s+',            # cat command to view files
        r'\bls\s+',             # ls command to list directories
        r'\bls$',               # ls command without arguments
        r'\bhead\s+',           # head command to view file start
        r'\btail\s+',           # tail command to view file end
        r'\bless\s+',           # less command for file viewing
        r'\bmore\s+',           # more command for file viewing
        r'\bwc\s+',             # word count (often used to explore files)
        r'\bawk\s+',            # awk for text processing/search
        r'\bsed\s+',            # sed for text processing/viewing
        r'\brg\s+',             # ripgrep
        r'\bag\s+',             # the silver searcher
        r'\bgit\s+show\s+',     # git show for viewing file content
        r'\bgit\s+log\s+',      # git log for viewing history
        r'\bgit\s+diff\s+',     # git diff for viewing changes
    ]
    
    # Pattern for editor view command (navigation)
    editor_view_pattern = r'str_replace_editor\s+view\s+'
    
    # Patterns that indicate code modification (NOT search)
    code_modification_patterns = [
        r'str_replace_editor\s+str_replace\s+',
        r'str_replace_editor\s+create\s+',
        r'str_replace_editor\s+insert\s+',
        r'str_replace_editor\s+undo_edit\s+',
    ]
    
    for step_idx, step in enumerate(trajectory):
        action = step.get('action', '') or ''
        thought = step.get('thought', '') or ''
        
        # First, check if this is a code modification action (NOT a search)
        is_modification = False
        for pattern in code_modification_patterns:
            if re.search(pattern, action):
                is_modification = True
                break
        
        if is_modification:
            continue
        
        is_search_step = False
        
        # Check for SWE-Agent specific search commands
        for cmd in swe_agent_search_commands:
            if action.startswith(cmd) or f' {cmd}' in action:
                is_search_step = True
                break
        
        if not is_search_step:
            # Check for editor view command (navigation)
            if re.search(editor_view_pattern, action):
                is_search_step = True
        
        if not is_search_step:
            # Check for bash search/navigation commands
            for pattern in bash_search_patterns:
                if re.search(pattern, action):
                    is_search_step = True
                    break
        
        if is_search_step:
            search_steps.append(step_idx)
    
    return search_steps



def generate_search_log_file(output_file: str = 'locate_search.log'):
    """
    Generate the log file with search/navigation locations for all trajectories.
    
    Format:
        -Input argument: str->ID of the instance
        -Output: [int] -> steps where the model conducts search/navigation
    
    Args:
        output_file: The output log file name.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)
    
    instance_ids = get_all_instance_ids()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SWE-Agent Trajectory Analysis: Search/Navigation Locations\n")
        f.write("Method: locate_search\n")
        f.write("=" * 80 + "\n\n")
        f.write("Format:\n")
        f.write("  -Input argument: str->ID of the instance\n")
        f.write("  -Output: [int] -> steps where the model conducts search/navigation\n")
        f.write("\n" + "-" * 80 + "\n\n")
        
        for instance_id in instance_ids:
            steps = locate_search(instance_id)
            f.write(f"Instance ID: {instance_id}\n")
            f.write(f"Output: {steps}\n")
            f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("End of Report\n")
        f.write("=" * 80 + "\n")
    
    print(f"Log file generated: {output_path}")
    return output_path


def locate_tool_use(instance_id: str) -> dict:
    """
    Identifies and counts tool uses in a trajectory.
    
    
    Args:
        instance_id (str): The ID of the instance to analyze (e.g., "django__django-11141")
        
    Returns:
        dict: A dictionary where keys are tool names and values are the count of times each tool is called.
    """
    # Find the trajectory file
    traj_file = find_trajectory_file(instance_id)
    if not traj_file:
        print(f"Warning: Could not find trajectory file for {instance_id}")
        return {}
    
    # Load the trajectory
    try:
        with open(traj_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading trajectory file {traj_file}: {e}")
        return {}
    
    trajectory = data.get('trajectory', [])
    tool_counts = {}
    
    # str_replace_editor commands
    editor_commands = ['view', 'create', 'str_replace', 'insert', 'undo_edit']
    
    # Common shell commands to track
    shell_commands = [
        'python', 'python3', 'pip', 'pip3',
        'cd', 'ls', 'cat', 'head', 'tail', 'less', 'more',
        'grep', 'find', 'sed', 'awk', 'wc',
        'echo', 'touch', 'mkdir', 'rm', 'mv', 'cp',
        'git', 'pytest', 'tox', 'make',
        'bash', 'sh', 'source', 'export',
    ]
    
    for step in trajectory:
        action = step.get('action', '') or ''
        
        if not action:
            continue
        
        # Check for str_replace_editor commands
        if action.startswith('str_replace_editor'):
            # Extract the command type (view, create, str_replace, insert, undo_edit)
            for cmd in editor_commands:
                pattern = rf'str_replace_editor\s+{cmd}\b'
                if re.search(pattern, action):
                    tool_name = f'str_replace_editor_{cmd}'
                    tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                    break
        else:
            # It's a shell command - identify the primary command
            # Handle cases like "cd /path && command" or "command1 | command2"
            # Also handle direct commands like "python script.py"
            
            # First, try to identify the most relevant command
            action_stripped = action.strip()
            
            # Check for compound commands (cd && command)
            if ' && ' in action_stripped:
                # Split and analyze each part
                parts = action_stripped.split(' && ')
                for part in parts:
                    part = part.strip()
                    cmd_found = False
                    for shell_cmd in shell_commands:
                        pattern = rf'^{shell_cmd}\b|^\/{shell_cmd}\b'
                        if re.search(pattern, part):
                            tool_counts[shell_cmd] = tool_counts.get(shell_cmd, 0) + 1
                            cmd_found = True
                            break
                    if not cmd_found and part:
                        # Extract first word as command
                        first_word = part.split()[0] if part.split() else ''
                        if first_word and not first_word.startswith('-'):
                            # Remove path prefix if present
                            first_word = os.path.basename(first_word)
                            tool_counts[first_word] = tool_counts.get(first_word, 0) + 1
            else:
                # Single command or piped command - get first command
                # Handle pipes
                if ' | ' in action_stripped:
                    action_stripped = action_stripped.split(' | ')[0].strip()
                
                cmd_found = False
                for shell_cmd in shell_commands:
                    pattern = rf'^{shell_cmd}\b|^\/{shell_cmd}\b'
                    if re.search(pattern, action_stripped):
                        tool_counts[shell_cmd] = tool_counts.get(shell_cmd, 0) + 1
                        cmd_found = True
                        break
                
                if not cmd_found and action_stripped:
                    # Extract first word as command
                    first_word = action_stripped.split()[0] if action_stripped.split() else ''
                    if first_word and not first_word.startswith('-'):
                        # Remove path prefix if present
                        first_word = os.path.basename(first_word)
                        tool_counts[first_word] = tool_counts.get(first_word, 0) + 1
    
    return tool_counts


def generate_tool_use_log_file(output_file: str = 'locate_tool_use.log'):
    """
    Generate the log file with tool use counts for all trajectories.
    
    Format:
        -Input argument: str->ID of the instance
        -Output: dictionary -> the key will be the tool name, and the value will be how many times the tool is called.
    
    Args:
        output_file: The output log file name.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, output_file)
    
    instance_ids = get_all_instance_ids()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SWE-Agent Trajectory Analysis: Tool Use Analysis\n")
        f.write("Method: locate_tool_use\n")
        f.write("=" * 80 + "\n\n")
        f.write("Format:\n")
        f.write("  -Input argument: str->ID of the instance\n")
        f.write("  -Output: dictionary -> the key will be the tool name, and the value will be how many times the tool is called.\n")
        f.write("\n" + "-" * 80 + "\n\n")
        
        for instance_id in instance_ids:
            tool_counts = locate_tool_use(instance_id)
            f.write(f"Instance ID: {instance_id}\n")
            f.write(f"Output: {tool_counts}\n")            
            f.write("\n")
        
        f.write("-" * 80 + "\n")
        f.write("End of Report\n")
        f.write("=" * 80 + "\n")
    
    print(f"Log file generated: {output_path}")
    return output_path


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == '--search':
            # Generate search log
            generate_search_log_file()
        elif command == '--reproduction':
            # Generate reproduction log
            generate_log_file()
        elif command == '--tool-use':
            # Generate tool use log
            generate_tool_use_log_file()
        elif command == '--all':
            # Generate all logs
            generate_log_file()
            generate_search_log_file()
            generate_tool_use_log_file()
        else:
            # Assume it's an instance_id - show all analyses
            instance_id = command
            
            print(f"\n=== Analysis for Instance: {instance_id} ===\n")
            
            # Reproduction code analysis
            repro_steps = locate_reproduction_code(instance_id)
            print(f"Reproduction code steps: {repro_steps}")
            for step_idx in repro_steps:
                details = get_step_details(instance_id, step_idx)
                print(f"  Step {step_idx}: {details.get('filename', 'N/A')}")
            
            print()
            
            # Search/navigation analysis
            search_steps = locate_search(instance_id)
            print(f"Search/navigation steps: {search_steps}")
            for step_idx in search_steps[:10]:  # Show first 10
                details = get_search_step_details(instance_id, step_idx)
                print(f"  Step {step_idx} [{details.get('action_type', 'N/A')}]: {details.get('target', 'N/A')[:60]}")
            if len(search_steps) > 10:
                print(f"  ... and {len(search_steps) - 10} more steps")
            
            print()
            
            # Tool use analysis
            tool_counts = locate_tool_use(instance_id)
            print(f"Tool use counts: {tool_counts}")
            total = sum(tool_counts.values()) if tool_counts else 0
            print(f"  Total tool calls: {total}")
    else:
        # Generate all log files by default
        print("Generating log files for all instances...")
        generate_log_file()
        generate_search_log_file()
        generate_tool_use_log_file()


if __name__ == '__main__':
    main()
