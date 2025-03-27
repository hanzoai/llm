import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { 
  getConfigFieldSetting, 
  updateConfigFieldSetting, 
  mcpServerCall, 
  getMCPServerUsageStats,
  updateMCPServerConfig
} from "./networking";
import {
  Card,
  Text,
  Title,
  Button,
  Tab,
  TabGroup,
  TabList,
  TabPanel,
  TabPanels,
  Badge,
} from "@tremor/react";
import { 
  RightOutlined, 
  CopyOutlined, 
  PoweroffOutlined,
  ReloadOutlined
} from "@ant-design/icons";

import { Modal, Tooltip, Switch, message } from "antd";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

interface MCPServerHubProps {
  accessToken: string | null;
  publicPage: boolean;
  premiumUser: boolean;
}

interface MCPServerInfo {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
  enabled: boolean;
}

interface MCPServerUsageStats {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_duration_ms: number;
  average_duration_ms: number;
  input_tokens: number;
  output_tokens: number;
}

const MCPServerHub: React.FC<MCPServerHubProps> = ({
  accessToken,
  publicPage,
  premiumUser,
}) => {
  const [publicPageAllowed, setPublicPageAllowed] = useState<boolean>(false);
  const [mcpServerData, setMCPServerData] = useState<MCPServerInfo[] | null>(null);
  const [mcpServerUsage, setMCPServerUsage] = useState<Record<string, MCPServerUsageStats>>({});
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isPublicPageModalVisible, setIsPublicPageModalVisible] = useState(false);
  const [selectedServer, setSelectedServer] = useState<null | MCPServerInfo>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isTogglingServer, setIsTogglingServer] = useState<string | null>(null);
  const router = useRouter();

  const fetchServers = async () => {
    setLoading(true);
    try {
      if (accessToken) {
        const data = await mcpServerCall(accessToken);
        // Transform the data from object to array format
        const serversArray = Object.entries(data).map(([name, config]: [string, any]) => ({
          name,
          ...config,
        }));
        
        setMCPServerData(serversArray);
        
        // Fetch usage statistics if admin
        try {
          const usageStats = await getMCPServerUsageStats(accessToken);
          setMCPServerUsage(usageStats);
        } catch (error) {
          // Not admin or other error - continue without usage stats
        }
      } else {
        // Public access without token
        const response = await fetch("/api/mcps", {
          headers: {
            "Accept": "application/json"
          }
        });

        if (response.ok) {
          const data = await response.json();
          // Transform the data from object to array format
          const serversArray = Object.entries(data).map(([name, config]: [string, any]) => ({
            name,
            ...config,
          }));
          
          setMCPServerData(serversArray);
        }
      }
    } catch (error) {
      console.error("There was an error fetching the MCP server data", error);
      message.error("Failed to load MCP servers");
    } finally {
      setLoading(false);
    }
  };
  
  const checkPublicAccess = async () => {
    // Always allow public access
    setPublicPageAllowed(true);
  };
  
  const toggleServerStatus = async (serverName: string, enabled: boolean) => {
    if (!accessToken) return;
    
    setIsTogglingServer(serverName);
    try {
      await updateMCPServerConfig(accessToken, serverName, { enabled });
      
      // Update the local state
      setMCPServerData(prev => {
        if (!prev) return null;
        
        return prev.map(server => {
          if (server.name === serverName) {
            return { ...server, enabled };
          }
          return server;
        });
      });
      
      message.success(`MCP server ${serverName} ${enabled ? 'enabled' : 'disabled'} successfully`);
    } catch (error) {
      console.error(`Failed to ${enabled ? 'enable' : 'disable'} MCP server:`, error);
      message.error(`Failed to ${enabled ? 'enable' : 'disable'} MCP server ${serverName}`);
    } finally {
      setIsTogglingServer(null);
    }
  };

  useEffect(() => {
    // Fetch MCP server data from the API
    fetchServers();
    checkPublicAccess();
  }, [accessToken, publicPage]);

  const showModal = (server: MCPServerInfo) => {
    setSelectedServer(server);
    setIsModalVisible(true);
  };

  const goToPublicMCPPage = () => {
    router.replace(`/mcp_servers?key=${accessToken}`);
  };

  const handleMakePublicPage = async () => {
    if (!accessToken) {
      return;
    }
    updateConfigFieldSetting(accessToken, "enable_public_mcp_hub", true).then(
      (data) => {
        setIsPublicPageModalVisible(true);
      }
    );
  };

  const handleOk = () => {
    setIsModalVisible(false);
    setIsPublicPageModalVisible(false);
    setSelectedServer(null);
  };

  const handleCancel = () => {
    setIsModalVisible(false);
    setIsPublicPageModalVisible(false);
    setSelectedServer(null);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const formatLaunchCommand = (server: MCPServerInfo) => {
    return `${server.command} ${server.args.join(' ')}`;
  };

  return (
    <div>
      {(publicPage && publicPageAllowed) || publicPage === false ? (
        <div className="w-full m-2 mt-2 p-8">
          <div className="relative w-full"></div>

          <div className={`flex ${publicPage ? "justify-between" : "items-center"}`}>
            <div className="flex items-center">
              <Title className="ml-8 text-center">Model Context Protocol (MCP) Servers</Title>
              <Tooltip title="Refresh server list">
                <Button 
                  size="xs" 
                  variant="light" 
                  icon={<ReloadOutlined />}
                  className="ml-2" 
                  onClick={fetchServers}
                  disabled={loading}
                />
              </Tooltip>
              {loading && <span className="ml-2 text-xs text-gray-500">Loading...</span>}
            </div>
            
            {publicPage === false ? (
              <div></div> // "Make Public" button hidden as requested - MCP is always public
            ) : (
              <div className="flex justify-between items-center">
                <p>Filter by key:</p>
                <Text className="bg-gray-200 pr-2 pl-2 pt-1 pb-1 text-center">{`/ui/mcp_servers?key=<YOUR_KEY>`}</Text>
              </div>
            )}
          </div>

          <div className="mb-8 ml-8 mt-2">
            <Text>
              MCP servers extend your AI assistants with powerful tools and capabilities. 
              Use these servers with OpenAI's Assistants API or Anthropic's Claude to add specialized functionality.
            </Text>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 pr-8">
            {mcpServerData &&
              mcpServerData.map((server: MCPServerInfo) => (
                <Card key={server.name} className={`mt-5 mx-8 ${!server.enabled ? 'opacity-60 hover:opacity-80' : 'hover:shadow-md'}`}>
                  <div className="flex justify-between">
                    <div>
                      <Title className="text-wrap flex items-center gap-2">
                        {server.name}
                        {!server.enabled && (
                          <Badge size="xs" color="red">Disabled</Badge>
                        )}
                        {server.enabled && (
                          <Badge size="xs" color="green">Enabled</Badge>
                        )}
                      </Title>
                    </div>
                    <div className="flex items-center">
                      {!publicPage && accessToken && (
                        <Tooltip title={server.enabled ? "Disable server" : "Enable server"}>
                          <Switch
                            size="small"
                            className="mr-2"
                            checked={server.enabled}
                            loading={isTogglingServer === server.name}
                            onChange={(checked) => toggleServerStatus(server.name, checked)}
                          />
                        </Tooltip>
                      )}
                      <Tooltip title="Copy name">
                        <CopyOutlined
                          onClick={() => copyToClipboard(server.name)}
                          style={{ cursor: "pointer", marginRight: "10px" }}
                        />
                      </Tooltip>
                    </div>
                  </div>
                  
                  <div className="my-4">
                    <div className="flex items-center mb-2">
                      <div className="w-3 h-3 rounded-full mr-2" 
                           style={{ backgroundColor: server.enabled ? '#4ade80' : '#f87171' }}></div>
                      <Text className="font-semibold">
                        {server.enabled ? 'Available' : 'Unavailable'}
                      </Text>
                    </div>
                    <Text className="block mb-2">
                      <span className="font-medium">Runtime:</span> {server.command}
                    </Text>
                    {Object.keys(server.env).length > 0 && (
                      <Text className="block mb-1">
                        <span className="font-medium">Required Keys:</span> {Object.keys(server.env).join(", ")}
                      </Text>
                    )}
                    
                    {mcpServerUsage[server.name] && (
                      <div className="mt-3 text-xs text-gray-500">
                        <div className="flex justify-between">
                          <span>Total calls:</span>
                          <span className="font-medium">{mcpServerUsage[server.name].total_calls}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Success rate:</span>
                          <span className="font-medium">
                            {mcpServerUsage[server.name].total_calls > 0 
                              ? `${Math.round(mcpServerUsage[server.name].successful_calls / mcpServerUsage[server.name].total_calls * 100)}%` 
                              : 'N/A'}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span>Avg. duration:</span>
                          <span className="font-medium">
                            {mcpServerUsage[server.name].average_duration_ms > 0 
                              ? `${Math.round(mcpServerUsage[server.name].average_duration_ms)}ms` 
                              : 'N/A'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-4 pt-2 border-t border-gray-100 flex justify-between items-center">
                    <Tooltip title="View usage examples">
                      <Button 
                        size="small" 
                        className="text-xs"
                        onClick={() => showModal(server)}
                      >
                        Usage Examples
                      </Button>
                    </Tooltip>
                    <a
                      href="#"
                      onClick={() => showModal(server)}
                      className="text-blue-500 hover:text-blue-700 text-xs flex items-center"
                    >
                      Details <RightOutlined style={{ fontSize: '10px', marginLeft: '4px' }} />
                    </a>
                  </div>
                </Card>
              ))}
          </div>
          
          {!mcpServerData || mcpServerData.length === 0 ? (
            <div className="text-center mt-10">
              <Text className="text-gray-500">No MCP servers found. Contact your administrator to set up MCP servers.</Text>
            </div>
          ) : null}
        </div>
      ) : (
        <Card className="mx-auto max-w-xl mt-10">
          <Text className="text-xl text-center mb-2 text-black">
            Public MCP Server Hub not enabled.
          </Text>
          <p className="text-base text-center text-slate-800">
            Ask your proxy admin to enable this on their Admin UI.
          </p>
        </Card>
      )}

      <Modal
        title={"Public MCP Server Hub"}
        width={600}
        visible={isPublicPageModalVisible}
        footer={null}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        <div className="pt-5 pb-5">
          <div className="flex justify-between mb-4">
            <Text className="text-base mr-2">Shareable Link:</Text>
            <Text className="max-w-sm ml-2 bg-gray-200 pr-2 pl-2 pt-1 pb-1 text-center rounded">{`<proxy_base_url>/ui/mcp_servers?key=<YOUR_API_KEY>`}</Text>
          </div>
          <div className="flex justify-end">
            <Button onClick={goToPublicMCPPage}>See Page</Button>
          </div>
        </div>
      </Modal>
      
      <Modal
        title={
          selectedServer
            ? `MCP Server: ${selectedServer.name}`
            : "Unknown Server"
        }
        width={800}
        visible={isModalVisible}
        footer={null}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        {selectedServer && (
          <div>
            <div className="mb-4 flex items-center">
              <div className="w-4 h-4 rounded-full mr-2" 
                   style={{ backgroundColor: selectedServer.enabled ? '#4ade80' : '#f87171' }}></div>
              <Text className="font-semibold mr-2">
                {selectedServer.enabled ? 'Available' : 'Unavailable'}
              </Text>
              <Text className="text-gray-500 text-sm">
                {selectedServer.enabled ? 
                  'This MCP server is enabled and ready to use.' : 
                  'This MCP server is currently disabled and not available for use.'}
              </Text>
            </div>

            <TabGroup>
              <TabList>
                <Tab>Server Information</Tab>
                <Tab>OpenAI Assistants</Tab>
                <Tab>Anthropic Claude</Tab>
                <Tab>Installation</Tab>
                <Tab>Direct API</Tab>
              </TabList>
              <TabPanels>
                <TabPanel>
                  <div className="space-y-4">
                    <div className="flex items-center p-3 bg-blue-50 rounded">
                      <div className="flex-shrink-0 mr-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
                          <circle cx="12" cy="12" r="10"></circle>
                          <line x1="12" y1="16" x2="12" y2="12"></line>
                          <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                      </div>
                      <p className="text-sm text-blue-700">
                        MCP Servers enable you to extend your AI assistants with specialized tools and capabilities.
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4">
                      <div className="col-span-1 font-medium text-gray-700">Server Name:</div>
                      <div className="col-span-2">{selectedServer.name}</div>
                      
                      <div className="col-span-1 font-medium text-gray-700">Launch Command:</div>
                      <div className="col-span-2 flex items-center">
                        <code className="bg-gray-100 p-1 rounded text-sm mr-2">
                          {formatLaunchCommand(selectedServer)}
                        </code>
                        <Tooltip title="Copy command">
                          <CopyOutlined
                            onClick={() => copyToClipboard(formatLaunchCommand(selectedServer))}
                            style={{ cursor: "pointer" }}
                          />
                        </Tooltip>
                      </div>
                      
                      <div className="col-span-1 font-medium text-gray-700">Status:</div>
                      <div className="col-span-2">{selectedServer.enabled ? 'Enabled' : 'Disabled'}</div>
                    </div>
                    
                    {Object.keys(selectedServer.env).length > 0 && (
                      <div className="mt-4 border-t pt-4">
                        <h3 className="font-medium text-gray-700 mb-2">Required Environment Variables:</h3>
                        <div className="bg-gray-50 p-3 rounded">
                          <table className="min-w-full">
                            <thead className="bg-gray-100">
                              <tr>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Variable</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Default Value</th>
                                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                              {Object.entries(selectedServer.env).map(([key, value]) => (
                                <tr key={key}>
                                  <td className="px-4 py-2 whitespace-nowrap text-sm font-medium">{key}</td>
                                  <td className="px-4 py-2 whitespace-nowrap text-sm">{value === "YOUR_API_KEY_HERE" ? <span className="text-gray-400">Not set</span> : value}</td>
                                  <td className="px-4 py-2 text-sm">{value === "YOUR_API_KEY_HERE" ? "API key required from provider" : "Configuration value"}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </TabPanel>
                <TabPanel>
                  <div className="mb-3 p-3 bg-yellow-50 rounded">
                    <p className="text-sm text-yellow-700">
                      This example shows how to use the {selectedServer.name} server with OpenAI's Assistants API.
                    </p>
                  </div>
                  <SyntaxHighlighter language="python">
                    {`
from openai import OpenAI
from openai.types.beta.assistant import Tool
from openai.types.beta.assistant_create_params import ToolResources

# Initialize the OpenAI client with Hanzo
client = OpenAI(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai/v1"
)

# Create an assistant with this MCP tool
assistant = client.beta.assistants.create(
    name="${selectedServer.name} Assistant",
    model="gpt-4-turbo",
    tools=[
        {
            "type": "function",
            "function": {
                "name": "${selectedServer.name}",
                "description": "Use ${selectedServer.name} MCP server",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Input query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
)

# Run the assistant
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Use ${selectedServer.name} to help me with my task"
)

run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

# Get the results when the run completes
import time
while True:
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )
    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        for msg in messages.data:
            if msg.role == "assistant":
                print(f"Assistant: {msg.content[0].text.value}")
        break
    elif run.status in ["failed", "cancelled", "expired"]:
        print(f"Run {run.status}")
        break
    time.sleep(1)
                    `}
                  </SyntaxHighlighter>
                </TabPanel>
                <TabPanel>
                  <div className="mb-3 p-3 bg-indigo-50 rounded">
                    <p className="text-sm text-indigo-700">
                      This example shows how to use the {selectedServer.name} server with Anthropic's Claude API.
                    </p>
                  </div>
                  <SyntaxHighlighter language="python">
                    {`
from anthropic import Anthropic

# Initialize the Anthropic client with Hanzo
anthropic = Anthropic(
    api_key="your_hanzo_api_key",
    base_url="https://api.hanzo.ai/v1"
)

# Create a message with the tool
message = anthropic.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": "Use the ${selectedServer.name} tool to help me with my task"
        }
    ],
    tools=[
        {
            "name": "${selectedServer.name}",
            "description": "Use ${selectedServer.name} MCP server",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Input query"
                    }
                },
                "required": ["query"]
            }
        }
    ]
)

print(message.content)
                    `}
                  </SyntaxHighlighter>
                </TabPanel>
                <TabPanel>
                  <div className="mb-3 p-3 bg-green-50 rounded">
                    <p className="text-sm text-green-700">
                      Follow these steps to run the {selectedServer.name} server locally.
                    </p>
                  </div>
                  <SyntaxHighlighter language="bash">
                    {`
# Step 1: Set up environment variables
${Object.entries(selectedServer.env).map(([key, value]) => 
  `export ${key}=${value === "YOUR_API_KEY_HERE" ? "your_api_key_here" : value}`
).join('\n')}

# Step 2: Run the server
${formatLaunchCommand(selectedServer)}

# The server will start and be available at:
# http://localhost:8000
                    `}
                  </SyntaxHighlighter>
                  
                  <div className="mt-4">
                    <h3 className="font-medium mb-2">Docker Installation</h3>
                    <SyntaxHighlighter language="bash">
                      {`
# Pull the Docker image
docker pull mcp/${selectedServer.name}

# Run the container with environment variables
docker run -i --rm ${Object.entries(selectedServer.env).map(([key, value]) => 
  `-e ${key}=${value === "YOUR_API_KEY_HERE" ? "your_api_key_here" : value}`
).join(' ')} mcp/${selectedServer.name}
                      `}
                    </SyntaxHighlighter>
                  </div>
                </TabPanel>
                <TabPanel>
                  <div className="mb-3 p-3 bg-purple-50 rounded">
                    <p className="text-sm text-purple-700">
                      You can call the {selectedServer.name} server directly using the Functions API.
                    </p>
                  </div>
                  <SyntaxHighlighter language="python">
                    {`
import requests

# Call function directly using the v1/functions API
response = requests.post(
    "https://api.hanzo.ai/v1/functions/${selectedServer.name}/call",
    headers={
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    },
    json={
        "arguments": {
            "query": "your query here"
        }
    }
)

# Print the result
print(response.json())
                    `}
                  </SyntaxHighlighter>
                  
                  <div className="mt-4">
                    <h3 className="font-medium mb-2">JavaScript/TypeScript Example</h3>
                    <SyntaxHighlighter language="javascript">
                      {`
// Using fetch
const callFunction = async () => {
  const response = await fetch('https://api.hanzo.ai/v1/functions/${selectedServer.name}/call', {
    method: 'POST',
    headers: {
      'Authorization': 'Bearer YOUR_API_KEY',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      arguments: {
        query: 'your query here'
      }
    })
  });
  
  const data = await response.json();
  console.log(data);
};

callFunction();
                      `}
                    </SyntaxHighlighter>
                  </div>
                </TabPanel>
              </TabPanels>
            </TabGroup>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default MCPServerHub;