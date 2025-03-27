#!/usr/bin/env python
"""
Script to scrape MCP server information from various sources and update the mcp_servers.json file.
"""

import os
import json
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, List
import argparse

# GitHub repositories that may contain MCP servers
GITHUB_REPOS = [
    "glama-ai/mcp-server-registry",  # Main repository for MCP servers
    "langchain-ai/langchain-contrib",  # May contain MCP-related tools
    "dagster-io/dagster-ai",  # May have MCP integrations
]

def scrape_glama_ai() -> Dict[str, Any]:
    """
    Scrape MCP server information from glama.ai
    """
    print("Scraping MCP server information from glama.ai...")
    
    try:
        response = requests.get("https://glama.ai/mcp-servers")
        if response.status_code != 200:
            print(f"Failed to retrieve data from glama.ai: {response.status_code}")
            return {}
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find MCP server entries
        servers = {}
        
        # This is a placeholder since we can't actually access the site
        # The real implementation would locate and extract server information
        server_elements = soup.find_all(class_="mcp-server-entry")
        
        for server_element in server_elements:
            try:
                name = server_element.find(class_="server-name").text.strip()
                description = server_element.find(class_="server-description").text.strip()
                command = server_element.find(class_="server-command").text.strip()
                
                # Parse arguments and environment variables
                args_text = server_element.find(class_="server-args").text.strip()
                args = [arg.strip() for arg in args_text.split(" ") if arg.strip()]
                
                env_vars = {}
                env_elements = server_element.find_all(class_="server-env-var")
                for env_element in env_elements:
                    var_name = env_element.find(class_="var-name").text.strip()
                    var_value = env_element.find(class_="var-value").text.strip()
                    env_vars[var_name] = var_value
                
                servers[name] = {
                    "description": description,
                    "command": command,
                    "args": args,
                    "env": env_vars
                }
            except Exception as e:
                print(f"Error parsing server element: {e}")
                continue
        
        return servers
        
    except Exception as e:
        print(f"Error scraping glama.ai: {e}")
        return {}

def scrape_github_repos() -> Dict[str, Any]:
    """
    Scrape MCP server information from GitHub repositories
    """
    print("Scraping MCP server information from GitHub repositories...")
    
    all_servers = {}
    
    for repo in GITHUB_REPOS:
        try:
            # Get repository contents
            repo_url = f"https://github.com/{repo}"
            api_url = f"https://api.github.com/repos/{repo}/contents"
            
            response = requests.get(api_url)
            if response.status_code != 200:
                print(f"Failed to retrieve data from {repo}: {response.status_code}")
                continue
                
            contents = response.json()
            
            # Look for server definition files
            for item in contents:
                if item["type"] == "file" and (item["name"].endswith(".json") or item["name"].endswith(".yaml") or item["name"].endswith(".yml")):
                    file_url = item["download_url"]
                    file_response = requests.get(file_url)
                    
                    if file_response.status_code != 200:
                        continue
                        
                    # Try to parse as JSON
                    try:
                        if item["name"].endswith(".json"):
                            servers = json.loads(file_response.text)
                            all_servers.update(servers)
                        # TODO: Add YAML parsing if needed
                    except Exception as e:
                        print(f"Error parsing {file_url}: {e}")
                        continue
                        
            # Look for server directories
            server_dirs = [item for item in contents if item["type"] == "dir" and "mcp" in item["name"].lower()]
            
            for server_dir in server_dirs:
                try:
                    dir_url = f"{api_url}/{server_dir['name']}"
                    dir_response = requests.get(dir_url)
                    
                    if dir_response.status_code != 200:
                        continue
                        
                    dir_contents = dir_response.json()
                    
                    # Look for Dockerfile or docker-compose.yml
                    docker_files = [item for item in dir_contents if item["type"] == "file" and 
                                    (item["name"] == "Dockerfile" or item["name"] == "docker-compose.yml")]
                    
                    if docker_files:
                        server_name = server_dir["name"].lower().replace("-", "_")
                        
                        # Extract environment variables from Dockerfile
                        env_vars = {}
                        
                        for docker_file in docker_files:
                            file_url = docker_file["download_url"]
                            file_response = requests.get(file_url)
                            
                            if file_response.status_code != 200:
                                continue
                                
                            # Extract ENV statements from Dockerfile
                            if docker_file["name"] == "Dockerfile":
                                env_matches = re.findall(r'ENV\s+(\w+)(?:\s+|=)([^\s]+)', file_response.text)
                                for var_name, var_value in env_matches:
                                    env_vars[var_name] = var_value
                        
                        # Create a server entry
                        all_servers[server_name] = {
                            "command": "docker",
                            "args": ["run", "-i", "--rm"] + [f"-e {var}" for var in env_vars.keys()] + [f"mcp/{server_name}"],
                            "env": env_vars
                        }
                except Exception as e:
                    print(f"Error processing directory {server_dir['name']}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error scraping {repo}: {e}")
            continue
            
    return all_servers

