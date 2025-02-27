import React, { useEffect } from "react";
import { Form, Table, Input } from "antd";
import { Text, TextInput } from "@tremor/react";
import { Row, Col } from "antd";

const ConditionalPublicModelName: React.FC = () => {
  // Access the form instance
  const form = Form.useFormInstance();

  // Watch the 'model' field for changes and ensure it's always an array
  const modelValue = Form.useWatch('model', form) || [];
  const selectedModels = Array.isArray(modelValue) ? modelValue : [modelValue];
  const customModelName = Form.useWatch('custom_model_name', form);
  const showPublicModelName = !selectedModels.includes('all-wildcard');

  // Update model mappings immediately when custom model name changes
  const handleCustomModelNameChange = (value: string) => {
    if (selectedModels.includes('custom') && value) {
      const currentMappings = form.getFieldValue('model_mappings') || [];
      const updatedMappings = currentMappings.map((mapping: any) => {
        if (mapping.public_name === 'custom' || 
            (mapping.public_name !== value && mapping.litellm_model !== value && 
             mapping.public_name === mapping.litellm_model)) {
          return {
            public_name: value,
            litellm_model: value
          };
        }
        return mapping;
      });
      form.setFieldValue('model_mappings', updatedMappings);
    }
  };

  // Listen for changes to the custom_model_name field
  useEffect(() => {
    const unsubscribe = form.getFieldInstance('custom_model_name')?.addEventListener('input', (e: any) => {
      handleCustomModelNameChange(e.target.value);
    });
    
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, [form]);

  // Initial setup of model mappings when models are selected
  useEffect(() => {
    if (selectedModels.length > 0 && !selectedModels.includes('all-wildcard')) {
      const mappings = selectedModels.map((model: string) => {
        if (model === 'custom' && customModelName) {
          return {
            public_name: customModelName,
            litellm_model: customModelName
          };
        }
        return {
          public_name: model,
          litellm_model: model
        };
      });
      form.setFieldValue('model_mappings', mappings);
    }
  }, [selectedModels, form]);

  if (!showPublicModelName) return null;

  const columns = [
    {
      title: 'Public Name',
      dataIndex: 'public_name',
      key: 'public_name',
      render: (text: string, record: any, index: number) => {
        return (
          <TextInput
            value={text}
            onChange={(e) => {
              const newMappings = [...form.getFieldValue('model_mappings')];
              newMappings[index].public_name = e.target.value;
              form.setFieldValue('model_mappings', newMappings);
            }}
          />
        );
      }
    },
    {
      title: 'LiteLLM Model',
      dataIndex: 'litellm_model',
      key: 'litellm_model',
    }
  ];

  return (
    <>
      <Form.Item
        label="Model Mappings"
        name="model_mappings"
        tooltip="Map public model names to LiteLLM model names for load balancing"
        labelCol={{ span: 10 }}
        wrapperCol={{ span: 16 }}
        labelAlign="left"
        required={true}
      >
        <Table 
          dataSource={form.getFieldValue('model_mappings')} 
          columns={columns} 
          pagination={false}
          size="small"
        />
      </Form.Item>
      <Row>
        <Col span={10}></Col>
        <Col span={10}>
          <Text className="mb-2">
            Model name your users will pass in.
          </Text>
        </Col>
      </Row>
    </>
  );
};

export default ConditionalPublicModelName;