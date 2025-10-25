"""
YAML validation and duplicate field removal
"""

import re
import yaml


def validate_yaml_content(content: str, filepath: str = "manifest") -> bool:
    """
    Validate YAML content and check for duplicate keys.
    Returns True if valid, False otherwise.
    """
    try:
        # Try to parse the YAML
        parsed = yaml.safe_load(content)
        
        # Check for common issues
        lines = content.split('\n')
        field_counts = {}
        current_section = None
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track sections
            if stripped and not stripped.startswith('#') and ':' in stripped:
                if not line.startswith(' '):  # Top-level field
                    current_section = 'top_level'
                
                # Count field occurrences (simple check)
                field_name = stripped.split(':')[0].strip('- ')
                key = f"{current_section}:{field_name}"
                field_counts[key] = field_counts.get(key, 0) + 1
        
        # Report duplicates
        has_duplicates = False
        for key, count in field_counts.items():
            if count > 1:
                section, field = key.split(':', 1)
                print(f"  ⚠️  Warning: Field '{field}' appears {count} times in {section}")
                has_duplicates = True
        
        if has_duplicates:
            print(f"  ℹ️  Note: Some duplicate fields were detected but may be intentional (e.g., in lists)")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"  ❌ YAML validation error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Validation error in {filepath}: {e}")
        return False


def remove_duplicate_fields(content: str) -> str:
    """
    Remove duplicate fields in YAML content while preserving structure.
    For each unique field name within a context (architecture, top-level, etc.),
    keeps only the first occurrence and removes duplicates.
    
    Smart detection:
    - Tracks context: top-level, within architecture blocks, within other sections
    - Preserves list items (multiple '- Architecture:' is intentional)
    - Only removes actual duplicates (same field name in same context)
    - Each architecture block is tracked separately
    """
    lines = content.split('\n')
    result_lines = []
    
    # Track field occurrences per context
    # Format: {context_key: {field_name: count}}
    field_tracker = {}
    
    # Track current context
    current_arch = None
    current_section = None
    current_list_item_idx = 0  # Track which list item we're in
    in_installer_list = False
    
    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            result_lines.append(line)
            continue
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        
        # Detect Installers section
        if stripped == 'Installers:':
            in_installer_list = True
            current_list_item_idx = 0
            result_lines.append(line)
            continue
        
        # Parse field name
        if ':' in stripped:
            field_match = stripped.split(':', 1)[0].strip('- ')
            field_name = field_match
            is_list_start = stripped.startswith('- ')
            
            # Detect new list item in Installers section
            if in_installer_list and is_list_start and field_name == 'Architecture':
                current_list_item_idx += 1
                arch_match = stripped.split(':', 1)[1].strip()
                current_arch = arch_match
                # Reset field tracker for this new architecture block
                context_key = f"arch_block:{current_list_item_idx}:{current_arch}"
                field_tracker[context_key] = {}
                result_lines.append(line)
                continue
            
            # Detect context changes (exit Installers section)
            if indent == 0 and not stripped.startswith('- '):
                in_installer_list = False
                current_arch = None
                current_section = field_name
                current_list_item_idx = 0
            
            # Build context key
            if current_arch and in_installer_list:
                # Inside a specific architecture block
                context_key = f"arch_block:{current_list_item_idx}:{current_arch}"
            elif is_list_start:
                # List item at this indent level (e.g., AppsAndFeaturesEntries)
                context_key = f"list_item:{indent}:{line_idx}"
            elif current_section:
                context_key = f"section:{current_section}:{indent}"
            else:
                context_key = f"top:{indent}"
            
            # Check if this is a duplicate (but not for list-starting fields like '- Architecture')
            if not (is_list_start and field_name == 'Architecture'):
                # Initialize tracker for this context
                if context_key not in field_tracker:
                    field_tracker[context_key] = {}
                
                # Check if field already seen in this context
                if field_name in field_tracker[context_key]:
                    # Duplicate detected - skip this line
                    field_tracker[context_key][field_name] += 1
                    context_desc = context_key.split(':')[0]
                    if current_arch:
                        context_desc = f"{current_arch} architecture"
                    print(f"  🧹 Removed duplicate '{field_name}' in {context_desc} (occurrence #{field_tracker[context_key][field_name]})")
                    continue
                else:
                    # First occurrence - track it
                    field_tracker[context_key][field_name] = 1
            
        result_lines.append(line)
    
    # Clean up multiple consecutive blank lines
    result = '\n'.join(result_lines)
    result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
    
    return result
