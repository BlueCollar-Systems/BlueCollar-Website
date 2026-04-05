
#!/usr/bin/env python3
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from repo_context_builder_core import main_with_preset

PRESET = {
  "title": "LLM Context Pack \u2014 BlueCollar Website",
  "config_paths": [
    "README.md",
    "RELEASE_CHECKLIST.md",
    "robots.txt",
    "sitemap.xml",
    "_headers",
    "_redirects",
    ".gitignore",
    ".cfignore"
  ],
  "script_paths": [
    "0build_master_output.py",
    "0build_master_output.cmd"
  ],
  "source_roots": [
    "."
  ],
  "test_roots": [],
  "dependency_files": [
    "package.json"
  ],
  "expected_files": {
    "expected_everywhere": [
      "index.html",
      "styles.css",
      "README.md"
    ],
    "expected_some_envs": [
      "_headers",
      "_redirects",
      ".github/workflows"
    ]
  },
  "exclude_dir_names": [
    ".git",
    "dev_logs",
    "node_modules",
    "dist",
    "build"
  ],
  "exclude_file_names": [],
  "exclude_suffixes": [],
  "include_extensions": [
    ".bat",
    ".c",
    ".cfg",
    ".cmake",
    ".cmd",
    ".conf",
    ".cpp",
    ".css",
    ".dart",
    ".go",
    ".gradle",
    ".h",
    ".hpp",
    ".htm",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".kt",
    ".kts",
    ".lua",
    ".md",
    ".php",
    ".plist",
    ".ps1",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scss",
    ".sh",
    ".sql",
    ".svg",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml"
  ],
  "tree_full_depth_roots": [
    ".github"
  ],
  "tree_shallow_depth_roots": {
    ".git": 1
  },
  "default_tree_depth": 2,
  "navigation_grep_patterns": [
    "\\bhref=",
    "\\bwindow\\.location\\b",
    "\\bfetch\\("
  ],
  "navigation_roots": [
    "."
  ],
  "check_commands": []
}

if __name__ == "__main__":
    raise SystemExit(main_with_preset(PRESET))
