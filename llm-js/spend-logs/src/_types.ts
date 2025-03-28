export type LLM_IncrementSpend = {
    key_transactions: Array<LLM_IncrementObject>, // [{"key": spend},..]
    user_transactions: Array<LLM_IncrementObject>, 
    team_transactions: Array<LLM_IncrementObject>,
    spend_logs_transactions: Array<LLM_SpendLogs>
}

export type LLM_IncrementObject = {
    key: string,
    spend: number
}

export type LLM_SpendLogs = {
    request_id: string; // @id means it's a unique identifier
    call_type: string;
    api_key: string; // @default("") means it defaults to an empty string if not provided
    spend: number; // Float in Prisma corresponds to number in TypeScript
    total_tokens: number; // Int in Prisma corresponds to number in TypeScript
    prompt_tokens: number;
    completion_tokens: number;
    startTime: Date; // DateTime in Prisma corresponds to Date in TypeScript
    endTime: Date;
    model: string; // @default("") means it defaults to an empty string if not provided
    api_base: string;
    user: string;
    metadata: any; // Json type in Prisma is represented by any in TypeScript; could also use a more specific type if the structure of JSON is known
    cache_hit: string;
    cache_key: string;
    request_tags: any; // Similarly, this could be an array or a more specific type depending on the expected structure
    team_id?: string | null; // ? indicates it's optional and can be undefined, but could also be null if not provided
    end_user?: string | null;
};