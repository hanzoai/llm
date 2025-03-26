export interface ModelInfo {
  id: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  team_id: string;
  db_model: boolean;
}

export interface LLMParams {
  model: string;
  api_base?: string;
  input_cost_per_token?: number;
  output_cost_per_token?: number;
  custom_llm_provider?: string;
  llm_credential_name?: string;
  [key: string]: any;
}

export interface ModelData {
  model_info: ModelInfo;
  model_name: string;
  provider: string;
  llm_model_name: string;
  input_cost: number;
  output_cost: number;
  max_tokens: number;
  max_input_tokens: number;
  api_base?: string;
  llm_params: LLMParams;
  cleanedLLMParams: Record<string, any>;
  accessToken?: string;
}

export interface ModelDashboardProps {
  accessToken: string;
  token: string;
  userRole: string;
  userID: string;
  modelData: { data: ModelData[] };
  keys: any[];
  setModelData: (data: any) => void;
  premiumUser: boolean;
  teams: any[];
}
