"use client";
import React from "react";
import { 
  Card, 
  Title, 
  Text, 
  Button, 
  Tab, 
  TabGroup, 
  TabList, 
  TabPanel, 
  TabPanels 
} from "@tremor/react";

export default function FlowsPage() {
  return (
    <div className="w-full p-8">
      <div className="mb-8">
        <Title className="text-2xl font-bold mb-2">AI Flows</Title>
        <Text className="text-gray-600 dark:text-gray-400">
          Create, manage, and deploy AI workflows powered by Langflow.
        </Text>
      </div>

      <TabGroup>
        <TabList className="mb-8">
          <Tab>My Flows</Tab>
          <Tab>Templates</Tab>
          <Tab>Shared</Tab>
        </TabList>
        
        <TabPanels>
          <TabPanel>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4 flex items-center justify-center">
                  <Text className="text-gray-500">Create New Flow</Text>
                </div>
                <Title className="text-xl mb-2">New Flow</Title>
                <Text className="mb-4">Start building a new AI workflow from scratch.</Text>
                <Button size="sm" variant="primary" className="mt-2">Create Flow</Button>
              </Card>
              
              {/* This is a placeholder for demonstration - will be replaced with real data */}
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4"></div>
                <Title className="text-xl mb-2">Document Processing</Title>
                <Text className="mb-4">Extract, summarize, and analyze document content.</Text>
                <Button size="sm" variant="secondary" className="mt-2">Edit Flow</Button>
              </Card>
              
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4"></div>
                <Title className="text-xl mb-2">Custom Search Engine</Title>
                <Text className="mb-4">Vector search across your data sources.</Text>
                <Button size="sm" variant="secondary" className="mt-2">Edit Flow</Button>
              </Card>
            </div>
          </TabPanel>
          
          <TabPanel>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4"></div>
                <Title className="text-xl mb-2">RAG Pipeline</Title>
                <Text className="mb-4">Retrieval Augmented Generation workflow template.</Text>
                <Button size="sm" variant="secondary" className="mt-2">Use Template</Button>
              </Card>
              
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4"></div>
                <Title className="text-xl mb-2">Multi-Agent System</Title>
                <Text className="mb-4">Collaborative AI agents working together.</Text>
                <Button size="sm" variant="secondary" className="mt-2">Use Template</Button>
              </Card>
              
              <Card className="p-6 hover:shadow-md transition-all">
                <div className="h-40 bg-gray-100 dark:bg-gray-800 rounded-md mb-4"></div>
                <Title className="text-xl mb-2">Data Analysis</Title>
                <Text className="mb-4">Process and visualize data with AI assistance.</Text>
                <Button size="sm" variant="secondary" className="mt-2">Use Template</Button>
              </Card>
            </div>
          </TabPanel>
          
          <TabPanel>
            <div className="p-8 text-center">
              <Text className="text-lg text-gray-500">
                No shared flows yet. Flows shared with you will appear here.
              </Text>
            </div>
          </TabPanel>
        </TabPanels>
      </TabGroup>
      
      <div className="mt-12 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <Title className="text-lg mb-2">Coming Soon: Langflow Integration</Title>
        <Text>
          We're working on integrating Langflow to provide a powerful visual builder for creating AI workflows.
          Stay tuned for updates!
        </Text>
      </div>
    </div>
  );
}