def scrape_npm_packages() -> Dict[str, Any]:
    """
    Scrape MCP server information from NPM packages
    """
    print("Scraping MCP server information from NPM packages...")
    
    servers = {}
    
    try:
        # Search for MCP-related packages
        search_url = "https://registry.npmjs.org/-/v1/search?text=mcp-server&size=100"
        response = requests.get(search_url)
        
        if response.status_code != 200:
            print(f"Failed to search NPM packages: {response.status_code}")
            return {}
            
        results = response.json()["objects"]
        
        for result in results:
            try:
                package = result["package"]
                name = package["name"]
                
                # Skip packages that don't look like MCP servers
                if not ("mcp" in name.lower() and "server" in name.lower()):
                    continue
                    
                # Get package details
                package_url = f"https://registry.npmjs.org/{name}/latest"
                package_response = requests.get(package_url)
                
                if package_response.status_code != 200:
                    continue
                    
                package_data = package_response.json()
                
                # Check if it has an MCP server configuration
                if "mcpConfig" in package_data:
                    mcp_config = package_data["mcpConfig"]
                    server_name = name.split("/")[-1].replace("-", "_")
                    
                    servers[server_name] = {
                        "command": "npx",
                        "args": [name],
                        "env": mcp_config.get("env", {})
                    }
            except Exception as e:
                print(f"Error processing package {name}: {e}")
                continue
                
    except Exception as e:
        print(f"Error scraping NPM packages: {e}")
        
    return servers

def merge_servers(existing_servers: Dict[str, Any], new_servers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge existing servers with newly scraped servers
    """
    merged = existing_servers.copy()
    
    for name, config in new_servers.items():
        if name in merged:
            # Update existing server with new information if available
            for key, value in config.items():
                if value and (key not in merged[name] or not merged[name][key]):
                    merged[name][key] = value
        else:
            # Add new server
            merged[name] = config
            
    return merged

def main():
    parser = argparse.ArgumentParser(description="Scrape MCP server information and update mcp_servers.json")
    parser.add_argument("--output", default=None, help="Path to output JSON file (default: mcp_servers.json in project root)")
    args = parser.parse_args()
    
    # Determine the output file path
    if args.output:
        output_path = args.output
    else:
        # Find the project root by locating the mcp_servers.json file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)  # Assuming scripts is a direct subdirectory of the project root
        output_path = os.path.join(project_root, "mcp_servers.json")
    
    # Load existing servers
    existing_servers = {}
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                existing_servers = json.load(f)
            print(f"Loaded {len(existing_servers)} existing MCP servers from {output_path}")
        except Exception as e:
            print(f"Error loading existing servers: {e}")
    
    # Scrape new servers
    servers_from_glama = scrape_glama_ai()
    servers_from_github = scrape_github_repos()
    servers_from_npm = scrape_npm_packages()
    
    # Merge all servers
    all_servers = existing_servers
    all_servers = merge_servers(all_servers, servers_from_glama)
    all_servers = merge_servers(all_servers, servers_from_github)
    all_servers = merge_servers(all_servers, servers_from_npm)
    
    # Add a new example server if we didn't find any
    if len(all_servers) <= len(existing_servers):
        print("No new servers found. Adding example servers.")
        
        # Example: Brave Search MCP server
        all_servers["brave_search"] = {
            "command": "docker",
            "args": [
                "run",
                "-i",
                "--rm",
                "-e",
                "BRAVE_API_KEY",
                "mcp/brave-search"
            ],
            "env": {
                "BRAVE_API_KEY": "YOUR_API_KEY_HERE"
            }
        }
        
        # Example: Web Scraper MCP server
        all_servers["web_scraper"] = {
            "command": "npx",
            "args": [
                "@mcp/web-scraper"
            ],
            "env": {
                "SCRAPER_TIMEOUT": "30000",
                "MAX_DEPTH": "2"
            }
        }
    
    # Save the updated servers
    try:
        with open(output_path, 'w') as f:
            json.dump(all_servers, f, indent=4, sort_keys=True)
        print(f"Saved {len(all_servers)} MCP servers to {output_path}")
    except Exception as e:
        print(f"Error saving servers: {e}")
    
if __name__ == "__main__":
    main()