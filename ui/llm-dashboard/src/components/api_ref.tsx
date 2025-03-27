"use client";
import React, { useEffect, useState } from "react";
import {
  Badge,
  Card,
  Table,
  Metric,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  Text,
  Title,
  Icon,
  Accordion,
  AccordionBody,
  AccordionHeader,
  List,
  ListItem,
  Tab,
  TabGroup,
  TabList,
  TabPanel,
  TabPanels,
  Grid,
} from "@tremor/react";
import { Statistic } from "antd"
import { modelAvailableCall }  from "./networking";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

interface ApiRefProps {
  proxySettings: any;
}


const APIRef: React.FC<ApiRefProps> = ({
  proxySettings,
}) => {

  let base_url = "<your_proxy_base_url>";

  if (proxySettings) {
    if (proxySettings.PROXY_BASE_URL && proxySettings.PROXY_BASE_URL !== undefined) {
      base_url = proxySettings.PROXY_BASE_URL;
    }
  }
    return (
        <>
         <Grid className="gap-2 p-8 h-[80vh] w-full mt-2">
        <div className="mb-5">
            <p className="text-2xl text-tremor-content-strong dark:text-dark-tremor-content-strong font-semibold">API Reference</p>        
            <Text className="mt-2 mb-2">Hanzo API is compatible with multiple SDKs and frameworks. Choose an SDK below to see examples:</Text>

                <TabGroup>
                  <TabList>
                    <Tab>Hanzo SDK</Tab>
                    <Tab>OpenAI SDK</Tab>
                    <Tab>LlamaIndex</Tab>
                    <Tab>Langchain</Tab>
                  </TabList>
                  <TabPanels>
                    <TabPanel>
                      <div className="mb-4">
                        <TabGroup>
                          <TabList className="mt-2">
                            <Tab>JavaScript/TypeScript</Tab>
                            <Tab>Python</Tab>
                            <Tab>Go</Tab>
                            <Tab>Ruby</Tab>
                            <Tab>Java</Tab>
                            <Tab>Kotlin</Tab>
                          </TabList>
                          <TabPanels>
                            <TabPanel>
                              <SyntaxHighlighter language="typescript">
                                {`
import { HanzoClient } from '@hanzo/sdk';

// Initialize the Hanzo client
const client = new HanzoClient({
  apiKey: 'your_api_key',
  baseUrl: '${base_url}'
});

async function main() {
  // Create a chat completion
  const response = await client.chat.completions.create({
    model: 'gpt-4',
    messages: [
      {
        role: 'user',
        content: 'Write a short poem about AI'
      }
    ]
  });

  console.log(response.choices[0].message.content);
}

main();
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="python">
                                {`
from hanzo import HanzoClient

# Initialize the Hanzo client
client = HanzoClient(
    api_key="your_api_key",
    base_url="${base_url}"
)

# Create a chat completion
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {
            "role": "user",
            "content": "Write a short poem about AI"
        }
    ]
)

print(response.choices[0].message.content)
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="go">
                                {`
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/hanzo/sdk-go"
)

func main() {
	// Initialize the Hanzo client
	client := hanzo.NewClient("your_api_key", "${base_url}")

	// Create a chat completion
	resp, err := client.CreateChatCompletion(
		context.Background(),
		hanzo.ChatCompletionRequest{
			Model: "gpt-4",
			Messages: []hanzo.Message{
				{
					Role:    "user",
					Content: "Write a short poem about AI",
				},
			},
		},
	)

	if err != nil {
		log.Fatalf("Error: %v", err)
	}

	fmt.Println(resp.Choices[0].Message.Content)
}
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="ruby">
                                {`
require 'hanzo'

# Initialize the Hanzo client
client = Hanzo::Client.new(
  api_key: 'your_api_key',
  base_url: '${base_url}'
)

# Create a chat completion
response = client.chat.completions.create(
  model: 'gpt-4',
  messages: [
    {
      role: 'user',
      content: 'Write a short poem about AI'
    }
  ]
)

puts response.choices[0].message.content
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="java">
                                {`
import ai.hanzo.client.HanzoClient;
import ai.hanzo.client.models.ChatCompletion;
import ai.hanzo.client.models.ChatCompletionRequest;
import ai.hanzo.client.models.Message;

import java.util.Arrays;

public class Example {
    public static void main(String[] args) {
        // Initialize the Hanzo client
        HanzoClient client = new HanzoClient.Builder()
            .setApiKey("your_api_key")
            .setBaseUrl("${base_url}")
            .build();

        // Create a chat completion
        ChatCompletionRequest request = new ChatCompletionRequest.Builder()
            .setModel("gpt-4")
            .setMessages(Arrays.asList(
                new Message("user", "Write a short poem about AI")
            ))
            .build();

        ChatCompletion response = client.createChatCompletion(request);
        System.out.println(response.getChoices().get(0).getMessage().getContent());
    }
}
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="kotlin">
                                {`
import ai.hanzo.client.HanzoClient
import ai.hanzo.client.models.ChatCompletionRequest
import ai.hanzo.client.models.Message

fun main() {
    // Initialize the Hanzo client
    val client = HanzoClient.Builder()
        .apiKey("your_api_key")
        .baseUrl("${base_url}")
        .build()

    // Create a chat completion
    val request = ChatCompletionRequest(
        model = "gpt-4",
        messages = listOf(
            Message(role = "user", content = "Write a short poem about AI")
        )
    )

    val response = client.createChatCompletion(request)
    println(response.choices[0].message.content)
}
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                          </TabPanels>
                        </TabGroup>
                      </div>
                    </TabPanel>
                    <TabPanel>
                      <div className="mb-4">
                        <TabGroup>
                          <TabList className="mt-2">
                            <Tab>JavaScript</Tab>
                            <Tab>Python</Tab>
                          </TabList>
                          <TabPanels>
                            <TabPanel>
                              <SyntaxHighlighter language="javascript">
                                {`
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: 'your_api_key',
  baseURL: '${base_url}'
});

async function main() {
  const response = await client.chat.completions.create({
    model: 'gpt-3.5-turbo',
    messages: [
      {
        role: 'user',
        content: 'this is a test request, write a short poem'
      }
    ]
  });

  console.log(response.choices[0].message.content);
}

main();
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="python">
                                {`
import openai
client = openai.OpenAI(
    api_key="your_api_key",
    base_url="${base_url}" # Hanzo API is OpenAI compatible
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo", # model to send to the proxy
    messages = [
        {
            "role": "user",
            "content": "this is a test request, write a short poem"
        }
    ]
)

print(response.choices[0].message.content)
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                          </TabPanels>
                        </TabGroup>
                      </div>
                    </TabPanel>
                    <TabPanel>
                      <div className="mb-4">
                        <TabGroup>
                          <TabList className="mt-2">
                            <Tab>JavaScript</Tab>
                            <Tab>Python</Tab>
                          </TabList>
                          <TabPanels>
                            <TabPanel>
                              <SyntaxHighlighter language="javascript">
                                {`
import { OpenAI } from "llamaindex";
import { VectorStoreIndex, SimpleDirectoryReader, ServiceContext } from "llamaindex";

const llm = new OpenAI({
  model: "gpt-3.5-turbo",
  temperature: 0,
  apiKey: "your_api_key",
  baseUrl: "${base_url}/v1"
});

async function main() {
  const documents = await new SimpleDirectoryReader().loadData("llamaindex_data");
  const serviceContext = ServiceContext.fromDefaults({ llm });
  const index = await VectorStoreIndex.fromDocuments(documents, { serviceContext });
  
  const queryEngine = index.asQueryEngine();
  const response = await queryEngine.query("What did the author do growing up?");
  
  console.log(response.toString());
}

main();
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="python">
                                {`
from llama_index.llms import OpenAI
from llama_index.embeddings import OpenAIEmbedding
from llama_index import VectorStoreIndex, SimpleDirectoryReader, ServiceContext

llm = OpenAI(
    model="gpt-3.5-turbo",
    temperature=0.0,
    api_base="${base_url}/v1",
    api_key="your_api_key",
)

embed_model = OpenAIEmbedding(
    model_name="text-embedding-ada-002",
    api_base="${base_url}/v1",
    api_key="your_api_key",
)

documents = SimpleDirectoryReader("llama_index_data").load_data()
service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)
index = VectorStoreIndex.from_documents(documents, service_context=service_context)

query_engine = index.as_query_engine()
response = query_engine.query("What did the author do growing up?")
print(response)
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                          </TabPanels>
                        </TabGroup>
                      </div>
                    </TabPanel>
                    <TabPanel>
                      <div className="mb-4">
                        <TabGroup>
                          <TabList className="mt-2">
                            <Tab>JavaScript</Tab>
                            <Tab>Python</Tab>
                          </TabList>
                          <TabPanels>
                            <TabPanel>
                              <SyntaxHighlighter language="javascript">
                                {`
import { ChatOpenAI } from "langchain/chat_models/openai";
import { HumanMessage, SystemMessage } from "langchain/schema";

const chat = new ChatOpenAI({
  openAIApiKey: "your_api_key",
  modelName: "gpt-3.5-turbo",
  temperature: 0.1,
  configuration: {
    baseURL: "${base_url}/v1",
  },
});

async function main() {
  const messages = [
    new SystemMessage(
      "You are a helpful assistant that I'm using to make a test request to."
    ),
    new HumanMessage(
      "Test from Hanzo. Tell me why it's amazing in 1 sentence."
    ),
  ];

  const response = await chat.call(messages);
  console.log(response.content);
}

main();
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                            <TabPanel>
                              <SyntaxHighlighter language="python">
                                {`
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

chat = ChatOpenAI(
    openai_api_base="${base_url}/v1",
    openai_api_key="your_api_key",
    model="gpt-3.5-turbo",
    temperature=0.1
)

messages = [
    SystemMessage(
        content="You are a helpful assistant that I'm using to make a test request to."
    ),
    HumanMessage(
        content="Test from Hanzo. Tell me why it's amazing in 1 sentence."
    ),
]
response = chat.invoke(messages)

print(response.content)
                                `}
                              </SyntaxHighlighter>
                            </TabPanel>
                          </TabPanels>
                        </TabGroup>
                      </div>
                    </TabPanel>
                  </TabPanels>
                </TabGroup>

        
        </div>
        </Grid>

        
    </>
    )
}

export default APIRef;

