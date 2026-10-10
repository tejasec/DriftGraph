export interface GodNode {
  id: string;
  name: string;
  type: string;
  degree: number;
  pagerank: number;
  betweenness: number;
  hub_score: number;
  explanation: string;
}

export interface PathStep {
  source: string;
  relation: string;
  target: string;
  weight: number;
}

export interface PathResult {
  source: string;
  target: string;
  path_found: boolean;
  hops: number;
  node_sequence: string[];
  steps: PathStep[];
  narrative: string;
}

export interface SurprisingConnection {
  source_name: string;
  source_type: string;
  target_name: string;
  target_type: string;
  relation: string;
  source_community_id?: any;
  target_community_id?: any;
  rationale: string;
}

export interface SuggestedQuestion {
  question: string;
  category: string;
  entities_involved: string[];
  rationale: string;
}

export interface GraphAnalyticsReport {
  node_count: number;
  edge_count: number;
  community_count: number;
  density: number;
  is_connected: boolean;
  god_nodes: GodNode[];
  top_relations: Array<{ relation: string; count: number; [key: string]: any }>;
  surprising_connections: SurprisingConnection[];
  suggested_questions: SuggestedQuestion[];
}
