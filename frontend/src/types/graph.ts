export interface GraphNodeData {
  id: string;
  label?: string;
  title?: string;
  type?: string;
  degree?: number;
  community?: number;
  community_levels?: Record<string | number, number>;
  date?: string;
  tags?: string[];
  description?: string;
  [key: string]: any;
}

export interface GraphNode {
  data: GraphNodeData;
  position?: { x: number; y: number };
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  label?: string;
  predicate?: string;
  description?: string;
  weight?: number;
  confidence?: number;
  [key: string]: any;
}

export interface GraphEdge {
  data: GraphEdgeData;
}

export interface Community {
  id: number;
  level: number;
  parent_id?: number | null;
  name: string;
  node_ids: string[];
  summary?: string | null;
  findings?: string[];
  themes?: string[];
  confidence?: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphStats {
  nodes_count: number;
  edges_count: number;
  communities_count: number;
  density: number;
  connectivity?: string;
  [key: string]: any;
}
